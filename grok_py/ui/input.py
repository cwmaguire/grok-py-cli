"""
Input Handling Module

Provides advanced input handling with multiline support, command history,
and F1 mode toggle functionality for the Grok CLI.
"""

import os
import sys
from typing import List, Optional, Callable
from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text
from rich.panel import Panel

from ..utils.logging import get_logger

logger = get_logger(__name__)


class InputHandler:
    """Advanced input handler with multiline, history, and mode toggle."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.history: List[str] = []
        self.history_index = -1
        self.current_input = ""
        self.multiline_buffer: List[str] = []
        self.mode = "chat"  # "chat" or "command"
        self.mode_toggle_callback: Optional[Callable[[str], None]] = None

    def set_mode_toggle_callback(self, callback: Callable[[str], None]):
        """Set callback for mode toggle events."""
        self.mode_toggle_callback = callback

    def toggle_mode(self):
        """Toggle between chat and command mode."""
        self.mode = "command" if self.mode == "chat" else "chat"
        if self.mode_toggle_callback:
            self.mode_toggle_callback(self.mode)
        logger.info(f"Toggled to {self.mode} mode")

    def get_input(self, prompt: str = "> ", multiline: bool = False) -> str:
        """Get user input with support for history and multiline."""
        if multiline:
            return self._get_multiline_input(prompt)
        else:
            return self._get_single_line_input(prompt)

    def _get_single_line_input(self, prompt: str) -> str:
        """Get single line input with history navigation."""
        try:
            # Create a custom prompt with history support
            while True:
                display_prompt = f"{prompt} [{self.mode}]"
                user_input = Prompt.ask(display_prompt, console=self.console)

                if user_input.strip():
                    self._add_to_history(user_input)
                    return user_input
                elif user_input == "":
                    # Allow empty input to continue
                    continue
        except KeyboardInterrupt:
            logger.info("Input interrupted by user")
            return ""
        except EOFError:
            logger.info("Input ended by EOF")
            return ""

    def _get_multiline_input(self, prompt: str) -> str:
        """Get multiline input, ending with Ctrl+D or specific marker."""
        self.console.print(f"[dim]Entering multiline mode. Press Ctrl+D to finish.[/dim]")
        self.multiline_buffer = []

        try:
            while True:
                line = input()  # Use raw input for multiline
                if line == "":  # Empty line
                    continue
                self.multiline_buffer.append(line)
        except EOFError:
            # Ctrl+D pressed
            pass

        full_input = "\n".join(self.multiline_buffer)
        if full_input.strip():
            self._add_to_history(full_input)
        logger.info(f"Collected multiline input: {len(full_input)} characters")
        return full_input

    def _add_to_history(self, input_str: str):
        """Add input to history."""
        if input_str not in self.history:
            self.history.append(input_str)
            self.history_index = len(self.history)
        logger.debug(f"Added to history: {input_str[:50]}...")

    def navigate_history(self, direction: str) -> Optional[str]:
        """Navigate through command history."""
        if not self.history:
            return None

        if direction == "up":
            if self.history_index > 0:
                self.history_index -= 1
                return self.history[self.history_index]
        elif direction == "down":
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                return self.history[self.history_index]
            else:
                self.history_index = len(self.history)
                return ""

        return None

    def handle_special_keys(self, key: str) -> Optional[str]:
        """Handle special key presses."""
        if key == "f1":
            self.toggle_mode()
            return None  # Don't return input
        elif key == "up":
            return self.navigate_history("up")
        elif key == "down":
            return self.navigate_history("down")
        elif key == "ctrl+c":
            raise KeyboardInterrupt()
        return None

    def display_mode_indicator(self):
        """Display current mode indicator."""
        mode_color = "green" if self.mode == "chat" else "blue"
        mode_text = f"Mode: [bold {mode_color}]{self.mode.upper()}[/bold {mode_color}]"
        panel = Panel(
            Text(mode_text),
            title="[bold]Current Mode[/bold]",
            border_style=mode_color
        )
        self.console.print(panel)

    def get_history(self) -> List[str]:
        """Get the command history."""
        return self.history.copy()

    def clear_history(self):
        """Clear the command history."""
        self.history.clear()
        self.history_index = -1
        logger.info("Cleared input history")

    def save_history(self, filepath: str = "~/.grok_cli_history"):
        """Save command history to file."""
        expanded_path = os.path.expanduser(filepath)
        try:
            with open(expanded_path, 'w') as f:
                for item in self.history:
                    f.write(item + '\n')
            logger.info(f"Saved history to {expanded_path}")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def load_history(self, filepath: str = "~/.grok_cli_history"):
        """Load command history from file."""
        expanded_path = os.path.expanduser(filepath)
        try:
            if os.path.exists(expanded_path):
                with open(expanded_path, 'r') as f:
                    self.history = [line.strip() for line in f if line.strip()]
                self.history_index = len(self.history)
                logger.info(f"Loaded {len(self.history)} history items from {expanded_path}")
        except Exception as e:
            logger.error(f"Failed to load history: {e}")

    def show_help(self):
        """Display input help."""
        help_text = """
[dim]Input Controls:[/dim]
• Type normally for input
• Up/Down arrows: Navigate history
• F1: Toggle between Chat/Command mode
• Ctrl+C: Interrupt current operation
• For multiline: Use --multiline flag or enter multiline mode

[dim]Modes:[/dim]
• [green]Chat Mode[/green]: Interactive conversation with Grok
• [blue]Command Mode[/blue]: Execute CLI commands and tools
        """
        panel = Panel(
            Text(help_text),
            title="[bold]Input Help[/bold]",
            border_style="yellow"
        )
        self.console.print(panel)