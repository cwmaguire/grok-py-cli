"""
User Prompt System Component

Provides interactive prompt components for various input types including text, password,
numeric, selection lists, and file path inputs with real-time validation and error handling.
"""

import os
import re
import getpass
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any, Union, Pattern
from rich.console import Console
from rich.prompt import Prompt as RichPrompt
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich.columns import Columns
import sys
import select
import termios
import tty

# Internationalization messages
PROMPT_MESSAGES = {
    'en': {
        'enter_text': 'Enter {field}: ',
        'enter_password': 'Enter password: ',
        'enter_number': 'Enter number ({min}-{max}): ',
        'select_option': 'Select option (use arrow keys or 1-{count}): ',
        'enter_path': 'Enter file path: ',
        'invalid_input': 'Invalid input: {error}',
        'value_required': 'This field is required',
        'number_range': 'Number must be between {min} and {max}',
        'invalid_format': 'Invalid format',
        'file_not_found': 'File not found',
        'directory_not_found': 'Directory not found',
        'path_not_absolute': 'Path must be absolute',
        'press_enter': 'Press Enter to confirm',
        'use_arrows': 'Use ↑↓ arrows to navigate, Enter to select',
        'current_selection': 'Current selection: {selection}',
    }
}

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

class InputValidator:
    """Base class for input validation."""
    
    def __init__(self, required: bool = False, custom_error: Optional[str] = None):
        self.required = required
        self.custom_error = custom_error
        
    def validate(self, value: str) -> str:
        """Validate input and return cleaned value or raise ValidationError."""
        if self.required and not value.strip():
            raise ValidationError(self.custom_error or "This field is required")
        return value.strip()

class TextValidator(InputValidator):
    """Validator for text inputs."""
    
    def __init__(self, min_length: int = 0, max_length: int = 0, pattern: Optional[Pattern] = None, **kwargs):
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        
    def validate(self, value: str) -> str:
        value = super().validate(value)
        if self.min_length and len(value) < self.min_length:
            raise ValidationError(f"Minimum length is {self.min_length} characters")
        if self.max_length and len(value) > self.max_length:
            raise ValidationError(f"Maximum length is {self.max_length} characters")
        if self.pattern and not self.pattern.match(value):
            raise ValidationError("Invalid format")
        return value

class NumericValidator(InputValidator):
    """Validator for numeric inputs."""
    
    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None, 
                 allow_float: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.allow_float = allow_float
        
    def validate(self, value: str) -> Union[int, float]:
        value = super().validate(value)
        try:
            if self.allow_float:
                num = float(value)
            else:
                num = int(value)
        except ValueError:
            raise ValidationError("Invalid number")
            
        if self.min_value is not None and num < self.min_value:
            raise ValidationError(f"Number must be at least {self.min_value}")
        if self.max_value is not None and num > self.max_value:
            raise ValidationError(f"Number must be at most {self.max_value}")
            
        return num

class PathValidator(InputValidator):
    """Validator for file/directory paths."""
    
    def __init__(self, must_exist: bool = False, must_be_file: bool = False, 
                 must_be_dir: bool = False, absolute: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.must_exist = must_exist
        self.must_be_file = must_be_file
        self.must_be_dir = must_be_dir
        self.absolute = absolute
        
    def validate(self, value: str) -> Path:
        value = super().validate(value)
        path = Path(value).expanduser()
        
        if self.absolute and not path.is_absolute():
            raise ValidationError("Path must be absolute")
            
        if self.must_exist and not path.exists():
            raise ValidationError("Path does not exist")
            
        if self.must_be_file and not path.is_file():
            raise ValidationError("Path must be a file")
            
        if self.must_be_dir and not path.is_dir():
            raise ValidationError("Path must be a directory")
            
        return path

class UserPromptSystem:
    """
    Interactive user prompt system with real-time validation and formatting.
    
    Supports various input types with customizable validation, error handling,
    and accessibility features.
    """
    
    def __init__(self, console: Optional[Console] = None, language: str = 'en'):
        self.console = console or Console()
        self.language = language
        self.messages = PROMPT_MESSAGES.get(language, PROMPT_MESSAGES['en'])
        self.theme = {
            'prompt_style': 'bold cyan',
            'input_style': 'white',
            'error_style': 'red',
            'success_style': 'green',
            'info_style': 'blue',
        }
        
    def set_theme(self, theme: Dict[str, str]):
        """Customize the prompt theme."""
        self.theme.update(theme)
        
    def prompt_text(
        self,
        field_name: str = "text",
        default: Optional[str] = None,
        validator: Optional[InputValidator] = None,
        placeholder: Optional[str] = None,
        multiline: bool = False
    ) -> str:
        """
        Prompt for text input with validation.
        
        Args:
            field_name: Name of the field for display
            default: Default value
            validator: InputValidator instance
            placeholder: Placeholder text
            multiline: Whether to allow multiline input
            
        Returns:
            Validated text input
        """
        prompt_text = self.messages['enter_text'].format(field=field_name)
        if placeholder:
            prompt_text += f"[{placeholder}] "
            
        while True:
            try:
                value = RichPrompt.ask(prompt_text, default=default, console=self.console)
                if validator:
                    value = validator.validate(value)
                return value
            except ValidationError as e:
                self._show_error(str(e))
                
    def prompt_password(
        self,
        field_name: str = "password",
        confirm: bool = False,
        validator: Optional[InputValidator] = None
    ) -> str:
        """
        Prompt for password input (masked).
        
        Args:
            field_name: Name of the field
            confirm: Whether to ask for confirmation
            validator: Password validator
            
        Returns:
            Password string
        """
        prompt_text = self.messages['enter_password']
        
        while True:
            try:
                password = getpass.getpass(prompt_text)
                if confirm:
                    confirm_password = getpass.getpass("Confirm password: ")
                    if password != confirm_password:
                        raise ValidationError("Passwords do not match")
                        
                if validator:
                    password = validator.validate(password)
                return password
            except ValidationError as e:
                self._show_error(str(e))
                
    def prompt_number(
        self,
        field_name: str = "number",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        default: Optional[float] = None,
        allow_float: bool = True
    ) -> Union[int, float]:
        """
        Prompt for numeric input with range validation.
        
        Args:
            field_name: Name of the field
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            default: Default value
            allow_float: Whether to allow decimal numbers
            
        Returns:
            Validated number
        """
        validator = NumericValidator(
            min_value=min_value, 
            max_value=max_value, 
            allow_float=allow_float,
            required=True
        )
        
        range_text = ""
        if min_value is not None and max_value is not None:
            range_text = f" ({min_value}-{max_value})"
        elif min_value is not None:
            range_text = f" (min: {min_value})"
        elif max_value is not None:
            range_text = f" (max: {max_value})"
            
        prompt_text = self.messages['enter_number'].format(
            field=field_name, 
            min=min_value or '', 
            max=max_value or ''
        ).replace(' ()', '').replace(f" ({min_value or ''}-{max_value or ''})", range_text)
        
        while True:
            try:
                value = RichPrompt.ask(prompt_text, default=str(default) if default else None, console=self.console)
                return validator.validate(value)
            except ValidationError as e:
                self._show_error(str(e))
                
    def prompt_selection(
        self,
        options: List[str],
        title: str = "Select option",
        default_index: int = 0,
        multi_select: bool = False
    ) -> Union[str, List[str]]:
        """
        Interactive selection from a list of options.
        
        Args:
            options: List of options to choose from
            title: Title for the selection prompt
            default_index: Default selected index
            multi_select: Whether to allow multiple selections
            
        Returns:
            Selected option(s)
        """
        if not options:
            raise ValueError("No options provided")
            
        selected_indices = [default_index] if not multi_select else []
        current_index = default_index
        
        with self.console.screen():
            while True:
                table = self._build_selection_table(options, selected_indices, current_index, title)
                self.console.clear()
                self.console.print(table)
                self.console.print(f"\n{self.messages['use_arrows']}", style=self.theme['info_style'])
                if multi_select:
                    self.console.print("Press Space to select/deselect, Enter to confirm", style=self.theme['info_style'])
                else:
                    self.console.print(self.messages['press_enter'], style=self.theme['info_style'])
                
                key = self._get_key()
                
                if key == '\n':  # Enter
                    if multi_select:
                        if selected_indices:
                            return [options[i] for i in selected_indices]
                        else:
                            self._show_error("Please select at least one option")
                            continue
                    else:
                        return options[current_index]
                        
                elif key == '\x1b[A':  # Up arrow
                    current_index = max(0, current_index - 1)
                elif key == '\x1b[B':  # Down arrow
                    current_index = min(len(options) - 1, current_index + 1)
                elif key == ' ' and multi_select:  # Space
                    if current_index in selected_indices:
                        selected_indices.remove(current_index)
                    else:
                        selected_indices.append(current_index)
                elif key in ('q', '\x1b'):  # Quit
                    return None
                    
    def prompt_path(
        self,
        field_name: str = "path",
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_dir: bool = False,
        absolute: bool = False,
        default: Optional[str] = None
    ) -> Path:
        """
        Prompt for file/directory path with validation.
        
        Args:
            field_name: Name of the field
            must_exist: Whether path must exist
            must_be_file: Whether path must be a file
            must_be_dir: Whether path must be a directory
            absolute: Whether path must be absolute
            default: Default path
            
        Returns:
            Validated Path object
        """
        validator = PathValidator(
            must_exist=must_exist,
            must_be_file=must_be_file,
            must_be_dir=must_be_dir,
            absolute=absolute,
            required=True
        )
        
        prompt_text = self.messages['enter_path']
        
        while True:
            try:
                path_str = RichPrompt.ask(prompt_text, default=default, console=self.console)
                return validator.validate(path_str)
            except ValidationError as e:
                self._show_error(str(e))
                
    def _build_selection_table(
        self, 
        options: List[str], 
        selected_indices: List[int], 
        current_index: int, 
        title: str
    ) -> Table:
        """Build a table for option selection."""
        table = Table(title=title, show_header=False, border_style=self.theme['prompt_style'])
        
        for i, option in enumerate(options):
            marker = ""
            style = self.theme['input_style']
            
            if i == current_index:
                marker += "→ "
                style = self.theme['prompt_style']
                
            if i in selected_indices:
                marker += "✓ "
                style = self.theme['success_style']
            elif selected_indices:  # Multi-select mode
                marker += "  "
                
            table.add_row(f"{i+1}. {marker}{option}", style=style)
            
        return table
        
    def _get_key(self) -> str:
        """Get a single key press (cross-platform)."""
        try:
            if sys.platform != 'win32':
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
                try:
                    key = sys.stdin.read(1)
                    if key == '\x1b':  # Escape sequence
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            key += sys.stdin.read(2)  # Read rest of escape sequence
                    return key
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            else:
                import msvcrt
                key = msvcrt.getch()
                if key == b'\xe0':  # Special key prefix
                    key = msvcrt.getch()
                    if key == b'H': return '\x1b[A'  # Up
                    elif key == b'P': return '\x1b[B'  # Down
                return key.decode('cp1252', errors='ignore')
        except Exception:
            return ''
            
    def _show_error(self, message: str):
        """Display an error message."""
        self.console.print(f"❌ {message}", style=self.theme['error_style'])