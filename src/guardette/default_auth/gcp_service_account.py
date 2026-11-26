import json
import time

import httpx
import jwt

from guardette.auth import AuthContext, auth_registry
from guardette.exceptions import AuthHandlerAuthException

GCP_IMPERSONATE_SUB_HEADER = "X-Guardette-Gcp-Impersonate-Sub"


def _resolve_subject(ctx: AuthContext, default_sub: str) -> str:
    requested = ctx.request.headers.get(GCP_IMPERSONATE_SUB_HEADER)
    if not requested:
        return default_sub

    configured = (ctx.config_params.get("impersonate_subs") or "").split(",")
    allowed = {sub.strip().lower(): sub.strip() for sub in configured if sub.strip()}
    match = allowed.get(requested.strip().lower())
    if match is None:
        raise AuthHandlerAuthException("gcp_service_account: requested impersonation subject is not allowed.")
    return match


@auth_registry.register("gcp_service_account", secret_keys=["secret"], config_keys=["scopes", "impersonate_subs"])
async def gcp_service_account(ctx: AuthContext):
    credentials = json.loads(ctx.secret_params["secret"])
    sub = _resolve_subject(ctx, credentials["client_email"])
    if GCP_IMPERSONATE_SUB_HEADER in ctx.request.headers:
        del ctx.request.headers[GCP_IMPERSONATE_SUB_HEADER]

    if not ctx.config_params["scopes"]:
        raise AuthHandlerAuthException("gcp_service_account: `scopes` is required.")

    scopes = " ".join(ctx.config_params["scopes"].split(","))
    payload = {
        "iss": credentials["client_email"],
        "sub": sub,
        "aud": "https://oauth2.googleapis.com/token",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "scope": scopes,
    }

    signed_jwt = jwt.encode(payload, credentials["private_key"], algorithm="RS256")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed_jwt,
            },
        )
        try:
            response.raise_for_status()
        except Exception as exc:
            raise AuthHandlerAuthException(
                f"gcp_service_account: encountered error "
                f"http status trying to obtain access token "
                f"({response.status_code})"
            ) from exc

    access_token: str = response.json()["access_token"]
    ctx.request.headers["authorization"] = f"Bearer {access_token}"
