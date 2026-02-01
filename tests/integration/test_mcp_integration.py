"""Integration tests for MCP client with mocked server responses."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from grok_py.mcp.client import MCPClient
from grok_py.tools.base import ToolResult


class TestMCPIntegration:
    """Integration tests for MCP client."""

    @pytest.fixture
    def client(self):
        """MCP client fixture."""
        return MCPClient("http://localhost:3000")

    async def test_full_connection_and_tool_execution_workflow(self, client):
        """Test full workflow: connect, list tools, execute tool."""
        # Mock httpx client
        mock_client = AsyncMock()
        client._client = mock_client

        # Mock health check
        health_response = MagicMock()
        health_response.status_code = 200
        health_response.json.return_value = {"status": "ok"}
        mock_client.get.return_value = health_response

        # Mock list tools
        tools_response = MagicMock()
        tools_response.status_code = 200
        tools_response.json.return_value = {
            "tools": [
                {
                    "name": "echo_tool",
                    "description": "Echoes input back",
                    "category": "utility",
                    "parameters": {
                        "message": {
                            "type": "string",
                            "description": "Message to echo",
                            "required": True
                        }
                    }
                }
            ]
        }
        mock_client.get.side_effect = [health_response, tools_response]

        # Mock tool execution
        execute_response = MagicMock()
        execute_response.status_code = 200
        execute_response.json.return_value = {
            "success": True,
            "data": {"echoed": "hello world"},
            "metadata": {"execution_time": "0.1s"}
        }
        mock_client.post.return_value = execute_response

        # Connect
        connected = await client.connect()
        assert connected
        assert client.is_connected

        # List tools
        tools = await client.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "echo_tool"
        assert tools[0].description == "Echoes input back"
        assert "message" in tools[0].parameters
        assert tools[0].parameters["message"].type == "string"
        assert tools[0].parameters["message"].required is True

        # Execute tool
        result = await client.execute_tool("echo_tool", {"message": "hello world"})
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == {"echoed": "hello world"}
        assert result.metadata == {"execution_time": "0.1s"}

        # Disconnect
        await client.disconnect()
        assert not client.is_connected

    async def test_connection_failure_handling(self, client):
        """Test handling of connection failures."""
        # Mock httpx client
        mock_client = AsyncMock()
        client._client = mock_client

        # Mock failed health check
        response = MagicMock()
        response.status_code = 503
        response.json.return_value = {"error": "Service unavailable"}
        mock_client.get.return_value = response

        connected = await client.connect()
        assert not connected
        assert not client.is_connected

    
    async def test_tool_execution_error_handling(self, client):
        """Test handling of tool execution errors."""
        # Mock httpx client
        mock_client = AsyncMock()
        client._client = mock_client

        # Mock successful connection
        health_response = MagicMock()
        health_response.status_code = 200
        health_response.json.return_value = {"status": "ok"}

        # Mock failed tool execution
        execute_response = MagicMock()
        execute_response.status_code = 400
        execute_response.json.return_value = {
            "success": False,
            "error": "Tool execution failed",
            "metadata": {"error_code": "TOOL_ERROR"}
        }

        mock_client.get.return_value = health_response
        mock_client.post.return_value = execute_response

        await client.connect()
        result = await client.execute_tool("failing_tool", {"param": "value"})

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert result.error == "Tool execution failed"
        assert result.metadata == {"error_code": "TOOL_ERROR"}

    
    async def test_multiple_tools_listing(self, client):
        """Test listing multiple tools from server."""
        # Mock httpx client
        mock_client = AsyncMock()
        client._client = mock_client

        # Mock health check
        health_response = MagicMock()
        health_response.status_code = 200
        health_response.json.return_value = {"status": "ok"}

        # Mock list tools with multiple tools
        tools_response = MagicMock()
        tools_response.status_code = 200
        tools_response.json.return_value = {
            "tools": [
                {
                    "name": "tool1",
                    "description": "First tool",
                    "category": "utility",
                    "parameters": {}
                },
                {
                    "name": "tool2",
                    "description": "Second tool",
                    "category": "development",
                    "parameters": {
                        "input": {
                            "type": "string",
                            "description": "Input parameter",
                            "required": False
                        }
                    }
                }
            ]
        }

        mock_client.get.side_effect = [health_response, tools_response]

        await client.connect()
        tools = await client.list_tools()

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "tool1" in tool_names
        assert "tool2" in tool_names

        tool2 = next(t for t in tools if t.name == "tool2")
        assert tool2.category == "development"
        assert "input" in tool2.parameters
        assert not tool2.parameters["input"].required

    
    async def test_network_timeout_handling(self, client):
        """Test handling of network timeouts."""
        # Mock httpx client
        mock_client = AsyncMock()
        client._client = mock_client

        # Mock timeout on health check
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")

        connected = await client.connect()
        assert not connected

    
    async def test_invalid_json_response_handling(self, client):
        """Test handling of invalid JSON responses."""
        # Mock httpx client
        mock_client = AsyncMock()
        client._client = mock_client

        # Mock health check with invalid JSON
        response = MagicMock()
        response.status_code = 200
        response.json.side_effect = ValueError("Invalid JSON")
        mock_client.get.return_value = response

        connected = await client.connect()
        assert not connected

    
    async def test_server_error_on_tools_list(self, client):
        """Test handling of server errors during tool listing."""
        # Mock httpx client
        mock_client = AsyncMock()
        client._client = mock_client

        # Mock health check
        health_response = MagicMock()
        health_response.status_code = 200
        health_response.json.return_value = {"status": "ok"}

        # Mock server error on tools list
        tools_response = MagicMock()
        tools_response.status_code = 500
        tools_response.json.return_value = {"error": "Internal server error"}
        tools_response.raise_for_status.side_effect = Exception("500")

        mock_client.get.side_effect = [health_response, tools_response]

        await client.connect()
        tools = await client.list_tools()

        # Should return empty list on error
        assert tools == []