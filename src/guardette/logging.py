import json
import logging
import os
import re
import sys

REDACTED = "[REDACTED]"

# Query strings and fragments routinely carry tokens, API keys and PII, so they
# are stripped from any URL that reaches a log line.
_URL_QUERY_RE = re.compile(r"(?P<base>[a-zA-Z][a-zA-Z0-9+.-]*://[^\s\"'?#]*)(?:\?[^\s\"'#]*)?(?:#[^\s\"']*)?")
_URL_HAS_QUERY_RE = re.compile(r"\?|#")

_SENSITIVE_KEY_RE = re.compile(
    r"(authorization|cookie|password|passwd|secret|token|api[-_]?key|query|signature)",
    re.IGNORECASE,
)


def redact_url(url: str) -> str:
    """Strip the query string and fragment from every URL found in ``url``."""

    def _sub(match: re.Match) -> str:
        text = match.group(0)
        base = match.group("base")
        return f"{base}?{REDACTED}" if _URL_HAS_QUERY_RE.search(text[len(base) :]) else text

    return _URL_QUERY_RE.sub(_sub, url)


def redact_value(key: str, value):
    if _SENSITIVE_KEY_RE.search(key):
        return REDACTED
    return _redact_nested(value)


def _redact_nested(value):
    if isinstance(value, str):
        return redact_url(value)
    if isinstance(value, dict):
        return {k: redact_value(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_nested(v) for v in value]
    return value


class CustomJSONFormatter(logging.Formatter):
    def format(self, record):
        # Create a log record dictionary
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": redact_url(record.getMessage()),
            "logger": "guardette",
        }

        # Include exception info if present
        if record.exc_info:
            log_record["exception"] = redact_url(self.formatException(record.exc_info))

        # Include other extra attributes
        extra_attributes = (
            set(record.__dict__.keys())
            - set(logging.LogRecord(None, None, None, None, "", (), None).__dict__.keys())
            - {"exc_info"}
        )
        for key in extra_attributes:
            if key not in log_record:
                log_record[key] = redact_value(key, record.__dict__.get(key))

        return json.dumps(log_record, default=str)


def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    formatter = CustomJSONFormatter()

    logger = logging.getLogger("guardette")
    logger.setLevel(log_level)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
