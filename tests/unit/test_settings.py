"""Unit tests for settings management."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from grok_py.utils.settings import SettingsManager


class TestSettingsManager:
    """Test settings management functionality."""

    def test_load_default_settings(self):
        """Test loading default settings."""
        manager = SettingsManager()
        settings = manager.load_settings()

        assert hasattr(settings, 'api_keys')
        assert hasattr(settings, 'custom_instructions')
        assert hasattr(settings, 'mcp_config')

    def test_save_and_load_settings(self):
        """Test saving and loading settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'test_config.json')

            manager = SettingsManager(config_file=config_file)

            # Modify settings
            settings = manager.load_settings()
            settings.api_keys.grok = "test-key"

            # Save
            manager.save_settings(settings)

            # Load in new manager
            new_manager = SettingsManager(config_file=config_file)
            loaded_settings = new_manager.load_settings()

            assert loaded_settings.api_keys.grok == "test-key"

    def test_settings_validation(self):
        """Test settings validation."""
        manager = SettingsManager()

        # Valid settings
        settings = manager.load_settings()
        assert manager.validate_settings(settings) is True

        # Invalid settings (if any validation exists)
        # This would depend on the actual validation logic

    def test_environment_variable_override(self):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {'GROK_API_KEY': 'env-key'}):
            manager = SettingsManager()
            settings = manager.load_settings()

            assert settings.api_keys.grok == "env-key"

    def test_config_file_not_found(self):
        """Test handling missing config file."""
        manager = SettingsManager(config_file='/nonexistent/config.json')
        settings = manager.load_settings()

        # Should load defaults
        assert settings is not None

    def test_settings_merge(self):
        """Test merging settings from multiple sources."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'config.json')

            # Create partial config
            with open(config_file, 'w') as f:
                f.write('{"api_keys": {"grok": "file-key"}}')

            with patch.dict(os.environ, {'TAVILY_API_KEY': 'env-key'}):
                manager = SettingsManager(config_file=config_file)
                settings = manager.load_settings()

                assert settings.api_keys.grok == "file-key"
                assert settings.api_keys.tavily == "env-key"

    def test_secure_key_storage(self):
        """Test that API keys are handled securely."""
        manager = SettingsManager()

        # Ensure keys are not logged or exposed
        settings = manager.load_settings()
        settings.api_keys.grok = "secret-key"

        # This is more of a code review item, but we can check
        # that the settings object doesn't expose keys in __str__
        settings_str = str(settings)
        assert "secret-key" not in settings_str

    def test_mcp_config_loading(self):
        """Test MCP configuration loading."""
        manager = SettingsManager()
        settings = manager.load_settings()

        # MCP config should exist
        assert hasattr(settings, 'mcp_config')
        assert isinstance(settings.mcp_config, dict)

    def test_custom_instructions_loading(self):
        """Test custom instructions loading."""
        manager = SettingsManager()
        settings = manager.load_settings()

        assert hasattr(settings, 'custom_instructions')
        assert isinstance(settings.custom_instructions, str)