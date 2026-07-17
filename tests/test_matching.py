from starlette.requests import Request

from guardette.matching import Matcher
from guardette.policy import Policy


def make_request(method, path):
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


def test_matcher_matches_host_method_and_path_parameters():
    matcher = Matcher(Policy.from_file("tests/test_policy.yml"))

    result = matcher.match(make_request("GET", "/repos/acme/guardette/pulls"), "api.github.com")

    assert result is not None
    assert result["path_params"] == {"owner": "acme", "repo": "guardette"}


def test_matcher_returns_none_for_unknown_host_or_method():
    matcher = Matcher(Policy.from_file("tests/test_policy.yml"))

    assert matcher.match(make_request("GET", "/v0/item/1"), "unknown.example.com") is None
    assert matcher.match(make_request("POST", "/v0/item/1"), "hacker-news.firebaseio.com") is None
