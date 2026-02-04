"""
Basic Terminal UI Framework for Grok CLI

Uses ANSI escape codes for colors and styling.
Provides vertical stack layout with sections.
"""

import os
import sys
import termios
import time
import tty
from typing import List, Optional, Dict


class TerminalUI:
    """Basic terminal UI with ANSI rendering."""

    # ANSI escape codes
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # Colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    GRAY = '\033[90m'
    DIM_GRAY = '\033[2;90m'

    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

    def __init__(self):
        self.width = self._get_terminal_width()
        self.height = self._get_terminal_height()
        self.header = "GROK CLI"
        self.chat_history: List[Dict[str, str]] = []
        self.input_buffer = ""
        self.status_bar = "Ready"
        self.processing = False  # True when assistant is responding
        self.placeholder = "Type your message..."
        self.cursor_pos = 0  # Cursor position in input buffer

        # Status bar components
        self.auto_edit_enabled = False
        self.model_name = "grok-code-fast-1"
        self.mcp_status = "disconnected"

        # Command suggestions
        self.available_commands = [
            "/help", "/model", "/clear", "/exit", "/history",
            "/settings", "/about", "/version"
        ]
        self.show_suggestions = False
        self.suggestions = []
        self.selected_suggestion = 0

        # Model selection
        self.available_models = ["grok-code-fast-1", "grok-3", "grok-2", "grok-1", "grok-beta"]
        self.show_model_selection = False
        self.model_suggestions = []
        self.selected_model = 0

        # Confirmation dialog
        self.show_confirmation = False
        self.confirmation_details = ""
        self.confirmation_diff = ""
        self.confirmation_options = ["Yes", "Yes (don't ask again)", "No", "No (with feedback)"]
        self.selected_option = 0
        self.feedback_mode = False
        self.feedback_buffer = ""
        self.feedback_cursor_pos = 0

        # Performance settings
        self.max_history_size = 100

    def _get_tool_icon(self, tool_name: str) -> str:
        """Get Unicode icon for tool."""
        icons = {
            "view_file": "📖",
            "str_replace_editor": "✏️",
            "create_file": "📝",
            "bash": "💻",
            "search": "🔍",
            "create_todo_list": "📋",
            "update_todo_list": "🔄",
        }
        return icons.get(tool_name, "🔧")  # default tool icon

    def _get_tool_action(self, tool_name: str) -> str:
        """Get action name for tool."""
        actions = {
            "view_file": "Read",
            "str_replace_editor": "Update",
            "create_file": "Create",
            "bash": "Bash",
            "search": "Search",
            "create_todo_list": "Created Todo",
            "update_todo_list": "Updated Todo",
        }
        return actions.get(tool_name, tool_name.replace("_", " ").title())

    def _update_suggestions(self):
        """Update suggestions based on current input buffer."""
        if self.input_buffer.startswith("/model"):
            # Show model selection
            self.model_suggestions = self.available_models
            self.selected_model = self.available_models.index(self.model_name) if self.model_name in self.available_models else 0
            self.show_model_selection = True
            self.show_suggestions = False
            self.suggestions = []
        elif self.input_buffer.startswith("/"):
            query = self.input_buffer.lower()
            self.suggestions = [
                cmd for cmd in self.available_commands
                if cmd.lower().startswith(query)
            ][:8]  # Up to 8 items
            self.selected_suggestion = 0
            self.show_suggestions = len(self.suggestions) > 0
            self.show_model_selection = False
            self.model_suggestions = []
        else:
            self.show_suggestions = False
            self.suggestions = []
            self.show_model_selection = False
            self.model_suggestions = []

    def show_confirmation(self, details: str, diff: str = ""):
        """Show confirmation dialog with operation details and optional diff."""
        self.confirmation_details = details
        self.confirmation_diff = diff
        self.show_confirmation = True
        self.selected_option = 0
        self.feedback_mode = False
        self.feedback_buffer = ""
        self.feedback_cursor_pos = 0

    def _get_terminal_width(self) -> int:
        """Get terminal width."""
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80  # fallback

    def _get_terminal_height(self) -> int:
        """Get terminal height."""
        try:
            return os.get_terminal_size().lines
        except OSError:
            return 24  # fallback

    def _clear_screen(self):
        """Clear the entire screen."""
        print('\033[2J\033[H', end='')

    def _move_cursor(self, row: int, col: int):
        """Move cursor to position."""
        print(f'\033[{row};{col}H', end='')

    def _draw_separator(self, y: int):
        """Draw horizontal separator at row y."""
        separator = '─' * (self.width - 2)
        self._move_cursor(y, 1)
        print(f" {separator} ")

    def _render_input_box(self, y: int) -> int:
        """Render the input box at position y. Returns the new y position."""
        # Border color based on processing state
        border_color = self.YELLOW if self.processing else self.BLUE

        # Input text to display
        if self.input_buffer:
            display_text = self.input_buffer
        else:
            display_text = self.DIM + self.placeholder + self.RESET

        # Calculate input box dimensions
        box_width = self.width - 4  # Leave some margin
        prompt = f"{self.CYAN}❯{self.RESET}"
        prompt_width = 1  # ❯ is 1 char wide
        text_width = box_width - prompt_width - 3  # Space for borders and padding

        # Truncate display text if too long
        if len(self.input_buffer) > text_width:
            display_text = self.input_buffer[:text_width-3] + "..."

        # Build the input line
        input_line = f"{prompt} {display_text}"

        # Create border characters (rounded corners)
        top_border = f"╭{'─' * (box_width - 2)}╮"
        bottom_border = f"╰{'─' * (box_width - 2)}╯"
        content_line = f"│ {input_line}{' ' * (box_width - len(input_line) - 2)}│"

        # Render the box
        self._move_cursor(y, 3)  # Center-ish
        print(f"{border_color}{top_border}{self.RESET}")
        y += 1

        self._move_cursor(y, 3)
        print(f"{border_color}{content_line}{self.RESET}")
        y += 1

        self._move_cursor(y, 3)
        print(f"{border_color}{bottom_border}{self.RESET}")
        y += 1

        # Position cursor inside the input box
        cursor_x = 3 + 2 + prompt_width + 1 + self.cursor_pos  # Border + space + prompt + space + position
        if cursor_x > 3 + box_width - 1:
            cursor_x = 3 + box_width - 1
        self._move_cursor(y - 2, cursor_x)  # Cursor on the content line

        return y

    def _render_suggestions(self, y: int) -> int:
        """Render suggestions dropdown. Returns the new y position."""
        if not self.show_suggestions:
            return y

        # Position above input box
        suggestion_y = y - len(self.suggestions) - 2  # Leave space for help text
        if suggestion_y < 3:  # Don't go above header
            suggestion_y = 3

        # Help text
        self._move_cursor(suggestion_y, 1)
        print(f"{self.DIM}Use ↑↓ or Tab to navigate, Enter to select, Esc to cancel{self.RESET}")
        suggestion_y += 1

        # Render each suggestion
        for i, suggestion in enumerate(self.suggestions):
            self._move_cursor(suggestion_y + i, 1)
            if i == self.selected_suggestion:
                # Cyan background for selected
                print(f"{self.BG_CYAN}{self.BLACK}{suggestion}{self.RESET}")
            else:
                print(f"{self.WHITE}{suggestion}{self.RESET}")

        return suggestion_y + len(self.suggestions) + 1

    def _render_model_selection(self, y: int) -> int:
        """Render model selection dropdown. Returns the new y position."""
        if not self.show_model_selection:
            return y

        # Position above input box
        selection_y = y - len(self.model_suggestions) - 2  # Leave space for help text
        if selection_y < 3:  # Don't go above header
            selection_y = 3

        # Help text
        self._move_cursor(selection_y, 1)
        print(f"{self.DIM}Use ↑↓ or Tab to navigate, Enter to select, Esc to cancel{self.RESET}")
        selection_y += 1

        # Render each model
        for i, model in enumerate(self.model_suggestions):
            self._move_cursor(selection_y + i, 1)
            display_text = model
            if model == self.model_name:
                display_text += " (current)"
            if i == self.selected_model:
                # Cyan background for selected
                print(f"{self.BG_CYAN}{self.BLACK}{display_text}{self.RESET}")
            else:
                print(f"{self.WHITE}{display_text}{self.RESET}")

        return selection_y + len(self.model_suggestions) + 1

    def _render_confirmation(self, y: int) -> int:
        """Render confirmation dialog. Returns the new y position."""
        if not self.show_confirmation:
            return y

        # Position above input box
        dialog_height = 6 + (len(self.confirmation_diff.split('\n')) if self.confirmation_diff else 0) + len(self.confirmation_options)
        dialog_y = y - dialog_height - 2
        if dialog_y < 3:
            dialog_y = 3

        current_y = dialog_y

        # Title
        self._move_cursor(current_y, 1)
        print(f"{self.BOLD}{self.YELLOW}Confirm Operation{self.RESET}")
        current_y += 1

        # Details
        if self.confirmation_details:
            self._move_cursor(current_y, 1)
            print(f"{self.WHITE}Details: {self.confirmation_details}{self.RESET}")
            current_y += 1

        # Diff/Content preview
        if self.confirmation_diff:
            self._move_cursor(current_y, 1)
            print(f"{self.DIM}Preview:{self.RESET}")
            current_y += 1
            diff_lines = self.confirmation_diff.split('\n')
            for line in diff_lines[:10]:  # Limit to 10 lines
                self._move_cursor(current_y, 1)
                if line.startswith('+'):
                    print(f"{self.GREEN}{line}{self.RESET}")
                elif line.startswith('-'):
                    print(f"{self.RED}{line}{self.RESET}")
                else:
                    print(f"{self.DIM}{line}{self.RESET}")
                current_y += 1

        # Options
        current_y += 1
        self._move_cursor(current_y, 1)
        print(f"{self.DIM}Choose an option (↑↓ to navigate, Enter to select):{self.RESET}")
        current_y += 1

        for i, option in enumerate(self.confirmation_options):
            self._move_cursor(current_y + i, 1)
            if i == self.selected_option:
                print(f"{self.BG_CYAN}{self.BLACK}> {option}{self.RESET}")
            else:
                print(f"  {option}")

        current_y += len(self.confirmation_options)

        if self.feedback_mode:
            current_y += 1
            self._move_cursor(current_y, 1)
            print(f"{self.DIM}Feedback:{self.RESET}")
            current_y += 1
            self._move_cursor(current_y, 1)
            display_feedback = self.feedback_buffer if self.feedback_buffer else self.DIM + "Enter your feedback..." + self.RESET
            print(f"❯ {display_feedback}")
            # Position cursor
            cursor_x = 3 + self.feedback_cursor_pos  # ❯ space
            self._move_cursor(current_y, cursor_x)
            current_y += 1

        return current_y + 1

    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to fit within width."""
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= width:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def render(self):
        """Render the entire screen."""
        self._clear_screen()

        # Update dimensions
        self.width = self._get_terminal_width()
        self.height = self._get_terminal_height()

        y = 1

        # Header
        self._move_cursor(y, 1)
        header_text = f" {self.header} "
        print(f"{self.BOLD}{self.CYAN}{header_text}{self.RESET}")
        y += 2

        if not self.chat_history:
            welcome_lines = [
                "🤖 Welcome to Grok CLI Conversational Assistant!",
                "",
                "Getting Started:",
                "1. Ask questions, edit files, or run commands.",
                "2. Be specific for the best results.",
                "3. Create GROK.md files to customize your interactions with Grok.",
                "4. Press Shift+Tab to toggle auto-edit mode.",
                "5. /help for more information."
            ]
            for line in welcome_lines:
                self._move_cursor(y, 1)
                print(f"{self.DIM} {line}{self.RESET}")
                y += 1

        # Separator
        self._draw_separator(y)
        y += 1

        # Help text
        self._move_cursor(y, 1)
        print(f"{self.DIM} Type your request in natural language. Ctrl+C to clear, 'exit' to quit.{self.RESET}")
        y += 1

        # Chat history
        y_pos = y
        max_y = self.height - 3
        for msg in self.chat_history:
            if msg["type"] == "user":
                lines = self._wrap_text(msg["content"], self.width - 4)
                for line in lines:
                    if y_pos > max_y:
                        break
                    self._move_cursor(y_pos, 1)
                    print(f"{self.DIM} > {line}{self.RESET}")
                    y_pos += 1
            elif msg["type"] == "assistant":
                # 1 line margin above each message
                y_pos += 1
                if y_pos > max_y:
                    break
                content = msg["content"]
                if msg.get("streaming", False):
                    content += self.CYAN + "█"
                lines = self._wrap_text(content, self.width - 4)
                for i, line in enumerate(lines):
                    if y_pos > max_y:
                        break
                    self._move_cursor(y_pos, 1)
                    prefix = "⏺" if i == 0 else "⏺"
                    print(f"{self.WHITE}{prefix} {line}{self.RESET}")
                    y_pos += 1
            elif msg["type"] == "tool":
                if y_pos > max_y:
                    break
                icon = self._get_tool_icon(msg["tool_name"])
                action = self._get_tool_action(msg["tool_name"])
                context = msg.get("context", "")
                self._move_cursor(y_pos, 1)
                print(f"{self.WHITE}{icon} {action}{self.RESET}{self.DIM}: {context}{self.RESET}")
                y_pos += 1
            if y_pos > max_y:
                break
        y = y_pos + 1

        # Separator
        self._draw_separator(y)
        y += 1

        # Suggestions or Model Selection (if shown)
        y = self._render_suggestions(y)
        y = self._render_model_selection(y)
        y = self._render_confirmation(y)

        # Input box
        y = self._render_input_box(y)

        # Status bar
        auto_edit_icon = "▶" if self.auto_edit_enabled else "⏸"
        model_display = f"≋ {self.model_name}"
        mcp_display = f"[MCP: {self.mcp_status}]"

        status_parts = [
            f"{self.CYAN}{auto_edit_icon}{self.RESET}",
            f"{self.YELLOW}{model_display}{self.RESET}",
            f"{self.DIM}{mcp_display}{self.RESET}"
        ]
        status_bar_text = "  ".join(status_parts)

        self._move_cursor(self.height, 1)
        print(status_bar_text)

    def get_input(self) -> str:
        """Get user input character by character."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            if ch == '\x1b':  # Escape sequence
                ch += sys.stdin.read(2)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def run(self):
        """Main UI loop."""
        try:
            while True:
                self.render()
                ch = self.get_input()

                if ch == '\x03' or ch == 'q':  # Ctrl+C or 'q' to quit
                    break
                elif ch == '\r' or ch == '\n':  # Enter
                    if self.feedback_mode:
                        # Submit feedback
                        # For now, just add to chat and close
                        self.chat_history.append({"type": "user", "content": f"Feedback: {self.feedback_buffer}"})
                        if len(self.chat_history) > self.max_history_size:
                            self.chat_history.pop(0)
                        self.feedback_mode = False
                        self.feedback_buffer = ""
                        self.feedback_cursor_pos = 0
                        self.show_confirmation = False
                    elif self.show_confirmation:
                        # Select confirmation option
                        selected = self.confirmation_options[self.selected_option]
                        if selected == "Yes":
                            # Proceed with operation
                            self.chat_history.append({"type": "user", "content": f"Confirmed: {self.confirmation_details}"})
                            if len(self.chat_history) > self.max_history_size:
                                self.chat_history.pop(0)
                            self.show_confirmation = False
                        elif selected == "Yes (don't ask again)":
                            # Proceed and disable future confirmations
                            self.chat_history.append({"type": "user", "content": f"Confirmed (auto): {self.confirmation_details}"})
                            if len(self.chat_history) > self.max_history_size:
                                self.chat_history.pop(0)
                            # TODO: set auto-approve flag
                            self.show_confirmation = False
                        elif selected == "No":
                            # Cancel operation
                            self.chat_history.append({"type": "user", "content": f"Cancelled: {self.confirmation_details}"})
                            if len(self.chat_history) > self.max_history_size:
                                self.chat_history.pop(0)
                            self.show_confirmation = False
                        elif selected == "No (with feedback)":
                            # Enter feedback mode
                            self.feedback_mode = True
                    elif self.show_suggestions and self.suggestions:
                        # Select current suggestion
                        self.input_buffer = self.suggestions[self.selected_suggestion]
                        self.cursor_pos = len(self.input_buffer)
                        self.show_suggestions = False
                    elif self.show_model_selection and self.model_suggestions:
                        # Select current model
                        self.model_name = self.model_suggestions[self.selected_model]
                        self.input_buffer = ""
                        self.cursor_pos = 0
                        self.show_model_selection = False
                        self.model_suggestions = []
                    elif self.input_buffer.strip():
                        self.chat_history.append({"type": "user", "content": self.input_buffer})
                        if len(self.chat_history) > self.max_history_size:
                            self.chat_history.pop(0)
                        self.input_buffer = ""
                        self.cursor_pos = 0
                        # Simulate streaming response
                        self.processing = True
                        self.render()
                        response = "Hello! This is a simulated streaming response."
                        self.chat_history.append({"type": "assistant", "content": "", "streaming": True})
                        if len(self.chat_history) > self.max_history_size:
                            self.chat_history.pop(0)
                        # Optimize streaming by batching renders
                        for i in range(0, len(response), 5):
                            chunk = response[i:i+5]
                            self.chat_history[-1]["content"] += chunk
                            self.render()
                            time.sleep(0.02 * len(chunk))  # Simulate typing speed
                        self.chat_history[-1]["streaming"] = False
                        self.processing = False
                        self.render()
                elif ch == '\x1b':  # Escape - cancel suggestions, model selection, or confirmation
                    self.show_suggestions = False
                    self.show_model_selection = False
                    if self.feedback_mode:
                        self.feedback_mode = False
                        self.feedback_buffer = ""
                        self.feedback_cursor_pos = 0
                    else:
                        self.show_confirmation = False
                elif ch == '\x1b[A':  # Up arrow
                    if self.show_confirmation:
                        self.selected_option = max(0, self.selected_option - 1)
                    elif self.show_suggestions:
                        self.selected_suggestion = max(0, self.selected_suggestion - 1)
                    elif self.show_model_selection:
                        self.selected_model = max(0, self.selected_model - 1)
                elif ch == '\x1b[B':  # Down arrow
                    if self.show_confirmation:
                        self.selected_option = min(len(self.confirmation_options) - 1, self.selected_option + 1)
                    elif self.show_suggestions:
                        self.selected_suggestion = min(len(self.suggestions) - 1, self.selected_suggestion + 1)
                    elif self.show_model_selection:
                        self.selected_model = min(len(self.model_suggestions) - 1, self.selected_model + 1)
                elif ch == '\t':  # Tab
                    if self.show_confirmation:
                        self.selected_option = (self.selected_option + 1) % len(self.confirmation_options)
                    elif self.show_suggestions:
                        self.selected_suggestion = (self.selected_suggestion + 1) % len(self.suggestions)
                    elif self.show_model_selection:
                        self.selected_model = (self.selected_model + 1) % len(self.model_suggestions)
                elif ch == '\x7f' or ch == '\b':  # Backspace
                    if self.feedback_mode:
                        if self.feedback_cursor_pos > 0:
                            self.feedback_buffer = self.feedback_buffer[:self.feedback_cursor_pos-1] + self.feedback_buffer[self.feedback_cursor_pos:]
                            self.feedback_cursor_pos -= 1
                    elif self.cursor_pos > 0:
                        self.input_buffer = self.input_buffer[:self.cursor_pos-1] + self.input_buffer[self.cursor_pos:]
                        self.cursor_pos -= 1
                        self._update_suggestions()
                elif len(ch) == 1 and ord(ch) >= 32:  # Printable chars
                    if self.feedback_mode:
                        self.feedback_buffer = self.feedback_buffer[:self.feedback_cursor_pos] + ch + self.feedback_buffer[self.feedback_cursor_pos:]
                        self.feedback_cursor_pos += 1
                    else:
                        self.input_buffer = self.input_buffer[:self.cursor_pos] + ch + self.input_buffer[self.cursor_pos:]
                        self.cursor_pos += 1
                        self._update_suggestions()

        except KeyboardInterrupt:
            pass
        finally:
            self._clear_screen()
            self._move_cursor(1, 1)
            print("Goodbye!")


if __name__ == "__main__":
    ui = TerminalUI()
    ui.run()