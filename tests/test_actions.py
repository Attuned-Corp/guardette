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
        dict(json_paths=[
            "$.path.to.data1",
            "$.path.to.data2",
            '$.path.multiple[*].items[?(@.field = "summary")].text',
        ], regex_pattern="test")
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
            "ignore": "test"
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

