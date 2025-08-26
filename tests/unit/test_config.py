"""Unit tests for config module."""

import os
import logging
from unittest.mock import patch
import pytest

import src.config as config


@pytest.fixture
def original_environ():
    """Store and restore original environment variables."""
    original = os.environ.copy()
    yield original
    os.environ.clear()
    os.environ.update(original)


@pytest.fixture
def clean_environment(original_environ):
    """Clear SISMANAGER environment variables for testing defaults."""
    for key in list(os.environ.keys()):
        if key.startswith("SISMANAGER_"):
            del os.environ[key]
    return original_environ


def test_default_paths(clean_environment):
    """Test default path configurations."""
    # Reload config to pick up changes
    import importlib

    importlib.reload(config)

    assert config.BASE_DIR is not None
    assert config.DATA_DIR.endswith("data")
    assert config.BACKUP_DIR.endswith(os.path.join("data", "backups"))
    assert config.CENTRAL_DB_PATH.endswith(os.path.join("data", "central_db.csv"))


def test_environment_variable_overrides(original_environ):
    """Test that environment variables override defaults."""
    custom_data_dir = "/custom/data"
    custom_backup_dir = "/custom/backups"
    custom_db_path = "/custom/central_db.csv"

    os.environ["SISMANAGER_DATA_DIR"] = custom_data_dir
    os.environ["SISMANAGER_BACKUP_DIR"] = custom_backup_dir
    os.environ["SISMANAGER_CENTRAL_DB_PATH"] = custom_db_path

    # Reload config to pick up changes
    import importlib

    importlib.reload(config)

    assert config.DATA_DIR == custom_data_dir
    assert config.BACKUP_DIR == custom_backup_dir
    assert config.CENTRAL_DB_PATH == custom_db_path


def test_environment_variable_validation(original_environ):
    """Test environment variable validation."""
    # Test with invalid path (empty string)
    os.environ["SISMANAGER_DATA_DIR"] = ""

    # Reload config to pick up changes
    import importlib

    importlib.reload(config)

    # Empty string is still used as the value, so it won't fall back to default
    assert config.DATA_DIR == ""


def test_base_dir_calculation():
    """Test BASE_DIR calculation."""
    import importlib

    importlib.reload(config)

    # BASE_DIR should be calculated relative to config module location
    assert config.BASE_DIR is not None
    assert os.path.isabs(config.BASE_DIR)


def test_path_construction():
    """Test path construction logic."""
    import importlib

    importlib.reload(config)

    # Paths should be constructed based on BASE_DIR or environment variables
    assert config.DATA_DIR is not None
    assert config.BACKUP_DIR is not None
    assert config.CENTRAL_DB_PATH is not None


def test_logging_config_defaults():
    """Test default logging configuration."""
    import importlib

    importlib.reload(config)

    assert config.LOG_LEVEL is not None
    assert config.LOG_FORMAT is not None
    assert hasattr(config, "LOG_FILE")


def test_logging_config_environment_override(original_environ):
    """Test logging configuration environment overrides."""
    os.environ["SISMANAGER_LOG_LEVEL"] = "DEBUG"

    import importlib

    importlib.reload(config)

    assert config.LOG_LEVEL == "DEBUG"


def test_log_level_case_insensitive(original_environ):
    """Test that log level setting is case insensitive."""
    os.environ["SISMANAGER_LOG_LEVEL"] = "debug"

    import importlib

    importlib.reload(config)

    # Should normalize to uppercase
    assert config.LOG_LEVEL == "DEBUG"


@patch("logging.basicConfig")
def test_logging_configuration_called(mock_basic_config):
    """Test that logging configuration is called."""
    import importlib

    importlib.reload(config)

    # logging.basicConfig should have been called
    mock_basic_config.assert_called_once()


def test_log_handlers_configuration():
    """Test log handlers configuration."""
    import importlib

    importlib.reload(config)

    # Should have appropriate log handlers configured
    logger = logging.getLogger()
    assert len(logger.handlers) > 0


def test_logger_instance():
    """Test logger instance creation."""
    import importlib

    importlib.reload(config)

    # Should be able to get a logger instance
    logger = config.logger
    assert isinstance(logger, logging.Logger)
    assert logger.name == "sismanager"


def test_database_config_defaults():
    """Test database configuration defaults."""
    import importlib

    importlib.reload(config)

    # Should have database-related configuration
    assert hasattr(config, "CENTRAL_DB_PATH")
    assert config.CENTRAL_DB_PATH is not None
    assert hasattr(config, "DB_TYPE")
    assert config.DB_TYPE == "csv"


def test_database_config_environment_override(original_environ):
    """Test database configuration environment override."""
    custom_db_path = "/tmp/test_central_db.csv"
    custom_db_type = "sqlite"
    os.environ["SISMANAGER_CENTRAL_DB_PATH"] = custom_db_path
    os.environ["SISMANAGER_DB_TYPE"] = custom_db_type

    import importlib

    importlib.reload(config)

    assert config.CENTRAL_DB_PATH == custom_db_path
    assert config.DB_TYPE == custom_db_type
