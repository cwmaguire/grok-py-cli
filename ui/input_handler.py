"""
Advanced Input Handler for Grok CLI

Provides advanced input handling capabilities including multi-line input,
syntax highlighting, auto-completion, and input validation.
"""

import os
import sys
from typing import Optional, List, Callable
from pathlib import Path

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.lexers import PygmentsLexer
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.shortcuts import print_formatted_text
    from prompt_toolkit.formatted_text import HTML
    from pygments.lexers.python import PythonLexer
    from pygments.lexers.shell import BashLexer
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from .validator import InputValidator
from .buffer import InputBufferManager


class CommandCompleter(Completer):
    """Auto-completion for CLI commands and tools."""

    def __init__(self, commands: List[str]):
        self.commands = commands

    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor()
        for command in self.commands:
            if command.startswith(word):
                yield Completion(command, start_position=-len(word))


class AdvancedInputHandler:
    """
    Advanced input handler with multi-line support, syntax highlighting,
    auto-completion, and validation.
    """

    def __init__(self, validator: InputValidator, buffer_manager: InputBufferManager):
        if not PROMPT_TOOLKIT_AVAILABLE:
            raise ImportError("prompt_toolkit is required for advanced input handling")

        self.validator = validator
        self.buffer_manager = buffer_manager

        # Setup history
        history_file = Path.home() / ".grok_cli_history"
        self.history = FileHistory(str(history_file))

        # Setup completer
        self.commands = [
            "help", "exit", "quit", "clear", "history",
            "view_file", "create_file", "str_replace_editor", "bash",
            "search", "create_todo_list", "update_todo_list", "apt",
            "systemctl", "disk", "network", "code_execution", "web_search"
        ]
        self.completer = CommandCompleter(self.commands)

        # Setup lexer for syntax highlighting
        self.lexer = PygmentsLexer(BashLexer)

        # Setup key bindings
        self.key_bindings = self._setup_key_bindings()

        # Setup prompt session
        self.session = PromptSession(
            history=self.history,
            completer=self.completer,
            lexer=self.lexer,
            key_bindings=self.key_bindings,
            multiline=True,
            wrap_lines=True
        )

    def _setup_key_bindings(self) -> KeyBindings:
        """Setup custom key bindings for enhanced functionality."""
        kb = KeyBindings()

        @kb.add('c-c')
        def _(event):
            """Handle Ctrl+C to cancel input."""
            event.app.exit(result=None)

        @kb.add('c-d')
        def _(event):
            """Handle Ctrl+D to exit."""
            event.app.exit(result="exit")

        @kb.add('c-l')
        def _(event):
            """Handle Ctrl+L to clear screen."""
            os.system('clear')

        @kb.add('c-z')
        def _(event):
            """Handle Ctrl+Z for undo (if in buffer)."""
            if self.buffer_manager.can_undo():
                self.buffer_manager.undo()
                # Refresh the input line somehow

        return kb

    def get_input(self, prompt: str = "> ") -> Optional[str]:
        """
        Get user input with advanced features.

        Args:
            prompt: The prompt to display

        Returns:
            The validated input string, or None if cancelled
        """
        while True:
            try:
                # Get raw input
                text = self.session.prompt(prompt)

                if text is None:
                    return None

                if text.strip() == "":
                    continue

                # Validate input
                validation_result = self.validator.validate(text)
                if not validation_result.is_valid:
                    print_formatted_text(HTML(f"<red>Input validation failed: {validation_result.error_message}</red>"))
                    continue

                # Add to history via buffer manager
                self.buffer_manager.add_to_history(text)

                return text

            except KeyboardInterrupt:
                return None
            except EOFError:
                return "exit"
            except Exception as e:
                print_formatted_text(HTML(f"<red>Error during input: {str(e)}</red>"))
                return None

    def get_multiline_input(self, prompt: str = ">>> ") -> Optional[str]:
        """
        Get multi-line input specifically.

        Args:
            prompt: The prompt to display

        Returns:
            The multi-line input string
        """
        print_formatted_text(HTML("<cyan>Enter multi-line input. Press Ctrl+D or type 'END' on a new line to finish.</cyan>"))

        lines = []
        line_num = 1

        while True:
            try:
                line = self.session.prompt(f"{prompt}({line_num}) ")
                if line.strip().upper() == "END":
                    break
                lines.append(line)
                line_num += 1
            except EOFError:
                break
            except KeyboardInterrupt:
                return None

        text = "\n".join(lines)

        # Validate
        validation_result = self.validator.validate(text)
        if not validation_result.is_valid:
            print_formatted_text(HTML(f"<red>Input validation failed: {validation_result.error_message}</red>"))
            return None

        self.buffer_manager.add_to_history(text)
        return text

    def display_help(self):
        """Display help for input features."""
        help_text = """
<bold>Advanced Input Features:</bold>

<cyan>Multi-line Input:</cyan>
- Use Shift+Enter or configure for multi-line
- Or use get_multiline_input() method

<cyan>Auto-completion:</cyan>
- Press Tab to complete commands
- Available commands: {commands}

<cyan>Keyboard Shortcuts:</cyan>
- Ctrl+C: Cancel current input
- Ctrl+D: Exit
- Ctrl+L: Clear screen
- Ctrl+Z: Undo (in buffer mode)

<cyan>Syntax Highlighting:</cyan>
- Automatic highlighting for shell commands

<cyan>History:</cyan>
- Up/Down arrows for history navigation
- History saved to ~/.grok_cli_history
        """.format(commands=", ".join(self.commands))

        print_formatted_text(HTML(help_text))


class ValidationResult:
    """Result of input validation."""

    def __init__(self, is_valid: bool, error_message: str = ""):
        self.is_valid = is_valid
        self.error_message = error_message