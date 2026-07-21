import importlib.util
from pathlib import Path

import requests

module_spec = importlib.util.spec_from_file_location("check_jira", Path(__file__).parents[1] / "scripts/check_jira.py")
assert module_spec is not None
assert module_spec.loader is not None
check_jira = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(check_jira)


def test_do_request_returns_json_and_preserves_timeout(monkeypatch):
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"ok": true}'

    def fake_get(url, *args, **kwargs):
        assert url == "https://jira.example.test/api"
        assert kwargs["timeout"] == 5
        return response

    monkeypatch.setattr(check_jira.requests, "get", fake_get)

    assert check_jira.do_request("https://jira.example.test/api", timeout=5) == {"ok": True}


def test_do_request_raises_for_non_success_response(monkeypatch):
    response = requests.Response()
    response.status_code = 503
    response._content = b"upstream unavailable"

    monkeypatch.setattr(check_jira.requests, "get", lambda *_args, **_kwargs: response)

    try:
        check_jira.do_request("https://jira.example.test/api")
    except requests.HTTPError as error:
        assert "503" in str(error)
        assert error.response is response
    else:
        raise AssertionError("Expected requests.HTTPError")


def test_jira_apis_creates_output_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def fake_request(url, **kwargs):
        if url.endswith("/rest/agile/1.0/board"):
            return {"values": [{"id": 42}]}
        if "/rest/agile/1.0/board/42/issue" in url:
            return {"total": 0, "issues": []}
        return {"issues": []}

    monkeypatch.setattr(check_jira, "do_request", fake_request)

    check_jira.jira_apis("token", "jira.example.test", "http://proxy.test")

    output_dir = tmp_path / ".guardette"
    assert output_dir.is_dir()
    assert (output_dir / "jira_issues_response.json").is_file()
    assert (output_dir / "jira_boards_response.json").is_file()
    assert (output_dir / "jira_board_issues_response.json").is_file()
