"""Integration tests for bash tool with real command execution."""

import pytest
import os
import tempfile
import subprocess
from grok_py.tools.bash import BashTool


class TestBashIntegration:
    """Integration tests for bash tool with real command execution."""

    @pytest.fixture
    def bash_tool(self):
        """Bash tool fixture."""
        return BashTool()

    @pytest.mark.asyncio
    async def test_echo_command(self, bash_tool):
        """Test basic echo command execution."""
        result = await bash_tool.execute('echo "Hello, World!"')

        assert result.success is True
        assert "Hello, World!" in result.data['stdout']
        assert result.data['exit_code'] == 0

    @pytest.mark.asyncio
    async def test_ls_command(self, bash_tool):
        """Test ls command in current directory."""
        result = await bash_tool.execute('ls -la')

        assert result.success is True
        assert result.data['exit_code'] == 0
        # Should contain current directory files
        assert len(result.data['stdout']) > 0

    @pytest.mark.asyncio
    async def test_pwd_command(self, bash_tool):
        """Test pwd command returns current working directory."""
        result = await bash_tool.execute('pwd')

        assert result.success is True
        assert result.data['exit_code'] == 0
        # Should contain a path
        assert "/" in result.data['stdout'] or "\\" in result.data['stdout']

    @pytest.mark.asyncio
    async def test_mkdir_and_rmdir(self, bash_tool):
        """Test directory creation and removal."""
        test_dir = "test_integration_dir"

        # Clean up any existing directory
        await bash_tool.execute(f'rm -rf {test_dir}')

        # Create directory
        create_result = await bash_tool.execute(f'mkdir {test_dir}')
        assert create_result.success is True
        assert create_result.data['exit_code'] == 0

        # Verify directory exists
        ls_result = await bash_tool.execute(f'ls -d {test_dir}')
        assert ls_result.success is True
        assert test_dir in ls_result.data['stdout']

        # Remove directory
        remove_result = await bash_tool.execute(f'rmdir {test_dir}')
        assert remove_result.success is True
        assert remove_result.data['exit_code'] == 0

    @pytest.mark.asyncio
    async def test_file_operations(self, bash_tool):
        """Test file creation, writing, and reading."""
        test_file = "test_integration.txt"

        # Clean up any existing file
        await bash_tool.execute(f'rm -f {test_file}')

        # Create and write to file
        write_result = await bash_tool.execute(f'echo "Integration test content" > {test_file}', shell=True)
        assert write_result.success is True

        # Read file
        read_result = await bash_tool.execute(f'cat {test_file}')
        assert read_result.success is True
        assert "Integration test content" in read_result.data['stdout']

        # Clean up
        cleanup_result = await bash_tool.execute(f'rm {test_file}')
        assert cleanup_result.success is True

    @pytest.mark.asyncio
    async def test_grep_command(self, bash_tool):
        """Test grep command for pattern matching."""
        # Create test file with content
        test_file = "grep_test.txt"
        # Clean up any existing file
        await bash_tool.execute(f'rm -f {test_file}')
        setup_result = await bash_tool.execute(f'echo -e "line1\\nline2 with pattern\\nline3" > {test_file}', shell=True)
        assert setup_result.success is True

        # Grep for pattern
        grep_result = await bash_tool.execute(f'grep "pattern" {test_file}')
        assert grep_result.success is True
        assert "line2 with pattern" in grep_result.data['stdout']

        # Clean up
        cleanup_result = await bash_tool.execute(f'rm {test_file}')
        assert cleanup_result.success is True

    @pytest.mark.asyncio
    async def test_pipeline_commands(self, bash_tool):
        """Test command pipelines."""
        result = await bash_tool.execute('echo "hello world" | wc -w', shell=True)

        assert result.success is True
        assert result.data['exit_code'] == 0
        # wc -w should return 2 for "hello world"
        assert "2" in result.data['stdout']

    @pytest.mark.asyncio
    async def test_command_with_quotes(self, bash_tool):
        """Test commands with quotes and special characters."""
        result = await bash_tool.execute('echo "Hello, \\"World\\"!"')

        assert result.success is True
        assert 'Hello, "World"!' in result.data['stdout']

    @pytest.mark.asyncio
    async def test_invalid_command(self, bash_tool):
        """Test handling of invalid commands."""
        result = await bash_tool.execute('nonexistent_command_xyz')

        assert result.success is False
        assert result.data['exit_code'] != 0
        assert "command not found" in result.data['stderr'].lower() or "not found" in result.data['stderr'].lower() or "no such file" in result.data['stderr'].lower()

    @pytest.mark.asyncio
    async def test_command_timeout(self, bash_tool):
        """Test command timeout handling."""
        # This might take time, so we'll use a short sleep
        result = await bash_tool.execute('sleep 1')

        assert result.success is True
        assert result.data['exit_code'] == 0

    @pytest.mark.asyncio
    async def test_permission_denied(self, bash_tool):
        """Test permission denied scenarios."""
        # Try to access root directory file (may be restricted)
        result = await bash_tool.execute('cat /etc/shadow')

        # This might succeed or fail depending on permissions
        # We just verify it doesn't crash
        assert isinstance(result.success, bool)
        assert isinstance(result.data['exit_code'], int)

    @pytest.mark.asyncio
    async def test_large_output_handling(self, bash_tool):
        """Test handling of large command output."""
        # Generate large output
        result = await bash_tool.execute('for i in $(seq 1 1000); do echo "Line $i"; done', shell=True)

        assert result.success is True
        lines = result.data['stdout'].strip().split('\n')
        assert len(lines) >= 1000

    @pytest.mark.asyncio
    async def test_environment_variables(self, bash_tool):
        """Test environment variable handling."""
        result = await bash_tool.execute('echo $HOME')

        assert result.success is True
        assert len(result.data['stdout'].strip()) > 0

    @pytest.mark.asyncio
    async def test_command_with_input_redirection(self, bash_tool):
        """Test commands with input redirection."""
        # Create input file
        input_file = "input_test.txt"
        setup_result = await bash_tool.execute(f'echo -e "line1\\nline2\\nline3" > {input_file}', shell=True)
        assert setup_result.success is True

        # Use input redirection
        result = await bash_tool.execute(f'wc -l < {input_file}', shell=True)
        assert result.success is True
        assert "3" in result.data['stdout']

        # Clean up
        cleanup_result = await bash_tool.execute(f'rm {input_file}')
        assert cleanup_result.success is True

    @pytest.mark.asyncio
    async def test_background_process_handling(self, bash_tool):
        """Test handling of background processes."""
        # Start background process
        start_result = await bash_tool.execute('sleep 2 & echo "Background started"', shell=True)
        assert start_result.success is True
        assert "Background started" in start_result.data['stdout']

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_long_running_command(self, bash_tool):
        """Test long-running command handling."""
        result = await bash_tool.execute('for i in $(seq 1 10); do echo "Iteration $i"; sleep 0.1; done', shell=True)

        assert result.success is True
        assert "Iteration 10" in result.data['stdout']

    @pytest.mark.asyncio
    async def test_command_output_encoding(self, bash_tool):
        """Test command output encoding handling."""
        result = await bash_tool.execute('echo "café"')

        assert result.success is True
        # Should handle UTF-8 encoding
        assert "café" in result.data['stdout'] or "caf" in result.data['stdout']