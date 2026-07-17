import pytest
from pydantic import ValidationError

from guardette.policy import Policy


def test_policy_from_file_builds_registered_actions():
    policy = Policy.from_file("tests/test_policy.yml")

    assert policy.sources[0].host == "hacker-news.firebaseio.com"
    assert policy.sources[0].rules[0].actions[0].json_paths == ["$.title"]
    assert policy.sources[1].auth == "bearer_token:github"


def test_policy_rejects_duplicate_hosts():
    policy_data = {
        "version": "1",
        "sources": [
            {"host": "example.com", "rules": []},
            {"host": "example.com", "rules": []},
        ],
    }

    with pytest.raises(ValidationError, match="Duplicated hosts"):
        Policy.model_validate(policy_data)


def test_policy_rejects_invalid_auth_format():
    policy_data = {
        "version": "1",
        "sources": [{"host": "example.com", "auth": "invalid:format:extra", "rules": []}],
    }

    with pytest.raises(ValidationError, match="Invalid `auth` format"):
        Policy.model_validate(policy_data)
