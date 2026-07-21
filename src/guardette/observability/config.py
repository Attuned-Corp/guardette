import os
from dataclasses import dataclass

from guardette.version import VERSION

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _read_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be one of: {', '.join(sorted(_TRUE_VALUES | _FALSE_VALUES))}")


@dataclass(frozen=True, slots=True)
class ObservabilityConfig:
    enabled: bool = False
    request_logging_enabled: bool = False
    metrics_enabled: bool = False
    service_name: str = "guardette"
    environment: str = "unknown"
    version: str = VERSION

    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        return cls(
            enabled=_read_bool("OBS_ENABLED"),
            request_logging_enabled=_read_bool("OBS_REQUEST_LOGGING_ENABLED"),
            metrics_enabled=_read_bool("OBS_METRICS_ENABLED"),
            service_name=os.getenv("SERVICE_NAME") or "guardette",
            environment=os.getenv("ENVIRONMENT") or "unknown",
            version=os.getenv("SERVICE_VERSION") or VERSION,
        )

    @property
    def active(self) -> bool:
        return self.enabled and (self.request_logging_enabled or self.metrics_enabled)

    @property
    def request_logging_active(self) -> bool:
        return self.enabled and self.request_logging_enabled

    @property
    def metrics_active(self) -> bool:
        return self.enabled and self.metrics_enabled
