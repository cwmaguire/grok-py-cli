"""
Enhanced Confirmation Dialog Component

Provides advanced interactive confirmation dialogs with multiple choices, timeout handling,
default selections, customizable styling, history tracking, and undo functionality.
"""

import threading
import time
from typing import Optional, Callable, List, Dict, Any, Union
from dataclasses import dataclass
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.columns import Columns
from rich.live import Live
from rich.spinner import Spinner
import sys
import select
import termios
import tty

# Internationalization support - simple dict for now
MESSAGES = {
    'en': {
        'yes': 'Yes',
        'no': 'No',
        'cancel': 'Cancel',
        'confirm_title': 'Confirmation',
        'timeout_warning': 'Timeout in {seconds} seconds...',
        'default_selection': '(default: {choice})',
        'press_key': 'Press {key} for {choice}',
        'undo_available': 'Undo available (press U)',
        'confirm_action': 'Confirm action: {action}',
        'invalid_choice': 'Invalid choice. Please select from: {choices}',
        'timeout_expired': 'Timeout expired. Using default: {default}',
    }
}

@dataclass
class ConfirmationRecord:
    """Record of a confirmation for history and undo."""
    id: str
    timestamp: float
    action: str
    choice: str
    callback: Optional[Callable] = None
    reverted: bool = False

class ConfirmationHistory:
    """Manages confirmation history and undo functionality."""
    
    def __init__(self, max_history: int = 100):
        self.history: List[ConfirmationRecord] = []
        self.max_history = max_history
        
    def add_record(self, record: ConfirmationRecord):
        """Add a confirmation record to history."""
        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
    def get_last(self) -> Optional[ConfirmationRecord]:
        """Get the last confirmation record."""
        return self.history[-1] if self.history else None
        
    def undo_last(self) -> Optional[ConfirmationRecord]:
        """Undo the last confirmation if possible."""
        last = self.get_last()
        if last and not last.reverted and last.callback:
            last.callback(last.choice)  # Revert action
            last.reverted = True
            return last
        return None
        
    def get_history(self, limit: int = 10) -> List[ConfirmationRecord]:
        """Get recent confirmation history."""
        return self.history[-limit:] if self.history else []

class EnhancedConfirmationDialog:
    """
    Enhanced confirmation dialog with advanced features.
    
    Features:
    - Multiple choice options (not just yes/no)
    - Timeout handling with auto-selection
    - Default selections
    - Customizable styling and themes
    - History tracking and undo functionality
    - Non-blocking mode with callbacks
    - Accessibility support
    - Internationalization
    """
    
    def __init__(self, console: Optional[Console] = None, language: str = 'en'):
        self.console = console or Console()
        self.language = language
        self.messages = MESSAGES.get(language, MESSAGES['en'])
        self.history = ConfirmationHistory()
        self.theme = {
            'border_style': 'blue',
            'title_style': 'bold blue',
            'default_style': 'dim cyan',
            'warning_style': 'yellow',
            'error_style': 'red',
            'success_style': 'green',
        }
        
    def set_theme(self, theme: Dict[str, str]):
        """Customize the dialog theme."""
        self.theme.update(theme)
        
    def confirm(
        self,
        message: str,
        choices: List[str] = None,
        default: Optional[str] = None,
        timeout: Optional[int] = None,
        title: Optional[str] = None,
        show_undo: bool = False,
        record_id: Optional[str] = None,
        undo_callback: Optional[Callable] = None,
    ) -> Optional[str]:
        """
        Display an enhanced confirmation dialog.
        
        Args:
            message: The confirmation message
            choices: List of available choices (default: ['yes', 'no'])
            default: Default choice if timeout or no input
            timeout: Timeout in seconds for auto-selection
            title: Dialog title
            show_undo: Whether to show undo option
            record_id: Unique ID for history recording
            undo_callback: Callback for undo operations
            
        Returns:
            Selected choice or None if cancelled
        """
        if choices is None:
            choices = [self.messages['yes'], self.messages['no']]
            
        if default is None:
            default = choices[0]
            
        if title is None:
            title = self.messages['confirm_title']
            
        # Validate default
        if default not in choices:
            raise ValueError(f"Default choice '{default}' not in available choices")
            
        # Create dialog content
        content = self._build_dialog_content(message, choices, default, timeout, show_undo)
        
        with self.console.screen():
            live = Live(content, console=self.console, refresh_per_second=4)
            live.start()
            
            choice = None
            start_time = time.time()
            
            while choice is None:
                # Check for timeout
                if timeout and (time.time() - start_time) >= timeout:
                    choice = default
                    self._show_timeout_message(live, default)
                    break
                    
                # Handle input
                choice = self._handle_input(choices, default, show_undo)
                
                if choice:
                    break
                    
                # Update countdown if timeout
                if timeout:
                    remaining = int(timeout - (time.time() - start_time))
                    if remaining > 0:
                        content = self._build_dialog_content(
                            message, choices, default, timeout, show_undo, remaining
                        )
                        live.update(content)
                        
                time.sleep(0.1)
                
            live.stop()
            
        # Record in history
        if record_id:
            record = ConfirmationRecord(
                id=record_id,
                timestamp=time.time(),
                action=message,
                choice=choice,
                callback=undo_callback
            )
            self.history.add_record(record)
            
        return choice
        
    def confirm_async(
        self,
        message: str,
        callback: Callable[[str], None],
        choices: List[str] = None,
        default: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs
    ):
        """
        Non-blocking confirmation that runs in background with callback.
        
        Args:
            message: Confirmation message
            callback: Callback function to call with result
            choices: Available choices
            default: Default choice
            timeout: Timeout for auto-selection
            **kwargs: Additional arguments for confirm()
        """
        def run_confirmation():
            result = self.confirm(message, choices, default, timeout, **kwargs)
            callback(result)
            
        thread = threading.Thread(target=run_confirmation, daemon=True)
        thread.start()
        
    def undo_last(self) -> bool:
        """Undo the last confirmation if possible."""
        record = self.history.undo_last()
        if record:
            self.console.print(f"[green]Undid action: {record.action}[/green]")
            return True
        self.console.print("[yellow]No action available to undo[/yellow]")
        return False
        
    def get_history(self, limit: int = 10) -> List[ConfirmationRecord]:
        """Get recent confirmation history."""
        return self.history.get_history(limit)
        
    def _build_dialog_content(
        self, 
        message: str, 
        choices: List[str], 
        default: str, 
        timeout: Optional[int] = None,
        show_undo: bool = False,
        remaining: Optional[int] = None
    ) -> Panel:
        """Build the dialog panel content."""
        lines = [Text(message, style='white')]
        lines.append(Text())
        
        # Show choices with shortcuts
        choice_lines = []
        for i, choice in enumerate(choices):
            key = str(i + 1) if len(choices) > 2 else ('y' if choice.lower() == 'yes' else 'n')
            style = self.theme['success_style'] if choice == default else 'white'
            choice_text = f"{key}. {choice}"
            if choice == default:
                choice_text += f" {self.messages['default_selection'].format(choice=choice)}"
            choice_lines.append(Text(choice_text, style=style))
            
        lines.extend(choice_lines)
        lines.append(Text())
        
        # Timeout warning
        if timeout and remaining is not None:
            warning = self.messages['timeout_warning'].format(seconds=remaining)
            lines.append(Text(warning, style=self.theme['warning_style']))
            
        # Undo option
        if show_undo:
            lines.append(Text(self.messages['undo_available'], style=self.theme['default_style']))
            
        content = Text("\n").join(lines)
        
        return Panel(
            content,
            title=title,
            border_style=self.theme['border_style'],
            title_align='left'
        )
        
    def _handle_input(self, choices: List[str], default: str, show_undo: bool) -> Optional[str]:
        """Handle user input for choices."""
        try:
            # Use select for non-blocking input
            if sys.platform != 'win32':
                # Unix-like systems
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
                try:
                    if select.select([sys.stdin], [], [], 0)[0]:
                        key = sys.stdin.read(1).lower()
                    else:
                        return None
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            else:
                # Windows - simplified
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8').lower()
                else:
                    return None
                    
            # Handle choices
            if len(choices) == 2:
                if key == 'y':
                    return choices[0] if choices[0].lower().startswith('y') else choices[1]
                elif key == 'n':
                    return choices[1] if choices[1].lower().startswith('n') else choices[0]
            else:
                try:
                    idx = int(key) - 1
                    if 0 <= idx < len(choices):
                        return choices[idx]
                except ValueError:
                    pass
                    
            # Undo
            if show_undo and key == 'u':
                self.undo_last()
                return None
                
        except Exception:
            pass
            
        return None
        
    def _show_timeout_message(self, live: Live, default: str):
        """Show timeout message."""
        message = self.messages['timeout_expired'].format(default=default)
        content = Panel(
            Text(message, style=self.theme['warning_style']),
            title=self.messages['confirm_title'],
            border_style=self.theme['border_style']
        )
        live.update(content)
        time.sleep(1)  # Brief pause to show message