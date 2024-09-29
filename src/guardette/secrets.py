import logging
import typing

from aiobotocore.session import get_session

from guardette.config import ConfigManager
from guardette.exceptions import ConfigurationException

from types_aiobotocore_secretsmanager import SecretsManagerClient

logger = logging.getLogger("guardette")

class SecretManagerType:
    DEFAULT = "default"
    AWS_SECRET_MANAGER = "aws_secret_manager"


class SecretsManager(typing.Protocol):
    async def get(self, key) -> str:
        ...


class ConfigSecretsManager:
    def __init__(self, config: ConfigManager):
        self.config = config

    async def get(self, key, correlation_id: str = None) -> str:
        secret = self.config.get(key)
        if secret is None:
            raise ConfigurationException(key)
        return secret


class AwsSecretsManager:
    def __init__(self, config: ConfigManager):
        self.config = config

    async def get(self, key, correlation_id: str = None) -> str:
        secret_id = self.config.get(key)
        if secret_id is None:
            raise ConfigurationException(key)

        logger.info(f"Fetching secret from AWS for {key}", extra={"correlation_id": correlation_id})
        session = get_session()
        async with session.create_client("secretsmanager") as client:
            client: SecretsManagerClient

            secret_value_resp = await client.get_secret_value(SecretId=secret_id)
            return secret_value_resp["SecretString"]
