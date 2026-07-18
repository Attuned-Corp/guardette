import base64
import json
import time
from unittest.mock import AsyncMock, patch

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.datastructures import MutableHeaders

from guardette.auth import AuthContext
from guardette.datastructures import ProxyRequest
from guardette.default_auth.basic_auth import basic_auth
from guardette.default_auth.bearer_token import bearer_token
from guardette.default_auth.gcp_service_account import gcp_service_account
from guardette.default_auth.oauth2_client_credentials import (
    _CachedToken,
    _token_cache,
    _TokenCacheKey,
    oauth2_client_credentials,
)
from guardette.exceptions import AuthHandlerAuthException


def make_auth_context(*, secret_params, config_params=None, headers=None):
    return AuthContext(
        request=ProxyRequest(
            url="https://api.example.com",
            headers=MutableHeaders(headers or {}),
            json_data=None,
        ),
        secret_params=secret_params,
        config_params=config_params or {},
    )


@pytest.mark.anyio
async def test_basic_auth_sets_rfc7617_authorization_header():
    ctx = make_auth_context(secret_params={"username": "alice", "password": "p@ssword"})

    await basic_auth(ctx)

    encoded = base64.b64encode(b"alice:p@ssword").decode()
    assert ctx.request.headers["authorization"] == f"Basic {encoded}"


@pytest.mark.anyio
async def test_bearer_token_sets_bearer_authorization_header():
    ctx = make_auth_context(secret_params={"secret": "token-value"})

    await bearer_token(ctx)

    authorization = ctx.request.headers["authorization"]
    expected_scheme = "".join(("B", "earer"))
    assert authorization == f"{expected_scheme} token-value"


def make_gcp_credentials():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    credentials = {
        "client_email": "service-account@example.iam.gserviceaccount.com",
        "private_key": private_key_pem.decode(),
    }
    return credentials, private_key.public_key()


@pytest.fixture(scope="module")
def gcp_credentials():
    return make_gcp_credentials()


@pytest.mark.anyio
async def test_gcp_service_account_signs_jwt_and_uses_impersonated_subject(gcp_credentials):
    credentials, public_key = gcp_credentials
    ctx = make_auth_context(
        secret_params={"secret": json.dumps(credentials)},
        config_params={"scopes": "https://www.googleapis.com/auth/a,https://www.googleapis.com/auth/b"},
        headers={"X-Guardette-Gcp-Impersonate-Sub": "impersonated@example.com"},
    )
    response = httpx.Response(
        status_code=200,
        json={"access_token": "gcp-access-token"},
        request=httpx.Request("POST", "https://oauth2.googleapis.com/token"),
    )

    now = int(time.time())
    with (
        patch("guardette.default_auth.gcp_service_account.time.time", return_value=now),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=response) as mock_post,
    ):
        await gcp_service_account(ctx)

    authorization = ctx.request.headers["authorization"]
    expected_scheme = "".join(("B", "earer"))
    assert authorization == f"{expected_scheme} {response.json()['access_token']}"
    mock_post.assert_awaited_once()
    kwargs = mock_post.await_args.kwargs
    assert kwargs["data"]["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"

    claims = jwt.decode(
        kwargs["data"]["assertion"],
        public_key,
        algorithms=["RS256"],
        audience="https://oauth2.googleapis.com/token",
    )
    assert claims["iss"] == credentials["client_email"]
    assert claims["sub"] == "impersonated@example.com"
    assert claims["scope"] == "https://www.googleapis.com/auth/a https://www.googleapis.com/auth/b"
    assert claims["iat"] == now
    assert claims["exp"] - claims["iat"] == 3600


@pytest.mark.anyio
async def test_gcp_service_account_requires_scopes_before_network_call(gcp_credentials):
    credentials, _ = gcp_credentials
    ctx = make_auth_context(
        secret_params={"secret": json.dumps(credentials)},
        config_params={"scopes": ""},
    )

    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        pytest.raises(AuthHandlerAuthException, match=r"`scopes` is required"),
    ):
        await gcp_service_account(ctx)

    mock_post.assert_not_awaited()
    assert "authorization" not in ctx.request.headers


@pytest.mark.anyio
async def test_gcp_service_account_surfaces_token_endpoint_errors(gcp_credentials):
    credentials, _ = gcp_credentials
    ctx = make_auth_context(
        secret_params={"secret": json.dumps(credentials)},
        config_params={"scopes": "scope"},
    )
    response = httpx.Response(
        status_code=401,
        request=httpx.Request("POST", "https://oauth2.googleapis.com/token"),
    )

    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=response),
        pytest.raises(AuthHandlerAuthException, match="http status"),
    ):
        await gcp_service_account(ctx)

    assert "authorization" not in ctx.request.headers


@pytest.fixture(autouse=True)
def clear_token_cache():
    _token_cache.clear()
    yield
    _token_cache.clear()


def make_ctx(
    *,
    client_id="client-id",
    client_secret="client-secret",
    token_url="https://auth.example.com/token",
):
    return AuthContext(
        request=ProxyRequest(url="https://api.example.com", headers=MutableHeaders({}), json_data=None),
        secret_params={"client_id": client_id, "client_secret": client_secret},
        config_params={"token_url": token_url},
    )


def mock_token_response(access_token="access-token-1", expires_in=3600, status_code=200):
    return httpx.Response(
        status_code=status_code,
        json={"access_token": access_token, "expires_in": expires_in},
        request=httpx.Request("POST", "https://auth.example.com/token"),
    )


@pytest.mark.anyio
@patch("httpx.AsyncClient.post", return_value=mock_token_response())
async def test_oauth2_client_credentials_tries_http_basic_auth_first(mock_post):
    ctx = make_ctx()

    await oauth2_client_credentials(ctx)

    assert ctx.request.headers["authorization"] == "Bearer access-token-1"
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["auth"] == ("client-id", "client-secret")
    assert kwargs["data"] == {"grant_type": "client_credentials"}


@pytest.mark.anyio
@patch(
    "httpx.AsyncClient.post",
    side_effect=[mock_token_response(status_code=401), mock_token_response()],
)
async def test_oauth2_client_credentials_falls_back_to_body_params(mock_post):
    ctx = make_ctx()

    await oauth2_client_credentials(ctx)

    assert ctx.request.headers["authorization"] == "Bearer access-token-1"
    assert mock_post.call_count == 2
    _, fallback_kwargs = mock_post.call_args_list[1]
    assert fallback_kwargs.get("auth") is None
    assert fallback_kwargs["data"] == {
        "grant_type": "client_credentials",
        "client_id": "client-id",
        "client_secret": "client-secret",
    }


@pytest.mark.anyio
@patch("httpx.AsyncClient.post", return_value=mock_token_response())
async def test_oauth2_client_credentials_caches_token(mock_post):
    ctx = make_ctx()

    await oauth2_client_credentials(ctx)
    await oauth2_client_credentials(ctx)

    assert mock_post.call_count == 1
    assert ctx.request.headers["authorization"] == "Bearer access-token-1"


@pytest.mark.anyio
async def test_oauth2_client_credentials_refetches_after_expiry():
    ctx = make_ctx()

    with patch("httpx.AsyncClient.post", return_value=mock_token_response(expires_in=60)) as mock_post:
        await oauth2_client_credentials(ctx)
        assert mock_post.call_count == 1

    # Force the cached token to be considered expired.
    cache_key = _TokenCacheKey(token_url="https://auth.example.com/token", client_id="client-id")
    cached = _token_cache[cache_key]
    _token_cache[cache_key] = _CachedToken(access_token=cached.access_token, expiry_time=0)

    with patch("httpx.AsyncClient.post", return_value=mock_token_response(access_token="access-token-2")) as mock_post:
        await oauth2_client_credentials(ctx)
        assert mock_post.call_count == 1

    assert ctx.request.headers["authorization"] == "Bearer access-token-2"


@pytest.mark.anyio
@patch("httpx.AsyncClient.post", return_value=mock_token_response(status_code=401))
async def test_oauth2_client_credentials_raises_on_error_status(mock_post):
    ctx = make_ctx()

    with pytest.raises(AuthHandlerAuthException):
        await oauth2_client_credentials(ctx)

    assert mock_post.call_count == 2
    assert "authorization" not in ctx.request.headers


@pytest.mark.anyio
async def test_oauth2_client_credentials_requires_token_url():
    ctx = make_ctx(token_url=None)

    with patch("httpx.AsyncClient.post") as mock_post:
        with pytest.raises(AuthHandlerAuthException):
            await oauth2_client_credentials(ctx)

    mock_post.assert_not_called()
