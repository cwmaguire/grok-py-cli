"""Unit tests for MCP functionality."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from grok_py.mcp.client import MCPClient
from grok_py.mcp.config import MCPConfig
from grok_py.tools.base import ToolDefinition, ToolResult


class TestMCPClient:
    """Test suite for MCPClient."""

    def test_initialization(self):
        """Test MCP client initialization."""
        client = MCPClient("http://localhost:3000")
        assert client.server_url == "http://localhost:3000"
        assert client.timeout == 30.0
        assert not client.is_connected
        assert client._client is None

    def test_initialization_with_timeout(self):
        """Test MCP client initialization with custom timeout."""
        client = MCPClient("http://localhost:3000", timeout=60.0)
        assert client.timeout == 60.0

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to MCP server."""
        client = MCPClient("http://localhost:3000")
        client._client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        client._client.get.return_value = mock_response

        result = await client.connect()

        assert result is True
        assert client.is_connected
        client._client.get.assert_called_once_with("http://localhost:3000/health")

    @pytest.mark.asyncio
    async def test_connect_failure_status(self):
        """Test connection failure due to bad status code."""
        client = MCPClient("http://localhost:3000")
        client._client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        client._client.get.return_value = mock_response

        result = await client.connect()

        assert result is False
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_connect_failure_exception(self):
        """Test connection failure due to exception."""
        client = MCPClient("http://localhost:3000")
        client._client = AsyncMock()
        client._client.get.side_effect = Exception("Connection error")

        result = await client.connect()

        assert result is False
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnecting from MCP server."""
        client = MCPClient("http://localhost:3000")
        mock_client = MagicMock()
        mock_client.aclose = AsyncMock()
        client._client = mock_client
        client._connected = True

        await client.disconnect()

        assert not client.is_connected
        assert client._client is None
        mock_client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_no_client(self):
        """Test disconnecting when no client exists."""
        client = MCPClient("http://localhost:3000")

        await client.disconnect()

        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_list_tools_not_connected(self):
        """Test listing tools when not connected."""
        client = MCPClient("http://localhost:3000")

        with pytest.raises(RuntimeError, match="Not connected to MCP server"):
            await client.list_tools()

    @pytest.mark.asyncio
    async def test_list_tools_success(self):
        """Test successful tool listing."""
        client = MCPClient("http://localhost:3000")
        client._connected = True
        client._client = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tools": [
                {
                    "name": "test_tool",
                    "description": "A test tool",
                    "category": "utility",
                    "parameters": {"param1": {"type": "string", "description": "A parameter"}}
                }
            ]
        }
        client._client.get.return_value = mock_response

        tools = await client.list_tools()

        assert len(tools) == 1
        assert isinstance(tools[0], ToolDefinition)
        assert tools[0].name == "test_tool"
        assert tools[0].description == "A test tool"
        assert tools[0].category == "utility"

    @pytest.mark.asyncio
    async def test_list_tools_failure(self):
        """Test tool listing failure."""
        client = MCPClient("http://localhost:3000")
        client._connected = True
        client._client = AsyncMock()
        client._client.get.side_effect = Exception("Request failed")

        tools = await client.list_tools()

        assert tools == []

    @pytest.mark.asyncio
    async def test_execute_tool_not_connected(self):
        """Test executing tool when not connected."""
        client = MCPClient("http://localhost:3000")

        with pytest.raises(RuntimeError, match="Not connected to MCP server"):
            await client.execute_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test successful tool execution."""
        client = MCPClient("http://localhost:3000")
        client._connected = True
        client._client = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {"result": "ok"},
            "metadata": {"time": "1s"}
        }
        client._client.post.return_value = mock_response

        result = await client.execute_tool("test_tool", {"param": "value"})

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == {"result": "ok"}
        assert result.metadata == {"time": "1s"}

    @pytest.mark.asyncio
    async def test_execute_tool_failure(self):
        """Test tool execution failure."""
        client = MCPClient("http://localhost:3000")
        client._connected = True
        client._client = AsyncMock()
        client._client.post.side_effect = Exception("Execution failed")

        result = await client.execute_tool("test_tool", {"param": "value"})

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Execution failed" in result.error

    def test_is_connected_property(self):
        """Test is_connected property."""
        client = MCPClient("http://localhost:3000")
        assert not client.is_connected

        client._connected = True
        assert client.is_connected


class TestMCPConfig:
    """Test suite for MCPConfig."""

    def test_initialization_default_config(self):
        """Test MCP config initialization with default config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "mcp_config.yaml"
            config = MCPConfig(str(config_file))
            assert config.config_file == config_file
            assert config._config == {}

    def test_load_config_yaml(self):
        """Test loading YAML configuration."""
        config_data = {
            "servers": {
                "test_server": {
                    "type": "stdio",
                    "command": "test_cmd"
                }
            },
            "tool_defaults": {
                "test_server.tool1": {
                    "param1": "default_value"
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = Path(f.name)

        try:
            config = MCPConfig(str(config_file))
            assert config.list_servers() == config_data["servers"]
            assert config.get_tool_defaults() == config_data["tool_defaults"]
        finally:
            config_file.unlink()

    def test_get_tool_defaults_empty(self):
        """Test getting tool defaults when none configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "mcp_config.yaml"
            config = MCPConfig(str(config_file))
            assert config.get_tool_defaults() == {}

    def test_add_server(self):
        """Test adding a server configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "mcp_config.yaml"
            config = MCPConfig(str(config_file))

            server_config = {
                "type": "stdio",
                "command": "test_cmd",
                "timeout": 30.0
            }
            config.add_server("test_server", server_config)

            assert config.get_server_config("test_server") == server_config
            # Check file was saved
            assert config_file.exists()
            with open(config_file, 'r') as f:
                saved_config = yaml.safe_load(f)
                assert saved_config["servers"]["test_server"] == server_config