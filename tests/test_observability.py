import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import fixture

from guardette.constants import PROXY_REQUEST_ID_HEADER
from guardette.logging import setup_logging
from guardette.observability import configure_observability
from guardette.observability.config import ObservabilityConfig
from guardette.observability.headers import sanitize_headers


@fixture(autouse=True)
def reset_logging():
    yield
    setup_logging(ObservabilityConfig())


def test_observability_is_disabled_by_default(capsys):
    app = FastAPI()
    configure_observability(app, ObservabilityConfig())

    @app.get("/items/{item_id}")
    async def get_item(item_id: str):
        return {"item_id": item_id}

    response = TestClient(app).get("/items/secret")

    assert response.status_code == 200
    assert PROXY_REQUEST_ID_HEADER not in response.headers
    assert capsys.readouterr().out == ""


def test_observability_config_requires_explicit_boolean_values(monkeypatch):
    monkeypatch.setenv("OBS_ENABLED", "true")
    monkeypatch.setenv("OBS_REQUEST_LOGGING_ENABLED", "on")
    monkeypatch.setenv("OBS_METRICS_ENABLED", "0")
    monkeypatch.setenv("SERVICE_VERSION", "")

    config = ObservabilityConfig.from_env()

    assert config.active is True
    assert config.request_logging_active is True
    assert config.metrics_active is False
    assert config.version

    monkeypatch.setenv("OBS_ENABLED", "sometimes")
    try:
        ObservabilityConfig.from_env()
    except ValueError as exc:
        assert "OBS_ENABLED" in str(exc)
    else:
        raise AssertionError("Invalid observability flags must be rejected")


def test_observability_logs_safe_request_response_data_and_metrics(capsys):
    app = FastAPI()
    configure_observability(
        app,
        ObservabilityConfig(
            enabled=True,
            request_logging_enabled=True,
            metrics_enabled=True,
            environment="test",
            version="test-version",
        ),
    )

    @app.post("/items/{item_id}")
    async def post_item(item_id: str):
        return {"item_id": item_id, "body": "response-secret"}

    response = TestClient(app).post(
        "/items/secret?query-secret=true",
        headers={
            "Accept": "application/json",
            "Authorization": "authorization-secret",
            "Cookie": "cookie-secret",
            "Content-Type": "application/json",
            "User-Agent": "test-client",
            "X-Api-Key": "api-key-secret",
        },
        content='{"body":"request-secret"}',
    )

    output = capsys.readouterr().out
    events = [json.loads(line) for line in output.splitlines()]
    request_event = next(event for event in events if event.get("event") == "guardette.request.completed")
    metric_names = {event["metric"] for event in events if event.get("event") == "guardette.metric"}

    assert response.status_code == 200
    assert response.headers[PROXY_REQUEST_ID_HEADER] == request_event["request_id"]
    assert request_event["route"] == "/items/{item_id}"
    assert request_event["headers"]["request"] == {
        "accept": "application/json",
        "content-type": "application/json",
        "user-agent": "test-client",
    }
    assert request_event["headers"]["response"]["content-type"] == "application/json"
    assert {
        "guardette_requests_total",
        "guardette_request_duration_seconds",
    } <= metric_names
    assert "authorization-secret" not in output
    assert "cookie-secret" not in output
    assert "api-key-secret" not in output
    assert "request-secret" not in output
    assert "response-secret" not in output
    assert "query-secret" not in output


def test_sanitize_headers_uses_allowlist_and_bounds_values():
    headers = {
        "Accept": "application/json",
        "Authorization": "secret",
        "X-Custom": "not-allowed",
        "User-Agent": "a" * 300,
    }

    sanitized = sanitize_headers(headers)

    assert sanitized == {
        "accept": "application/json",
        "user-agent": "a" * 256,
    }
