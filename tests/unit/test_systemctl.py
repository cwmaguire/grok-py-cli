"""Unit tests for SystemctlTool."""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from grok_py.tools.systemctl import SystemctlTool


class TestSystemctlTool:
    """Test suite for SystemctlTool."""

    @pytest.fixture
    def systemctl_tool(self):
        """Fixture to create a SystemctlTool instance."""
        return SystemctlTool()

    def test_execute_invalid_operation(self, systemctl_tool):
        """Test executing an invalid operation."""
        result = systemctl_tool.execute_sync(operation="invalid_op", service="nginx")

        assert result.success is False
        assert "Invalid operation: invalid_op" in result.error
        assert "Valid operations:" in result.error

    def test_execute_empty_service(self, systemctl_tool):
        """Test executing with empty service name."""
        result = systemctl_tool.execute_sync(operation="start", service="")

        assert result.success is False
        assert result.error == "Service name cannot be empty"

    def test_execute_whitespace_service(self, systemctl_tool):
        """Test executing with whitespace-only service name."""
        result = systemctl_tool.execute_sync(operation="start", service="   ")

        assert result.success is False
        assert result.error == "Service name cannot be empty"

    @patch('subprocess.run')
    def test_execute_start_success(self, mock_run, systemctl_tool):
        """Test successful service start."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="start", service="nginx")

        assert result.success is True
        assert result.data['operation'] == 'start'
        assert result.data['service'] == 'nginx'
        assert result.data['exit_code'] == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['systemctl', 'start', 'nginx']

    @patch('subprocess.run')
    def test_execute_stop_success(self, mock_run, systemctl_tool):
        """Test successful service stop."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="stop", service="apache2")

        assert result.success is True
        assert result.data['operation'] == 'stop'
        assert result.data['service'] == 'apache2'
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['systemctl', 'stop', 'apache2']

    @patch('subprocess.run')
    def test_execute_restart_success(self, mock_run, systemctl_tool):
        """Test successful service restart."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="restart", service="docker")

        assert result.success is True
        assert result.data['operation'] == 'restart'
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['systemctl', 'restart', 'docker']

    @patch('subprocess.run')
    def test_execute_status_success(self, mock_run, systemctl_tool):
        """Test successful service status check."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """● nginx.service - A high performance web server and a reverse proxy server
     Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2024-01-15 10:00:00 UTC; 2 days ago
     Main PID: 1234 (nginx)
     Tasks: 2 (limit: 4915)
     Memory: 10.2M
     CPU: 1.234s
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="status", service="nginx")

        assert result.success is True
        assert result.data['operation'] == 'status'
        assert "nginx.service" in result.data['stdout']
        assert "Active: active (running)" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['systemctl', 'status', 'nginx']

    @patch('subprocess.run')
    def test_execute_enable_success(self, mock_run, systemctl_tool):
        """Test successful service enable."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Created symlink /etc/systemd/system/multi-user.target.wants/ssh.service"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="enable", service="ssh")

        assert result.success is True
        assert result.data['operation'] == 'enable'
        assert "Created symlink" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['systemctl', 'enable', 'ssh']

    @patch('subprocess.run')
    def test_execute_disable_success(self, mock_run, systemctl_tool):
        """Test successful service disable."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Removed symlink /etc/systemd/system/multi-user.target.wants/mysql.service"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="disable", service="mysql")

        assert result.success is True
        assert result.data['operation'] == 'disable'
        assert "Removed symlink" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['systemctl', 'disable', 'mysql']

    @patch('subprocess.run')
    def test_execute_is_active_success(self, mock_run, systemctl_tool):
        """Test successful is-active check."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "active"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="is-active", service="nginx")

        assert result.success is True
        assert result.data['operation'] == 'is-active'
        assert result.data['stdout'].strip() == "active"
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['systemctl', 'is-active', 'nginx']

    @patch('subprocess.run')
    def test_execute_is_enabled_success(self, mock_run, systemctl_tool):
        """Test successful is-enabled check."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "enabled"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="is-enabled", service="cron")

        assert result.success is True
        assert result.data['operation'] == 'is-enabled'
        assert result.data['stdout'].strip() == "enabled"
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['systemctl', 'is-enabled', 'cron']

    @patch('subprocess.run')
    def test_execute_command_failure(self, mock_run, systemctl_tool):
        """Test handling of command execution failure."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "Failed to start nonexistent.service: Unit nonexistent.service not found."
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="start", service="nonexistent")

        assert result.success is False
        assert result.data['exit_code'] == 1
        assert "Unit nonexistent.service not found" in result.data['stderr']
        assert result.error == "Failed to start nonexistent.service: Unit nonexistent.service not found."

    @patch('subprocess.run')
    def test_execute_is_active_inactive(self, mock_run, systemctl_tool):
        """Test is-active when service is inactive."""
        mock_process = MagicMock()
        mock_process.returncode = 3  # inactive exit code
        mock_process.stdout = "inactive"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="is-active", service="stopped-service")

        assert result.success is False  # For status checks, non-zero might be expected
        assert result.data['exit_code'] == 3
        assert result.data['stdout'].strip() == "inactive"

    @patch('subprocess.run')
    def test_execute_is_enabled_disabled(self, mock_run, systemctl_tool):
        """Test is-enabled when service is disabled."""
        mock_process = MagicMock()
        mock_process.returncode = 1  # disabled exit code
        mock_process.stdout = "disabled"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="is-enabled", service="disabled-service")

        assert result.success is False
        assert result.data['exit_code'] == 1
        assert result.data['stdout'].strip() == "disabled"

    @patch('subprocess.run')
    def test_execute_subprocess_exception(self, mock_run, systemctl_tool):
        """Test handling of subprocess exceptions."""
        mock_run.side_effect = subprocess.SubprocessError("Permission denied")

        result = systemctl_tool.execute_sync(operation="restart", service="nginx")

        assert result.success is False
        assert "Permission denied" in result.error

    @pytest.mark.parametrize("operation", ["start", "stop", "restart", "status", "enable", "disable", "is-active", "is-enabled"])
    @patch('subprocess.run')
    def test_execute_all_operations_success(self, mock_run, systemctl_tool, operation):
        """Test that all operations work with successful subprocess calls."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = f"Operation {operation} successful"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation=operation, service="test-service")

        assert result.success is True
        assert result.data['operation'] == operation
        assert result.data['service'] == 'test-service'
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['systemctl', operation, 'test-service']

    @patch('subprocess.run')
    def test_execute_with_service_containing_spaces(self, mock_run, systemctl_tool):
        """Test executing with service name containing spaces (should work with proper quoting)."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Success"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = systemctl_tool.execute_sync(operation="status", service="my custom service")

        assert result.success is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['systemctl', 'status', 'my custom service']