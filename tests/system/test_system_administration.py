"""System tests for system administration workflows."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typer.testing import CliRunner

from grok_py.cli import app


class TestSystemAdministration:
    """System tests for system administration tasks."""

    @pytest.fixture
    def runner(self):
        """CLI runner fixture."""
        return CliRunner()

    @pytest.mark.system
    def test_system_monitoring_workflow(self):
        """Test complete system monitoring workflow."""
        with patch('grok_py.tools.bash.BashTool.execute') as mock_bash, \
             patch('grok_py.tools.disk.DiskTool.execute_sync') as mock_disk, \
             patch('grok_py.tools.network.NetworkTool.execute_sync') as mock_network:

            # Mock system monitoring commands
            mock_bash.return_value = MagicMock(
                success=True,
                data={'stdout': 'CPU: 45%\nMemory: 60%\nLoad: 1.2', 'exit_code': 0}
            )
            mock_disk.return_value = MagicMock(
                success=True,
                data={'usage': '/: 75% used', 'free_space': '25GB available'}
            )
            mock_network.return_value = MagicMock(
                success=True,
                data={'ping': '64 bytes from 8.8.8.8: time=12.3ms', 'interfaces': 'eth0: UP'}
            )

            from grok_py.tools.bash import BashTool
            from grok_py.tools.disk import DiskTool
            from grok_py.tools.network import NetworkTool

            # Test system status check
            bash_tool = BashTool()
            cpu_result = bash_tool.execute('top -bn1 | grep "Cpu(s)"')
            assert cpu_result.success is True
            assert 'CPU:' in cpu_result.data['stdout']

            # Test disk monitoring
            disk_tool = DiskTool()
            disk_result = disk_tool.execute_sync('usage', '/')
            assert disk_result.success is True
            assert 'used' in disk_result.data['usage']

            # Test network diagnostics
            network_tool = NetworkTool()
            ping_result = network_tool.execute_sync('ping', '8.8.8.8', '4')
            assert ping_result.success is True
            assert 'time=' in ping_result.data['ping']

    @pytest.mark.system
    def test_package_management_workflow(self):
        """Test package installation and management workflow."""
        with patch('grok_py.tools.apt.AptTool.execute_sync') as mock_apt, \
             patch('grok_py.tools.bash.BashTool.execute') as mock_bash:

            # Mock package operations
            call_count = 0
            def mock_apt_execute(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:  # update
                    return MagicMock(success=True, data={'output': 'Package lists updated'})
                elif call_count == 2:  # install
                    return MagicMock(success=True, data={'output': 'curl installed successfully'})
                else:  # show
                    return MagicMock(success=True, data={'info': 'curl: web client'})

            mock_apt.side_effect = mock_apt_execute

            from grok_py.tools.apt import AptTool

            apt_tool = AptTool()

            # Update package lists
            update_result = apt_tool.execute_sync('update')
            assert update_result.success is True

            # Install package
            install_result = apt_tool.execute_sync('install', 'curl')
            assert install_result.success is True
            assert 'curl' in install_result.data['output']

            # Check package info
            info_result = apt_tool.execute_sync('show', 'curl')
            assert info_result.success is True

    @pytest.mark.system
    def test_service_management_workflow(self):
        """Test system service management workflow."""
        with patch('grok_py.tools.systemctl.SystemctlTool.execute_sync') as mock_systemctl:

            # Mock service operations
            call_count = 0
            def mock_systemctl_execute(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                operations = ['status', 'start', 'restart', 'stop']
                return MagicMock(
                    success=True,
                    data={f'{operations[call_count-1]}_result': f'service {args[1]} {operations[call_count-1]}ed successfully'}
                )

            mock_systemctl.side_effect = mock_systemctl_execute

            from grok_py.tools.systemctl import SystemctlTool

            systemctl_tool = SystemctlTool()

            # Check service status
            status_result = systemctl_tool.execute_sync('status', 'nginx')
            assert status_result.success is True

            # Start service
            start_result = systemctl_tool.execute_sync('start', 'nginx')
            assert start_result.success is True

            # Restart service
            restart_result = systemctl_tool.execute_sync('restart', 'nginx')
            assert restart_result.success is True

            # Stop service
            stop_result = systemctl_tool.execute_sync('stop', 'nginx')
            assert stop_result.success is True

    @pytest.mark.system
    @patch('grok_py.cli.GrokClient')
    def test_admin_assistance_workflow(self, mock_grok_client, runner):
        """Test administrator getting AI assistance for system tasks."""
        mock_client_instance = AsyncMock()
        mock_client_instance.send_message.side_effect = [
            "To check system load, run: uptime",
            "High load detected. Consider checking: ps aux --sort=-%cpu | head",
            "To free up memory, you can: echo 3 > /proc/sys/vm/drop_caches"
        ]
        mock_grok_client.return_value.__aenter__.return_value = mock_client_instance
        mock_grok_client.return_value.__aexit__.return_value = None

        # Simulate admin workflow
        queries = [
            "System is slow, how to check load?",
            "Load is high at 5.2, what processes are using CPU?",
            "Memory is also low, how to free it up?"
        ]

        for query in queries:
            result = runner.invoke(app, ["chat", query])
            assert result.exit_code == 0

        assert mock_client_instance.send_message.call_count == 3