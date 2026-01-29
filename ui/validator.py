"""
Input Validator for Grok CLI

Provides comprehensive input validation, parameter checking, and security scanning
to ensure safe and valid user inputs.
"""

import re
import os
import shlex
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import platform

from .input_handler import ValidationResult


class InputValidator:
    """
    Validates and sanitizes user input for security and correctness.
    """

    def __init__(self):
        # Define allowed commands and their parameter requirements
        self.allowed_commands = {
            "help": {"params": [], "required": []},
            "exit": {"params": [], "required": []},
            "quit": {"params": [], "required": []},
            "clear": {"params": [], "required": []},
            "history": {"params": [], "required": []},
            "view_file": {"params": ["path"], "required": ["path"]},
            "create_file": {"params": ["path", "content"], "required": ["path", "content"]},
            "str_replace_editor": {"params": ["path", "old_str", "new_str"], "required": ["path", "old_str", "new_str"]},
            "bash": {"params": ["command"], "required": ["command"]},
            "search": {"params": ["query"], "required": ["query"]},
            "create_todo_list": {"params": ["todos"], "required": ["todos"]},
            "update_todo_list": {"params": ["updates"], "required": ["updates"]},
            "apt": {"params": ["operation"], "required": ["operation"]},
            "systemctl": {"params": ["operation", "service"], "required": ["operation", "service"]},
            "disk": {"params": ["operation"], "required": ["operation"]},
            "network": {"params": ["operation"], "required": ["operation"]},
            "code_execution": {"params": ["operation", "code", "language"], "required": ["operation", "code", "language"]},
            "web_search": {"params": ["query"], "required": ["query"]},
        }

        # Security patterns to detect potentially dangerous inputs
        self.dangerous_patterns = [
            re.compile(r';\s*rm\s', re.IGNORECASE),  # rm commands
            re.compile(r';\s*del\s', re.IGNORECASE),  # delete commands
            re.compile(r';\s*format\s', re.IGNORECASE),  # format commands
            re.compile(r'`.*`', re.IGNORECASE),  # command substitution
            re.compile(r'\$\(.*\)', re.IGNORECASE),  # command substitution
            re.compile(r'>\s*/', re.IGNORECASE),  # redirect to root
            re.compile(r'<\s*/', re.IGNORECASE),  # redirect from root
            re.compile(r'\.\./\.\./\.\./\.\./\.\./\.\./', re.IGNORECASE),  # excessive directory traversal
            re.compile(r'passwd|shadow|/etc/', re.IGNORECASE),  # sensitive files
            re.compile(r'sudo\s', re.IGNORECASE),  # sudo usage
        ]

        # Allowed file extensions for safety
        self.allowed_file_extensions = {
            '.py', '.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.html', '.css', '.js',
            '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd'
        }

        # Platform-specific path handling
        self.system = platform.system().lower()

    def validate(self, input_text: str) -> ValidationResult:
        """
        Validate the entire input string.

        Args:
            input_text: The raw input to validate

        Returns:
            ValidationResult indicating success/failure and error message
        """
        if not input_text or not input_text.strip():
            return ValidationResult(False, "Input cannot be empty")

        # Sanitize first
        sanitized = self.sanitize(input_text)
        if sanitized != input_text:
            return ValidationResult(False, "Input contains potentially dangerous characters")

        # Parse command and parameters
        try:
            parts = shlex.split(input_text)
            if not parts:
                return ValidationResult(False, "No command provided")

            command = parts[0].lower()
            params = parts[1:]
        except ValueError as e:
            return ValidationResult(False, f"Invalid input format: {str(e)}")

        # Validate command
        command_result = self._validate_command(command)
        if not command_result.is_valid:
            return command_result

        # Validate parameters
        param_result = self._validate_parameters(command, params)
        if not param_result.is_valid:
            return param_result

        # Security scan
        security_result = self._security_scan(input_text)
        if not security_result.is_valid:
            return security_result

        return ValidationResult(True)

    def sanitize(self, input_text: str) -> str:
        """
        Sanitize input to remove potentially dangerous characters.

        Args:
            input_text: Raw input

        Returns:
            Sanitized input
        """
        # Remove null bytes
        sanitized = input_text.replace('\0', '')

        # Remove control characters except newlines and tabs
        sanitized = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', sanitized)

        # Limit length
        if len(sanitized) > 10000:
            sanitized = sanitized[:10000] + "..."

        return sanitized

    def _validate_command(self, command: str) -> ValidationResult:
        """Validate that the command is allowed."""
        if command not in self.allowed_commands:
            return ValidationResult(False, f"Unknown command: {command}")

        return ValidationResult(True)

    def _validate_parameters(self, command: str, params: List[str]) -> ValidationResult:
        """Validate command parameters."""
        cmd_config = self.allowed_commands[command]
        required_params = cmd_config["required"]
        allowed_params = cmd_config["params"]

        # Check minimum required parameters
        if len(params) < len(required_params):
            missing = required_params[len(params):]
            return ValidationResult(False, f"Missing required parameters: {', '.join(missing)}")

        # Validate specific parameter types
        param_dict = self._parse_params_to_dict(params)

        for param_name in allowed_params:
            if param_name in param_dict:
                value = param_dict[param_name]
                result = self._validate_parameter_value(command, param_name, value)
                if not result.is_valid:
                    return result

        return ValidationResult(True)

    def _parse_params_to_dict(self, params: List[str]) -> Dict[str, str]:
        """Parse parameter list into key-value pairs."""
        param_dict = {}
        i = 0
        while i < len(params):
            if params[i].startswith('--') or params[i].startswith('-'):
                key = params[i].lstrip('-')
                if i + 1 < len(params) and not params[i + 1].startswith('-'):
                    param_dict[key] = params[i + 1]
                    i += 2
                else:
                    param_dict[key] = ""
                    i += 1
            else:
                # Positional parameter
                param_dict[str(len(param_dict))] = params[i]
                i += 1
        return param_dict

    def _validate_parameter_value(self, command: str, param_name: str, value: str) -> ValidationResult:
        """Validate individual parameter values."""
        if not value:
            return ValidationResult(True)  # Allow empty for optional params

        if param_name in ["path", "0"]:  # File paths
            return self._validate_file_path(value)
        elif param_name == "command":  # Bash commands
            return self._validate_bash_command(value)
        elif param_name == "query":  # Search queries
            return self._validate_search_query(value)
        elif param_name == "content":  # File content
            return self._validate_file_content(value)
        elif param_name in ["old_str", "new_str"]:  # Replace strings
            return self._validate_replace_string(value)
        elif param_name == "operation":  # Operations
            return self._validate_operation(command, value)
        elif param_name == "language":  # Programming languages
            return self._validate_language(value)

        return ValidationResult(True)

    def _validate_file_path(self, path: str) -> ValidationResult:
        """Validate file path for safety."""
        try:
            # Convert to Path object
            path_obj = Path(path)

            # Check for directory traversal
            if ".." in path or path.startswith("/"):
                # Allow absolute paths but check for sensitive areas
                resolved = path_obj.resolve()
                sensitive_paths = ["/etc", "/usr", "/bin", "/sbin", "/root", "/home"]
                for sensitive in sensitive_paths:
                    if str(resolved).startswith(sensitive):
                        return ValidationResult(False, f"Access to system path not allowed: {path}")

            # Check file extension if it exists
            if path_obj.suffix and path_obj.suffix.lower() not in self.allowed_file_extensions:
                return ValidationResult(False, f"File extension not allowed: {path_obj.suffix}")

            # Check path length
            if len(str(path_obj)) > 255:
                return ValidationResult(False, "Path too long")

        except Exception as e:
            return ValidationResult(False, f"Invalid path: {str(e)}")

        return ValidationResult(True)

    def _validate_bash_command(self, command: str) -> ValidationResult:
        """Validate bash commands for safety."""
        # Check for dangerous commands
        dangerous_commands = ['rm', 'del', 'format', 'fdisk', 'mkfs', 'dd', 'sudo', 'su']
        for dangerous in dangerous_commands:
            if dangerous in command.lower():
                return ValidationResult(False, f"Dangerous command detected: {dangerous}")

        # Check command length
        if len(command) > 1000:
            return ValidationResult(False, "Command too long")

        return ValidationResult(True)

    def _validate_search_query(self, query: str) -> ValidationResult:
        """Validate search queries."""
        if len(query) > 500:
            return ValidationResult(False, "Search query too long")

        # Check for potentially malicious patterns
        if re.search(r'[;&|`$]', query):
            return ValidationResult(False, "Search query contains invalid characters")

        return ValidationResult(True)

    def _validate_file_content(self, content: str) -> ValidationResult:
        """Validate file content."""
        if len(content) > 100000:  # 100KB limit
            return ValidationResult(False, "File content too large")

        return ValidationResult(True)

    def _validate_replace_string(self, string: str) -> ValidationResult:
        """Validate strings for replacement operations."""
        if len(string) > 10000:
            return ValidationResult(False, "Replacement string too long")

        return ValidationResult(True)

    def _validate_operation(self, command: str, operation: str) -> ValidationResult:
        """Validate operation parameters."""
        valid_operations = {
            "apt": ["install", "remove", "update", "upgrade", "search", "show"],
            "systemctl": ["start", "stop", "restart", "status", "enable", "disable", "is-active", "is-enabled"],
            "disk": ["usage", "free", "du", "large-files", "cleanup"],
            "network": ["ping", "traceroute", "interfaces", "connections", "dns", "speedtest"],
            "code_execution": ["run", "test"]
        }

        if command in valid_operations and operation not in valid_operations[command]:
            return ValidationResult(False, f"Invalid operation for {command}: {operation}")

        return ValidationResult(True)

    def _validate_language(self, language: str) -> ValidationResult:
        """Validate programming language."""
        valid_languages = [
            "javascript", "typescript", "python", "python3", "java", "cpp", "c",
            "go", "rust", "bash", "shell", "sh"
        ]

        if language.lower() not in valid_languages:
            return ValidationResult(False, f"Unsupported language: {language}")

        return ValidationResult(True)

    def _security_scan(self, input_text: str) -> ValidationResult:
        """Perform security scanning for dangerous patterns."""
        for pattern in self.dangerous_patterns:
            if pattern.search(input_text):
                return ValidationResult(False, "Input contains potentially dangerous pattern")

        return ValidationResult(True)