import time
from typing import NamedTuple

import httpx

from guardette.auth import AuthContext, auth_registry
from guardette.exceptions import AuthHandlerAuthException

_TOKEN_EXPIRY_BUFFER_SECS = 60


class _TokenCacheKey(NamedTuple):
    token_url: str
    client_id: str


class _CachedToken(NamedTuple):
    access_token: str
    expiry_time: float


_token_cache: dict[_TokenCacheKey, _CachedToken] = {}


@auth_registry.register(
    "oauth2_client_credentials",
    secret_keys=["client_id", "client_secret"],
    config_keys=["token_url"],
)
async def oauth2_client_credentials(ctx: AuthContext):
    client_id = ctx.secret_params["client_id"]
    client_secret = ctx.secret_params["client_secret"]
    token_url = ctx.config_params["token_url"]

    if not token_url:
        raise AuthHandlerAuthException("oauth2_client_credentials: `token_url` is required.")

    cache_key = _TokenCacheKey(token_url=token_url, client_id=client_id)
    cached = _token_cache.get(cache_key)
    if cached and cached.expiry_time > time.time():
        ctx.request.headers["authorization"] = f"Bearer {cached.access_token}"
        return

    async with httpx.AsyncClient() as client:
        # RFC 6749 ยง2.3.1: HTTP Basic auth is the primary client authentication
        # method; sending client_id/client_secret in the body is a fallback for
        # authorization servers that don't support Basic auth on their token endpoint.
        response = await client.post(
            token_url,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
        )
        if response.status_code in (400, 401):
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
        try:
            response.raise_for_status()
        except Exception as exc:
            raise AuthHandlerAuthException(
                f"oauth2_client_credentials: encountered error "
                f"http status trying to obtain access token "
                f"({response.status_code})"
            ) from exc

    body = response.json()
    access_token: str = body["access_token"]
    expires_in: float = body.get("expires_in", 0)
    _token_cache[cache_key] = _CachedToken(
        access_token=access_token,
        expiry_time=time.time() + max(expires_in - _TOKEN_EXPIRY_BUFFER_SECS, 0),
    )

    ctx.request.headers["authorization"] = f"Bearer {access_token}"
