"""Unit tests for MCP client functionality."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mcp import ClientSession, StdioServerParameters
from grok_py.mcp.client import MCPClient
from grok_py.agent.tool_manager import MCPToolWrapper


class TestMCPClientHandshake:
    """Test cases for MCP client handshake and connection establishment."""

    @pytest.mark.asyncio
    async def test_successful_handshake_stdio(self):
        """Test successful establishment of MCP connection via stdio."""
        server_params = StdioServerParameters(
            command="echo",
            args=["hello"]
        )

        client = MCPClient(server_params)

        # Mock the stdio_client context manager
        with patch('grok_py.mcp.client.stdio_client') as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.__aenter__.return_value = (mock_read, mock_write)

            # Mock session initialization
            with patch('grok_py.mcp.client.ClientSession') as mock_session_cls:
                mock_session = MagicMock()
                mock_session.initialize = AsyncMock()
                mock_session_cls.return_value = mock_session

                result = await client.connect()
                assert result is True
                assert client.is_connected is True
                mock_session.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_handshake_sse(self):
        """Test successful establishment of MCP connection via SSE."""
        server_url = "http://example.com/mcp"

        client = MCPClient(server_url)

        # Mock the sse_client context manager
        with patch('grok_py.mcp.client.sse_client') as mock_sse:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_sse.__aenter__.return_value = (mock_read, mock_write)

            # Mock session initialization
            with patch('grok_py.mcp.client.ClientSession') as mock_session_cls:
                mock_session = MagicMock()
                mock_session.initialize = AsyncMock()
                mock_session_cls.return_value = mock_session

                result = await client.connect()
                assert result is True
                assert client.is_connected is True
                mock_session.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_handshake_with_invalid_server(self):
        """Test handshake failure with invalid server."""
        server_params = StdioServerParameters(
            command="invalid_command"
        )

        client = MCPClient(server_params)

        # Mock failure
        with patch('grok_py.mcp.client.stdio_client') as mock_stdio:
            mock_stdio.__aenter__.side_effect = Exception("Command not found")

            result = await client.connect()
            assert result is False
            assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_handshake_timeout(self):
        """Test handshake timeout handling."""
        server_params = StdioServerParameters(
            command="sleep",
            args=["10"]
        )

        client = MCPClient(server_params, timeout=0.1)

        # Mock timeout
        with patch('grok_py.mcp.client.stdio_client') as mock_stdio:
            mock_stdio.__aenter__.side_effect = asyncio.TimeoutError()

            result = await client.connect()
            assert result is False
            assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_connection_retry_logic(self):
        """Test that connection retries on failure."""
        server_params = StdioServerParameters(
            command="failing_command"
        )

        client = MCPClient(server_params, max_retries=2)

        # Mock persistent failure
        with patch('grok_py.mcp.client.stdio_client') as mock_stdio:
            mock_stdio.__aenter__.side_effect = Exception("Command failed")

            with patch('asyncio.sleep') as mock_sleep:
                result = await client.connect()
                assert result is False
                # Should have tried max_retries + 1 times
                assert mock_stdio.__aenter__.call_count == 3
                # Should have slept for backoff
                assert mock_sleep.call_count == 2


class TestMCPCoreFunctionality:
    """Test cases for core MCP operations like listing and executing tools."""

    @pytest.fixture
    async def connected_client(self):
        """Fixture for a connected MCP client."""
        server_params = StdioServerParameters(command="test_server")
        client = MCPClient(server_params)

        # Mock connection
        with patch('grok_py.mcp.client.stdio_client') as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.__aenter__.return_value = (mock_read, mock_write)

            with patch('grok_py.mcp.client.ClientSession') as mock_session_cls:
                mock_session = MagicMock()
                mock_session.initialize = AsyncMock()
                mock_session_cls.return_value = mock_session
                client._session = mock_session
                client._connected = True

        return client

    @pytest.mark.asyncio
    async def test_list_tools_success(self, connected_client):
        """Test successful tool listing."""
        # Mock tools result
        mock_tools_result = MagicMock()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"}
            },
            "required": ["param1"]
        }
        mock_tools_result.tools = [mock_tool]

        connected_client._session.list_tools = AsyncMock(return_value=mock_tools_result)

        tools = await connected_client.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "test_tool"
        assert tools[0].description == "A test tool"
        assert "param1" in tools[0].parameters

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, connected_client):
        """Test successful tool execution."""
        # Mock execution result
        mock_result = MagicMock()
        mock_result.isError = False
        mock_content = MagicMock()
        mock_content.text = "Tool output"
        mock_result.content = [mock_content]

        connected_client._session.call_tool = AsyncMock(return_value=mock_result)

        result = await connected_client.execute_tool("test_tool", {"param": "value"})

        assert result.success is True
        assert result.data == "Tool output"
        assert result.metadata["tool"] == "test_tool"

    @pytest.mark.asyncio
    async def test_execute_tool_error(self, connected_client):
        """Test tool execution with error."""
        # Mock error result
        mock_result = MagicMock()
        mock_result.isError = True
        mock_result.content = "Tool failed"

        connected_client._session.call_tool = AsyncMock(return_value=mock_result)

        result = await connected_client.execute_tool("failing_tool", {})

        assert result.success is False
        assert "Tool failed" in result.error

    @pytest.mark.asyncio
    async def test_reconnection_on_disconnection(self, connected_client):
        """Test automatic reconnection when disconnected."""
        # Simulate disconnection
        connected_client._connected = False

        # Mock reconnection
        with patch.object(connected_client, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True

            # Mock successful tool listing after reconnect
            mock_tools_result = MagicMock()
            mock_tools_result.tools = []
            connected_client._session.list_tools = AsyncMock(return_value=mock_tools_result)

            tools = await connected_client.list_tools()

            mock_connect.assert_called_once()
            assert tools == []


@pytest.mark.integration
class TestMCPIntegration:
    """Integration tests with actual MCP server."""

    @pytest.mark.asyncio
    async def test_tool_discovery_with_test_server(self):
        """Test tool discovery with the test MCP server."""
        # This test requires the test server to be running
        # For now, it's a placeholder
        pytest.skip("Integration test requires running MCP server")

        # Example of how it would work:
        # server_params = StdioServerParameters(
        #     command="python",
        #     args=["tests/test_mcp_server.py"]
        # )
        # client = MCPClient(server_params)
        #
        # connected = await client.connect()
        # assert connected
        #
        # tools = await client.list_tools()
        # assert len(tools) == 3  # add_numbers, get_weather, search_files
        # assert any(t.name == "add_numbers" for t in tools)

    @pytest.mark.asyncio
    async def test_tool_execution_with_test_server(self):
        """Test tool execution with the test MCP server."""
        pytest.skip("Integration test requires running MCP server")

        # Example:
        # server_params = StdioServerParameters(
        #     command="python",
        #     args=["tests/test_mcp_server.py"]
        # )
        # client = MCPClient(server_params)
        #
        # await client.connect()
        # result = await client.execute_tool("add_numbers", {"a": 5, "b": 3})
        # assert result.success
        # assert result.data == 8


class TestMCPClientServerParams:
    """Test cases for MCP client server parameters serialization."""

    def test_get_server_params_dict_sse(self):
        """Test serialization of SSE server parameters."""
        client = MCPClient("http://example.com/mcp")
        params = client.get_server_params_dict()
        assert params == {"type": "sse", "url": "http://example.com/mcp"}

    def test_get_server_params_dict_stdio(self):
        """Test serialization of stdio server parameters."""
        server_params = StdioServerParameters(
            command="python",
            args=["server.py"],
            env={"PATH": "/usr/bin"},
            cwd="/home/user",
            encoding="utf-8"
        )
        client = MCPClient(server_params)
        params = client.get_server_params_dict()
        expected = {
            "type": "stdio",
            "command": "python",
            "args": ["server.py"],
            "env": {"PATH": "/usr/bin"},
            "cwd": "/home/user",
            "encoding": "utf-8"
        }
        assert params == expected


class TestMCPToolWrapperSecureExecution:
    """Test cases for secure MCP tool execution in Docker containers."""

    def test_generate_sandbox_code(self):
        """Test generation of sandbox execution code."""
        server_params = {"type": "sse", "url": "http://test.com"}
        code = MCPToolWrapper.generate_sandbox_code(
            server_params, "test_tool", {"param": "value"}, 30.0
        )

        assert "import asyncio" in code
        assert "http://test.com" in code
        assert "test_tool" in code
        assert '"param": "value"' in code
        assert "asyncio.run(main())" in code

    @pytest.mark.asyncio
    @patch('grok_py.agent.tool_manager.CodeExecutionTool')
    async def test_secure_execute_success(self, mock_code_tool_cls):
        """Test successful secure tool execution."""
        # Mock the code execution tool
        mock_tool = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = '{"success": true, "data": "output"}'
        mock_result.error = None
        mock_tool.execute_sync.return_value = mock_result
        mock_code_tool_cls.return_value = mock_tool

        # Create wrapper
        server_params = StdioServerParameters(command="echo", args=["test"])
        client = MCPClient(server_params)
        tool_def = MagicMock()
        tool_def.name = "test_tool"
        wrapper = MCPToolWrapper(client, tool_def)

        result = await wrapper.execute(param="value")

        assert result.success is True
        assert result.data == "output"
        mock_tool.execute_sync.assert_called_once()

    @pytest.mark.asyncio
    @patch('grok_py.agent.tool_manager.CodeExecutionTool')
    async def test_secure_execute_error(self, mock_code_tool_cls):
        """Test secure tool execution with error."""
        # Mock the code execution tool with error
        mock_tool = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = '{"success": false, "error": "Tool failed"}'
        mock_tool.execute_sync.return_value = mock_result
        mock_code_tool_cls.return_value = mock_tool

        # Create wrapper
        client = MCPClient("http://test.com")
        tool_def = MagicMock()
        tool_def.name = "failing_tool"
        wrapper = MCPToolWrapper(client, tool_def)

        result = await wrapper.execute()

        assert result.success is False
        assert result.error == "Tool failed"