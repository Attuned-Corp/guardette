import json
import logging

from guardette.logging import REDACTED, CustomJSONFormatter, redact_url


def _format(msg: str, **extra) -> dict:
    record = logging.LogRecord("guardette", logging.INFO, __file__, 1, msg, (), None)
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(CustomJSONFormatter().format(record))


def test_redact_url_strips_query_and_fragment():
    assert redact_url("https://example.com/a/b?token=abc&x=1#frag") == f"https://example.com/a/b?{REDACTED}"


def test_redact_url_leaves_urls_without_query_untouched():
    assert redact_url("https://example.com/a/b") == "https://example.com/a/b"


def test_formatter_redacts_urls_in_message_and_extras():
    out = _format("Fetching https://example.com/x?api_key=secret", url="https://example.com/y?email=a@b.com")
    assert "secret" not in json.dumps(out)
    assert "a@b.com" not in json.dumps(out)


def test_formatter_redacts_sensitive_keys():
    out = _format("hello", authorization="Bearer abc", nested={"password": "pw", "ok": "v"})
    assert out["authorization"] == REDACTED
    assert out["nested"] == {"password": REDACTED, "ok": "v"}
