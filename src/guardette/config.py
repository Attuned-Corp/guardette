import os

PSEUDONYMIZE_SALT = "PSEUDONYMIZE_SALT"
CLIENT_SECRET = "CLIENT_SECRET"
SECRET_MANAGER = "SECRET_MANAGER"
PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST = "PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST"


class ConfigManager:
    redact_token = "[REDACTED]"

    def get(self, key, default=None):
        return os.environ.get(key, default=default)

    @property
    def pseudonymize_email_domains_allowlist(self):
        raw_allowlist = self.get(PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST) or ""
        return [d.lower() for d in raw_allowlist.split(",") if d]
