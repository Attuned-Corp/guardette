from unittest.mock import patch

import httpx
import pytest
from starlette.datastructures import MutableHeaders

from guardette.auth import AuthContext
from guardette.datastructures import ProxyRequest
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
