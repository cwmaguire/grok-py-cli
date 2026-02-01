"""Unit tests for BashTool."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from grok_py.tools.bash import BashTool


class TestBashTool:
    """Test suite for BashTool."""

    @pytest.fixture
    def bash_tool(self):
        """Fixture to create a BashTool instance."""
        return BashTool()

    @pytest.mark.asyncio
    async def test_execute_successful_command(self, bash_tool):
        """Test executing a successful command."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Hello\n", b""))
        mock_process.wait = AsyncMock()

        with patch('grok_py.tools.bash.asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            result = await bash_tool.execute(command="echo Hello")

            assert result.success is True
            assert result.data['stdout'] == "Hello"
            assert result.data['stderr'] == ""
            assert result.data['exit_code'] == 0
            assert result.data['command'] == "echo Hello"
            assert result.error is None
            assert result.metadata['exit_code'] == 0
            assert result.metadata['has_stderr'] is False
            assert result.metadata['has_stdout'] is True

            # Verify subprocess was called correctly
            mock_exec.assert_called_once()
            args, kwargs = mock_exec.call_args
            assert args == ('echo', 'Hello')
            assert kwargs['stdout'] == asyncio.subprocess.PIPE
            assert kwargs['stderr'] == asyncio.subprocess.PIPE

    @pytest.mark.asyncio
    async def test_execute_command_with_stderr(self, bash_tool):
        """Test executing a command that produces stderr."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error message\n"))
        mock_process.wait = AsyncMock()

        with patch('grok_py.tools.bash.asyncio.create_subprocess_exec', return_value=mock_process):
            result = await bash_tool.execute(command="false")

            assert result.success is False
            assert result.data['stdout'] == ""
            assert result.data['stderr'] == "Error message"
            assert result.data['exit_code'] == 1
            assert result.error == "Error message"
            assert result.metadata['exit_code'] == 1
            assert result.metadata['has_stderr'] is True
            assert result.metadata['has_stdout'] is False

    @pytest.mark.asyncio
    async def test_execute_empty_command(self, bash_tool):
        """Test executing an empty command."""
        result = await bash_tool.execute(command="")

        assert result.success is False
        assert result.error == "Command cannot be empty"
        assert result.data is None

    @pytest.mark.asyncio
    async def test_execute_whitespace_command(self, bash_tool):
        """Test executing a whitespace-only command."""
        result = await bash_tool.execute(command="   ")

        assert result.success is False
        assert result.error == "Command cannot be empty"

    @pytest.mark.asyncio
    async def test_execute_dangerous_command(self, bash_tool):
        """Test executing a dangerous command."""
        result = await bash_tool.execute(command="rm -rf /")

        assert result.success is False
        assert "potentially dangerous operation" in result.error
        assert "rm -rf /" in result.error

    @pytest.mark.asyncio
    async def test_execute_multiple_dangerous_commands(self, bash_tool):
        """Test various dangerous commands are blocked."""
        dangerous_cmds = [
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            "fdisk /dev/sda",
            "format c:"
        ]

        for cmd in dangerous_cmds:
            result = await bash_tool.execute(command=cmd)
            assert result.success is False
            assert "potentially dangerous operation" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_shell_true(self, bash_tool):
        """Test executing command with shell=True."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.wait = AsyncMock()

        with patch('grok_py.tools.bash.asyncio.create_subprocess_shell', return_value=mock_process) as mock_exec:
            result = await bash_tool.execute(command="echo test | grep test", shell=True)

            assert result.success is True
            mock_exec.assert_called_once()
            args, kwargs = mock_exec.call_args
            assert args == ('echo test | grep test',)

    @pytest.mark.asyncio
    async def test_execute_with_custom_cwd(self, bash_tool):
        """Test executing command with custom working directory."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"pwd", b""))
        mock_process.wait = AsyncMock()

        with patch('grok_py.tools.bash.asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            result = await bash_tool.execute(command="pwd", cwd="/tmp")

            assert result.success is True
            assert result.data['working_directory'] == "/tmp"
            mock_exec.assert_called_once()
            args, kwargs = mock_exec.call_args
            assert kwargs['cwd'] == "/tmp"

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, bash_tool):
        """Test command execution with custom timeout."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.wait = AsyncMock()

        with patch('grok_py.tools.bash.asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            result = await bash_tool.execute(command="sleep 1", timeout=60.0)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_timeout_error(self, bash_tool):
        """Test command execution timeout."""
        mock_process = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with patch('grok_py.tools.bash.asyncio.create_subprocess_exec', return_value=mock_process), \
             patch('grok_py.tools.bash.asyncio.wait_for', side_effect=asyncio.TimeoutError):
            result = await bash_tool.execute(command="sleep 100", timeout=1.0)

            assert result.success is False
            assert "timed out after 1.0 seconds" in result.error
            assert result.metadata['timed_out'] is True
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_invalid_command_syntax(self, bash_tool):
        """Test executing command with invalid syntax."""
        result = await bash_tool.execute(command='echo "unclosed quote')

        assert result.success is False
        assert "Invalid command syntax" in result.error

    @pytest.mark.asyncio
    async def test_execute_general_exception(self, bash_tool):
        """Test handling of general exceptions during execution."""
        with patch('grok_py.tools.bash.asyncio.create_subprocess_exec', side_effect=Exception("Test error")):
            result = await bash_tool.execute(command="echo test")

            assert result.success is False
            assert "Failed to execute command: Test error" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_unicode_output(self, bash_tool):
        """Test handling of unicode characters in output."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("Hello 世界".encode('utf-8'), b"")
        mock_process.wait = AsyncMock()

        with patch('grok_py.tools.bash.asyncio.create_subprocess_exec', return_value=mock_process):
            result = await bash_tool.execute(command="echo unicode")

            assert result.success is True
            assert "Hello 世界" in result.data['stdout']

    @pytest.mark.asyncio
    async def test_execute_with_binary_output(self, bash_tool):
        """Test handling of binary data in output."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        # Simulate binary data that can't be decoded as UTF-8
        mock_process.communicate.return_value = (b'\x80\x81\x82', b"")
        mock_process.wait = AsyncMock()

        with patch('grok_py.tools.bash.asyncio.create_subprocess_exec', return_value=mock_process):
            result = await bash_tool.execute(command="cat binary")

            assert result.success is True
            # Should contain replacement characters for invalid UTF-8
            assert '�' in result.data['stdout']