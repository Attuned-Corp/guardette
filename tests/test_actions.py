import pytest

from guardette.actions import action_registry


@pytest.mark.anyio
async def test_filter_regex(action_context):
    # Test case where regex matches
    action = action_registry.get_action_cls("filter_regex").model_validate(
        dict(json_paths=["$.path.to.data"], regex_pattern="test", delimiter=" ")
    )
    action_context.response.json_data = {"path": {"to": {"data": "test and test"}}}
    await action.response(action_context)
    assert action_context.response.json_data == {"path": {"to": {"data": "test test"}}}

    # Test case where regex does not match
    action = action_registry.get_action_cls("filter_regex").model_validate(
        dict(json_paths=["$.path.to.data"], regex_pattern="no match")
    )
    action_context.response.json_data = {"path": {"to": {"data": "test data"}}}
    await action.response(action_context)
    assert action_context.response.json_data == {"path": {"to": {"data": ""}}}

    # Test case where json path does not exist
    action = action_registry.get_action_cls("filter_regex").model_validate(
        dict(json_paths=["$.non.existent.path"], regex_pattern="test")
    )
    action_context.response.json_data = {"path": {"to": {"data": "test data"}}}
    await action.response(action_context)
    assert action_context.response.json_data == {"path": {"to": {"data": "test data"}}}


@pytest.mark.anyio
async def test_redact_regex(action_context):
    redact_token = action_context.config.REDACT_TOKEN
    action = action_registry.get_action_cls("redact_regex").model_validate(
        dict(
            json_paths=[
                "$.path.to.data1",
                "$.path.to.data2",
                '$.path.multiple[*].items[?(@.field = "summary")].text',
            ],
            regex_pattern="test",
        )
    )
    action_context.response.json_data = {
        "path": {
            "to": {"data1": "test and test", "data2": "more test"},
            "multiple": [
                {
                    "items": [
                        {"field": "summary", "text": "test"},
                        {"field": "description", "text": "test"},
                        {"field": "summary", "text": "more test"},
                    ],
                }
            ],
            "ignore": "test",
        }
    }

    await action.response(action_context)
    assert action_context.response.json_data == {
        "path": {
            "to": {"data1": f"{redact_token} and {redact_token}", "data2": f"more {redact_token}"},
            "multiple": [
                {
                    "items": [
                        {"field": "summary", "text": f"{redact_token}"},
                        {"field": "description", "text": "test"},
                        {"field": "summary", "text": f"more {redact_token}"},
                    ],
                }
            ],
            "ignore": "test",
        }
    }


@pytest.mark.anyio
async def test_redact_secrets_gitlab_diff(action_context):
    redact_token = action_context.config.REDACT_TOKEN
    aws_key = "AKIAIOSFODNN7EXAMPLE"

    diff_with_secret = (
        "--- a/config.py\n"
        "+++ b/config.py\n"
        "@@ -1,3 +1,3 @@\n"
        ' SERVICE = "billing"\n'
        '-AWS_KEY = "placeholder"\n'
        f'+AWS_KEY = "{aws_key}"\n'
        ' REGION = "us-east-1"\n'
    )
    diff_clean = "--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,1 @@\n-old title\n+new title\n"

    action = action_registry.get_action_cls("redact_secrets").model_validate(dict(json_paths=["$[*].diff"]))
    action_context.response.json_data = [
        {"old_path": "config.py", "new_path": "config.py", "diff": diff_with_secret},
        {"old_path": "README.md", "new_path": "README.md", "diff": diff_clean},
    ]

    await action.response(action_context)

    expected_redacted = (
        "--- a/config.py\n"
        "+++ b/config.py\n"
        "@@ -1,3 +1,3 @@\n"
        ' SERVICE = "billing"\n'
        '-AWS_KEY = "placeholder"\n'
        f'+AWS_KEY = "{redact_token}"\n'
        ' REGION = "us-east-1"\n'
    )
    assert action_context.response.json_data == [
        {"old_path": "config.py", "new_path": "config.py", "diff": expected_redacted},
        {"old_path": "README.md", "new_path": "README.md", "diff": diff_clean},
    ]


@pytest.mark.anyio
async def test_redact_secrets_ignores_allowlist(action_context):
    redact_token = action_context.config.REDACT_TOKEN
    aws_key = "AKIAIOSFODNN7EXAMPLE"

    action = action_registry.get_action_cls("redact_secrets").model_validate(dict(json_paths=["$.body"]))
    action_context.response.json_data = {
        "body": f'AWS_KEY = "{aws_key}"  # pragma: allowlist secret',
    }

    await action.response(action_context)

    assert action_context.response.json_data == {
        "body": f'AWS_KEY = "{redact_token}"  # pragma: allowlist secret',
    }
