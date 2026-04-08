import hashlib
import base64
from guardette.actions import action_registry, Action, ActionContext
from guardette.config import ConfigManager
from guardette.exceptions import ConfigurationException


@action_registry.register("pseudonymize_email")
class PseudonymizeEmail(Action):
    json_paths: list[str]

    @classmethod
    def validate_config(cls, config: ConfigManager):
        if not config.PSEUDONYMIZE_SALT:
            raise ConfigurationException(
                "PSEUDONYMIZE_SALT environment variable must be set and non-empty "
                "when pseudonymize_email action is configured."
            )

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
