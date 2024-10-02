import json
import logging
import os
import sys


class CustomJSONFormatter(logging.Formatter):
    def format(self, record):
        # Create a log record dictionary
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": "guardette",
        }

        # Include exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Include other extra attributes
        extra_attributes = set(record.__dict__.keys()) \
            - set(logging.LogRecord(None, None, None, None, '', (), None).__dict__.keys()) \
            - {"exc_info"}
        for key in extra_attributes:
            if key not in log_record:
                log_record[key] = record.__dict__.get(key)

        return json.dumps(log_record)


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

