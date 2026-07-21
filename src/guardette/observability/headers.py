from collections.abc import Mapping

from guardette.constants import PROXY_REQUEST_ID_HEADER

MAX_HEADER_VALUE_LENGTH = 256

SAFE_HEADER_NAMES = frozenset(
    {
        "accept",
        "content-type",
        "user-agent",
        "cf-ray",
        PROXY_REQUEST_ID_HEADER.lower(),
    },
)

SENSITIVE_HEADER_MARKERS = (
    "api-key",
    "authorization",
    "credential",
    "cookie",
    "password",
    "secret",
    "session",
    "token",
)


def sanitize_headers(headers: Mapping[str, str], request_id: str | None = None) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for name, value in headers.items():
        normalized_name = name.lower()
        if normalized_name not in SAFE_HEADER_NAMES:
            continue
        if any(marker in normalized_name for marker in SENSITIVE_HEADER_MARKERS):
            continue

        normalized_value = request_id if normalized_name == PROXY_REQUEST_ID_HEADER.lower() and request_id else value
        sanitized[normalized_name] = normalized_value[:MAX_HEADER_VALUE_LENGTH]

    return sanitized
