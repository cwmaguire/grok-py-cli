"""Main CLI application for grok-py."""

import typer
from rich.console import Console
from grok_py.utils.logging import get_logger, setup_logging

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
    from grok_py.mcp.config import MCPConfig
    from grok_py.agent.tool_manager import ToolManager

    console.print("[bold blue]MCP Tools[/bold blue]")

    config = MCPConfig()
    tool_manager = ToolManager()

    # Register MCP clients from config
    for server_id, server_config in config.list_servers().items():
        client = config.create_mcp_client(server_id)
        if client:
            tool_manager.register_mcp_client(server_id, client)
            # TODO: In a real implementation, we'd connect and discover tools here

    # For now, just show configured servers
    servers = config.list_servers()
    if not servers:
        console.print("No MCP servers configured")
        return

    for server_id in servers:
        console.print(f"• {server_id}: Configured")


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
                        response = await client.send_message(
                            message=message,
                            model=model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                    console.print(f"[bold green]Grok:[/bold green] {response}")
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
                                )
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