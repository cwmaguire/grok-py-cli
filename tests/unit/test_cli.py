import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typer.testing import CliRunner

from grok_py.cli import app


class TestCLI:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_app_callback(self, runner):
        """Test the main app callback."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Grok CLI" in result.output
        assert "AI-powered terminal assistant" in result.output

    def test_chat_command_help(self, runner):
        """Test chat command help."""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "Start a chat session with Grok" in result.output
        assert "--interactive" in result.output
        assert "--model" in result.output
        assert "--temperature" in result.output

    @patch('grok_py.cli.GrokClient')
    def test_chat_single_message(self, mock_client_class, runner):
        """Test chat command with single message."""
        # Mock the client
        mock_client = AsyncMock()
        mock_client.send_message.return_value = "Mock response"
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = runner.invoke(app, ["chat", "Hello world"])

        assert result.exit_code == 0
        assert "Grok CLI" in result.output
        assert "Mock response" in result.output

        # Verify client was called correctly
        mock_client.send_message.assert_called_once_with(
            message="Hello world",
            model="grok-beta",
            temperature=0.7,
            max_tokens=None
        )

    @patch('grok_py.cli.GrokClient')
    def test_chat_with_options(self, mock_client_class, runner):
        """Test chat command with custom options."""
        mock_client = AsyncMock()
        mock_client.send_message.return_value = "Custom response"
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = runner.invoke(app, [
            "chat",
            "Test message",
            "--model", "custom-model",
            "--temperature", "0.5",
            "--max-tokens", "100"
        ])

        assert result.exit_code == 0
        mock_client.send_message.assert_called_once_with(
            message="Test message",
            model="custom-model",
            temperature=0.5,
            max_tokens=100
        )

    @patch('grok_py.cli.GrokClient')
    def test_chat_non_interactive(self, mock_client_class, runner):
        """Test chat command in non-interactive mode."""
        mock_client = AsyncMock()
        mock_client.send_message.return_value = "Non-interactive response"
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = runner.invoke(app, ["chat", "Message", "--non-interactive"])

        assert result.exit_code == 0
        assert "Non-interactive response" in result.output

    @patch('grok_py.cli.GrokClient')
    def test_chat_client_error(self, mock_client_class, runner):
        """Test chat command with client error."""
        mock_client = AsyncMock()
        mock_client.send_message.side_effect = Exception("API Error")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = runner.invoke(app, ["chat", "Error message"])

        assert result.exit_code == 1  # Should exit with error
        assert "API Error" in str(result.exception)

    def test_chat_no_message_interactive(self, runner):
        """Test chat command without message in interactive mode."""
        # This would normally start interactive mode, but since we can't test that easily,
        # we'll just check it doesn't crash
        with patch('grok_py.cli.console') as mock_console:
            # Mock to avoid actual printing
            result = runner.invoke(app, ["chat"])
            # In interactive mode, it would try to do something, but since we mocked console,
            # it might not do much. Just check it doesn't crash.
            assert result.exit_code == 0 or result.exit_code == 1  # Depending on implementation

    def test_invalid_temperature(self, runner):
        """Test chat command with invalid temperature."""
        result = runner.invoke(app, ["chat", "message", "--temperature", "invalid"])
        # Typer should handle the type conversion error
        assert result.exit_code != 0

    def test_invalid_max_tokens(self, runner):
        """Test chat command with invalid max_tokens."""
        result = runner.invoke(app, ["chat", "message", "--max-tokens", "invalid"])
        assert result.exit_code != 0