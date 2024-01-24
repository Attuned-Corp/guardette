import hashlib
import typing
import base64
from guardette.actions import action_registry, Action, ActionContext
from guardette.config import PSEUDONYMIZE_SALT


@action_registry.register("pseudonymize_email")
class PseudonymizeEmail(Action):
    json_paths: typing.List[str]

    async def response(self, ctx: ActionContext):
        salt = await ctx.secrets.get(PSEUDONYMIZE_SALT)

        def updater(email, data, k):
            if not isinstance(email, str):
                return

            try:
                username, domain = email.lower().split("@")
            except ValueError:
                return

            if domain in ctx.config.pseudonymize_email_domains_allowlist:
                return

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
            pseudonymized_email = f"u-{username_hash}@d-{domain_hash}.invalid".lower()
            data.update({k: pseudonymized_email})

        for path in self.json_paths:
            ctx.update_json_path(ctx.response.json_data, path, updater)
