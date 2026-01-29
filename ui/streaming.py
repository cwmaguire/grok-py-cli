"""
Streaming Response Processor Module

Handles real-time streaming of responses from Grok API, including chunk processing,
buffering, and live display updates in the terminal interface.
"""

import asyncio
import time
from typing import AsyncIterator, Optional, Callable, List, Dict, Any
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.spinner import Spinner
from rich.columns import Columns
import threading

# Assuming logger is available; adjust import as needed
try:
    from ..utils.logging import get_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
else:
    logger = get_logger(__name__)


class StreamingResponseProcessor:
    """
    Processes streaming responses from Grok API with real-time display updates.

    Handles chunk processing, buffering, error recovery, and live UI updates.
    """

    def __init__(
        self,
        console: Console,
        display_callback: Optional[Callable[[str], None]] = None,
        buffer_size: int = 1024,
        update_interval: float = 0.1
    ):
        """
        Initialize the streaming processor.

        Args:
            console: Rich console for display
            display_callback: Optional callback for custom display handling
            buffer_size: Maximum buffer size for chunks
            update_interval: Minimum time between UI updates
        """
        self.console = console
        self.display_callback = display_callback
        self.buffer_size = buffer_size
        self.update_interval = update_interval

        self.buffer: List[str] = []
        self.full_response = ""
        self.is_streaming = False
        self.last_update = 0.0
        self.error_count = 0
        self.max_errors = 3

        # Threading for async processing
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    async def process_stream(
        self,
        stream_iterator: AsyncIterator[str],
        live_display: Optional[Live] = None,
        show_spinner: bool = True
    ) -> str:
        """
        Process a streaming response iterator.

        Args:
            stream_iterator: Async iterator yielding response chunks
            live_display: Optional Rich Live display for real-time updates
            show_spinner: Whether to show a spinner during streaming

        Returns:
            Complete response string
        """
        self.is_streaming = True
        self.buffer = []
        self.full_response = ""
        self.error_count = 0
        self._stop_event.clear()

        spinner = Spinner("dots", text="Streaming response...") if show_spinner else None
        start_time = time.time()

        try:
            async for chunk in stream_iterator:
                if self._stop_event.is_set():
                    break

                # Process chunk
                success = await self._process_chunk(chunk)
                if not success:
                    self.error_count += 1
                    if self.error_count >= self.max_errors:
                        logger.error("Too many streaming errors, aborting")
                        break
                    continue

                # Update display if enough time has passed
                current_time = time.time()
                if current_time - self.last_update >= self.update_interval:
                    await self._update_display(live_display, spinner)
                    self.last_update = current_time

            # Final update
            await self._update_display(live_display, spinner, final=True)

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            self._handle_stream_error(e)

        finally:
            self.is_streaming = False
            elapsed = time.time() - start_time
            logger.info(".2f")

        return self.full_response

    async def _process_chunk(self, chunk: str) -> bool:
        """
        Process a single chunk from the stream.

        Args:
            chunk: Response chunk

        Returns:
            True if processed successfully
        """
        try:
            if not chunk or not chunk.strip():
                return True

            with self._lock:
                self.buffer.append(chunk)
                self.full_response += chunk

                # Maintain buffer size
                if len(self.buffer) > self.buffer_size:
                    # Remove oldest chunks but keep enough for context
                    remove_count = len(self.buffer) - self.buffer_size
                    self.buffer = self.buffer[remove_count:]

            logger.debug(f"Processed chunk: {len(chunk)} chars")
            return True

        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            return False

    async def _update_display(
        self,
        live_display: Optional[Live],
        spinner: Optional[Spinner],
        final: bool = False
    ) -> None:
        """
        Update the live display with current response content.

        Args:
            live_display: Rich Live display object
            spinner: Optional spinner to display
            final: Whether this is the final update
        """
        try:
            if live_display is None and self.display_callback is None:
                return

            # Build display content
            display_text = self._build_display_text(final)

            if live_display:
                # Update live display
                if spinner and not final:
                    content = Columns([spinner, display_text], expand=True)
                else:
                    content = display_text

                live_display.update(content)

            if self.display_callback:
                self.display_callback(display_text.plain if hasattr(display_text, 'plain') else str(display_text))

        except Exception as e:
            logger.error(f"Error updating display: {e}")

    def _build_display_text(self, final: bool = False) -> Text:
        """
        Build the text content for display.

        Args:
            final: Whether this is the final display

        Returns:
            Rich Text object for display
        """
        with self._lock:
            content = self.full_response

        # Create styled text
        if final:
            text = Text(content, style="green")
        else:
            text = Text(content, style="yellow")

        # Add cursor indicator if still streaming
        if not final and self.is_streaming:
            text.append("▊", style="bold cyan")

        return text

    def _handle_stream_error(self, error: Exception) -> None:
        """
        Handle streaming errors gracefully.

        Args:
            error: The exception that occurred
        """
        error_msg = f"Streaming interrupted: {str(error)}"
        logger.error(error_msg)

        # Display error in console
        error_panel = Panel(
            Text(error_msg, style="red"),
            title="[bold red]Streaming Error[/bold red]",
            border_style="red"
        )
        self.console.print(error_panel)

        # Try to display partial response if available
        if self.full_response:
            partial_panel = Panel(
                Text(self.full_response[:500] + "..." if len(self.full_response) > 500 else self.full_response),
                title="[yellow]Partial Response[/yellow]",
                border_style="yellow"
            )
            self.console.print(partial_panel)

    def stop_streaming(self) -> None:
        """Stop the current streaming operation."""
        self._stop_event.set()
        self.is_streaming = False
        logger.info("Streaming stopped by user")

    def get_buffered_content(self) -> str:
        """
        Get the currently buffered content.

        Returns:
            Buffered response content
        """
        with self._lock:
            return "".join(self.buffer)

    def clear_buffer(self) -> None:
        """Clear the chunk buffer."""
        with self._lock:
            self.buffer.clear()
            self.full_response = ""

    def is_active(self) -> bool:
        """
        Check if streaming is currently active.

        Returns:
            True if streaming is in progress
        """
        return self.is_streaming