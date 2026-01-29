"""
Input Buffer Manager for Grok CLI

Provides advanced text editing capabilities with undo/redo functionality,
clipboard operations, and buffer management for input handling.
"""

import os
import sys
from typing import List, Optional, Deque
from collections import deque
import platform

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class BufferState:
    """Represents a snapshot of the buffer state for undo/redo."""

    def __init__(self, text: str, cursor_position: int = 0):
        self.text = text
        self.cursor_position = cursor_position


class InputBufferManager:
    """
    Manages input buffer with editing, undo/redo, and clipboard operations.
    """

    def __init__(self, max_history_size: int = 100):
        self.current_text = ""
        self.cursor_position = 0
        self.max_history_size = max_history_size

        # Undo/redo stacks
        self.undo_stack: Deque[BufferState] = deque(maxlen=max_history_size)
        self.redo_stack: Deque[BufferState] = deque(maxlen=max_history_size)

        # Command history for input history
        self.command_history: List[str] = []
        self.history_index = -1

        # Clipboard
        self.clipboard_text = ""

        # Multi-line buffer
        self.multi_line_buffer: List[str] = []
        self.multi_line_mode = False

        # Platform detection for clipboard
        self.system = platform.system().lower()

    def set_text(self, text: str, save_state: bool = True):
        """
        Set the current buffer text.

        Args:
            text: The text to set
            save_state: Whether to save current state for undo
        """
        if save_state:
            self._save_state()

        self.current_text = text
        self.cursor_position = len(text)

    def get_text(self) -> str:
        """Get the current buffer text."""
        return self.current_text

    def insert_text(self, text: str, position: Optional[int] = None):
        """
        Insert text at the specified position.

        Args:
            text: Text to insert
            position: Position to insert at (current cursor if None)
        """
        self._save_state()

        if position is None:
            position = self.cursor_position

        self.current_text = (
            self.current_text[:position] + text + self.current_text[position:]
        )
        self.cursor_position = position + len(text)

    def delete_text(self, start: int, end: Optional[int] = None):
        """
        Delete text from start to end position.

        Args:
            start: Start position
            end: End position (start+1 if None)
        """
        self._save_state()

        if end is None:
            end = start + 1

        self.current_text = self.current_text[:start] + self.current_text[end:]
        self.cursor_position = min(self.cursor_position, len(self.current_text))

    def move_cursor(self, position: int):
        """
        Move cursor to specified position.

        Args:
            position: New cursor position
        """
        self.cursor_position = max(0, min(position, len(self.current_text)))

    def move_cursor_left(self, count: int = 1):
        """Move cursor left by count characters."""
        self.cursor_position = max(0, self.cursor_position - count)

    def move_cursor_right(self, count: int = 1):
        """Move cursor right by count characters."""
        self.cursor_position = min(len(self.current_text), self.cursor_position + count)

    def move_cursor_to_start(self):
        """Move cursor to start of line."""
        self.cursor_position = 0

    def move_cursor_to_end(self):
        """Move cursor to end of line."""
        self.cursor_position = len(self.current_text)

    def move_cursor_to_word_start(self):
        """Move cursor to start of current word."""
        text = self.current_text
        pos = self.cursor_position

        # Skip whitespace backwards
        while pos > 0 and text[pos - 1].isspace():
            pos -= 1

        # Skip word characters backwards
        while pos > 0 and not text[pos - 1].isspace():
            pos -= 1

        self.cursor_position = pos

    def move_cursor_to_word_end(self):
        """Move cursor to end of current word."""
        text = self.current_text
        pos = self.cursor_position

        # Skip word characters forwards
        while pos < len(text) and not text[pos].isspace():
            pos += 1

        # Skip whitespace forwards
        while pos < len(text) and text[pos].isspace():
            pos += 1

        self.cursor_position = pos

    def undo(self) -> bool:
        """
        Undo the last operation.

        Returns:
            True if undo was successful, False if no more undo states
        """
        if not self.undo_stack:
            return False

        # Save current state to redo stack
        current_state = BufferState(self.current_text, self.cursor_position)
        self.redo_stack.append(current_state)

        # Restore previous state
        previous_state = self.undo_stack.pop()
        self.current_text = previous_state.text
        self.cursor_position = previous_state.cursor_position

        return True

    def redo(self) -> bool:
        """
        Redo the last undone operation.

        Returns:
            True if redo was successful, False if no more redo states
        """
        if not self.redo_stack:
            return False

        # Save current state to undo stack
        current_state = BufferState(self.current_text, self.cursor_position)
        self.undo_stack.append(current_state)

        # Restore next state
        next_state = self.redo_stack.pop()
        self.current_text = next_state.text
        self.cursor_position = next_state.cursor_position

        return True

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self.redo_stack) > 0

    def copy_to_clipboard(self, text: Optional[str] = None):
        """
        Copy text to clipboard.

        Args:
            text: Text to copy (current selection or all if None)
        """
        if not CLIPBOARD_AVAILABLE:
            return

        if text is None:
            text = self.current_text

        try:
            pyperclip.copy(text)
            self.clipboard_text = text
        except Exception:
            # Fallback for some systems
            pass

    def paste_from_clipboard(self):
        """Paste text from clipboard at cursor position."""
        if not CLIPBOARD_AVAILABLE:
            return

        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                self.insert_text(clipboard_content)
        except Exception:
            # Fallback
            if self.clipboard_text:
                self.insert_text(self.clipboard_text)

    def cut_to_clipboard(self, start: int, end: Optional[int] = None):
        """
        Cut text to clipboard.

        Args:
            start: Start position
            end: End position
        """
        if end is None:
            end = start + 1

        cut_text = self.current_text[start:end]
        self.copy_to_clipboard(cut_text)
        self.delete_text(start, end)

    def select_all(self):
        """Select all text (conceptually - returns range)."""
        return 0, len(self.current_text)

    def clear(self):
        """Clear the buffer."""
        self._save_state()
        self.current_text = ""
        self.cursor_position = 0

    def add_to_history(self, command: str):
        """
        Add command to history.

        Args:
            command: Command to add
        """
        if command and (not self.command_history or self.command_history[-1] != command):
            self.command_history.append(command)
            self.history_index = len(self.command_history)

    def get_previous_command(self) -> Optional[str]:
        """Get previous command from history."""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            return self.command_history[self.history_index]
        return None

    def get_next_command(self) -> Optional[str]:
        """Get next command from history."""
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            return self.command_history[self.history_index]
        elif self.history_index == len(self.command_history) - 1:
            self.history_index = len(self.command_history)
            return ""
        return None

    def start_multi_line_mode(self):
        """Start multi-line input mode."""
        self.multi_line_mode = True
        self.multi_line_buffer = [self.current_text]

    def add_multi_line(self, line: str):
        """Add a line to multi-line buffer."""
        self.multi_line_buffer.append(line)

    def end_multi_line_mode(self) -> str:
        """End multi-line mode and return combined text."""
        self.multi_line_mode = False
        combined = "\n".join(self.multi_line_buffer)
        self.multi_line_buffer = []
        return combined

    def is_multi_line_mode(self) -> bool:
        """Check if in multi-line mode."""
        return self.multi_line_mode

    def _save_state(self):
        """Save current state for undo."""
        state = BufferState(self.current_text, self.cursor_position)
        self.undo_stack.append(state)

        # Clear redo stack when new action is performed
        self.redo_stack.clear()

    def get_cursor_position(self) -> int:
        """Get current cursor position."""
        return self.cursor_position

    def get_line_info(self) -> tuple:
        """
        Get current line information.

        Returns:
            Tuple of (line_number, column, total_lines)
        """
        lines = self.current_text.split('\n')
        current_pos = 0
        line_number = 0

        for i, line in enumerate(lines):
            if current_pos + len(line) >= self.cursor_position:
                line_number = i
                column = self.cursor_position - current_pos
                break
            current_pos += len(line) + 1  # +1 for newline

        return line_number + 1, column + 1, len(lines)

    def search_text(self, query: str, direction: str = "forward") -> Optional[int]:
        """
        Search for text in buffer.

        Args:
            query: Text to search for
            direction: "forward" or "backward"

        Returns:
            Position of found text, or None
        """
        if not query:
            return None

        text = self.current_text
        start_pos = self.cursor_position

        if direction == "forward":
            pos = text.find(query, start_pos)
            if pos == -1 and start_pos > 0:
                pos = text.find(query, 0, start_pos)
        else:
            # Backward search
            pos = text.rfind(query, 0, start_pos)
            if pos == -1:
                pos = text.rfind(query, start_pos)

        if pos != -1:
            self.cursor_position = pos
            return pos

        return None

    def replace_text(self, old_text: str, new_text: str, all_occurrences: bool = False):
        """
        Replace text in buffer.

        Args:
            old_text: Text to replace
            new_text: Replacement text
            all_occurrences: Replace all occurrences
        """
        self._save_state()

        if all_occurrences:
            self.current_text = self.current_text.replace(old_text, new_text)
        else:
            pos = self.current_text.find(old_text, self.cursor_position)
            if pos == -1:
                return False

            self.current_text = (
                self.current_text[:pos] + new_text + self.current_text[pos + len(old_text):]
            )
            self.cursor_position = pos + len(new_text)

        return True