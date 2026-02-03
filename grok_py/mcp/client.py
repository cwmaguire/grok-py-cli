"""MCP (Model Context Protocol) client for integrating with MCP servers."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from grok_py.tools.base import ToolDefinition, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for connecting to MCP servers using the official MCP protocol."""

    def __init__(self, server_params: Union[StdioServerParameters, str], connect_timeout: float = 30.0, execute_timeout: float = 10.0, max_retries: int = 3):
        """Initialize MCP client.

        Args:
            server_params: Either StdioServerParameters for stdio servers or URL string for HTTP servers
            connect_timeout: Connection timeout in seconds
            execute_timeout: Execution timeout in seconds
            max_retries: Maximum number of reconnection attempts
        """
        self.server_params = server_params
        self.connect_timeout = connect_timeout
        self.execute_timeout = execute_timeout
        self.max_retries = max_retries
        self._read = None
        self._write = None
        self._session: Optional[ClientSession] = None
        self._connected = False

    def get_server_params_dict(self) -> Dict[str, Any]:
        """Get server parameters as a serializable dictionary for sandbox execution.

        Returns:
            Dictionary containing server parameters
        """
        if isinstance(self.server_params, str):
            return {"type": "sse", "url": self.server_params}
        else:
            # StdioServerParameters
            return {
                "type": "stdio",
                "command": self.server_params.command,
                "args": self.server_params.args,
                "env": dict(self.server_params.env) if self.server_params.env else None,
                "cwd": self.server_params.cwd,
                "encoding": self.server_params.encoding
            }

    async def connect(self) -> bool:
        """Connect to the MCP server and perform handshake with retry logic.

        Returns:
            True if connection and handshake successful, False otherwise
        """
        for attempt in range(self.max_retries + 1):
            try:
                if isinstance(self.server_params, StdioServerParameters):
                    # Stdio connection - create persistent session
                    self._read, self._write = await asyncio.wait_for(
                        stdio_client.__aenter__(self.server_params),
                        timeout=self.connect_timeout
                    )
                    self._session = ClientSession(self._read, self._write)
                    await asyncio.wait_for(
                        self._session.initialize(),
                        timeout=self.connect_timeout
                    )
                    self._connected = True
                    logger.info("Connected to MCP server via stdio")
                    return True
                else:
                    # HTTP/SSE connection - create persistent session
                    self._read, self._write = await asyncio.wait_for(
                        sse_client.__aenter__(self.server_params),
                        timeout=self.connect_timeout
                    )
                    self._session = ClientSession(self._read, self._write)
                    await asyncio.wait_for(
                        self._session.initialize(),
                        timeout=self.connect_timeout
                    )
                    self._connected = True
                    logger.info(f"Connected to MCP server at {self.server_params}")
                    return True

            except asyncio.TimeoutError:
                logger.warning(f"Connection attempt {attempt + 1} timed out")
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")

            if attempt < self.max_retries:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying connection in {wait_time} seconds...")
                await asyncio.sleep(wait_time)

        logger.error(f"Failed to connect after {self.max_retries + 1} attempts")
        self._connected = False
        return False

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self._session:
            # Close the session and underlying transport
            try:
                if hasattr(self, '_read') and hasattr(self, '_write'):
                    if isinstance(self.server_params, StdioServerParameters):
                        await stdio_client.__aexit__(None, None, None)
                    else:
                        await sse_client.__aexit__(None, None, None)
            except:
                pass
        self._connected = False
        self._session = None

    async def list_tools(self) -> List[ToolDefinition]:
        """List available tools from the MCP server.

        Returns:
            List of tool definitions
        """
        if not self._connected or not self._session:
            # Try to reconnect
            if not await self.connect():
                raise RuntimeError("Not connected to MCP server and reconnection failed")

        try:
            # Use the session to list tools with timeout
            tools_result = await asyncio.wait_for(
                self._session.list_tools(),
                timeout=self.execute_timeout
            )
            tools = []

            for tool in tools_result.tools:
                parameters = {}
                if tool.inputSchema and tool.inputSchema.get("properties"):
                    for param_name, param_schema in tool.inputSchema["properties"].items():
                        required = param_name in tool.inputSchema.get("required", [])
                        parameters[param_name] = ToolParameter(
                            name=param_name,
                            type=param_schema.get("type", "string"),
                            description=param_schema.get("description", ""),
                            required=required,
                            default=param_schema.get("default"),
                            enum=param_schema.get("enum")
                        )

                tool_def = ToolDefinition(
                    name=tool.name,
                    description=tool.description or "",
                    category="mcp",  # Default category for MCP tools
                    parameters=parameters
                )
                tools.append(tool_def)

            return tools
        except asyncio.TimeoutError:
            logger.error("Timeout while listing tools")
            self._connected = False  # Mark as disconnected
            return []
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            self._connected = False  # Mark as disconnected on error
            return []

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """Execute a tool on the MCP server.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        if not self._connected or not self._session:
            # Try to reconnect
            if not await self.connect():
                raise RuntimeError("Not connected to MCP server and reconnection failed")

        start_time = time.time()
        try:
            # Call the tool using the session with timeout
            result = await asyncio.wait_for(
                self._session.call_tool(tool_name, arguments=parameters),
                timeout=self.execute_timeout
            )

            # Process the result
            elapsed = time.time() - start_time
            logger.info(f"Tool {tool_name} executed in {elapsed:.2f}s")
            if result.isError:
                return ToolResult(
                    success=False,
                    error=str(result.content) if result.content else "Tool execution failed"
                )
            else:
                # Extract data from content
                data = None
                if result.content:
                    # Assuming text content for simplicity
                    if isinstance(result.content, list) and len(result.content) > 0:
                        data = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])

                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"tool": tool_name}
                )
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"Timeout while executing tool {tool_name} after {elapsed:.2f}s")
            self._connected = False  # Mark as disconnected
            return ToolResult(success=False, error="Tool execution timed out")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error executing tool {tool_name} after {elapsed:.2f}s: {e}")
            self._connected = False  # Mark as disconnected on error
            return ToolResult(success=False, error=str(e))

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected