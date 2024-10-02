import os

class ConfigManager:
    REDACT_TOKEN = "[REDACTED]"

    PSEUDONYMIZE_SALT: str = os.environ.get("PSEUDONYMIZE_SALT", "")

    CLIENT_SECRET: str = os.environ.get("CLIENT_SECRET", "")
    SECRET_MANAGER: str = os.environ.get("SECRET_MANAGER", "default")
    PROXY_CLIENT_TIMEOUT_SECS: int = os.environ.get("PROXY_CLIENT_TIMEOUT_SECS", 60)
    SECRET_MANAGER_CACHE_TTL_SECS: int = os.environ.get("SECRET_MANAGER_CACHE_TTL_SECS", 120)
    PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST: tuple[str, ...] = tuple([
        d.lower()
        for d in os.environ.get("PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST", "").split(",")
        if d
    ])

    def get(self, key, default=None):
        return os.environ.get(key, default=default)
