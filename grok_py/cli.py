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
                    # Interactive mode with Rich UI
                    from grok_py.ui import ChatInterface, InputHandler

                    chat_ui = ChatInterface(console)
                    input_handler = InputHandler(console)

                    console.print("[bold green]Entering interactive chat mode. Type 'exit' or 'quit' to leave.[/bold green]")
                    console.print("Press F1 to toggle between chat and command modes.\n")

                    while True:
                        try:
                            user_input = input_handler.get_input("You: ")
                            if not user_input or user_input.lower() in ['exit', 'quit']:
                                break

                            # Send message and display streaming response
                            await chat_ui.start_streaming_response("assistant")

                            async for chunk in client.send_message(
                                message=user_input,
                                model=model,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                stream=True,
                            ):
                                await chat_ui.stream_chunk(chunk)

                            await chat_ui.end_streaming_response()

                        except KeyboardInterrupt:
                            console.print("\n[yellow]Chat interrupted. Type 'exit' to quit.[/yellow]")
                            continue
                        except Exception as e:
                            chat_ui.display_error(f"Error in chat: {str(e)}")
                            continue
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