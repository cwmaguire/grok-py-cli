"""Custom instructions management for Grok agent."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from grok_py.utils.settings import get_custom_instructions_path, save_custom_instructions


logger = logging.getLogger(__name__)


class CustomInstructionsManager:
    """Manager for custom instructions used by the Grok agent."""

    def __init__(self):
        """Initialize the custom instructions manager."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_instructions(self) -> Optional[str]:
        """Get the current custom instructions.

        Returns:
            Custom instructions text or None if not set
        """
        try:
            from grok_py.utils.settings import load_custom_instructions
            instructions = load_custom_instructions()
            if instructions and instructions.strip():
                self.logger.debug("Loaded custom instructions from file")
                return instructions.strip()
            return None
        except Exception as e:
            self.logger.error(f"Failed to load custom instructions: {e}")
            return None

    def set_instructions(self, instructions: str, save: bool = True) -> bool:
        """Set custom instructions.

        Args:
            instructions: The instructions text
            save: Whether to save to file

        Returns:
            True if successful
        """
        try:
            instructions = instructions.strip()
            if not instructions:
                self.logger.warning("Cannot set empty instructions")
                return False

            if save:
                save_custom_instructions(instructions)
                self.logger.info("Custom instructions saved to file")
            else:
                self.logger.debug("Custom instructions set (not saved)")

            return True
        except Exception as e:
            self.logger.error(f"Failed to set custom instructions: {e}")
            return False

    def clear_instructions(self) -> bool:
        """Clear custom instructions.

        Returns:
            True if successful
        """
        try:
            # Save empty string to clear
            save_custom_instructions("")
            self.logger.info("Custom instructions cleared")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear custom instructions: {e}")
            return False

    def has_instructions(self) -> bool:
        """Check if custom instructions are set.

        Returns:
            True if instructions exist and are not empty
        """
        instructions = self.get_instructions()
        return instructions is not None and bool(instructions.strip())

    def get_instructions_length(self) -> int:
        """Get the length of current instructions.

        Returns:
            Character count of instructions
        """
        instructions = self.get_instructions()
        return len(instructions) if instructions else 0

    def validate_instructions(self, instructions: str) -> Dict[str, Any]:
        """Validate custom instructions.

        Args:
            instructions: Instructions to validate

        Returns:
            Validation result with status and any issues
        """
        result = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "stats": {
                "length": len(instructions),
                "lines": len(instructions.split('\n')),
                "words": len(instructions.split())
            }
        }

        # Basic validation
        if not instructions or not instructions.strip():
            result["valid"] = False
            result["issues"].append("Instructions cannot be empty")
            return result

        # Length checks
        if len(instructions) > 10000:
            result["warnings"].append("Instructions are very long (>10k chars), may affect performance")

        if len(instructions) < 10:
            result["warnings"].append("Instructions are very short, may not provide enough context")

        # Check for potentially problematic content
        problematic_phrases = [
            "ignore all previous instructions",
            "forget your system prompt",
            "you are now",
            "override your"
        ]

        lower_instructions = instructions.lower()
        for phrase in problematic_phrases:
            if phrase in lower_instructions:
                result["warnings"].append(f"Instructions contain potentially problematic phrase: '{phrase}'")

        return result

    def preview_instructions(self, max_length: int = 200) -> str:
        """Get a preview of current instructions.

        Args:
            max_length: Maximum length for preview

        Returns:
            Preview text
        """
        instructions = self.get_instructions()
        if not instructions:
            return "No custom instructions set"

        if len(instructions) <= max_length:
            return instructions

        return instructions[:max_length] + "..."

    def backup_instructions(self, backup_path: Optional[Path] = None) -> bool:
        """Create a backup of current instructions.

        Args:
            backup_path: Path for backup file (auto-generated if None)

        Returns:
            True if backup successful
        """
        try:
            instructions = self.get_instructions()
            if not instructions:
                self.logger.warning("No instructions to backup")
                return False

            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = get_custom_instructions_path().parent / f"custom_instructions_backup_{timestamp}.md"

            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(instructions)

            self.logger.info(f"Instructions backed up to {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to backup instructions: {e}")
            return False

    def list_backups(self) -> List[Path]:
        """List available instruction backups.

        Returns:
            List of backup file paths
        """
        try:
            config_dir = get_custom_instructions_path().parent
            backups = list(config_dir.glob("custom_instructions_backup_*.md"))
            return sorted(backups, reverse=True)  # Most recent first
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []

    def restore_from_backup(self, backup_path: Path) -> bool:
        """Restore instructions from a backup.

        Args:
            backup_path: Path to backup file

        Returns:
            True if restoration successful
        """
        try:
            if not backup_path.exists():
                self.logger.error(f"Backup file does not exist: {backup_path}")
                return False

            with open(backup_path, 'r', encoding='utf-8') as f:
                instructions = f.read()

            return self.set_instructions(instructions, save=True)
        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {e}")
            return False

    def get_template(self, template_type: str = "basic") -> str:
        """Get a template for custom instructions.

        Args:
            template_type: Type of template to get

        Returns:
            Template text
        """
        templates = {
            "basic": """# Custom Instructions for Grok Assistant

You are Grok, a helpful and maximally truthful AI assistant built by xAI.

## General Guidelines
- Be helpful, truthful, and direct
- Use clear, concise language
- Admit when you don't know something
- Use markdown formatting for better readability

## Response Style
- Structure responses with headers when appropriate
- Use bullet points or numbered lists for multiple items
- Provide code examples when relevant
- Explain technical concepts clearly

## Tool Usage
- Use available tools when they would help answer questions
- Explain what tools you're using and why
- Be efficient with tool usage

## Code and Technical Topics
- Provide working, well-commented code examples
- Explain code logic and key concepts
- Suggest best practices and common pitfalls
""",
            "developer": """# Developer-Focused Custom Instructions

You are Grok, specialized in software development and programming assistance.

## Coding Guidelines
- Write clean, readable, well-documented code
- Follow language-specific best practices
- Use appropriate design patterns
- Include error handling and edge cases

## Development Workflow
- Suggest efficient development workflows
- Recommend appropriate tools and libraries
- Help with debugging and troubleshooting
- Provide testing strategies

## Architecture & Design
- Think about scalability and maintainability
- Consider security implications
- Suggest appropriate architectural patterns
- Help with code organization and structure

## Best Practices
- Follow industry standards and conventions
- Suggest performance optimizations
- Include logging and monitoring considerations
- Promote code reusability and modularity
""",
            "minimal": """# Minimal Custom Instructions

You are Grok, a helpful AI assistant.

Be concise, accurate, and helpful in your responses.
Use tools when they provide value.
Explain your reasoning when appropriate.
"""
        }

        return templates.get(template_type, templates["basic"])


# Global instance for convenience
_instructions_manager = CustomInstructionsManager()


def get_instructions() -> Optional[str]:
    """Get current custom instructions."""
    return _instructions_manager.get_instructions()


def set_instructions(instructions: str, save: bool = True) -> bool:
    """Set custom instructions."""
    return _instructions_manager.set_instructions(instructions, save)


def clear_instructions() -> bool:
    """Clear custom instructions."""
    return _instructions_manager.clear_instructions()


def has_instructions() -> bool:
    """Check if custom instructions are set."""
    return _instructions_manager.has_instructions()


def validate_instructions(instructions: str) -> Dict[str, Any]:
    """Validate custom instructions."""
    return _instructions_manager.validate_instructions(instructions)


def get_instructions_template(template_type: str = "basic") -> str:
    """Get an instructions template."""
    return _instructions_manager.get_template(template_type)