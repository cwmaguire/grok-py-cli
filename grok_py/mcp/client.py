"""MCP (Model Context Protocol) client for integrating with MCP servers."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from grok_py.tools.base import ToolDefinition, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for connecting to MCP servers."""

    def __init__(self, server_url: str, timeout: float = 30.0):
        """Initialize MCP client.

        Args:
            server_url: URL of the MCP server
            timeout: Request timeout in seconds
        """
        self.server_url = server_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to the MCP server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=self.timeout)

            # Test connection with a ping or basic request
            response = await self._client.get(f"{self.server_url}/health")
            if response.status_code == 200:
                self._connected = True
                logger.info(f"Connected to MCP server at {self.server_url}")
                return True
            else:
                logger.error(f"Failed to connect to MCP server: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def list_tools(self) -> List[ToolDefinition]:
        """List available tools from the MCP server.

        Returns:
            List of tool definitions
        """
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        try:
            response = await self._client.get(f"{self.server_url}/tools")
            response.raise_for_status()

            data = response.json()
            tools = []
            for tool_data in data.get("tools", []):
                parameters = {}
                for param_name, param_data in tool_data.get("parameters", {}).items():
                    if isinstance(param_data, dict):
                        parameters[param_name] = ToolParameter(
                            name=param_name,
                            type=param_data.get("type", "string"),
                            description=param_data.get("description", ""),
                            required=param_data.get("required", False),
                            default=param_data.get("default"),
                            enum=param_data.get("enum")
                        )
                    else:
                        # If already ToolParameter, use as is
                        parameters[param_name] = param_data

                tool = ToolDefinition(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    category=tool_data.get("category", "utility"),
                    parameters=parameters
                )
                tools.append(tool)

            return tools
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """Execute a tool on the MCP server.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        try:
            payload = {
                "tool": tool_name,
                "parameters": parameters
            }

            response = await self._client.post(
                f"{self.server_url}/execute",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            return ToolResult(
                success=data.get("success", False),
                data=data.get("data"),
                error=data.get("error"),
                metadata=data.get("metadata", {})
            )
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return ToolResult(success=False, error=str(e))

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected