"""
MCP CLI Configuration Management

Handles loading and saving of CLI configuration including session state.
"""

import logging
import json
import os
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger('mcp_cli.config')


class Config:
    """Configuration manager for MCP CLI"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            home = Path.home()
            self.config_dir = home / '.mcp-cli'
        else:
            self.config_dir = Path(config_dir)

        self.config_file = self.config_dir / 'config.json'
        self._config: Dict[str, Any] = {}

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
                logger.debug(f"Loaded config from {self.config_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load config file {self.config_file}: {e}")
                print(f"Warning: Could not load config file: {e}")
                self._config = {}
        else:
            logger.debug("Config file does not exist, starting with empty config")
            self._config = {}

    def _save_config(self) -> None:
        """Save configuration to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.debug(f"Saved config to {self.config_file}")
        except IOError as e:
            logger.error(f"Could not save config file {self.config_file}: {e}")
            print(f"Warning: Could not save config file: {e}")

    @property
    def session_id(self) -> Optional[str]:
        """Get current session ID"""
        return self._config.get('session_id')

    @session_id.setter
    def session_id(self, value: Optional[str]) -> None:
        """Set session ID"""
        if value is None:
            self._config.pop('session_id', None)
        else:
            self._config['session_id'] = value
        self._save_config()

    @property
    def server_url(self) -> str:
        """Get default server URL"""
        return self._config.get('server_url', 'http://localhost:8000/mcp')

    @server_url.setter
    def server_url(self, value: str) -> None:
        """Set default server URL"""
        self._config['server_url'] = value
        self._save_config()

    def get_server_config(self, server_url: str) -> Dict[str, Any]:
        """Get configuration for a specific server"""
        servers = self._config.get('servers', {})
        return servers.get(server_url, {})

    def set_server_config(self, server_url: str, config: Dict[str, Any]) -> None:
        """Set configuration for a specific server"""
        if 'servers' not in self._config:
            self._config['servers'] = {}
        self._config['servers'][server_url] = config
        self._save_config()

    def clear_session(self) -> None:
        """Clear current session"""
        self.session_id = None