import json
import logging
import os
import sys

_SAFE_EXTRA_FIELDS = frozenset(
    {
        "correlation_id",
        "status_code",
        "content_type",
        "elapsed_time",
        "error_class",
        "source_count",
        "rule_count",
    },
)


class _DynamicStdoutHandler(logging.StreamHandler):
    def emit(self, record):
        self.stream = sys.stdout
        super().emit(record)


class CustomJSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": "guardette",
        }

        observability_event = getattr(record, "observability_event", None)
        if isinstance(observability_event, dict):
            log_record.update(observability_event)

        if record.exc_info:
            log_record["error_class"] = record.exc_info[0].__name__

        for key in _SAFE_EXTRA_FIELDS:
            if key not in log_record and hasattr(record, key):
                log_record[key] = getattr(record, key)

        return json.dumps(log_record)


def setup_logging(config=None):
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    formatter = CustomJSONFormatter()

    logger = logging.getLogger("guardette")
    logger.setLevel(log_level)
    observability_active = bool(config and config.active)
    logger.disabled = False
    logger.propagate = not observability_active

    for handler in list(logger.handlers):
        if getattr(handler, "_guardette_handler", False):
            logger.removeHandler(handler)

    if observability_active:
        console_handler = _DynamicStdoutHandler(sys.stdout)
        console_handler._guardette_handler = True
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
