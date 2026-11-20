import json
from unittest.mock import patch

import httpx
import pytest
from starlette.datastructures import MutableHeaders

from guardette.auth import AuthContext
from guardette.datastructures import ProxyRequest
from guardette.default_auth.gcp_service_account import gcp_service_account
from guardette.default_auth.oauth2_client_credentials import (
    _CachedToken,
    _token_cache,
    _TokenCacheKey,
    oauth2_client_credentials,
)
from guardette.exceptions import AuthHandlerAuthException


@pytest.fixture(autouse=True)
def clear_token_cache():
    _token_cache.clear()
    yield
    _token_cache.clear()


def make_ctx(
    *,
    client_id="client-id",
    client_secret="client-secret",  # noqa: S107
    token_url="https://auth.example.com/token",  # noqa: S107
):
    return AuthContext(
        request=ProxyRequest(url="https://api.example.com", headers=MutableHeaders({}), json_data=None),
        secret_params={"client_id": client_id, "client_secret": client_secret},
        config_params={"token_url": token_url},
    )


def mock_token_response(access_token="access-token-1", expires_in=3600, status_code=200):  # noqa: S107
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
    cache_key = _TokenCacheKey(token_url="https://auth.example.com/token", client_id="client-id")  # noqa: S106
    cached = _token_cache[cache_key]
    _token_cache[cache_key] = _CachedToken(access_token=cached.access_token, expiry_time=0)

    with patch(
        "httpx.AsyncClient.post",
        return_value=mock_token_response(access_token="access-token-2"),  # noqa: S106
    ) as mock_post:
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

    with patch("httpx.AsyncClient.post") as mock_post, pytest.raises(AuthHandlerAuthException):
        await oauth2_client_credentials(ctx)

    mock_post.assert_not_called()


def make_gcp_ctx(*, header=None, allowed=None):
    headers = {"X-Guardette-Gcp-Impersonate-Sub": header} if header else {}
    return AuthContext(
        request=ProxyRequest(url="https://api.example.com", headers=MutableHeaders(headers), json_data=None),
        secret_params={"secret": json.dumps({"client_email": "sa@proj.iam.gserviceaccount.com", "private_key": "k"})},
        config_params={"scopes": "scope1", "impersonate_subs": allowed},
    )


def gcp_token_response():
    return httpx.Response(
        status_code=200,
        json={"access_token": "gcp-token"},
        request=httpx.Request("POST", "https://oauth2.googleapis.com/token"),
    )


@pytest.mark.anyio
async def test_gcp_service_account_rejects_unlisted_subject():
    ctx = make_gcp_ctx(header="victim@example.com", allowed=None)

    with (
        patch("jwt.encode") as mock_encode,
        patch("httpx.AsyncClient.post") as mock_post,
        pytest.raises(AuthHandlerAuthException),
    ):
        await gcp_service_account(ctx)

    mock_encode.assert_not_called()
    mock_post.assert_not_called()


@pytest.mark.anyio
async def test_gcp_service_account_rejects_subject_not_in_allowlist():
    ctx = make_gcp_ctx(header="victim@example.com", allowed="a@example.com,b@example.com")

    with patch("httpx.AsyncClient.post") as mock_post, pytest.raises(AuthHandlerAuthException):
        await gcp_service_account(ctx)

    mock_post.assert_not_called()


@pytest.mark.anyio
async def test_gcp_service_account_allows_listed_subject():
    ctx = make_gcp_ctx(header="B@example.com", allowed="a@example.com, b@example.com")

    with (
        patch("jwt.encode", return_value="signed") as mock_encode,
        patch("httpx.AsyncClient.post", return_value=gcp_token_response()),
    ):
        await gcp_service_account(ctx)

    assert mock_encode.call_args.args[0]["sub"] == "b@example.com"
    assert ctx.request.headers["authorization"] == "Bearer gcp-token"
    assert "x-guardette-gcp-impersonate-sub" not in ctx.request.headers


@pytest.mark.anyio
async def test_gcp_service_account_defaults_to_service_account_identity():
    ctx = make_gcp_ctx()

    with (
        patch("jwt.encode", return_value="signed") as mock_encode,
        patch("httpx.AsyncClient.post", return_value=gcp_token_response()),
    ):
        await gcp_service_account(ctx)

    assert mock_encode.call_args.args[0]["sub"] == "sa@proj.iam.gserviceaccount.com"
