import os

from guardette.exceptions import ConfigurationException


class ConfigManager:
    REDACT_TOKEN = "[REDACTED]"

    def __init__(self):
        self.PSEUDONYMIZE_SALT: str = os.environ.get("PSEUDONYMIZE_SALT", "")
        self.CLIENT_SECRET: str = os.environ.get("CLIENT_SECRET", "")
        self.SECRET_MANAGER: str = os.environ.get("SECRET_MANAGER", "default")
        self.PROXY_CLIENT_TIMEOUT_SECS: int = int(os.environ.get("PROXY_CLIENT_TIMEOUT_SECS", 60))
        self.SECRET_MANAGER_CACHE_TTL_SECS: int = int(os.environ.get("SECRET_MANAGER_CACHE_TTL_SECS", 120))
        self.PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST: tuple[str, ...] = tuple(
            [d.lower() for d in os.environ.get("PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST", "").split(",") if d]
        )

        if not self.CLIENT_SECRET:
            raise ConfigurationException("CLIENT_SECRET environment variable must be set and non-empty.")

    def get(self, key, default=None):
        return os.environ.get(key, default=default)
