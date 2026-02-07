"""MCP (Model Context Protocol) client for integrating with MCP servers."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

import httpx

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

# Custom SSE client for HTTP MCP servers that already have session initialized
try:
    from aiosseclient import aiosseclient
except ImportError:
    aiosseclient = None

class WriteTransport:
    def __init__(self, client, url, headers):
        self.client = client
        self.url = url
        self.headers = headers

    async def send(self, message):
        # message is SessionMessage with .message being JSONRPCMessage
        real_message = message.message
        # The actual data is in root, which is JSONRPCRequest
        data = real_message.root.model_dump()
        # For requests, use Accept: application/json, text/event-stream
        headers = self.headers.copy()
        headers['Accept'] = 'application/json'
        await self.client.post(self.url, json=data, headers=headers)

class CustomSSEClient:
    def __init__(self, url, headers=None):
        if aiosseclient is None:
            raise ImportError("aiosseclient not installed")
        self.url = url
        self.headers = headers or {}
        self.client = None
        self.read_queue = asyncio.Queue()
        self.write_transport = None
        self.task = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient()
        # For write, create transport object
        self.write_transport = WriteTransport(self.client, self.url, self.headers)
        # For read, start SSE reading
        self.task = asyncio.create_task(self._read_sse())
        # Return read iterator and write transport
        return self._read_iter(), self.write_transport

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        if self.client:
            await self.client.aclose()

    async def _read_sse(self):
        try:
            async for event in aiosseclient(self.url, headers=self.headers):
                if event.event == 'message':
                    import json
                    data = json.loads(event.data)
                    message = types.JSONRPCMessage(**data)
                    await self.read_queue.put(message)
        except Exception as e:
            logger.warning(f"SSE read error: {e}")

    async def _read_iter(self):
        while True:
            yield await self.read_queue.get()

from grok_py.tools.base import ToolDefinition, ToolParameter, ToolResult, ToolCategory

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
        self.is_http = isinstance(self.server_params, str)
        self._read = None
        self._write = None
        self._session: Optional[ClientSession] = None
        self._connected = False
        self._cm = None
        self.session_id = None
        self.client: Optional[httpx.AsyncClient] = None
        self._request_id = 1

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
                    self._cm = stdio_client(self.server_params)
                    self._read, self._write = await asyncio.wait_for(
                        self._cm.__aenter__(),
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
                elif self.is_http:
                    # HTTP connection: initialize via POST for streamable-http
                    self.client = httpx.AsyncClient(timeout=self.execute_timeout)
                    init_data = {
                        "jsonrpc": "2.0",
                        "id": self._request_id,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "grok-py", "version": "0.1.0"}
                        }
                    }
                    headers = {"Accept": "application/json, text/event-stream"}
                    response = await self.client.post(self.server_params, json=init_data, headers=headers)
                    response.raise_for_status()

                    # Parse the initialize response to get server capabilities
                    init_response = response.json()
                    if init_response.get("result"):
                        # Store session info if available, but don't require it
                        self.session_id = response.headers.get("mcp-session-id")
                        self._request_id += 1
                        self._connected = True
                    else:
                        raise Exception(f"Initialize failed: {init_response.get('error', 'Unknown error')}")
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
        if self.client:
            try:
                await self.client.aclose()
            except:
                pass
        if self._session:
            # Close the session and underlying transport
            try:
                if hasattr(self, '_cm'):
                    await self._cm.__aexit__(None, None, None)
            except:
                pass
        self._connected = False
        self._session = None
        self._cm = None
        self.client = None
        self.session_id = None

    async def list_tools(self) -> List[ToolDefinition]:
        """List available tools from the MCP server.

        Returns:
            List of tool definitions
        """
        if not self._connected:
            # Try to reconnect
            if not await self.connect():
                raise RuntimeError("Not connected to MCP server and reconnection failed")

        try:
            if self.is_http:
                # HTTP: send tools/list request
                data = {
                    "jsonrpc": "2.0",
                    "id": self._request_id,
                    "method": "tools/list",
                    "params": {}
                }
                headers = {"Accept": "application/json, text/event-stream"}
                if self.session_id:
                    headers["Mcp-Session-Id"] = self.session_id
                response = await asyncio.wait_for(
                    self.client.post(self.server_params, json=data, headers=headers),
                    timeout=self.execute_timeout
                )
                response.raise_for_status()
                try:
                    rpc_result = response.json()
                except:
                    # Parse SSE response
                    text = response.text
                    if 'data: ' in text:
                        data_str = text.split('data: ')[1].strip()
                        rpc_result = json.loads(data_str)
                    else:
                        raise ValueError("Invalid response format")
                self._request_id += 1
                tools_data = rpc_result["result"]["tools"]
            else:
                # Stdio: use session
                tools_result = await asyncio.wait_for(
                    self._session.list_tools(),
                    timeout=self.execute_timeout
                )
                tools_data = tools_result.tools

            tools = []
            for tool in tools_data:
                parameters = {}
                input_schema = tool.get("inputSchema")
                if input_schema and input_schema.get("properties"):
                    for param_name, param_schema in input_schema["properties"].items():
                        required = param_name in input_schema.get("required", [])
                        parameters[param_name] = ToolParameter(
                            name=param_name,
                            type=param_schema.get("type", "string"),
                            description=param_schema.get("description", ""),
                            required=required,
                            default=param_schema.get("default"),
                            enum=param_schema.get("enum")
                        )

                tool_def = ToolDefinition(
                    name=tool.get("name", ""),
                    description=tool.get("description", ""),
                    category=ToolCategory.UTILITY,  # Default category for MCP tools
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
        if not self._connected:
            # Try to reconnect
            if not await self.connect():
                raise RuntimeError("Not connected to MCP server and reconnection failed")

        start_time = time.time()
        try:
            if self.is_http:
                # HTTP: send tools/call request
                data = {
                    "jsonrpc": "2.0",
                    "id": self._request_id,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": parameters
                    }
                }
                headers = {"Accept": "application/json, text/event-stream"}
                if self.session_id:
                    headers["Mcp-Session-Id"] = self.session_id
                response = await asyncio.wait_for(
                    self.client.post(self.server_params, json=data, headers=headers),
                    timeout=self.execute_timeout
                )
                response.raise_for_status()
                try:
                    rpc_result = response.json()
                except:
                    # Parse SSE response
                    text = response.text
                    if 'data: ' in text:
                        data_str = text.split('data: ')[1].strip()
                        rpc_result = json.loads(data_str)
                    else:
                        raise ValueError("Invalid response format")
                self._request_id += 1
                logger.info("Full MCP server response for tools/call: %s", json.dumps(rpc_result, indent=2))
                tool_result = rpc_result["result"]
            else:
                # Stdio: use session
                tool_result = await asyncio.wait_for(
                    self._session.call_tool(tool_name, arguments=parameters),
                    timeout=self.execute_timeout
                )

            # Process the result
            elapsed = time.time() - start_time
            logger.info(f"Tool {tool_name} executed in {elapsed:.2f}s")
            if self.is_http:
                if "isError" in tool_result and tool_result["isError"]:
                    return ToolResult(
                        success=False,
                        error=str(tool_result.get("content", "Tool execution failed"))
                    )
                else:
                    data = None
                    if tool_result.get("content"):
                        content = tool_result["content"]
                        if isinstance(content, list) and len(content) > 0:
                            data = content[0].get("text", str(content[0]))
                    return ToolResult(
                        success=True,
                        data=data,
                        metadata={"tool": tool_name}
                    )
            else:
                if tool_result.isError:
                    return ToolResult(
                        success=False,
                        error=str(tool_result.content) if tool_result.content else "Tool execution failed"
                    )
                else:
                    data = None
                    if tool_result.content:
                        if isinstance(tool_result.content, list) and len(tool_result.content) > 0:
                            data = tool_result.content[0].text if hasattr(tool_result.content[0], 'text') else str(tool_result.content[0])
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