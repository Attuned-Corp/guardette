import os

import pytest
from starlette.datastructures import MutableHeaders

from guardette.actions import ActionContext
from guardette.config import ConfigManager
from guardette.datastructures import ProxyRequest, ProxyResponse
from guardette.secrets import ConfigSecretsManager


def pytest_configure(config):
    os.environ.setdefault("CLIENT_SECRET", "test")


@pytest.fixture
def action_context():
    config = ConfigManager()
    secrets = ConfigSecretsManager(config)
    request = ProxyRequest(url="http://test.com", headers=MutableHeaders({}), json_data={})
    response = ProxyResponse(status_code=200, headers=MutableHeaders({}), json_data={})
    return ActionContext(config=config, secrets=secrets, request=request, response=response)


@pytest.fixture
def anyio_backend():
    return "asyncio"
