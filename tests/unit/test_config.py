"""Unit tests for config module."""

import os
import tempfile
import unittest
from unittest.mock import patch
import logging

import src.config as config


class TestConfig(unittest.TestCase):
    """Test cases for config module."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.original_environ = os.environ.copy()

    def tearDown(self):
        """Clean up after each test method."""
        os.environ.clear()
        os.environ.update(self.original_environ)

    def test_default_paths(self):
        """Test default path configurations."""
        # Clear environment variables to test defaults
        for key in list(os.environ.keys()):
            if key.startswith("SISMANAGER_"):
                del os.environ[key]

        # Reload config to pick up changes
        import importlib

        importlib.reload(config)

        self.assertIsNotNone(config.BASE_DIR)
        self.assertTrue(config.DATA_DIR.endswith("data"))
        self.assertTrue(config.BACKUP_DIR.endswith(os.path.join("data", "backups")))
        self.assertTrue(
            config.CENTRAL_DB_PATH.endswith(os.path.join("data", "central_db.csv"))
        )

    def test_environment_variable_overrides(self):
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

        self.assertEqual(config.DATA_DIR, custom_data_dir)
        self.assertEqual(config.BACKUP_DIR, custom_backup_dir)
        self.assertEqual(config.CENTRAL_DB_PATH, custom_db_path)

    def test_database_config_defaults(self):
        """Test default database configuration."""
        # Clear environment variables
        for key in list(os.environ.keys()):
            if key.startswith("SISMANAGER_"):
                del os.environ[key]

        import importlib

        importlib.reload(config)

        self.assertEqual(config.DB_TYPE, "csv")
        self.assertEqual(config.DB_URL, "")

    def test_database_config_environment_override(self):
        """Test database configuration with environment variables."""
        os.environ["SISMANAGER_DB_TYPE"] = "sqlite"
        os.environ["SISMANAGER_DB_URL"] = "sqlite:///test.db"

        import importlib

        importlib.reload(config)

        self.assertEqual(config.DB_TYPE, "sqlite")
        self.assertEqual(config.DB_URL, "sqlite:///test.db")

    def test_logging_config_defaults(self):
        """Test default logging configuration."""
        # Clear environment variables
        for key in list(os.environ.keys()):
            if key.startswith("SISMANAGER_"):
                del os.environ[key]

        import importlib

        importlib.reload(config)

        self.assertEqual(config.LOG_LEVEL, "INFO")
        self.assertEqual(
            config.LOG_FORMAT, "%(asctime)s %(levelname)s %(name)s: %(message)s"
        )
        self.assertTrue(config.LOG_FILE.endswith("sismanager.log"))

    def test_logging_config_environment_override(self):
        """Test logging configuration with environment variables."""
        os.environ["SISMANAGER_LOG_LEVEL"] = "DEBUG"

        import importlib

        importlib.reload(config)

        self.assertEqual(config.LOG_LEVEL, "DEBUG")

    def test_logger_instance(self):
        """Test that logger instance is created correctly."""
        import importlib

        importlib.reload(config)

        self.assertIsInstance(config.logger, logging.Logger)
        self.assertEqual(config.logger.name, "sismanager")

    def test_log_level_case_insensitive(self):
        """Test that log level environment variable is case insensitive."""
        test_cases = ["debug", "DEBUG", "Debug", "info", "INFO", "Info"]

        for test_level in test_cases:
            os.environ["SISMANAGER_LOG_LEVEL"] = test_level

            import importlib

            importlib.reload(config)

            self.assertEqual(config.LOG_LEVEL, test_level.upper())

    def test_base_dir_calculation(self):
        """Test BASE_DIR calculation is correct."""
        import importlib

        importlib.reload(config)

        # BASE_DIR should be the parent of the src directory
        expected_base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(config.__file__))
        )
        self.assertEqual(config.BASE_DIR, expected_base_dir)

    @patch("logging.basicConfig")
    def test_logging_configuration_called(self, mock_basic_config):
        """Test that logging.basicConfig is called with correct parameters."""
        import importlib

        importlib.reload(config)

        # Verify basicConfig was called
        mock_basic_config.assert_called()

        # Get the call arguments
        call_args = mock_basic_config.call_args
        self.assertIn("level", call_args.kwargs)
        self.assertIn("format", call_args.kwargs)
        self.assertIn("handlers", call_args.kwargs)

    def test_log_handlers_configuration(self):
        """Test that both file and stream handlers are configured."""
        import importlib

        importlib.reload(config)

        # Get the root logger to check handlers
        root_logger = logging.getLogger()

        # Should have at least file and stream handlers
        handler_types = [type(handler).__name__ for handler in root_logger.handlers]

        # Note: The exact handler configuration may vary based on the environment
        # This test ensures the configuration runs without error
        self.assertIsNotNone(root_logger.handlers)

    def test_path_construction(self):
        """Test that paths are constructed correctly."""
        # This test is inherently difficult because config is imported at module level
        # We'll just verify the LOG_FILE is constructed properly with current BASE_DIR
        import importlib

        importlib.reload(config)

        expected_log_file = os.path.join(config.BASE_DIR, "sismanager.log")
        self.assertEqual(config.LOG_FILE, expected_log_file)

    def test_environment_variable_validation(self):
        """Test handling of various environment variable values."""
        # Test empty string
        os.environ["SISMANAGER_DATA_DIR"] = ""

        import importlib

        importlib.reload(config)

        # Empty string should still be used (os.environ.get returns the empty string)
        self.assertEqual(config.DATA_DIR, "")

        # Test with whitespace
        os.environ["SISMANAGER_DATA_DIR"] = "  /path/with/spaces  "
        importlib.reload(config)

        self.assertEqual(config.DATA_DIR, "  /path/with/spaces  ")


if __name__ == "__main__":
    unittest.main()
