"""Unit tests for DiskTool."""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from grok_py.tools.disk import DiskTool


class TestDiskTool:
    """Test suite for DiskTool."""

    @pytest.fixture
    def disk_tool(self):
        """Fixture to create a DiskTool instance."""
        return DiskTool()

    def test_execute_invalid_operation(self, disk_tool):
        """Test executing an invalid operation."""
        result = disk_tool.execute_sync(operation="invalid_op")

        assert result.success is False
        assert "Invalid operation: invalid_op" in result.error
        assert "Valid operations:" in result.error

    @patch('subprocess.run')
    def test_execute_usage_success(self, mock_run, disk_tool):
        """Test successful disk usage check."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   20G   28G  42% /
tmpfs           1.9G     0  1.9G   0% /tmp
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = disk_tool.execute_sync(operation="usage")

        assert result.success is True
        assert result.data['operation'] == 'usage'
        assert "Filesystem" in result.data['stdout']
        assert "/dev/sda1" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['df', '-h']

    @patch('subprocess.run')
    def test_execute_usage_with_path(self, mock_run, disk_tool):
        """Test disk usage check with specific path."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   20G   28G  42% /home
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = disk_tool.execute_sync(operation="usage", path="/home")

        assert result.success is True
        assert result.data['operation'] == 'usage'
        assert result.data['path'] == '/home'
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['df', '-h', '/home']

    @patch('subprocess.run')
    def test_execute_free_success(self, mock_run, disk_tool):
        """Test successful disk free space check."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   20G   28G  42% /
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = disk_tool.execute_sync(operation="free")

        assert result.success is True
        assert result.data['operation'] == 'free'
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['df', '-h']

    @patch('subprocess.run')
    def test_execute_du_success(self, mock_run, disk_tool):
        """Test successful disk usage summary."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """4.2G	/home/user
1.8G	/home/user/Documents
2.1G	/home/user/Downloads
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = disk_tool.execute_sync(operation="du", path="/home/user")

        assert result.success is True
        assert result.data['operation'] == 'du'
        assert result.data['path'] == '/home/user'
        assert "4.2G" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['du', '-sh', '/home/user']

    @patch('subprocess.run')
    def test_execute_du_default_path(self, mock_run, disk_tool):
        """Test disk usage summary with default path."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """50G	/
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = disk_tool.execute_sync(operation="du")

        assert result.success is True
        assert result.data['path'] == '/'
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['du', '-sh', '/']

    @patch('subprocess.run')
    def test_execute_large_files_success(self, mock_run, disk_tool):
        """Test successful large files search."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """2.1G	/home/user/large_file.zip
1.8G	/home/user/big_database.db
500M	/home/user/backup.tar.gz
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = disk_tool.execute_sync(operation="large-files", path="/home/user", size="500M")

        assert result.success is True
        assert result.data['operation'] == 'large-files'
        assert result.data['path'] == '/home/user'
        assert result.data['size'] == '500M'
        assert "2.1G" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['find', '/home/user', '-type', 'f', '-size', '+500M', '-exec', 'ls', '-lh', '{}', ';']

    @patch('subprocess.run')
    def test_execute_large_files_default_size(self, mock_run, disk_tool):
        """Test large files search with default size."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """Large files found..."""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = disk_tool.execute_sync(operation="large-files", path="/tmp")

        assert result.success is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        # Should use default size of 100M
        assert '+100M' in args[0]

    @patch('subprocess.run')
    def test_execute_cleanup_success(self, mock_run, disk_tool):
        """Test successful cleanup suggestions."""
        # Mock multiple subprocess calls for cleanup
        mock_processes = [
            MagicMock(returncode=0, stdout="Package cache: 200MB\n", stderr=""),
            MagicMock(returncode=0, stdout="Thumbnail cache: 50MB\n", stderr=""),
            MagicMock(returncode=0, stdout="System logs: 100MB\n", stderr=""),
        ]
        mock_run.side_effect = mock_processes

        result = disk_tool.execute_sync(operation="cleanup")

        assert result.success is True
        assert result.data['operation'] == 'cleanup'
        assert "Package cache" in result.data['cleanup_suggestions']
        assert "Thumbnail cache" in result.data['cleanup_suggestions']
        assert "System logs" in result.data['cleanup_suggestions']
        assert mock_run.call_count == 3

    @patch('subprocess.run')
    def test_execute_command_failure(self, mock_run, disk_tool):
        """Test handling of command execution failure."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "df: /nonexistent: No such file or directory"
        mock_run.return_value = mock_process

        result = disk_tool.execute_sync(operation="usage", path="/nonexistent")

        assert result.success is False
        assert result.data['exit_code'] == 1
        assert "No such file or directory" in result.data['stderr']
        assert result.error == "df: /nonexistent: No such file or directory"

    @patch('subprocess.run')
    def test_execute_cleanup_partial_failure(self, mock_run, disk_tool):
        """Test cleanup with some commands failing."""
        # Mock processes: first succeeds, second fails, third succeeds
        mock_processes = [
            MagicMock(returncode=0, stdout="Package cache: 200MB\n", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="Command not found"),
            MagicMock(returncode=0, stdout="System logs: 100MB\n", stderr=""),
        ]
        mock_run.side_effect = mock_processes

        result = disk_tool.execute_sync(operation="cleanup")

        assert result.success is True  # Overall success even with partial failures
        assert "Package cache" in result.data['cleanup_suggestions']
        assert "System logs" in result.data['cleanup_suggestions']
        # Should still include failed command info or note partial success

    @patch('subprocess.run')
    def test_execute_subprocess_exception(self, mock_run, disk_tool):
        """Test handling of subprocess exceptions."""
        mock_run.side_effect = subprocess.SubprocessError("Permission denied")

        result = disk_tool.execute_sync(operation="usage")

        assert result.success is False
        assert "Permission denied" in result.error

    @pytest.mark.parametrize("operation", ["usage", "free"])
    @patch('subprocess.run')
    def test_execute_usage_free_variations(self, mock_run, disk_tool, operation):
        """Test usage and free operations."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = f"{operation} output"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = disk_tool.execute_sync(operation=operation)

        assert result.success is True
        assert result.data['operation'] == operation

    @patch('subprocess.run')
    def test_execute_large_files_with_different_sizes(self, mock_run, disk_tool):
        """Test large files search with different size specifications."""
        test_cases = [
            ("100M", "+100M"),
            ("1G", "+1G"),
            ("500K", "+500K"),
        ]

        for size_input, expected_size in test_cases:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = f"Files larger than {size_input}"
            mock_process.stderr = ""
            mock_run.return_value = mock_process

            result = disk_tool.execute_sync(
                operation="large-files",
                path="/var",
                size=size_input
            )

            assert result.success is True
            assert result.data['size'] == size_input
            args, kwargs = mock_run.call_args
            assert expected_size in args[0]

    @patch('subprocess.run')
    def test_execute_with_path_containing_spaces(self, mock_run, disk_tool):
        """Test executing with path containing spaces."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Usage info"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = disk_tool.execute_sync(operation="du", path="/path with spaces")

        assert result.success is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        # Should handle spaces properly (shlex.quote would be used in real implementation)
        assert '/path with spaces' in args[0]