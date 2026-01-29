"""
Chat Interface Module

Provides a Rich-based chat interface for the Grok CLI with message history,
streaming response support, and syntax highlighting.
"""

import asyncio
import sys
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.layout import Layout
from rich.columns import Columns
from rich.align import Align
from rich.spinner import Spinner
import re

from ..utils.logging import get_logger

# Import new UI modules
sys.path.append('../..')  # Add root to path
try:
    from ui.streaming import StreamingResponseProcessor
    from ui.parser import ResponseParser, ParsedResponse, ResponseType
    from ui.updates import RealTimeUpdateManager, UIState
except ImportError:
    # Fallback if not available
    StreamingResponseProcessor = None
    ResponseParser = None
    ParsedResponse = None
    ResponseType = None
    RealTimeUpdateManager = None
    UIState = None

logger = get_logger(__name__)


class Message:
    """Represents a chat message."""

    def __init__(self, role: str, content: str, timestamp: Optional[str] = None):
        self.role = role  # 'user' or 'assistant'
        self.content = content
        self.timestamp = timestamp

    def render(self, console: Console, width: int = 80) -> Panel:
        """Render the message as a Rich panel."""
        if self.role == 'user':
            title = "You"
            border_style = "blue"
        else:
            title = "Grok"
            border_style = "green"

        # Process content for markdown and syntax highlighting
        rendered_content = self._process_content(self.content, console)

        return Panel(
            rendered_content,
            title=f"[bold]{title}[/bold]",
            border_style=border_style,
            title_align="left",
            width=width
        )

    def _process_content(self, content: str, console: Console) -> str:
        """Process content for markdown and code blocks."""
        # Split content into markdown and code blocks
        parts = []
        code_block_pattern = r'```(\w+)?\n(.*?)\n```'

        last_end = 0
        for match in re.finditer(code_block_pattern, content, re.DOTALL):
            # Add text before code block
            if match.start() > last_end:
                text_before = content[last_end:match.start()]
                if text_before.strip():
                    parts.append(Markdown(text_before))

            # Add code block
            lang = match.group(1) or 'text'
            code = match.group(2)
            syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
            parts.append(syntax)

            last_end = match.end()

        # Add remaining text
        if last_end < len(content):
            remaining = content[last_end:]
            if remaining.strip():
                parts.append(Markdown(remaining))

        return Columns(parts, equal=False, expand=True) if parts else Text("")


class ChatInterface:
    """Rich-based chat interface with streaming support."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.messages: List[Message] = []
        self.live: Optional[Live] = None
        self.streaming_message: Optional[Message] = None
        self.layout = Layout()
        self._setup_layout()

        # Initialize enhanced UI components if available
        self.streaming_processor = None
        self.response_parser = None
        self.update_manager = None

        if StreamingResponseProcessor:
            self.streaming_processor = StreamingResponseProcessor(
                console=self.console,
                display_callback=self._on_streaming_update
            )

        if ResponseParser:
            self.response_parser = ResponseParser(console=self.console)

        if RealTimeUpdateManager:
            self.update_manager = RealTimeUpdateManager(
                console=self.console,
                live_display=self.live
            )
            # Register content component
            self.update_manager.register_component("chat_content", Text(""))

    def _setup_layout(self):
        """Setup the layout for the chat interface."""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="chat", ratio=1),
            Layout(name="input", size=5)
        )

    def _on_streaming_update(self, content: str):
        """Callback for streaming updates."""
        if self.streaming_message:
            self.streaming_message.content = content
            self._update_display()

    def add_message(self, role: str, content: str):
        """Add a message to the chat history."""
        message = Message(role, content)
        self.messages.append(message)
        logger.info(f"Added {role} message: {len(content)} characters")
        self._update_display()

    async def start_streaming_response(self, role: str = "assistant"):
        """Start streaming a response."""
        self.streaming_message = Message(role, "")
        self.live = Live(self._render_chat(), console=self.console, refresh_per_second=10)
        self.live.start()
        if self.update_manager:
            self.update_manager.set_ui_state(UIState.STREAMING)
        logger.info("Started streaming response")

    async def stream_chunk(self, chunk: str):
        """Add a chunk to the streaming response."""
        if self.streaming_message:
            self.streaming_message.content += chunk
            self.live.update(self._render_chat())

    async def end_streaming_response(self):
        """End the streaming response."""
        if self.live:
            self.live.stop()
            self.live = None
        if self.streaming_message:
            self.messages.append(self.streaming_message)
            self.streaming_message = None
        if self.update_manager:
            self.update_manager.set_ui_state(UIState.IDLE)
        self._update_display()
        logger.info("Ended streaming response")

    async def process_streaming_response_enhanced(self, stream_iterator, role: str = "assistant"):
        """
        Process a streaming response using the enhanced processor.

        Args:
            stream_iterator: Async iterator yielding response chunks
            role: Role of the message (user/assistant)
        """
        if not self.streaming_processor:
            # Fallback to basic streaming
            await self.start_streaming_response(role)
            try:
                async for chunk in stream_iterator:
                    await self.stream_chunk(chunk)
            finally:
                await self.end_streaming_response()
            return

        # Use enhanced processor
        if self.update_manager:
            self.update_manager.set_ui_state(UIState.STREAMING)

        self.streaming_message = Message(role, "")

        try:
            # Create live display for the processor
            live_display = Live(console=self.console, refresh_per_second=10)
            live_display.start()

            # Process stream
            full_response = await self.streaming_processor.process_stream(
                stream_iterator=stream_iterator,
                live_display=live_display,
                show_spinner=True
            )

            live_display.stop()

            # Parse and format the response
            if self.response_parser:
                parsed = self.response_parser.parse_response(full_response)
                rendered_panel = self.response_parser.render_parsed_response(parsed)
                self.streaming_message.content = full_response  # Keep original content
                # Could store parsed info for display

            # Add to messages
            self.messages.append(self.streaming_message)
            self.streaming_message = None

        except Exception as e:
            logger.error(f"Enhanced streaming failed: {e}")
            # Fallback to basic
            if self.streaming_message:
                self.streaming_message.content = f"Error: {str(e)}"
                self.messages.append(self.streaming_message)
                self.streaming_message = None

        finally:
            if self.update_manager:
                self.update_manager.set_ui_state(UIState.IDLE)
            self._update_display()

    def _render_chat(self) -> Layout:
        """Render the current chat state."""
        # Header
        header = Panel(
            Align.center("[bold blue]Grok CLI Chat Interface[/bold blue]"),
            border_style="blue"
        )

        # Chat messages
        chat_panels = []
        for msg in self.messages:
            chat_panels.append(msg.render(self.console))

        if self.streaming_message:
            chat_panels.append(self.streaming_message.render(self.console))

        chat_content = Columns(chat_panels, equal=False, expand=True) if chat_panels else Text("No messages yet...")

        # Input area (placeholder)
        input_panel = Panel(
            Text("Type your message... (F1 for mode toggle)"),
            title="[bold]Input[/bold]",
            border_style="yellow"
        )

        # Update layout
        self.layout["header"].update(header)
        self.layout["chat"].update(chat_content)
        self.layout["input"].update(input_panel)

        return self.layout

    def _update_display(self):
        """Update the display without live mode."""
        if not self.live:
            self.console.clear()
            self.console.print(self._render_chat())

    def clear_history(self):
        """Clear the message history."""
        self.messages.clear()
        self._update_display()
        logger.info("Cleared message history")

    def get_message_count(self) -> int:
        """Get the number of messages."""
        return len(self.messages)

    async def display_spinner(self, message: str = "Processing..."):
        """Display a spinner while processing."""
        with self.console.status(f"[bold green]{message}[/bold green]", spinner="dots"):
            await asyncio.sleep(0.1)  # Allow spinner to show

    def display_error(self, error: str):
        """Display an error message."""
        error_panel = Panel(
            Text(f"❌ {error}", style="bold red"),
            title="[bold red]Error[/bold red]",
            border_style="red"
        )
        self.console.print(error_panel)
        logger.error(f"Displayed error: {error}")

    def display_success(self, message: str):
        """Display a success message."""
        success_panel = Panel(
            Text(f"✅ {message}", style="bold green"),
            title="[bold green]Success[/bold green]",
            border_style="green"
        )
        self.console.print(success_panel)
        logger.info(f"Displayed success: {message}")