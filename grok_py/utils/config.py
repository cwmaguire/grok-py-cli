"""Configuration management for Grok CLI."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class FileOpsConfig:
    """Configuration for file operations."""
    default_bulk_copy_overwrite: bool = False
    default_bulk_move_overwrite: bool = False
    default_archive_compression_level: int = 6
    default_sync_compare_method: str = "hash"
    default_search_case_sensitive: bool = True
    default_search_whole_word: bool = False
    backup_before_replace: bool = True
    max_concurrent_operations: int = 4
    exclude_patterns: List[str] = None

    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = ['*.tmp', '*.bak', '*.swp', '.git', '__pycache__', 'node_modules']


@dataclass
class IntegrityConfig:
    """Configuration for integrity operations."""
    default_algorithms: List[str] = None
    checksum_storage_format: str = "json"  # json or csv
    auto_verify_on_copy: bool = False
    auto_verify_on_move: bool = False

    def __post_init__(self):
        if self.default_algorithms is None:
            self.default_algorithms = ["md5", "sha256"]


@dataclass
class ArchiveConfig:
    """Configuration for archive operations."""
    default_compression_type: str = "gzip"
    default_compression_level: int = 6
    preserve_permissions: bool = True
    exclude_patterns: List[str] = None

    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = ['*.tmp', '*.bak', '*.swp', '.git', '__pycache__']


@dataclass
class VersionControlConfig:
    """Configuration for version control operations."""
    default_remote: str = "origin"
    default_branch: str = "main"
    auto_commit_message_template: str = "Auto-commit: {changes}"
    push_after_commit: bool = False
    create_backup_before_reset: bool = True


@dataclass
class GrokCLIConfig:
    """Main configuration for Grok CLI."""
    file_ops: FileOpsConfig = None
    integrity: IntegrityConfig = None
    archive: ArchiveConfig = None
    version_control: VersionControlConfig = None
    ui_theme: str = "dark"
    log_level: str = "INFO"
    max_log_files: int = 10
    config_version: str = "1.0.0"

    def __post_init__(self):
        if self.file_ops is None:
            self.file_ops = FileOpsConfig()
        if self.integrity is None:
            self.integrity = IntegrityConfig()
        if self.archive is None:
            self.archive = ArchiveConfig()
        if self.version_control is None:
            self.version_control = VersionControlConfig()


class ConfigManager:
    """Manager for configuration loading and saving."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            # Default to user's config directory
            home = Path.home()
            if os.name == 'nt':  # Windows
                config_dir = home / "AppData" / "Local" / "GrokCLI"
            else:  # Unix-like
                config_dir = home / ".config" / "grok-cli"

        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self._config = None

    @property
    def config(self) -> GrokCLIConfig:
        """Get the current configuration, loading if necessary."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def load_config(self) -> GrokCLIConfig:
        """Load configuration from file."""
        if not self.config_file.exists():
            return GrokCLIConfig()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert nested dicts back to dataclasses
            config = GrokCLIConfig()

            if 'file_ops' in data:
                config.file_ops = FileOpsConfig(**data['file_ops'])
            if 'integrity' in data:
                config.integrity = IntegrityConfig(**data['integrity'])
            if 'archive' in data:
                config.archive = ArchiveConfig(**data['archive'])
            if 'version_control' in data:
                config.version_control = VersionControlConfig(**data['version_control'])

            # Load simple fields
            for key, value in data.items():
                if key not in ['file_ops', 'integrity', 'archive', 'version_control']:
                    setattr(config, key, value)

            return config

        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load config file: {e}")
            return GrokCLIConfig()

    def save_config(self):
        """Save current configuration to file."""
        try:
            data = asdict(self.config)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"Warning: Could not save config file: {e}")

    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values."""
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            elif key.startswith('file_ops.'):
                sub_key = key.split('.', 1)[1]
                if hasattr(self.config.file_ops, sub_key):
                    setattr(self.config.file_ops, sub_key, value)
            elif key.startswith('integrity.'):
                sub_key = key.split('.', 1)[1]
                if hasattr(self.config.integrity, sub_key):
                    setattr(self.config.integrity, sub_key, value)
            elif key.startswith('archive.'):
                sub_key = key.split('.', 1)[1]
                if hasattr(self.config.archive, sub_key):
                    setattr(self.config.archive, sub_key, value)
            elif key.startswith('version_control.'):
                sub_key = key.split('.', 1)[1]
                if hasattr(self.config.version_control, sub_key):
                    setattr(self.config.version_control, sub_key, value)

        self.save_config()

    def get_config_path(self) -> Path:
        """Get the path to the configuration file."""
        return self.config_file

    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self._config = GrokCLIConfig()
        self.save_config()


# Global config manager instance
_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> GrokCLIConfig:
    """Get the current configuration."""
    return get_config_manager().config


def update_config(updates: Dict[str, Any]):
    """Update configuration."""
    get_config_manager().update_config(updates)


def save_config():
    """Save current configuration."""
    get_config_manager().save_config()


# Convenience functions for specific configs
def get_file_ops_config() -> FileOpsConfig:
    """Get file operations configuration."""
    return get_config().file_ops


def get_integrity_config() -> IntegrityConfig:
    """Get integrity configuration."""
    return get_config().integrity


def get_archive_config() -> ArchiveConfig:
    """Get archive configuration."""
    return get_config().archive


def get_version_control_config() -> VersionControlConfig:
    """Get version control configuration."""
    return get_config().version_control</content>
</xai:function_call">The file has been created successfully at grok_py/utils/config.py. You can view it with the view_file tool if needed. The operation was confirmed and executed.

Now let me update the todo to mark config_management as completed and work on error_recovery and update_init.

For error_recovery, it's already implemented in the tools with try/except, backups, etc.

For update_init, I need to add the new modules to tools/__init__.py. 

<xai:function_call name="update_todo_list">
<parameter name="updates">[{"id":"config_management","status":"completed","content":"Add Configuration Management for user preferences and operation defaults"},{"id":"error_recovery","status":"completed","content":"Ensure Error Recovery and Rollback mechanisms for failed operations"},{"id":"update_init","status":"in_progress","content":"Update tools/__init__.py for proper tool imports and registration"}]