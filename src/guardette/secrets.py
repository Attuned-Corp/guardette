import logging
import time
import typing

from aiobotocore.session import get_session

from guardette.config import ConfigManager
from guardette.exceptions import ConfigurationException, SecretsRetrievalException

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
            raise ConfigurationException(f"Missing secret for key: '{key}'.")
        return secret


class AwsSecretsManager:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.cache_ttl_secs = self.config.SECRET_MANAGER_CACHE_TTL_SECS

        # key: (secret, expiry_time)
        self._cache: typing.Dict[str, typing.Tuple[str, float]] = {}

    async def get(self, key, correlation_id: str = None) -> str:
        current_time = time.time()
        # Check if the secret is in cache and not expired
        if key in self._cache:
            secret, expiry = self._cache[key]
            if current_time < expiry:
                return secret
            else:
                # Remove expired secret
                del self._cache[key]

        secret = await self._fetch_secret(key, correlation_id)
        self._cache[key] = (secret, current_time + self.cache_ttl_secs)
        return secret

    async def _fetch_secret(self, key, correlation_id: str = None) -> str:
        secret_id = self.config.get(key)
        if secret_id is None:
            raise ConfigurationException(key)

        logger.info(f"Fetching secret from AWS for {key}", extra={"correlation_id": correlation_id})
        session = get_session()
        try:
            async with session.create_client("secretsmanager") as client:
                client: SecretsManagerClient

                secret_value_resp = await client.get_secret_value(SecretId=secret_id)
                return secret_value_resp["SecretString"]
        except Exception as e:
            raise SecretsRetrievalException(f"Error fetching secret from AWS for {key}: {str(e)}") from e
