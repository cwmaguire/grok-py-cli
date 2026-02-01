import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from grok_py.utils.config import (
    FileOpsConfig, IntegrityConfig, ArchiveConfig, VersionControlConfig,
    GrokCLIConfig, ConfigManager
)


class TestFileOpsConfig:
    """Test FileOpsConfig dataclass."""

    def test_default_values(self):
        config = FileOpsConfig()
        assert config.default_bulk_copy_overwrite == False
        assert config.default_bulk_move_overwrite == False
        assert config.default_archive_compression_level == 6
        assert config.default_sync_compare_method == "hash"
        assert config.default_search_case_sensitive == True
        assert config.default_search_whole_word == False
        assert config.backup_before_replace == True
        assert config.max_concurrent_operations == 4
        assert config.exclude_patterns == ['*.tmp', '*.bak', '*.swp', '.git', '__pycache__', 'node_modules']

    def test_custom_values(self):
        config = FileOpsConfig(
            default_bulk_copy_overwrite=True,
            max_concurrent_operations=8,
            exclude_patterns=['*.log']
        )
        assert config.default_bulk_copy_overwrite == True
        assert config.max_concurrent_operations == 8
        assert config.exclude_patterns == ['*.log']


class TestIntegrityConfig:
    """Test IntegrityConfig dataclass."""

    def test_default_values(self):
        config = IntegrityConfig()
        assert config.default_algorithms == ["md5", "sha256"]
        assert config.checksum_storage_format == "json"
        assert config.auto_verify_on_copy == False
        assert config.auto_verify_on_move == False

    def test_custom_values(self):
        config = IntegrityConfig(
            default_algorithms=["sha1"],
            checksum_storage_format="csv",
            auto_verify_on_copy=True
        )
        assert config.default_algorithms == ["sha1"]
        assert config.checksum_storage_format == "csv"
        assert config.auto_verify_on_copy == True


class TestArchiveConfig:
    """Test ArchiveConfig dataclass."""

    def test_default_values(self):
        config = ArchiveConfig()
        assert config.default_compression_type == "gzip"
        assert config.default_compression_level == 6
        assert config.preserve_permissions == True
        assert config.exclude_patterns == ['*.tmp', '*.bak', '*.swp', '.git', '__pycache__']

    def test_custom_values(self):
        config = ArchiveConfig(
            default_compression_type="zip",
            preserve_permissions=False
        )
        assert config.default_compression_type == "zip"
        assert config.preserve_permissions == False


class TestVersionControlConfig:
    """Test VersionControlConfig dataclass."""

    def test_default_values(self):
        config = VersionControlConfig()
        assert config.default_remote == "origin"
        assert config.default_branch == "main"
        assert config.auto_commit_message_template == "Auto-commit: {changes}"
        assert config.push_after_commit == False
        assert config.create_backup_before_reset == True

    def test_custom_values(self):
        config = VersionControlConfig(
            default_branch="develop",
            push_after_commit=True
        )
        assert config.default_branch == "develop"
        assert config.push_after_commit == True


class TestGrokCLIConfig:
    """Test GrokCLIConfig dataclass."""

    def test_default_values(self):
        config = GrokCLIConfig()
        assert isinstance(config.file_ops, FileOpsConfig)
        assert isinstance(config.integrity, IntegrityConfig)
        assert isinstance(config.archive, ArchiveConfig)
        assert isinstance(config.version_control, VersionControlConfig)
        assert config.ui_theme == "dark"
        assert config.log_level == "INFO"
        assert config.max_log_files == 10
        assert config.config_version == "1.0.0"

    def test_custom_values(self):
        file_ops = FileOpsConfig(default_bulk_copy_overwrite=True)
        config = GrokCLIConfig(
            file_ops=file_ops,
            ui_theme="light",
            log_level="DEBUG"
        )
        assert config.file_ops.default_bulk_copy_overwrite == True
        assert config.ui_theme == "light"
        assert config.log_level == "DEBUG"


class TestConfigManager:
    """Test ConfigManager class."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        return tmp_path / "config_test"

    def test_init_default_config_dir(self, temp_dir):
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = temp_dir
            with patch('os.name', 'posix'):
                manager = ConfigManager()
                expected = temp_dir / ".config" / "grok-cli"
                assert manager.config_dir == expected
                assert manager.config_file == expected / "config.json"

    def test_init_custom_config_dir(self, temp_dir):
        manager = ConfigManager(temp_dir)
        assert manager.config_dir == temp_dir
        assert manager.config_file == temp_dir / "config.json"

    def test_load_config_file_not_exists(self, temp_dir):
        manager = ConfigManager(temp_dir)
        config = manager.load_config()
        assert isinstance(config, GrokCLIConfig)
        assert config.ui_theme == "dark"

    def test_load_config_success(self, temp_dir):
        manager = ConfigManager(temp_dir)
        config_data = {
            "ui_theme": "light",
            "log_level": "DEBUG",
            "file_ops": {
                "default_bulk_copy_overwrite": True
            }
        }

        with open(manager.config_file, 'w') as f:
            json.dump(config_data, f)

        config = manager.load_config()
        assert config.ui_theme == "light"
        assert config.log_level == "DEBUG"
        assert config.file_ops.default_bulk_copy_overwrite == True

    def test_load_config_invalid_json(self, temp_dir):
        manager = ConfigManager(temp_dir)
        with open(manager.config_file, 'w') as f:
            f.write("invalid json")

        config = manager.load_config()
        # Should return default config on error
        assert isinstance(config, GrokCLIConfig)

    def test_save_config(self, temp_dir):
        manager = ConfigManager(temp_dir)
        manager._config = GrokCLIConfig(ui_theme="light")

        manager.save_config()

        assert manager.config_file.exists()
        with open(manager.config_file, 'r') as f:
            data = json.load(f)

        assert data["ui_theme"] == "light"

    def test_config_property_lazy_loading(self, temp_dir):
        manager = ConfigManager(temp_dir)
        # First access should load config
        config1 = manager.config
        assert isinstance(config1, GrokCLIConfig)

        # Second access should return cached config
        config2 = manager.config
        assert config1 is config2

    def test_save_config_error_handling(self, temp_dir):
        manager = ConfigManager(temp_dir)
        manager._config = GrokCLIConfig()

        # Make config_file point to a directory to cause OSError
        manager.config_file = temp_dir  # This is a directory

        # Should not raise exception, just print warning
        manager.save_config()
        # Since we can't easily test print output, just ensure no exception

    def test_load_config_with_missing_nested_configs(self, temp_dir):
        manager = ConfigManager(temp_dir)
        config_data = {
            "ui_theme": "light"
            # Missing file_ops, integrity, etc.
        }

        with open(manager.config_file, 'w') as f:
            json.dump(config_data, f)

        config = manager.load_config()
        assert config.ui_theme == "light"
        # Should still have default nested configs
        assert isinstance(config.file_ops, FileOpsConfig)
        assert isinstance(config.integrity, IntegrityConfig)

    def test_config_with_list_fields(self, temp_dir):
        manager = ConfigManager(temp_dir)
        config_data = {
            "file_ops": {
                "exclude_patterns": ["*.custom"]
            },
            "integrity": {
                "default_algorithms": ["sha1"]
            }
        }

        with open(manager.config_file, 'w') as f:
            json.dump(config_data, f)

        config = manager.load_config()
        assert config.file_ops.exclude_patterns == ["*.custom"]
        assert config.integrity.default_algorithms == ["sha1"]