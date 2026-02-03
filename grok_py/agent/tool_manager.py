"""Tool manager for registering, discovering, and executing tools."""

import asyncio
import importlib
import inspect
import json
import logging
import pkgutil
from typing import Any, Dict, List, Optional, Type, Union
from concurrent.futures import ThreadPoolExecutor

from grok_py.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from grok_py.mcp.client import MCPClient
from grok_py.tools.code_execution import CodeExecutionTool


logger = logging.getLogger(__name__)


class ToolManager:
    """Manager for tool registration, discovery, and execution."""

    def __init__(self, max_workers: int = 4):
        """Initialize the tool manager.

        Args:
            max_workers: Maximum number of worker threads for sync tool execution
        """
        self._tools: Dict[str, BaseTool] = {}
        self._tool_definitions: Dict[str, ToolDefinition] = {}
        self._mcp_clients: Dict[str, MCPClient] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    async def cleanup(self):
        """Clean up resources."""
        self._executor.shutdown(wait=True)

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool instance.

        Args:
            tool: Tool instance to register
        """
        if tool.name in self._tools:
            self.logger.warning(f"Tool '{tool.name}' already registered, overwriting")

        self._tools[tool.name] = tool
        self._tool_definitions[tool.name] = tool.get_definition()
        self.logger.info(f"Registered tool: {tool.name} ({tool.category.value})")

    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool.

        Args:
            tool_name: Name of tool to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            del self._tool_definitions[tool_name]
            self.logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False

    def register_mcp_client(self, client_id: str, mcp_client: MCPClient) -> None:
        """Register an MCP client.

        Args:
            client_id: Unique identifier for the MCP client
            mcp_client: MCP client instance
        """
        if client_id in self._mcp_clients:
            self.logger.warning(f"MCP client '{client_id}' already registered, overwriting")

        self._mcp_clients[client_id] = mcp_client
        self.logger.info(f"Registered MCP client: {client_id}")

    def unregister_mcp_client(self, client_id: str) -> bool:
        """Unregister an MCP client.

        Args:
            client_id: Identifier of MCP client to unregister

        Returns:
            True if client was unregistered, False if not found
        """
        if client_id in self._mcp_clients:
            # Disconnect the client
            asyncio.create_task(self._mcp_clients[client_id].disconnect())
            del self._mcp_clients[client_id]
            self.logger.info(f"Unregistered MCP client: {client_id}")
            return True
        return False

    async def discover_mcp_tools(self, client_id: str, mcp_config: Optional['MCPConfig'] = None) -> int:
        """Discover and register tools from an MCP client.

        Args:
            client_id: ID of the registered MCP client
            mcp_config: MCP configuration for applying tool defaults

        Returns:
            Number of tools discovered and registered
        """
        if client_id not in self._mcp_clients:
            self.logger.error(f"MCP client '{client_id}' not found")
            return 0

        client = self._mcp_clients[client_id]
        tools_registered = 0

        try:
            # Get tools from MCP client
            mcp_tools = await client.list_tools()

            for tool_def in mcp_tools:
                # Apply user-defined defaults if config provided
                if mcp_config:
                    tool_key = f"{client_id}.{tool_def.name}"
                    defaults = mcp_config.get_tool_defaults().get(tool_key, {})
                    # Update parameter defaults
                    for param_name, param in tool_def.parameters.items():
                        if param_name in defaults:
                            param.default = defaults[param_name]

                # Create a wrapper for MCP tools
                mcp_tool = MCPToolWrapper(client, tool_def)
                tool_name = f"mcp_{client_id}_{tool_def.name}"

                # Register the wrapper as a tool
                self._tools[tool_name] = mcp_tool
                self._tool_definitions[tool_name] = tool_def
                tools_registered += 1

            self.logger.info(f"Discovered and registered {tools_registered} MCP tools from {client_id}")
        except Exception as e:
            self.logger.error(f"Failed to discover tools from MCP client {client_id}: {e}")

        return tools_registered

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a registered tool by name.

        Args:
            tool_name: Name of tool to get

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def list_tools_by_category(self, category: ToolCategory) -> List[str]:
        """List tools by category.

        Args:
            category: Tool category to filter by

        Returns:
            List of tool names in the category
        """
        return [
            name for name, tool in self._tools.items()
            if tool.category == category
        ]

    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name.

        Args:
            tool_name: Name of tool

        Returns:
            Tool definition or None if not found
        """
        return self._tool_definitions.get(tool_name)

    def get_all_definitions(self) -> Dict[str, ToolDefinition]:
        """Get all tool definitions.

        Returns:
            Dictionary of tool names to definitions
        """
        return self._tool_definitions.copy()

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found",
                metadata={"available_tools": self.list_tools()}
            )

        self.logger.debug(f"Executing tool '{tool_name}' with parameters: {kwargs}")
        return await tool._execute_with_error_handling(**kwargs)

    async def execute_tools_parallel(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResult]:
        """Execute multiple tools in parallel.

        Args:
            tool_calls: List of tool call dictionaries with 'name' and 'parameters'

        Returns:
            List of tool results in the same order as input
        """
        tasks = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            parameters = tool_call.get("parameters", {})
            task = self.execute_tool(tool_name, **parameters)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tool_call = tool_calls[i]
                processed_results.append(ToolResult(
                    success=False,
                    error=f"Tool execution failed: {str(result)}",
                    metadata={"tool_call": tool_call}
                ))
            else:
                processed_results.append(result)

        return processed_results

    def discover_tools(self, package_name: str = "grok_py.tools") -> int:
        """Discover and register tools from a package.

        Args:
            package_name: Name of package to search for tools

        Returns:
            Number of tools discovered and registered
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            self.logger.error(f"Could not import package '{package_name}'")
            return 0

        tools_registered = 0

        # Walk through all modules in the package
        for _, module_name, _ in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            try:
                module = importlib.import_module(module_name)
                tools_registered += self._register_tools_from_module(module)
            except Exception as e:
                self.logger.warning(f"Failed to load tools from {module_name}: {e}")

        self.logger.info(f"Discovered and registered {tools_registered} tools from {package_name}")
        return tools_registered

    def _register_tools_from_module(self, module) -> int:
        """Register tools from a module.

        Args:
            module: Module to search for tools

        Returns:
            Number of tools registered
        """
        tools_registered = 0

        # Look for tool classes in the module
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and
                issubclass(obj, BaseTool) and
                obj != BaseTool):

                # Check if class has tool metadata
                if hasattr(obj, '_tool_category'):
                    try:
                        # Create instance with metadata
                        tool_name = getattr(obj, '_tool_name', obj.__name__.lower())
                        tool_description = getattr(obj, '_tool_description',
                                                 obj.__doc__ or f"{obj.__name__} tool")
                        tool_category = obj._tool_category

                        tool_instance = obj(
                            name=tool_name,
                            description=tool_description,
                            category=tool_category
                        )
                        self.register_tool(tool_instance)
                        tools_registered += 1

                    except Exception as e:
                        self.logger.error(f"Failed to register tool {name}: {e}")
                else:
                    # Try to create with default parameters
                    try:
                        # Assume tool classes have a default constructor
                        tool_instance = obj()
                        if isinstance(tool_instance, BaseTool):
                            self.register_tool(tool_instance)
                            tools_registered += 1
                    except Exception as e:
                        self.logger.debug(f"Could not auto-register tool {name}: {e}")

        return tools_registered

    def get_tool_stats(self) -> Dict[str, Any]:
        """Get statistics about registered tools.

        Returns:
            Dictionary with tool statistics
        """
        categories = {}
        total_tools = len(self._tools)

        for tool in self._tools.values():
            cat_name = tool.category.value
            categories[cat_name] = categories.get(cat_name, 0) + 1

        return {
            "total_tools": total_tools,
            "categories": categories,
            "tools": list(self._tools.keys())
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all registered tools.

        Returns:
            Dictionary with health status for each tool
        """
        health_results = {}

        for tool_name, tool in self._tools.items():
            try:
                # Simple health check - just verify tool can be called
                # In a real implementation, you might do more sophisticated checks
                definition = tool.get_definition()
                health_results[tool_name] = {
                    "status": "healthy",
                    "definition": definition.dict()
                }
            except Exception as e:
                health_results[tool_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }

        return health_results


class MCPToolWrapper(BaseTool):
    """Wrapper to make MCP tools compatible with the BaseTool interface."""

    def __init__(self, mcp_client: MCPClient, tool_definition: ToolDefinition):
        """Initialize MCP tool wrapper.

        Args:
            mcp_client: The MCP client to use for execution
            tool_definition: Definition of the MCP tool
        """
        self.mcp_client = mcp_client
        self.tool_definition = tool_definition
        self._name = tool_definition.name
        self._description = tool_definition.description
        self._category = tool_definition.category

    @property
    def name(self) -> str:
        """Tool name."""
        return self._name

    @property
    def description(self) -> str:
        """Tool description."""
        return self._description

    @property
    def category(self) -> ToolCategory:
        """Tool category."""
        return self._category

    def get_definition(self) -> ToolDefinition:
        """Get tool definition."""
        return self.tool_definition

    @staticmethod
    def generate_sandbox_code(server_params_dict: Dict[str, Any], tool_name: str, parameters: Dict[str, Any], timeout: float) -> str:
        """Generate Python code for sandboxed MCP tool execution.

        Args:
            server_params_dict: Serialized server parameters
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            timeout: Timeout for the operation

        Returns:
            Python code as string
        """
        import json
        params_json = json.dumps(server_params_dict)
        args_json = json.dumps(parameters)

        code = f"""
import asyncio
import json
import sys
from typing import Any, Dict

from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

async def main():
    try:
        server_params_dict = {params_json!r}
        tool_name = {tool_name!r}
        parameters = {args_json!r}
        timeout = {timeout!r}

        if server_params_dict["type"] == "sse":
            url = server_params_dict["url"]
            read, write = await asyncio.wait_for(
                sse_client.__aenter__(url),
                timeout=timeout
            )
        else:
            # stdio
            params = StdioServerParameters(
                command=server_params_dict["command"],
                args=server_params_dict["args"],
                env=server_params_dict["env"],
                cwd=server_params_dict["cwd"],
                encoding=server_params_dict["encoding"]
            )
            read, write = await asyncio.wait_for(
                stdio_client.__aenter__(params),
                timeout=timeout
            )

        session = ClientSession(read, write)
        await asyncio.wait_for(
            session.initialize(),
            timeout=timeout
        )

        result = await asyncio.wait_for(
            session.call_tool(tool_name, arguments=parameters),
            timeout=timeout
        )

        if result.isError:
            output = json.dumps({{
                "success": False,
                "error": str(result.content) if result.content else "Tool execution failed"
            }})
        else:
            data = None
            if result.content:
                if isinstance(result.content, list) and len(result.content) > 0:
                    data = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
            output = json.dumps({{
                "success": True,
                "data": data
            }})

        print(output)

    except Exception as e:
        error_output = json.dumps({{
            "success": False,
            "error": str(e)
        }})
        print(error_output)

if __name__ == "__main__":
    asyncio.run(main())
"""
        return code

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the MCP tool in a secure Docker container.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        try:
            # Get server params
            server_params_dict = self.mcp_client.get_server_params_dict()

            # Generate sandbox code
            code = self.generate_sandbox_code(
                server_params_dict,
                self.name,
                kwargs,
                self.mcp_client.timeout
            )

            # Execute in Docker sandbox
            execution_tool = CodeExecutionTool()
            result = await asyncio.to_thread(
                execution_tool.execute_sync,
                operation="run",
                code=code,
                language="python"
            )

            # Parse the JSON output
            if result.success and result.data:
                try:
                    output = json.loads(result.data.strip())
                    return ToolResult(
                        success=output.get("success", False),
                        data=output.get("data"),
                        error=output.get("error"),
                        metadata={"tool": self.name}
                    )
                except json.JSONDecodeError:
                    return ToolResult(
                        success=False,
                        error=f"Invalid JSON output from sandbox: {result.data}"
                    )
            else:
                return ToolResult(
                    success=False,
                    error=result.error or "Sandbox execution failed"
                )

        except Exception as e:
            logger.error(f"Error executing MCP tool {self.name}: {e}")
            return ToolResult(success=False, error=str(e))