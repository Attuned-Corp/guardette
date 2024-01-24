from guardette.auth import AuthContext, auth_registry


@auth_registry.register("bearer_token", secret_keys=["secret"])
async def bearer_token(ctx: AuthContext):
    ctx.request.headers["authorization"] = f"Bearer {ctx.secret_params['secret']}"
