"""
Input Handling Module

Provides advanced input handling with multiline support, command history,
and F1 mode toggle functionality for the Grok CLI.
"""

import os
import sys
from typing import List, Optional, Callable
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

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
        self.display_callback: Optional[Callable[[str, Optional[List[str]]], None]] = None
        self.auto_edit_toggle_callback: Optional[Callable[[], None]] = None

        # Setup prompt_toolkit session if available
        if PROMPT_TOOLKIT_AVAILABLE:
            self.session = PromptSession(history=None)  # We'll manage history ourselves
            self.key_bindings = self._setup_key_bindings()
        else:
            self.session = None
            self.key_bindings = None

    def set_mode_toggle_callback(self, callback: Callable[[str], None]):
        """Set callback for mode toggle events."""
        self.mode_toggle_callback = callback

    def set_display_callback(self, callback: Callable[[str, Optional[List[str]]], None]):
        """Set callback for updating multi-line display."""
        self.display_callback = callback

    def set_auto_edit_toggle_callback(self, callback: Callable[[], None]):
        """Set callback for auto-edit toggle events."""
        self.auto_edit_toggle_callback = callback

    def toggle_mode(self):
        """Toggle between chat and command mode."""
        self.mode = "command" if self.mode == "chat" else "chat"
        if self.mode_toggle_callback:
            self.mode_toggle_callback(self.mode)
        logger.info(f"Toggled to {self.mode} mode")

    def toggle_auto_edit(self):
        """Toggle auto-edit mode."""
        if self.auto_edit_toggle_callback:
            self.auto_edit_toggle_callback()
        logger.info("Toggled auto-edit mode")

    def _setup_key_bindings(self) -> Optional[KeyBindings]:
        """Setup key bindings for prompt_toolkit."""
        if not PROMPT_TOOLKIT_AVAILABLE:
            return None

        kb = KeyBindings()

        @kb.add('f1')
        def _(event):
            """Handle F1 to toggle mode."""
            self.toggle_mode()
            # Update the prompt
            event.app.invalidate()

        @kb.add('up')
        def _(event):
            """Handle up arrow for history."""
            if self.history:
                if self.history_index == -1:
                    self.history_index = len(self.history) - 1
                elif self.history_index > 0:
                    self.history_index -= 1
                event.app.current_buffer.text = self.history[self.history_index]

        @kb.add('down')
        def _(event):
            """Handle down arrow for history."""
            if self.history and self.history_index >= 0:
                if self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    event.app.current_buffer.text = self.history[self.history_index]
                else:
                    self.history_index = -1
                    event.app.current_buffer.text = ""

        @kb.add('s-tab')
        def _(event):
            """Handle Shift+Tab to toggle auto-edit."""
            self.toggle_auto_edit()

        @kb.add('c-c')
        def _(event):
            """Handle Ctrl+C to clear input."""
            event.app.current_buffer.text = ""
            event.app.invalidate()

        @kb.add('escape')
        def _(event):
            """Handle Escape to cancel current operation."""
            # For now, just exit the prompt
            event.app.exit(result=None)

        @kb.add('tab')
        def _(event):
            """Handle Tab for navigation (placeholder for menus)."""
            # Placeholder, as menu navigation would be handled elsewhere
            pass

        return kb

    def get_input(self, prompt: str = "> ", multiline: bool = False, chat_interface: Optional[object] = None) -> str:
        """Get user input with support for history and multiline."""
        import asyncio
        try:
            # Check if we're in an async context
            asyncio.get_running_loop()
            # We're in an async context, run input in thread pool to avoid event loop conflicts
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._get_input_sync, prompt, multiline, chat_interface)
                return future.result()
        except RuntimeError:
            # Not in async context, run normally
            return self._get_input_sync(prompt, multiline, chat_interface)

    def _get_input_sync(self, prompt: str = "> ", multiline: bool = False, chat_interface: Optional[object] = None) -> str:
        """Get user input synchronously."""
        if multiline:
            return self._get_multiline_input(prompt)
        else:
            return self._get_single_line_input(prompt, chat_interface)

    def _get_single_line_input(self, prompt: str, chat_interface: Optional[object] = None) -> str:
        """Get single line input with history navigation."""
        try:
            if PROMPT_TOOLKIT_AVAILABLE and self.session:
                # Use prompt_toolkit for advanced features
                display_prompt = f"{prompt} [{self.mode}]> "
                user_input = self.session.prompt(
                    display_prompt,
                    key_bindings=self.key_bindings
                )
            else:
                # Fallback to Rich Prompt
                from rich.prompt import Prompt
                display_prompt = f"{prompt} [{self.mode}]"
                user_input = Prompt.ask(display_prompt, console=self.console)

            # Check for multi-line triggers
            if user_input.endswith('\\'):
                # Remove the backslash and enter multi-line mode
                initial_line = user_input[:-1]
                if chat_interface:
                    chat_interface.enter_multiline_mode()
                    chat_interface.update_multiline_input("", [initial_line] if initial_line else [])
                    return self._get_multiline_input_with_ui(prompt, chat_interface)
                else:
                    # Fallback to regular multiline
                    return initial_line + '\n' + self._get_multiline_input(prompt)
            elif '\n' in user_input:
                # Input contains newlines (probably pasted), treat as multi-line
                if chat_interface:
                    lines = user_input.split('\n')
                    chat_interface.enter_multiline_mode()
                    chat_interface.update_multiline_input("", lines[:-1] if lines else [])
                    return chat_interface.exit_multiline_mode()
                else:
                    return user_input

            if user_input.strip():
                self._add_to_history(user_input)
                return user_input
            elif user_input == "":
                # Allow empty input to continue
                return ""
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

    def _get_multiline_input_with_ui(self, prompt: str, chat_interface: object) -> str:
        """Get multiline input with UI updates."""
        try:
            while True:
                if PROMPT_TOOLKIT_AVAILABLE and self.session:
                    # Use prompt_toolkit for line input
                    line = self.session.prompt("↳ ", key_bindings=self.key_bindings)
                else:
                    # Fallback
                    line = input("↳ ")

                if line.strip() == "":
                    # Empty line submits
                    break
                elif line == "\\":
                    # Backslash alone also submits
                    break

                # Add line to completed lines
                current_completed = chat_interface.multiline_lines + [chat_interface.multiline_current_line]
                chat_interface.update_multiline_input("", current_completed + [line])

        except (KeyboardInterrupt, EOFError):
            # Submit on interrupt or EOF
            pass

        return chat_interface.exit_multiline_mode()

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