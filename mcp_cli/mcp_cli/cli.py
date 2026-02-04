"""
MCP (Model Context Protocol) CLI

Command-line interface for interacting with MCP servers.
"""

import logging
import click
import requests
from rich.console import Console
from rich.table import Table
from typing import Optional
from .client import MCPClient
from .sse_handler import SSEHandler
from .config import Config

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_cli.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('mcp_cli')


@click.group()
@click.option('--server-url', default='http://localhost:8000/mcp', help='MCP server URL')
@click.pass_context
def cli(ctx, server_url):
    """MCP Client CLI - Interact with MCP servers via command line"""
    ctx.ensure_object(dict)
    ctx.obj['server_url'] = server_url
    ctx.obj['client'] = None  # MCPClient instance
    ctx.obj['sse_handler'] = None  # SSEHandler instance
    ctx.obj['config'] = Config()  # Configuration manager

    # Load or create session
    config = ctx.obj['config']
    if config.session_id:
        ctx.obj['session_id'] = config.session_id
    else:
        ctx.obj['session_id'] = None


# Placeholder for commands - to be implemented in next steps
@cli.command()
@click.pass_context
def init(ctx):
    """Initialize connection to MCP server"""
    server_url = ctx.obj['server_url']
    config = ctx.obj['config']

    logger.info(f"Initializing MCP connection to {server_url}")

    try:
        # Create client if not exists
        if ctx.obj['client'] is None:
            logger.debug("Creating new MCPClient instance")
            ctx.obj['client'] = MCPClient(server_url)

        client = ctx.obj['client']

        # Send initialize request
        with console.status("[bold green]Initializing connection..."):
            logger.debug("Sending initialize request")
            init_response = client.initialize()

        # Store session info
        ctx.obj['session_id'] = client.session_id
        if client.session_id:
            logger.info(f"Session ID established: {client.session_id}")
            config.session_id = client.session_id

        logger.info(f"Connected to server: {init_response.serverInfo.name} v{init_response.serverInfo.version}")

        # Display server information
        table = Table(title="MCP Server Info")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        table.add_row("Server Name", init_response.serverInfo.name)
        table.add_row("Server Version", init_response.serverInfo.version)
        table.add_row("Protocol Version", init_response.protocolVersion)

        if init_response.capabilities:
            caps = init_response.capabilities
            if caps.resources:
                table.add_row("Resources", "✓ Supported")
            if caps.tools:
                table.add_row("Tools", "✓ Supported")
            if caps.prompts:
                table.add_row("Prompts", "✓ Supported")
            if caps.logging:
                table.add_row("Logging", "✓ Supported")
            if caps.tasks:
                table.add_row("Tasks", "✓ Supported")

        console.print(table)

        # Store capabilities for later use
        ctx.obj['capabilities'] = init_response.capabilities

        console.print("[green]✓[/green] Successfully initialized MCP connection")
        logger.info("MCP initialization completed successfully")

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error during initialization: {e}")
        console.print(f"[red]✗[/red] Connection failed: Unable to connect to {server_url}")
        console.print("Make sure the MCP server is running and accessible.")
        raise click.Abort()
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout during initialization: {e}")
        console.print(f"[red]✗[/red] Connection timeout: Server at {server_url} did not respond")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {e}", exc_info=True)
        console.print(f"[red]✗[/red] Failed to initialize: {e}")
        raise click.Abort()


@cli.command()
@click.pass_context
def ping(ctx):
    """Send ping to MCP server"""
    client = ctx.obj.get('client')
    if not client:
        logger.warning("Ping attempted without initialization")
        console.print("[red]✗[/red] Not initialized. Run 'init' first.")
        raise click.Abort()

    logger.info("Sending ping request")

    try:
        with console.status("[bold green]Sending ping..."):
            response = client.send_request("ping")

        console.print("[green]✓[/green] Ping successful")
        logger.info("Ping completed successfully")
        if response:
            console.print(f"Response: {response}")

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error during ping: {e}")
        console.print(f"[red]✗[/red] Connection failed during ping")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Ping failed: {e}", exc_info=True)
        console.print(f"[red]✗[/red] Ping failed: {e}")
        raise click.Abort()


@cli.command()
@click.option('--cursor', help='Pagination cursor')
@click.option('--limit', type=int, help='Maximum number of resources to return')
@click.pass_context
def resources_list(ctx, cursor, limit):
    """List available resources"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]✗[/red] Not initialized. Run 'init' first.")
        raise click.Abort()

    try:
        params = {}
        if cursor:
            params['cursor'] = cursor
        if limit:
            params['limit'] = limit

        with console.status("[bold green]Fetching resources..."):
            response = client.send_request("resources/list", params)

        resources = response.get('resources', [])
        if not resources:
            console.print("No resources available")
            return

        table = Table(title="Available Resources")
        table.add_column("URI", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Description", style="white")
        table.add_column("MIME Type", style="yellow")

        for resource in resources:
            table.add_row(
                resource.get('uri', ''),
                resource.get('name', ''),
                resource.get('description', ''),
                resource.get('mimeType', '')
            )

        console.print(table)

        # Show pagination info if available
        if 'nextCursor' in response:
            console.print(f"Next cursor: {response['nextCursor']}")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list resources: {e}")
        raise click.Abort()


@cli.command()
@click.argument('uri')
@click.pass_context
def resources_read(ctx, uri):
    """Read a resource by URI"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]✗[/red] Not initialized. Run 'init' first.")
        raise click.Abort()

    try:
        with console.status(f"[bold green]Reading resource: {uri}"):
            response = client.send_request("resources/read", {"uri": uri})

        contents = response.get('contents', [])
        if not contents:
            console.print("No content returned")
            return

        for i, content in enumerate(contents):
            if i > 0:
                console.print()  # Separator between multiple contents

            content_type = content.get('type')

            if content_type == 'text':
                console.print(f"[bold cyan]Text Content:[/bold cyan]")
                console.print(content.get('text', ''))

            elif content_type == 'blob':
                console.print(f"[bold cyan]Binary Content:[/bold cyan]")
                console.print(f"MIME Type: {content.get('mimeType', 'unknown')}")
                blob_data = content.get('blob', '')
                console.print(f"Size: {len(blob_data)} bytes")
                # For binary data, we could save to file or show hex dump
                console.print(f"Data: {blob_data[:100]}{'...' if len(blob_data) > 100 else ''}")

            else:
                console.print(f"[yellow]Unknown content type: {content_type}[/yellow]")
                console.print(content)

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to read resource: {e}")
        raise click.Abort()


@cli.command()
@click.pass_context
def tools_list(ctx):
    """List available tools"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]✗[/red] Not initialized. Run 'init' first.")
        raise click.Abort()

    try:
        with console.status("[bold green]Fetching tools..."):
            response = client.send_request("tools/list")

        tools = response.get('tools', [])
        if not tools:
            console.print("No tools available")
            return

        table = Table(title="Available Tools")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Input Schema", style="yellow")

        for tool in tools:
            input_schema = tool.get('inputSchema', {})
            schema_desc = f"{input_schema.get('type', 'object')}"
            if 'properties' in input_schema:
                props = list(input_schema['properties'].keys())
                schema_desc += f" ({', '.join(props[:3])}{'...' if len(props) > 3 else ''})"

            table.add_row(
                tool.get('name', ''),
                tool.get('description', ''),
                schema_desc
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list tools: {e}")
        raise click.Abort()


@cli.command()
@click.argument('name')
@click.option('--arguments', help='JSON arguments for the tool call')
@click.pass_context
def tools_call(ctx, name, arguments):
    """Call a tool by name"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]✗[/red] Not initialized. Run 'init' first.")
        raise click.Abort()

    try:
        # Parse arguments
        args_dict = {}
        if arguments:
            import json
            try:
                args_dict = json.loads(arguments)
            except json.JSONDecodeError as e:
                console.print(f"[red]✗[/red] Invalid JSON arguments: {e}")
                raise click.Abort()

        params = {
            "name": name,
            "arguments": args_dict
        }

        with console.status(f"[bold green]Calling tool: {name}"):
            response = client.send_request("tools/call", params)

        # Handle response
        if 'content' in response:
            console.print(f"[green]✓[/green] Tool call successful")
            for content in response['content']:
                content_type = content.get('type')
                if content_type == 'text':
                    console.print(content.get('text', ''))
                elif content_type == 'image':
                    console.print(f"[cyan]Image:[/cyan] {content.get('data', '')[:50]}...")
                else:
                    console.print(f"[{content_type}]: {content}")
        else:
            # Could be async or error
            console.print("Tool call initiated (async or no immediate result)")
            console.print(f"Response: {response}")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to call tool: {e}")
        raise click.Abort()


@cli.command()
@click.pass_context
def prompts_list(ctx):
    """List available prompts"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]✗[/red] Not initialized. Run 'init' first.")
        raise click.Abort()

    try:
        with console.status("[bold green]Fetching prompts..."):
            response = client.send_request("prompts/list")

        prompts = response.get('prompts', [])
        if not prompts:
            console.print("No prompts available")
            return

        table = Table(title="Available Prompts")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Arguments", style="yellow")

        for prompt in prompts:
            args_desc = ""
            if 'arguments' in prompt:
                args = [f"{arg['name']} ({arg.get('description', '')})" for arg in prompt['arguments']]
                args_desc = ", ".join(args[:2]) + ("..." if len(args) > 2 else "")

            table.add_row(
                prompt.get('name', ''),
                prompt.get('description', ''),
                args_desc
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list prompts: {e}")
        raise click.Abort()


@cli.command()
@click.argument('name')
@click.option('--arguments', help='JSON arguments for the prompt')
@click.pass_context
def prompts_get(ctx, name, arguments):
    """Get a prompt by name"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]✗[/red] Not initialized. Run 'init' first.")
        raise click.Abort()

    try:
        # Parse arguments
        args_dict = {}
        if arguments:
            import json
            try:
                args_dict = json.loads(arguments)
            except json.JSONDecodeError as e:
                console.print(f"[red]✗[/red] Invalid JSON arguments: {e}")
                raise click.Abort()

        params = {
            "name": name,
            "arguments": args_dict
        }

        with console.status(f"[bold green]Getting prompt: {name}"):
            response = client.send_request("prompts/get", params)

        # Display the prompt
        if 'messages' in response:
            console.print(f"[green]✓[/green] Prompt retrieved: {name}")
            for message in response['messages']:
                role = message.get('role', 'unknown')
                content = message.get('content', '')

                console.print(f"[bold {role}]{role.upper()}:[/bold {role}]")
                if isinstance(content, str):
                    console.print(content)
                elif isinstance(content, list):
                    for item in content:
                        if item.get('type') == 'text':
                            console.print(item.get('text', ''))
                        else:
                            console.print(f"[{item.get('type')}]: {item}")
                console.print()
        else:
            console.print(f"Response: {response}")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to get prompt: {e}")
        raise click.Abort()


@cli.command()
@click.argument('uri')
@click.pass_context
def subscribe(ctx, uri):
    """Subscribe to resource updates"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]✗[/red] Not initialized. Run 'init' first.")
        raise click.Abort()

    try:
        # Send subscribe request
        with console.status(f"[bold green]Subscribing to: {uri}"):
            response = client.send_request("resources/subscribe", {"uri": uri})

        console.print(f"[green]✓[/green] Subscribed to resource: {uri}")

        # Start SSE handler if not already running
        if ctx.obj['sse_handler'] is None:
            server_url = ctx.obj['server_url']
            ctx.obj['sse_handler'] = SSEHandler(server_url)

            # Add callback for resource updates
            def on_resource_update(notification):
                method = notification.method
                params = notification.params or {}
                if method == "resources/updated":
                    updated_uri = params.get('uri')
                    console.print(f"[yellow]Resource updated:[/yellow] {updated_uri}")
                elif method == "resources/list_changed":
                    console.print("[yellow]Resource list changed[/yellow]")

            ctx.obj['sse_handler'].add_callback("resources/updated", on_resource_update)
            ctx.obj['sse_handler'].add_callback("resources/list_changed", on_resource_update)

        # Start listening
        ctx.obj['sse_handler'].start()
        console.print("[cyan]Listening for resource updates... (Ctrl+C to stop)[/cyan]")

        # Keep running until interrupted
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[cyan]Stopping subscription...[/cyan]")
            if ctx.obj['sse_handler']:
                ctx.obj['sse_handler'].stop()

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to subscribe: {e}")
        raise click.Abort()


@cli.command()
@click.pass_context
def tasks_list(ctx):
    """List running tasks"""
    client = ctx.obj.get('client')
    if not client:
        console.print("[red]✗[/red] Not initialized. Run 'init' first.")
        raise click.Abort()

    try:
        with console.status("[bold green]Fetching tasks..."):
            response = client.send_request("tasks/list")

        tasks = response.get('tasks', [])
        if not tasks:
            console.print("No running tasks")
            return

        table = Table(title="Running Tasks")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Name", style="white")
        table.add_column("Progress", style="yellow")

        for task in tasks:
            progress = ""
            if 'progress' in task:
                prog = task['progress']
                if isinstance(prog, dict):
                    current = prog.get('current', 0)
                    total = prog.get('total', 0)
                    progress = f"{current}/{total}" if total > 0 else str(current)
                else:
                    progress = str(prog)

            table.add_row(
                task.get('id', ''),
                task.get('status', ''),
                task.get('name', ''),
                progress
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list tasks: {e}")
        raise click.Abort()


if __name__ == '__main__':
    cli()