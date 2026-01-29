"""Main CLI application for grok-py."""

import typer
from rich.console import Console

# TODO: Import when implemented
# from grok_py.agent import grok_agent
# from grok_py.utils import settings

app = typer.Typer(
    name="grok-py",
    help="AI-powered terminal assistant - Python implementation of Grok CLI",
    add_completion=False,
)
console = Console()


@app.callback()
def callback():
    """Grok CLI - AI-powered terminal assistant."""
    pass


@app.command()
def chat(
    message: str = typer.Argument(None, help="Message to send to Grok"),
    interactive: bool = typer.Option(True, "--interactive/--non-interactive", help="Run in interactive mode"),
    model: str = typer.Option("grok-beta", "--model", "-m", help="Grok model to use"),
    temperature: float = typer.Option(0.7, "--temperature", "-t", help="Temperature for response generation"),
    max_tokens: int = typer.Option(None, "--max-tokens", help="Maximum tokens in response"),
):
    """Start a chat session with Grok."""
    console.print("[bold blue]Grok CLI[/bold blue] - Python Implementation")
    console.print("Initializing...")

    async def run_chat():
        try:
            from grok_py.grok.client import GrokClient

            async with GrokClient() as client:
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
                    # Interactive mode (placeholder for now)
                    console.print("[yellow]Interactive mode not yet implemented[/yellow]")
                    console.print("Use: grok-py chat 'your message here'")
        except Exception as e:
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