"""Main CLI application for grok-py."""

import json
import typer
from rich.console import Console
from grok_py.utils.logging import get_logger, setup_logging
from grok_py.grok.client import MessageRole

# TODO: Import when implemented
# from grok_py.agent import grok_agent
# from grok_py.utils import settings

app = typer.Typer(
    name="grok-py",
    help="AI-powered terminal assistant - Python implementation of Grok CLI",
    add_completion=False,
)

# MCP subcommand group
mcp_app = typer.Typer(
    name="mcp",
    help="Manage MCP (Model Context Protocol) tools and servers",
)
app.add_typer(mcp_app)

console = Console()
setup_logging(log_file="grok_cli.log")
logger = get_logger(__name__)


@app.callback()
def callback():
    """Grok CLI - AI-powered terminal assistant."""
    pass


@mcp_app.command("list-tools")
def mcp_list_tools():
    """List all available MCP tools."""
    import asyncio
    from grok_py.mcp.config import MCPConfig
    from grok_py.agent.tool_manager import ToolManager

    console.print("[bold blue]MCP Tools[/bold blue]")

    config = MCPConfig()
    tool_manager = ToolManager()

    servers = config.list_servers()
    if not servers:
        console.print("No MCP servers configured")
        return

    async def discover_and_list():
        # Register MCP clients from config
        for server_id, server_config in servers.items():
            client = config.create_mcp_client(server_id)
            if client:
                tool_manager.register_mcp_client(server_id, client)
                # Discover tools from this client
                try:
                    tools_count = await tool_manager.discover_mcp_tools(server_id, config)
                    console.print(f"• {server_id}: {tools_count} tools discovered")
                except Exception as e:
                    console.print(f"• {server_id}: Error discovering tools - {e}")
            else:
                console.print(f"• {server_id}: Failed to create client")

        # List discovered tools
        tool_definitions = tool_manager.get_all_definitions()
        mcp_tools = {name: defn for name, defn in tool_definitions.items() if name.startswith('mcp_')}

        if not mcp_tools:
            console.print("No MCP tools discovered")
            return

        console.print(f"\n[bold]Discovered {len(mcp_tools)} MCP tools:[/bold]")
        for tool_name, tool_def in mcp_tools.items():
            console.print(f"\n[cyan]{tool_name}[/cyan]")
            console.print(f"  Description: {tool_def.description}")
            if tool_def.parameters:
                console.print("  Parameters:")
                for param_name, param in tool_def.parameters.items():
                    default_str = f" (default: {param.default})" if param.default is not None else ""
                    console.print(f"    - {param_name}: {param.type} - {param.description}{default_str}")
            else:
                console.print("  Parameters: None")

    asyncio.run(discover_and_list())


@mcp_app.command("add-server")
def mcp_add_server(
    server_id: str = typer.Argument(..., help="Unique ID for the MCP server"),
    command: str = typer.Option(None, "--command", "-c", help="Command to run the MCP server (for stdio)"),
    args: str = typer.Option("", "--args", "-a", help="Arguments for the command (space-separated)"),
    url: str = typer.Option(None, "--url", "-u", help="HTTP URL for the MCP server"),
    timeout: float = typer.Option(30.0, "--timeout", "-t", help="Timeout in seconds"),
    max_retries: int = typer.Option(3, "--max-retries", "-r", help="Maximum retry attempts"),
):
    """Add an MCP server."""
    from grok_py.mcp.config import MCPConfig

    config = MCPConfig()

    if command and url:
        console.print("[red]Error: Cannot specify both command and URL[/red]")
        return
    if not command and not url:
        console.print("[red]Error: Must specify either command or URL[/red]")
        return

    server_config = {
        "timeout": timeout,
        "max_retries": max_retries,
    }

    if command:
        server_config.update({
            "type": "stdio",
            "command": command,
            "args": args.split() if args else [],
        })
    else:
        server_config.update({
            "type": "http",
            "url": url,
        })

    try:
        config.add_server(server_id, server_config)
        console.print(f"[green]✓[/green] Added MCP server: {server_id}")
        console.print(f"  Type: {server_config['type']}")
        if command:
            console.print(f"  Command: {command} {' '.join(server_config['args'])}")
        else:
            console.print(f"  URL: {url}")
    except Exception as e:
        console.print(f"[red]Error adding server: {e}[/red]")


@mcp_app.command("remove-server")
def mcp_remove_server(
    server_id: str = typer.Argument(..., help="ID of the MCP server to remove"),
):
    """Remove an MCP server."""
    from grok_py.mcp.config import MCPConfig

    config = MCPConfig()

    if config.remove_server(server_id):
        console.print(f"[green]✓[/green] Removed MCP server: {server_id}")
    else:
        console.print(f"[red]Server '{server_id}' not found[/red]")


@mcp_app.command("list-servers")
def mcp_list_servers():
    """List configured MCP servers."""
    from grok_py.mcp.config import MCPConfig

    config = MCPConfig()
    servers = config.list_servers()

    console.print("[bold blue]MCP Servers[/bold blue]")

    if not servers:
        console.print("No MCP servers configured")
        return

    for server_id, server_config in servers.items():
        console.print(f"[bold]{server_id}[/bold]")
        console.print(f"  Type: {server_config.get('type', 'unknown')}")
        if server_config.get('type') == 'stdio':
            console.print(f"  Command: {server_config.get('command', 'N/A')}")
            args = server_config.get('args', [])
            if args:
                console.print(f"  Args: {' '.join(args)}")
        elif server_config.get('type') == 'http':
            console.print(f"  URL: {server_config.get('url', 'N/A')}")
        console.print(f"  Timeout: {server_config.get('timeout', 30.0)}s")
        console.print(f"  Max retries: {server_config.get('max_retries', 3)}")
        console.print()


@app.command()
def chat(
    message: str = typer.Argument(None, help="Message to send to Grok"),
    interactive: bool = typer.Option(True, "--interactive/--non-interactive", help="Run in interactive mode"),
    model: str = typer.Option("grok-3", "--model", "-m", help="Grok model to use"),
    temperature: float = typer.Option(0.7, "--temperature", "-t", help="Temperature for response generation"),
    max_tokens: int = typer.Option(None, "--max-tokens", help="Maximum tokens in response"),
    mock: bool = typer.Option(False, "--mock", help="Use mock responses for testing"),
):
    """Start a chat session with Grok."""
    console.print("[bold blue]Grok CLI[/bold blue] - Python Implementation")
    console.print("Initializing...")

    async def run_chat():
        logger.info("Starting chat session")
        try:
            # Initialize tools if not mock
            tools = None
            if not mock:
                from grok_py.mcp.config import MCPConfig
                from grok_py.agent.tool_manager import ToolManager

                config = MCPConfig()
                tool_manager = ToolManager()

                servers = config.list_servers()
                if servers:
                    console.print("Discovering MCP tools...")
                    # Register MCP clients from config
                    for server_id, server_config in servers.items():
                        client_mcp = config.create_mcp_client(server_id)
                        if client_mcp:
                            tool_manager.register_mcp_client(server_id, client_mcp)
                            # Discover tools from this client
                            try:
                                tools_count = await tool_manager.discover_mcp_tools(server_id, config)
                                console.print(f"  • {server_id}: {tools_count} tools discovered")
                            except Exception as e:
                                console.print(f"  • {server_id}: Error discovering tools - {e}")

                    # Convert tool definitions to OpenAI format
                    tool_definitions = tool_manager.get_all_definitions()
                    if tool_definitions:
                        tools = []
                        for tool_name, tool_def in tool_definitions.items():
                            # Convert ToolDefinition to OpenAI function format
                            function_def = {
                                "name": tool_name,
                                "description": tool_def.description,
                                "parameters": {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            }

                            for param_name, param in tool_def.parameters.items():
                                function_def["parameters"]["properties"][param_name] = {
                                    "type": param.type,
                                    "description": param.description
                                }
                                if param.required:
                                    function_def["parameters"]["required"].append(param_name)
                                if param.default is not None:
                                    function_def["parameters"]["properties"][param_name]["default"] = param.default
                                if param.enum:
                                    function_def["parameters"]["properties"][param_name]["enum"] = param.enum

                            tools.append({
                                "type": "function",
                                "function": function_def
                            })
                        console.print(f"Prepared {len(tools)} tools for Grok")
                        logger.debug(f"Tools: {tools}")

            if mock:
                # Mock client for testing
                class MockClient:
                    async def send_message(self, message, **kwargs):
                        await asyncio.sleep(0.5)  # Simulate delay
                        return f"Mock response to: {message}"
                    async def __aenter__(self):
                        return self
                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        pass

                client = MockClient()
            else:
                from grok_py.grok.client import GrokClient
                client = GrokClient()

            async with client:
                if message:
                    # Single message mode
                    with console.status("[bold green]Thinking..."):
                        try:
                            response = await client.send_message(
                                message=message,
                                model=model,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                tools=tools,
                            )
                            console.print(f"[bold green]Grok:[/bold green] {response}")
                        except Exception as e:
                            console.print(f"[red]Error: {e}[/red]")
                            import traceback
                            traceback.print_exc()
                else:
                    # Interactive mode with Rich UI
                    from grok_py.ui import ChatInterface, InputHandler

                    chat_ui = ChatInterface(console)
                    input_handler = InputHandler(console)

                    console.print("[bold green]Entering interactive chat mode. Type 'exit' or 'quit' to leave.[/bold green]")
                    console.print("Press F1 to toggle between chat and command modes.\n")

                    while True:
                        try:
                            logger.info("Waiting for user input")
                            # Display current chat state
                            chat_ui._update_display()

                            user_input = input_handler.get_input("You: ", chat_interface=chat_ui)
                            if not user_input or user_input.lower() in ['exit', 'quit']:
                                logger.info("User exited chat")
                                break

                            logger.info(f"User input: {user_input}")
                            # Add user message to chat
                            chat_ui.add_message("user", user_input)

                            # Display updated chat with user message
                            chat_ui._update_display()

                            logger.info("Sending message to Grok")
                            # Start spinner and set processing border
                            chat_ui.set_input_border_color("yellow")
                            await chat_ui.start_spinner(token_count=0)  # TODO: Get actual token count if available

                            try:
                                # Send message and get response
                                response = await client.send_message(
                                    message=user_input,
                                    model=model,
                                    temperature=temperature,
                                    max_tokens=max_tokens,
                                    stream=False,
                                    tools=tools,
                                )

                                # Handle tool calls if present
                                if response.startswith("Grok is calling tools:"):
                                    # Get tool calls from the last assistant message
                                    messages = client.get_conversation_messages()
                                    if messages:
                                        last_msg = messages[-1]
                                        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                                            tool_calls_data = last_msg.tool_calls
                                            # Execute tools
                                            tool_results = await tool_manager.execute_tools_parallel([
                                                {
                                                    "name": tc["function"]["name"],
                                                    "parameters": json.loads(tc["function"]["arguments"])
                                                }
                                                for tc in tool_calls_data
                                            ])

                                            # Add tool results to conversation
                                            for tc, result in zip(tool_calls_data, tool_results):
                                                tool_msg = Message(
                                                    role=MessageRole.TOOL,
                                                    content=json.dumps({
                                                        "success": result.success,
                                                        "data": result.data,
                                                        "error": result.error
                                                    }),
                                                    tool_call_id=tc["id"]
                                                )
                                                client.add_message_to_conversation(tool_msg)

                                            # Get follow-up response
                                            followup_result = await client.chat_completion(
                                                model=model,
                                                temperature=temperature,
                                                max_tokens=max_tokens,
                                                stream=False
                                            )

                                            if followup_result.choices and followup_result.choices[0].get("message", {}).get("content"):
                                                response = followup_result.choices[0]["message"]["content"]
                                            else:
                                                response = "Tool execution completed, but no follow-up response generated."
                                        else:
                                            response = "Tool calls detected but unable to execute."
                                    else:
                                        response = "Unable to retrieve tool calls for execution."
                                # TODO: Handle tool calls and display tool error messages in chat if tools fail
                            except Exception as tool_error:
                                # Placeholder for tool error handling
                                chat_ui.add_message("system", f"Tool error: {str(tool_error)}")
                                response = "I encountered an error while processing your request."
                            finally:
                                # Stop spinner and reset border
                                await chat_ui.stop_spinner()
                                chat_ui.set_input_border_color("blue")

                            logger.info(f"Received response: {response[:100]}...")
                            # Add assistant response to chat
                            chat_ui.add_message("assistant", response)

                        except KeyboardInterrupt:
                            logger.info("Chat interrupted by user")
                            chat_ui.add_message("system", "Chat interrupted. Type 'exit' to quit.")
                            continue
                        except Exception as e:
                            logger.error(f"Error in chat loop: {e}")
                            chat_ui.add_message("system", f"Error: {str(e)}")
                            continue
        except Exception as e:
            logger.error(f"Error in run_chat: {e}")
            # Stop the live display on error
            if 'chat_ui' in locals() and chat_ui.live:
                chat_ui.live.stop()
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Run the async function
    import asyncio
    asyncio.run(run_chat())


@app.command()
def version():
    """Show version information."""
    from grok_py import __version__
    console.print(f"grok-py version {__version__}")


def main():
    """Entry point for the CLI."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    main()