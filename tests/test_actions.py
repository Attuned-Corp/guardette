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
