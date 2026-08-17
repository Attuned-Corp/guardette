from pathlib import Path

import jinja2
import pytest
import yaml
from starlette.requests import Request

from guardette.matching import Matcher
from guardette.policy import Policy


def make_request(path):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


@pytest.mark.parametrize(
    ("kind", "host", "path", "path_params"),
    [
        (
            "jira_oauth2",
            "api.atlassian.com",
            "/ex/jira/cloud-id/rest/api/3/project/PROJ/version",
            {"cloudId": "cloud-id", "projectKey": "PROJ"},
        ),
        (
            "jira_basic_auth",
            "acme.atlassian.net",
            "/rest/api/3/project/PROJ/version",
            {"projectKey": "PROJ"},
        ),
    ],
)
def test_jira_project_versions_route(kind, host, path, path_params):
    templates = Path("scripts/policygen/sources")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates), autoescape=False)  # noqa: S701
    rendered = yaml.safe_load(
        env.get_template(f"{kind}/template.yml").render(config={"jira_domain": "acme.atlassian.net"})
    )
    sources = rendered["sources"] if "sources" in rendered else [rendered["source"]]
    matcher = Matcher(Policy(version="1", sources=sources))

    result = matcher.match(make_request(path), host)

    assert result is not None
    assert result["path_params"] == path_params
