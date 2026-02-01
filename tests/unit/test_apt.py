"""Unit tests for AptTool."""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from grok_py.tools.apt import AptTool


class TestAptTool:
    """Test suite for AptTool."""

    @pytest.fixture
    def apt_tool(self):
        """Fixture to create an AptTool instance."""
        return AptTool()

    @pytest.mark.parametrize("operation", ["install", "remove", "search", "show"])
    def test_execute_requires_package(self, apt_tool, operation):
        """Test that operations requiring package fail without package name."""
        result = apt_tool.execute_sync(operation=operation)

        assert result.success is False
        assert "Package name required" in result.error
        assert result.data is None

    def test_execute_invalid_operation(self, apt_tool):
        """Test executing an invalid operation."""
        result = apt_tool.execute_sync(operation="invalid_op")

        assert result.success is False
        assert "Invalid operation: invalid_op" in result.error
        assert "Valid operations:" in result.error

    @patch('subprocess.run')
    def test_execute_install_success(self, mock_run, apt_tool):
        """Test successful package installation."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Package installed successfully"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="install", package="curl")

        assert result.success is True
        assert result.data['operation'] == 'install'
        assert result.data['package'] == 'curl'
        assert result.data['exit_code'] == 0
        assert "Package installed successfully" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['apt', 'install', 'curl']
        assert kwargs['capture_output'] is True
        assert kwargs['text'] is True

    @patch('subprocess.run')
    def test_execute_install_with_assume_yes(self, mock_run, apt_tool):
        """Test package installation with assume_yes flag."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Package installed"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="install", package="git", assume_yes=True)

        assert result.success is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['apt', 'install', '-y', 'git']

    @patch('subprocess.run')
    def test_execute_remove_success(self, mock_run, apt_tool):
        """Test successful package removal."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Package removed"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="remove", package="old-package")

        assert result.success is True
        assert result.data['operation'] == 'remove'
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['apt', 'remove', 'old-package']

    @patch('subprocess.run')
    def test_execute_update_success(self, mock_run, apt_tool):
        """Test successful package list update."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Package lists updated"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="update")

        assert result.success is True
        assert result.data['operation'] == 'update'
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['apt', 'update']

    @patch('subprocess.run')
    def test_execute_upgrade_success(self, mock_run, apt_tool):
        """Test successful system upgrade."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "System upgraded"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="upgrade")

        assert result.success is True
        assert result.data['operation'] == 'upgrade'
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['apt', 'upgrade']

    @patch('subprocess.run')
    def test_execute_upgrade_with_assume_yes(self, mock_run, apt_tool):
        """Test system upgrade with assume_yes flag."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Upgraded"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="upgrade", assume_yes=True)

        assert result.success is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['apt', 'upgrade', '-y']

    @patch('subprocess.run')
    def test_execute_search_success(self, mock_run, apt_tool):
        """Test successful package search."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "python3-dev/focal 3.8.10-0ubuntu1 amd64\n  Header files and a static library for Python (default)"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="search", package="python3-dev")

        assert result.success is True
        assert result.data['operation'] == 'search'
        assert "python3-dev" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['apt', 'search', 'python3-dev']

    @patch('subprocess.run')
    def test_execute_show_success(self, mock_run, apt_tool):
        """Test successful package information display."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """Package: curl
Version: 7.68.0-1ubuntu2.22
Description: command line tool for transferring data with URL syntax
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="show", package="curl")

        assert result.success is True
        assert result.data['operation'] == 'show'
        assert "Package: curl" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['apt', 'show', 'curl']

    @patch('subprocess.run')
    def test_execute_command_failure(self, mock_run, apt_tool):
        """Test handling of command execution failure."""
        mock_process = MagicMock()
        mock_process.returncode = 100
        mock_process.stdout = ""
        mock_process.stderr = "E: Unable to locate package nonexistent"
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="install", package="nonexistent")

        assert result.success is False
        assert result.data['exit_code'] == 100
        assert "Unable to locate package" in result.data['stderr']
        assert result.error == "E: Unable to locate package nonexistent"

    @patch('subprocess.run')
    def test_execute_subprocess_exception(self, mock_run, apt_tool):
        """Test handling of subprocess exceptions."""
        mock_run.side_effect = subprocess.SubprocessError("Command failed")

        result = apt_tool.execute_sync(operation="update")

        assert result.success is False
        assert "Command failed" in result.error

    @patch('subprocess.run')
    def test_execute_with_package_and_operation_data(self, mock_run, apt_tool):
        """Test that result includes operation and package information."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Success"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="install", package="vim", assume_yes=True)

        assert result.success is True
        assert result.data['operation'] == 'install'
        assert result.data['package'] == 'vim'
        assert result.data['assume_yes'] is True

    @patch('subprocess.run')
    def test_execute_remove_with_assume_yes(self, mock_run, apt_tool):
        """Test package removal with assume_yes flag."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Removed"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = apt_tool.execute_sync(operation="remove", package="unwanted", assume_yes=True)

        assert result.success is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['apt', 'remove', '-y', 'unwanted']