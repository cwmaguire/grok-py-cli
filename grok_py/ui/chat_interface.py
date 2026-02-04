"""
Chat Interface Module

Provides a Rich-based chat interface for the Grok CLI with message history,
streaming response support, and syntax highlighting.
"""

import asyncio
import sys
import time
import random
import shutil
from typing import List, Optional, Dict, Any
from enum import Enum
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
from grok_py.grok.client import Message, MessageRole

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


class InputState(Enum):
    """Input modes for the chat interface."""
    SINGLE_LINE = "single_line"
    MULTI_LINE = "multi_line"
    COMMAND_MODE = "command_mode"


class MenuState(Enum):
    """Active menu states."""
    NONE = "none"
    COMMAND_SUGGESTIONS = "command_suggestions"
    MODEL_SELECTION = "model_selection"


def format_token_count(count: int) -> str:
    """Format token count with K/M suffixes."""
    if count < 1000:
        return str(count)
    elif count < 1000000:
        return f"{count / 1000:.1f}K"
    else:
        return f"{count / 1000000:.1f}M"


def create_grok_logo() -> str:
    """Create ASCII art logo for GROK with gradient from magenta to cyan."""
    logo_lines = [
        "  GGGG   RRRR    OOO   K   K  ",
        " G       R   R  O   O  K  K   ",
        " G  GG   RRRR   O   O  KKK    ",
        " G   G   R  R   O   O  K  K   ",
        "  GGGG   R   R   OOO   K   K  "
    ]

    # Apply gradient colors: magenta to cyan across each line
    colored_lines = []
    for line in logo_lines:
        colored_line = ""
        for i, char in enumerate(line):
            if char == " ":
                colored_line += char
                continue
            # Gradient from magenta to cyan based on position
            ratio = i / len(line) if len(line) > 0 else 0
            if ratio < 0.25:
                color = '\033[35m'  # Magenta
            elif ratio < 0.5:
                color = '\033[31m'  # Red
            elif ratio < 0.75:
                color = '\033[33m'  # Yellow
            else:
                color = '\033[36m'  # Cyan
            colored_line += f"{color}{char}"
        colored_line += '\033[0m'  # Reset at end of line
        colored_lines.append(colored_line)

    return "\n".join(colored_lines)


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

        # Spinner state
        self.spinner_active = False
        self.spinner_task: Optional[asyncio.Task] = None
        self.spinner_chars = ['/', '-', '\\', '|']
        self.spinner_index = 0
        self.loading_texts = [
            "Thinking...", "Computing...", "Analyzing...", "Processing...",
            "Generating...", "Reasoning...", "Calculating...", "Searching...",
            "Loading...", "Working...", "Crunching data...", "Formulating response...",
            "Connecting to Grok...", "Retrieving information...", "Optimizing...", "Finalizing..."
        ]
        self.loading_text_index = 0
        self.spinner_start_time: Optional[float] = None
        self.spinner_token_count = 0

        # Multi-line input state
        self.multiline_mode = False
        self.multiline_lines: List[str] = []
        self.multiline_current_line = ""
        self.input_border_color = "blue"  # "blue" for idle, "yellow" for processing

        # Session state management
        self.ui_state = UIState.IDLE if UIState else "idle"  # idle, processing, streaming, error, waiting
        self.input_state = InputState.SINGLE_LINE
        self.confirmation_pending = False  # True if a confirmation dialog is active
        self.auto_approval_flags = {
            'file_ops': False,  # Auto-approve file operations
            'bash': False,     # Auto-approve bash commands
            'all': False       # Auto-approve all operations
        }
        self.active_menu = MenuState.NONE

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


    def get_terminal_size(self) -> tuple[int, int]:
        """Get terminal width and height, with minimum width of 80."""
        try:
            size = shutil.get_terminal_size()
            width = max(size.columns, 80)
            height = size.lines
            return width, height
        except (OSError, AttributeError):
            # Fallback if terminal size can't be determined
            return 80, 24

    def truncate_path(self, path: str, max_length: int = 60) -> str:
        """Truncate long file paths for display."""
        if len(path) <= max_length:
            return path
        # Keep start and end, truncate middle
        start_len = max_length // 2 - 2
        end_len = max_length - start_len - 3  # 3 for "..."
        return f"{path[:start_len]}...{path[-end_len:]}"

    def process_text_for_display(self, text: str) -> str:
        """Process text to truncate long paths for better display."""
        import re
        # Find potential file paths (simple regex for Unix/Windows paths)
        path_pattern = r'(/[^\s]+|[A-Za-z]:[^\s]+)'
        def replace_path(match):
            path = match.group(0)
            return self.truncate_path(path)
        return re.sub(path_pattern, replace_path, text)


    def _on_streaming_update(self, content: str):
        """Callback for streaming updates."""
        if self.streaming_message:
            self.streaming_message.content = content
            self._update_display()

    def add_message(self, role: str, content: str):
        """Add a message to the chat history."""
        message = Message(MessageRole(role), content)
        self.messages.append(message)
        logger.info(f"Added {role} message: {len(content)} characters")
        self._update_display()

    def start_interactive_display(self):
        """Start continuous live display for interactive chat."""
        if not self.live:
            self.live = Live(self._render_chat(), console=self.console, refresh_per_second=4)
            self.live.start()
        if self.update_manager:
            self.update_manager.set_ui_state(UIState.IDLE)
        logger.info("Started interactive display")

    async def start_streaming_response(self, role: str = "assistant"):
        """Start streaming a response."""
        self.streaming_message = Message(MessageRole(role), "")
        # If not already in live mode, start it
        if not self.live:
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
        """Render the current chat state in a scrolling layout."""
        width, height = self.get_terminal_size()

        # Create a single scrolling chat area
        chat_lines = []

        # Add messages in chronological order
        for msg in self.messages:
            processed_content = self.process_text_for_display(msg.content)
            if msg.role == 'user':
                chat_lines.append(f"[bold cyan]You:[/bold cyan] {processed_content}")
            else:
                chat_lines.append(f"[bold green]Grok:[/bold green] {processed_content}")
            chat_lines.append("")  # Empty line between messages

        # Add streaming message if active
        if self.streaming_message:
            processed_streaming = self.process_text_for_display(self.streaming_message.content)
            if self.streaming_message.role == 'user':
                chat_lines.append(f"[bold cyan]You:[/bold cyan] {processed_streaming}")
            else:
                chat_lines.append(f"[bold green]Grok:[/bold green] {processed_streaming}")
            chat_lines.append("")  # Empty line

        # If no messages, show welcome text
        if not chat_lines:
            chat_lines = [
                "[dim]Welcome to Grok CLI![/dim]",
                "[dim]Type your message and press Enter.[/dim]",
                ""
            ]

        # Join all lines
        chat_text = "\n".join(chat_lines)

        # Calculate chat panel width (terminal width minus borders and padding)
        chat_width = width - 4  # Account for panel borders

        # Create the main layout: header + scrolling chat + input area
        layout = Layout()

        # Header with ASCII logo
        logo_text = "  " + create_grok_logo().replace('\n', '\n  ')  # Add 2 spaces padding
        logo_lines = logo_text.split('\n')
        header_height = len(logo_lines) + 2  # +2 for panel borders
        header = Panel(
            Text.from_ansi(logo_text),
            border_style="blue"
        )

        # Chat area (scrolling text)
        chat_text_obj = Text.from_markup(chat_text, overflow="fold")
        chat_panel = Panel(
            chat_text_obj,
            title="[bold]Chat[/bold]",
            border_style="green",
            width=chat_width
        )

        # Spinner area (shown when processing)
        spinner_panel = None
        if self.spinner_active:
            elapsed = time.time() - self.spinner_start_time if self.spinner_start_time else 0
            spinner_char = self.spinner_chars[self.spinner_index]
            loading_text = self.loading_texts[self.loading_text_index]
            token_str = format_token_count(self.spinner_token_count)

            spinner_text = f"[cyan]{spinner_char} {loading_text}[/cyan] [dim]({elapsed:.1f}s · ↑ {token_str} tokens · esc to interrupt)[/dim]"
            spinner_panel = Panel(
                Text.from_markup(spinner_text),
                border_style="cyan"
            )

        # Input instruction area
        if self.multiline_mode:
            # Build multi-line input display
            input_lines = []
            for i, line in enumerate(self.multiline_lines):
                if i == 0:
                    input_lines.append(f"❯ {line}")
                else:
                    input_lines.append(f"│ {line}")
            # Add current line
            input_lines.append(f"↳ {self.multiline_current_line}")

            input_text = "\n".join(input_lines)
            input_border = self.input_border_color
            input_title = "[bold]Multi-line Input[/bold]"
        else:
            input_text = "Type your message below | F1: toggle mode | Ctrl+C: exit"
            input_border = self.input_border_color
            input_title = "[bold]Input[/bold]"

        input_instruction = Panel(
            Text.from_markup(input_text),
            title=input_title,
            border_style=input_border
        )

        # Split layout
        if spinner_panel:
            layout.split(
                Layout(header, size=header_height),
                Layout(chat_panel, ratio=1),
                Layout(spinner_panel, size=1),
                Layout(input_instruction, size=3)
            )
        else:
            layout.split(
                Layout(header, size=header_height),
                Layout(chat_panel, ratio=1),
                Layout(input_instruction, size=3)
            )

        return layout

    def _update_display(self):
        """Update the display."""
        if self.live:
            self.live.update(self._render_chat())
        else:
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

    async def start_spinner(self, token_count: int = 0):
        """Start the loading spinner."""
        if self.spinner_active:
            return

        self.spinner_active = True
        self.ui_state = UIState.PROCESSING if UIState else "processing"
        self.spinner_start_time = time.time()
        self.spinner_token_count = token_count
        self.spinner_index = 0
        self.loading_text_index = random.randint(0, len(self.loading_texts) - 1)

        # Start the spinner task
        self.spinner_task = asyncio.create_task(self._run_spinner())
        logger.info("Started loading spinner")

    async def stop_spinner(self):
        """Stop the loading spinner."""
        if not self.spinner_active:
            return

        self.spinner_active = False
        self.ui_state = UIState.IDLE if UIState else "idle"
        if self.spinner_task:
            self.spinner_task.cancel()
            try:
                await self.spinner_task
            except asyncio.CancelledError:
                pass
            self.spinner_task = None
        self._update_display()
        logger.info("Stopped loading spinner")

    async def _run_spinner(self):
        """Run the spinner animation loop."""
        last_text_change = time.time()
        try:
            while self.spinner_active:
                current_time = time.time()
                elapsed = current_time - self.spinner_start_time if self.spinner_start_time else 0

                # Update spinner character every 500ms
                self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)

                # Update text every 4 seconds
                if current_time - last_text_change >= 4.0:
                    self.loading_text_index = (self.loading_text_index + 1) % len(self.loading_texts)
                    last_text_change = current_time

                # Update display
                if self.live:
                    self.live.update(self._render_chat())

                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    def enter_multiline_mode(self):
        """Enter multi-line input mode."""
        self.multiline_mode = True
        self.input_state = InputState.MULTI_LINE
        self.multiline_lines = []
        self.multiline_current_line = ""
        self.input_border_color = "blue"
        self._update_display()
        logger.info("Entered multi-line input mode")

    def exit_multiline_mode(self) -> str:
        """Exit multi-line input mode and return the complete input."""
        self.multiline_mode = False
        self.input_state = InputState.SINGLE_LINE
        full_input = "\n".join(self.multiline_lines + [self.multiline_current_line])
        self.multiline_lines = []
        self.multiline_current_line = ""
        self.input_border_color = "blue"
        self._update_display()
        logger.info(f"Exited multi-line input mode with {len(full_input)} characters")
        return full_input

    def update_multiline_input(self, current_line: str, completed_lines: Optional[List[str]] = None):
        """Update the current multi-line input display."""
        self.multiline_current_line = current_line
        if completed_lines is not None:
            self.multiline_lines = completed_lines.copy()
        self._update_display()

    def is_multiline_mode(self) -> bool:
        """Check if currently in multi-line input mode."""
        return self.multiline_mode

    def set_input_border_color(self, color: str):
        """Set the input border color."""
        self.input_border_color = color
        self._update_display()

    def display_error(self, error: str):
        """Display an error message."""
        if self.live:
            # Stop live display temporarily to show error
            self.live.stop()
            self.live = None

        error_panel = Panel(
            Text(f"❌ {error}", style="bold red"),
            title="[bold red]Error[/bold red]",
            border_style="red"
        )
        self.console.print(error_panel)
        logger.error(f"Displayed error: {error}")

        # Restart live display if we had one
        if self.messages or self.streaming_message:
            self.live = Live(self._render_chat(), console=self.console, refresh_per_second=4)
            self.live.start()

    def display_success(self, message: str):
        """Display a success message."""
        success_panel = Panel(
            Text(f"✅ {message}", style="bold green"),
            title="[bold green]Success[/bold green]",
            border_style="green"
        )
        self.console.print(success_panel)
        logger.info(f"Displayed success: {message}")