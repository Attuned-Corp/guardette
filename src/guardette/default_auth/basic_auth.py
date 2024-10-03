import base64
from guardette.auth import AuthContext, auth_registry


@auth_registry.register("basic_auth", secret_keys=["username", "password"])
async def basic_auth(ctx: AuthContext):
    username = ctx.secret_params["username"]
    password = ctx.secret_params["password"]

    auth_string = f"{username}:{password}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    ctx.request.headers["authorization"] = f"Basic {encoded_auth}"
