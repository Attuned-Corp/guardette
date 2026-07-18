import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from guardette.config import ConfigManager
from guardette.secrets import (
    AwsSecretsManager,
    ConfigSecretsManager,
    ConfigurationException,
    SecretsRetrievalException,
)


@pytest.mark.anyio
async def test_config_secrets_manager_returns_configured_secret():
    config = ConfigManager()
    config.get = Mock(return_value="configured-secret")

    value = await ConfigSecretsManager(config).get("API_TOKEN", correlation_id="abcd-1234")

    assert value == "configured-secret"


@pytest.mark.anyio
async def test_config_secrets_manager_reports_missing_secret():
    config = ConfigManager()
    config.get = Mock(return_value=None)

    with pytest.raises(ConfigurationException, match="Missing secret for key"):
        await ConfigSecretsManager(config).get("MISSING_SECRET")


@pytest.mark.anyio
async def test_aws_secrets_manager_logs_fetching_secret(caplog):
    # Arrange
    config = ConfigManager()
    config.get = Mock(return_value="test")
    aws_secrets_manager = AwsSecretsManager(config)

    # Mock the AWS session and client
    with patch("guardette.secrets.get_session") as mock_get_session:
        mock_client = Mock()
        mock_get_session.return_value.create_client.return_value.__aenter__.return_value = mock_client
        mock_client.get_secret_value = AsyncMock(return_value={"SecretString": "mock_secret"})

        # Act
        with caplog.at_level(logging.INFO):
            secret = await aws_secrets_manager.get("TEST_SECRET", correlation_id="abcd-1234")

    # Assert
    assert secret == "mock_secret"
    assert any(
        record.levelname == "INFO"
        and record.message.startswith("Fetching secret from AWS")
        and record.correlation_id == "abcd-1234"
        for record in caplog.records
    )


@pytest.mark.anyio
async def test_aws_secrets_manager_raises_exception_when_secret_missing(caplog):
    # Arrange
    config = ConfigManager()
    config.get = Mock(return_value=None)
    aws_secrets_manager = AwsSecretsManager(config)

    # Act & Assert
    with pytest.raises(ConfigurationException) as exc_info:
        await aws_secrets_manager.get("MISSING_SECRET", correlation_id="efgh-5678")

    assert str(exc_info.value) == "MISSING_SECRET"
    # No log should be generated since exception is raised before logging
    assert not any(record.levelname == "INFO" for record in caplog.records)


@pytest.mark.anyio
async def test_aws_secrets_manager_caches_secrets(caplog):
    # Arrange
    config = ConfigManager()
    config.get = Mock(return_value="test")

    aws_secrets_manager = AwsSecretsManager(config)

    with patch("guardette.secrets.get_session") as mock_get_session:
        mock_client = Mock()
        mock_get_session.return_value.create_client.return_value.__aenter__.return_value = mock_client
        mock_client.get_secret_value = AsyncMock(return_value={"SecretString": "cached_secret"})

        # First fetch - should log
        with caplog.at_level(logging.INFO):
            secret1 = await aws_secrets_manager.get("CACHED_SECRET", correlation_id="ijkl-9012")

        # Second fetch - should not log since it's cached
        with caplog.at_level(logging.INFO):
            secret2 = await aws_secrets_manager.get("CACHED_SECRET", correlation_id="mnop-3456")

    # Assert
    assert secret1 == "cached_secret"
    assert secret2 == "cached_secret"

    # Check that the log was only created once
    info_logs = [
        record
        for record in caplog.records
        if record.levelname == "INFO" and record.message == "Fetching secret from AWS for CACHED_SECRET"
    ]
    assert len(info_logs) == 1
    assert info_logs[0].correlation_id == "ijkl-9012"


@pytest.mark.anyio
async def test_aws_secrets_manager_refetches_at_cache_expiry():
    config = ConfigManager()
    config.get = Mock(return_value="test")
    aws_secrets_manager = AwsSecretsManager(config)
    aws_secrets_manager.cache_ttl_secs = 120

    with (
        patch("guardette.secrets.time.time", side_effect=[100, 220]),
        patch("guardette.secrets.get_session") as mock_get_session,
    ):
        mock_client = Mock()
        mock_get_session.return_value.create_client.return_value.__aenter__.return_value = mock_client
        mock_client.get_secret_value = AsyncMock(
            side_effect=[
                {"SecretString": "first-secret"},
                {"SecretString": "refreshed-secret"},
            ]
        )

        assert await aws_secrets_manager.get("ROTATING_SECRET") == "first-secret"
        assert await aws_secrets_manager.get("ROTATING_SECRET") == "refreshed-secret"

    assert mock_client.get_secret_value.await_count == 2


@pytest.mark.anyio
async def test_aws_secrets_manager_wraps_client_errors():
    config = ConfigManager()
    config.get = Mock(return_value="test")
    aws_secrets_manager = AwsSecretsManager(config)

    with patch("guardette.secrets.get_session") as mock_get_session:
        mock_client = Mock()
        mock_get_session.return_value.create_client.return_value.__aenter__.return_value = mock_client
        mock_client.get_secret_value = AsyncMock(side_effect=RuntimeError("AWS unavailable"))

        with pytest.raises(SecretsRetrievalException, match="Error fetching secret from AWS"):
            await aws_secrets_manager.get("BROKEN_SECRET", correlation_id="corr-123")

    mock_client.get_secret_value.assert_awaited_once_with(SecretId="test")
