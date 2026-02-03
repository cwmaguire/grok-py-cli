"""Configuration management for MCP servers."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml

from grok_py.mcp.client import MCPClient
from mcp import StdioServerParameters


class MCPConfig:
    """Configuration manager for MCP servers."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize MCP configuration.

        Args:
            config_file: Path to configuration file (default: ~/.grok/mcp_config.yaml)
        """
        if config_file is None:
            config_file = os.path.expanduser("~/.grok/mcp_config.yaml")

        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                if self.config_file.suffix in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif self.config_file.suffix == '.json':
                    return json.load(f)
        return {}

    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_file, 'w') as f:
            if self.config_file.suffix in ['.yaml', '.yml']:
                yaml.dump(self._config, f, default_flow_style=False)
            elif self.config_file.suffix == '.json':
                json.dump(self._config, f, indent=2)

    def add_server(self, server_id: str, server_config: Dict):
        """Add an MCP server configuration.

        Args:
            server_id: Unique identifier for the server
            server_config: Server configuration dictionary
        """
        if 'servers' not in self._config:
            self._config['servers'] = {}

        self._config['servers'][server_id] = server_config
        self._save_config()

    def remove_server(self, server_id: str) -> bool:
        """Remove an MCP server configuration.

        Args:
            server_id: ID of the server to remove

        Returns:
            True if server was removed, False if not found
        """
        if 'servers' in self._config and server_id in self._config['servers']:
            del self._config['servers'][server_id]
            self._save_config()
            return True
        return False

    def get_server_config(self, server_id: str) -> Optional[Dict]:
        """Get configuration for a specific server.

        Args:
            server_id: ID of the server

        Returns:
            Server configuration or None if not found
        """
        return self._config.get('servers', {}).get(server_id)

    def list_servers(self) -> Dict[str, Dict]:
        """List all configured servers.

        Returns:
            Dictionary of server configurations
        """
        return self._config.get('servers', {})

    def create_mcp_client(self, server_id: str) -> Optional[MCPClient]:
        """Create an MCP client from server configuration.

        Args:
            server_id: ID of the server

        Returns:
            MCPClient instance or None if configuration invalid
        """
        config = self.get_server_config(server_id)
        if not config:
            return None

        server_type = config.get('type', 'stdio')

        if server_type == 'stdio':
            command = config.get('command')
            args = config.get('args', [])
            if not command:
                return None

            server_params = StdioServerParameters(
                command=command,
                args=args
            )
        elif server_type == 'http':
            url = config.get('url')
            if not url:
                return None
            server_params = url
        else:
            return None

        timeout = config.get('timeout', 30.0)
        max_retries = config.get('max_retries', 3)

        return MCPClient(server_params, connect_timeout=timeout, max_retries=max_retries)