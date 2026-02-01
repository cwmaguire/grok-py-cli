"""Unit tests for NetworkTool."""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from grok_py.tools.network import NetworkTool


class TestNetworkTool:
    """Test suite for NetworkTool."""

    @pytest.fixture
    def network_tool(self):
        """Fixture to create a NetworkTool instance."""
        return NetworkTool()

    def test_execute_invalid_operation(self, network_tool):
        """Test executing an invalid operation."""
        result = network_tool.execute_sync(operation="invalid_op")

        assert result.success is False
        assert "Invalid operation: invalid_op" in result.error
        assert "Valid operations:" in result.error

    @pytest.mark.parametrize("operation", ["ping", "traceroute", "dns"])
    def test_execute_requires_host(self, network_tool, operation):
        """Test that operations requiring host fail without host."""
        result = network_tool.execute_sync(operation=operation)

        assert result.success is False
        assert "Host is required" in result.error

    @patch('subprocess.run')
    def test_execute_ping_success(self, mock_run, network_tool):
        """Test successful ping operation."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """PING google.com (142.250.184.206) 56(84) bytes of data.
64 bytes from lga25s65-in-f14.1e100.net (142.250.184.206): icmp_seq=1 ttl=118 time=12.3 ms
64 bytes from lga25s65-in-f14.1e100.net (142.250.184.206): icmp_seq=2 ttl=118 time=11.8 ms
64 bytes from lga25s65-in-f14.1e100.net (142.250.184.206): icmp_seq=3 ttl=118 time=12.1 ms

--- google.com ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 11.800/12.067/12.300/0.200 ms
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="ping", host="google.com")

        assert result.success is True
        assert result.data['operation'] == 'ping'
        assert result.data['host'] == 'google.com'
        assert "google.com ping statistics" in result.data['stdout']
        assert "0% packet loss" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['ping', '-c', '4', 'google.com']

    @patch('subprocess.run')
    def test_execute_ping_with_count(self, mock_run, network_tool):
        """Test ping operation with custom count."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Ping output with 2 packets"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="ping", host="example.com", count="2")

        assert result.success is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['ping', '-c', '2', 'example.com']

    @patch('subprocess.run')
    def test_execute_traceroute_success(self, mock_run, network_tool):
        """Test successful traceroute operation."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """traceroute to google.com (142.250.184.206), 30 hops max, 60 byte packets
 1  router.local (192.168.1.1)  1.234 ms  1.456 ms  1.567 ms
 2  isp.gateway (10.0.0.1)  12.345 ms  11.234 ms  13.456 ms
 3  google.com (142.250.184.206)  25.678 ms  24.567 ms  26.789 ms
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="traceroute", host="google.com")

        assert result.success is True
        assert result.data['operation'] == 'traceroute'
        assert result.data['host'] == 'google.com'
        assert "traceroute to google.com" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['traceroute', 'google.com']

    @patch('subprocess.run')
    def test_execute_interfaces_success(self, mock_run, network_tool):
        """Test successful network interfaces listing."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP qlen 1000
    link/ether 00:1b:21:0a:0b:0c brd ff:ff:ff:ff:ff:ff
    inet 192.168.1.100/24 brd 192.168.1.255 scope global eth0
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="interfaces")

        assert result.success is True
        assert result.data['operation'] == 'interfaces'
        assert "eth0:" in result.data['stdout']
        assert "192.168.1.100" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['ip', 'addr', 'show']

    @patch('subprocess.run')
    def test_execute_connections_success(self, mock_run, network_tool):
        """Test successful network connections listing."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """Active Internet connections (servers and established)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      1234/sshd
tcp        0      0 127.0.0.1:5432          0.0.0.0:*               LISTEN      5678/postgres
tcp        0     52 192.168.1.100:22        192.168.1.50:54321      ESTABLISHED 9012/ssh
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="connections")

        assert result.success is True
        assert result.data['operation'] == 'connections'
        assert "ESTABLISHED" in result.data['stdout']
        assert "sshd" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['netstat', '-tuln']

    @patch('subprocess.run')
    def test_execute_dns_success(self, mock_run, network_tool):
        """Test successful DNS lookup."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """google.com has address 142.250.184.206
google.com has IPv6 address 2a00:1450:4001:814::200e
google.com mail is handled by 10 smtp.google.com.
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="dns", host="google.com")

        assert result.success is True
        assert result.data['operation'] == 'dns'
        assert result.data['host'] == 'google.com'
        assert "142.250.184.206" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['nslookup', 'google.com']

    @patch('subprocess.run')
    def test_execute_speedtest_success(self, mock_run, network_tool):
        """Test successful speedtest operation."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """Retrieving speedtest.net configuration...
Testing from ISP (IP)...
Retrieving speedtest.net server list...
Selecting best server based on ping...
Hosted by Example ISP (City, ST) [10.00 km]: 15.678 ms
Testing download speed................................................................................
Download: 85.67 Mbps (9.8 MB/s)
Testing upload speed................................................................................................
Upload: 42.34 Mbps (5.3 MB/s)
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="speedtest")

        assert result.success is True
        assert result.data['operation'] == 'speedtest'
        assert "Download: 85.67 Mbps" in result.data['stdout']
        assert "Upload: 42.34 Mbps" in result.data['stdout']
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ['speedtest-cli', '--simple']

    @patch('subprocess.run')
    def test_execute_ping_failure(self, mock_run, network_tool):
        """Test ping operation failure."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "ping: unknown host nonexistent.example.com"
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="ping", host="nonexistent.example.com")

        assert result.success is False
        assert result.data['exit_code'] == 1
        assert "unknown host" in result.data['stderr']
        assert result.error == "ping: unknown host nonexistent.example.com"

    @patch('subprocess.run')
    def test_execute_traceroute_failure(self, mock_run, network_tool):
        """Test traceroute operation failure."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "traceroute: unknown host unreachable.host"
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="traceroute", host="unreachable.host")

        assert result.success is False
        assert "unknown host unreachable.host" in result.error

    @patch('subprocess.run')
    def test_execute_dns_failure(self, mock_run, network_tool):
        """Test DNS lookup failure."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "** server can't find nonexistent.domain: NXDOMAIN"
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="dns", host="nonexistent.domain")

        assert result.success is False
        assert "NXDOMAIN" in result.data['stderr']

    @patch('subprocess.run')
    def test_execute_speedtest_not_installed(self, mock_run, network_tool):
        """Test speedtest when speedtest-cli is not installed."""
        mock_run.side_effect = FileNotFoundError("speedtest-cli not found")

        result = network_tool.execute_sync(operation="speedtest")

        assert result.success is False
        assert "speedtest-cli not found" in result.error

    @patch('subprocess.run')
    def test_execute_subprocess_exception(self, mock_run, network_tool):
        """Test handling of subprocess exceptions."""
        mock_run.side_effect = subprocess.SubprocessError("Network unreachable")

        result = network_tool.execute_sync(operation="ping", host="example.com")

        assert result.success is False
        assert "Network unreachable" in result.error

    @pytest.mark.parametrize("operation,requires_host", [
        ("ping", True),
        ("traceroute", True),
        ("dns", True),
        ("interfaces", False),
        ("connections", False),
        ("speedtest", False),
    ])
    def test_execute_host_requirements(self, network_tool, operation, requires_host):
        """Test host requirements for different operations."""
        if requires_host:
            result = network_tool.execute_sync(operation=operation)
            assert result.success is False
            assert "Host is required" in result.error
        else:
            # Mock successful execution for operations that don't require host
            with patch('subprocess.run') as mock_run:
                mock_process = MagicMock()
                mock_process.returncode = 0
                mock_process.stdout = f"{operation} output"
                mock_process.stderr = ""
                mock_run.return_value = mock_process

                result = network_tool.execute_sync(operation=operation)
                assert result.success is True

    @patch('subprocess.run')
    def test_execute_ping_with_large_count(self, mock_run, network_tool):
        """Test ping with large count parameter."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Ping with 10 packets"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="ping", host="test.com", count="10")

        assert result.success is True
        args, kwargs = mock_run.call_args
        assert args[0] == ['ping', '-c', '10', 'test.com']

    @patch('subprocess.run')
    def test_execute_interfaces_parsing(self, mock_run, network_tool):
        """Test network interfaces output parsing."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """1: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP
    inet 192.168.0.100/24 brd 192.168.0.255 scope global wlan0
2: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="interfaces")

        assert result.success is True
        assert "wlan0:" in result.data['stdout']
        assert "192.168.0.100" in result.data['stdout']
        assert "docker0:" in result.data['stdout']

    @patch('subprocess.run')
    def test_execute_connections_filtering(self, mock_run, network_tool):
        """Test network connections output filtering."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """Active Internet connections
tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:3306          0.0.0.0:*               LISTEN
tcp6       0      0 :::22                   :::*                    LISTEN
udp        0      0 0.0.0.0:53              0.0.0.0:*               LISTEN
"""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = network_tool.execute_sync(operation="connections")

        assert result.success is True
        assert "LISTEN" in result.data['stdout']
        assert "tcp" in result.data['stdout']
        assert "udp" in result.data['stdout']