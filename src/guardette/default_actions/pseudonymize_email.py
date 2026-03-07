import hashlib
import typing
import base64
from guardette.actions import action_registry, Action, ActionContext


@action_registry.register("pseudonymize_email")
class PseudonymizeEmail(Action):
    json_paths: typing.List[str]

    async def response(self, ctx: ActionContext):
        salt = await ctx.secrets.get('PSEUDONYMIZE_SALT')

        def updater(email, data, k):
            if not isinstance(email, str):
                return email

            try:
                username, domain = email.lower().split("@")
            except ValueError:
                return email

            if domain in ctx.config.PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST:
                return email

            username_hash = (
                base64.b32encode(hashlib.sha256((username + salt).encode()).digest())
                .decode()
                .rstrip("=")
            )
            domain_hash = (
                base64.b32encode(hashlib.sha256((domain + salt).encode()).digest())
                .decode()
                .rstrip("=")
            )
            return f"u-{username_hash}@d-{domain_hash}.invalid".lower()

        for path in self.json_paths:
            ctx.update_json_path(ctx.response.json_data, path, updater)
