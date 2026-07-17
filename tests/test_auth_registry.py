from unittest.mock import AsyncMock, Mock

import pytest

from guardette.auth import AuthContext, AuthHandlerRegistry
from guardette.datastructures import ProxyRequest


@pytest.mark.anyio
async def test_auth_handler_registry_resolves_secret_and_config_parameters():
    registry = AuthHandlerRegistry()
    handler = AsyncMock()

    @registry.register("demo", secret_keys=["username"], config_keys=["region"])
    async def registered_handler(ctx: AuthContext):
        await handler(ctx)

    secrets = Mock()
    secrets.get = AsyncMock(return_value="secret-value")
    config = Mock()
    config.get.return_value = "eu-west-1"
    request = ProxyRequest(url="https://example.com", headers={}, json_data=None)

    await registry("demo:github", request, secrets, config)

    context = handler.await_args.args[0]
    assert context.secret_params == {"username": "secret-value"}
    assert context.config_params == {"region": "eu-west-1"}
    secrets.get.assert_awaited_once_with("AUTH_DEMO_GITHUB_USERNAME")
    config.get.assert_called_once_with("AUTH_DEMO_GITHUB_REGION")


def test_auth_handler_registry_rejects_duplicate_kinds():
    registry = AuthHandlerRegistry()

    @registry.register("demo", secret_keys=[])
    async def first_handler(ctx):
        return ctx

    with pytest.raises(KeyError, match="already exists"):

        @registry.register("demo", secret_keys=[])
        async def second_handler(ctx):
            return ctx
