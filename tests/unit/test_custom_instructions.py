"""Unit tests for custom instructions management."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from grok_py.utils.custom_instructions import CustomInstructionsManager


class TestCustomInstructionsManager:
    """Test custom instructions functionality."""

    def test_load_default_instructions(self):
        """Test loading default custom instructions."""
        manager = CustomInstructionsManager()
        instructions = manager.load_instructions()

        assert isinstance(instructions, str)
        assert len(instructions) > 0

    def test_save_and_load_instructions(self):
        """Test saving and loading custom instructions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            instructions_file = os.path.join(temp_dir, 'test_instructions.txt')

            manager = CustomInstructionsManager(instructions_file=instructions_file)

            test_instructions = "You are a helpful AI assistant."

            # Save
            manager.save_instructions(test_instructions)

            # Load in new manager
            new_manager = CustomInstructionsManager(instructions_file=instructions_file)
            loaded_instructions = new_manager.load_instructions()

            assert loaded_instructions == test_instructions

    def test_instructions_file_not_found(self):
        """Test handling missing instructions file."""
        manager = CustomInstructionsManager(instructions_file='/nonexistent/instructions.txt')
        instructions = manager.load_instructions()

        # Should load defaults
        assert isinstance(instructions, str)

    def test_empty_instructions_file(self):
        """Test handling empty instructions file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            instructions_file = os.path.join(temp_dir, 'empty_instructions.txt')

            # Create empty file
            with open(instructions_file, 'w') as f:
                f.write('')

            manager = CustomInstructionsManager(instructions_file=instructions_file)
            instructions = manager.load_instructions()

            # Should load defaults when file is empty
            assert isinstance(instructions, str)

    def test_instructions_validation(self):
        """Test instructions validation."""
        manager = CustomInstructionsManager()

        # Valid instructions
        valid_instructions = "You are a helpful assistant."
        assert manager.validate_instructions(valid_instructions) is True

        # Empty instructions
        assert manager.validate_instructions("") is False

        # Too long instructions
        too_long = "x" * 10000
        assert manager.validate_instructions(too_long) is False

    def test_instructions_formatting(self):
        """Test instructions formatting."""
        manager = CustomInstructionsManager()

        raw_instructions = "  You are a helpful assistant.  "
        formatted = manager.format_instructions(raw_instructions)

        # Should strip whitespace
        assert formatted == "You are a helpful assistant."

    def test_instructions_with_placeholders(self):
        """Test instructions with placeholders."""
        manager = CustomInstructionsManager()

        instructions = "Hello {name}, you are using {app}."
        formatted = manager.format_instructions_with_context(
            instructions,
            {"name": "User", "app": "Grok CLI"}
        )

        assert formatted == "Hello User, you are using Grok CLI."

    def test_context_variable_extraction(self):
        """Test extracting context variables from instructions."""
        manager = CustomInstructionsManager()

        instructions = "Hello {name}, today is {date}."
        variables = manager.extract_context_variables(instructions)

        assert "name" in variables
        assert "date" in variables

    def test_instructions_cache(self):
        """Test instructions caching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            instructions_file = os.path.join(temp_dir, 'instructions.txt')

            manager = CustomInstructionsManager(instructions_file=instructions_file)

            # First load
            instructions1 = manager.load_instructions()

            # Modify file
            with open(instructions_file, 'w') as f:
                f.write("Modified instructions")

            # Second load (should use cache if implemented)
            instructions2 = manager.load_instructions()

            # Depending on cache implementation, this might be same or different
            # For this test, we just check it doesn't crash
            assert isinstance(instructions2, str)

    def test_multiline_instructions(self):
        """Test handling multiline instructions."""
        manager = CustomInstructionsManager()

        multiline = """You are a helpful assistant.
You should be polite and informative.
Always provide accurate information."""

        formatted = manager.format_instructions(multiline)

        # Should preserve newlines but strip extra whitespace
        assert "\n" in formatted
        assert formatted.startswith("You are a helpful assistant.")
        assert formatted.endswith("accurate information.")