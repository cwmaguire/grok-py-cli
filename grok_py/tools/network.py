"""Network diagnostics and monitoring tool."""

import subprocess
import shlex
import json
import re
from typing import Optional

from .base import SyncTool, ToolCategory, ToolResult


class NetworkTool(SyncTool):
    """Tool for network diagnostics and monitoring."""

    def __init__(self):
        super().__init__(
            name="network",
            description="Network diagnostics (ping, traceroute, interfaces, connections, dns, speedtest)",
            category=ToolCategory.NETWORK
        )

    def execute_sync(
        self,
        operation: str,
        host: Optional[str] = None,
        count: Optional[str] = None
    ) -> ToolResult:
        """Execute network diagnostic operation.

        Args:
            operation: Operation to perform (ping, traceroute, interfaces, connections, dns, speedtest)
            host: Host to test (for ping, traceroute, dns)
            count: Number of ping packets to send

        Returns:
            ToolResult with operation result
        """
        try:
            # Validate operation
            valid_operations = ['ping', 'traceroute', 'interfaces', 'connections', 'dns', 'speedtest']
            if operation not in valid_operations:
                return ToolResult(
                    success=False,
                    error=f"Invalid operation: {operation}. Valid operations: {', '.join(valid_operations)}"
                )

            # Validate host requirement for certain operations
            if operation in ['ping', 'traceroute', 'dns'] and not host:
                return ToolResult(
                    success=False,
                    error=f"Host required for operation: {operation}"
                )

            # Execute operation
            if operation == 'ping':
                return self._ping(host, count)
            elif operation == 'traceroute':
                return self._traceroute(host)
            elif operation == 'interfaces':
                return self._interfaces()
            elif operation == 'connections':
                return self._connections()
            elif operation == 'dns':
                return self._dns(host)
            elif operation == 'speedtest':
                return self._speedtest()
            else:
                return ToolResult(
                    success=False,
                    error=f"Operation '{operation}' not implemented"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Network operation failed: {str(e)}"
            )

    def _ping(self, host: str, count: Optional[str] = None) -> ToolResult:
        """Perform ping operation."""
        cmd_parts = ['ping']
        if count:
            cmd_parts.extend(['-c', count])
        else:
            cmd_parts.extend(['-c', '4'])  # Default 4 packets
        cmd_parts.append(host)

        command = shlex.join(cmd_parts)

        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse ping results
            stats = self._parse_ping_output(result.stdout)

            result_data = {
                'operation': 'ping',
                'host': host,
                'command': command,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'exit_code': result.returncode,
                'stats': stats
            }

            success = result.returncode == 0
            return ToolResult(
                success=success,
                data=result_data,
                error=result.stderr.strip() if not success else None,
                metadata={
                    'exit_code': result.returncode,
                    'has_output': bool(result.stdout.strip()),
                    'operation': 'ping'
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Ping to {host} timed out after 30 seconds",
                metadata={'timed_out': True}
            )

    def _traceroute(self, host: str) -> ToolResult:
        """Perform traceroute operation."""
        cmd_parts = ['traceroute', host]

        command = shlex.join(cmd_parts)

        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=60  # Traceroute can take longer
            )

            # Parse traceroute output
            hops = self._parse_traceroute_output(result.stdout)

            result_data = {
                'operation': 'traceroute',
                'host': host,
                'command': command,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'exit_code': result.returncode,
                'hops': hops
            }

            success = result.returncode == 0
            return ToolResult(
                success=success,
                data=result_data,
                error=result.stderr.strip() if not success else None,
                metadata={
                    'exit_code': result.returncode,
                    'has_output': bool(result.stdout.strip()),
                    'operation': 'traceroute'
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Traceroute to {host} timed out after 60 seconds",
                metadata={'timed_out': True}
            )

    def _interfaces(self) -> ToolResult:
        """Get network interface information."""
        try:
            # Try ip command first (modern), fall back to ifconfig
            result = subprocess.run(
                ['ip', 'addr', 'show'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                # Fallback to ifconfig
                result = subprocess.run(
                    ['ifconfig'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            interfaces = self._parse_interfaces_output(result.stdout)

            result_data = {
                'operation': 'interfaces',
                'command': 'ip addr show' if result.returncode == 0 else 'ifconfig',
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'exit_code': result.returncode,
                'interfaces': interfaces
            }

            success = result.returncode == 0
            return ToolResult(
                success=success,
                data=result_data,
                error=result.stderr.strip() if not success else None,
                metadata={
                    'exit_code': result.returncode,
                    'has_output': bool(result.stdout.strip()),
                    'operation': 'interfaces'
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error="Interface listing timed out after 10 seconds",
                metadata={'timed_out': True}
            )

    def _connections(self) -> ToolResult:
        """Get active network connections."""
        try:
            # Use ss command (modern), fall back to netstat
            result = subprocess.run(
                ['ss', '-tuln'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                # Fallback to netstat
                result = subprocess.run(
                    ['netstat', '-tuln'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            connections = self._parse_connections_output(result.stdout)

            result_data = {
                'operation': 'connections',
                'command': 'ss -tuln' if result.returncode == 0 else 'netstat -tuln',
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'exit_code': result.returncode,
                'connections': connections
            }

            success = result.returncode == 0
            return ToolResult(
                success=success,
                data=result_data,
                error=result.stderr.strip() if not success else None,
                metadata={
                    'exit_code': result.returncode,
                    'has_output': bool(result.stdout.strip()),
                    'operation': 'connections'
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error="Connection listing timed out after 10 seconds",
                metadata={'timed_out': True}
            )

    def _dns(self, host: str) -> ToolResult:
        """Perform DNS resolution."""
        try:
            # Use dig command
            result = subprocess.run(
                ['dig', '+short', host],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Also try to resolve with nslookup as fallback
            if result.returncode != 0 or not result.stdout.strip():
                result = subprocess.run(
                    ['nslookup', host],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            addresses = self._parse_dns_output(result.stdout)

            result_data = {
                'operation': 'dns',
                'host': host,
                'command': 'dig +short' if result.returncode == 0 else 'nslookup',
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'exit_code': result.returncode,
                'addresses': addresses
            }

            success = result.returncode == 0 and bool(addresses)
            return ToolResult(
                success=success,
                data=result_data,
                error=result.stderr.strip() if not success else None,
                metadata={
                    'exit_code': result.returncode,
                    'has_output': bool(result.stdout.strip()),
                    'operation': 'dns'
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"DNS resolution for {host} timed out after 10 seconds",
                metadata={'timed_out': True}
            )

    def _speedtest(self) -> ToolResult:
        """Perform internet speed test."""
        try:
            # Use speedtest-cli if available
            result = subprocess.run(
                ['speedtest-cli', '--json'],
                capture_output=True,
                text=True,
                timeout=120  # Speed tests can take time
            )

            if result.returncode == 0:
                try:
                    speed_data = json.loads(result.stdout.strip())
                    result_data = {
                        'operation': 'speedtest',
                        'command': 'speedtest-cli --json',
                        'stdout': result.stdout.strip(),
                        'stderr': result.stderr.strip(),
                        'exit_code': result.returncode,
                        'speed_data': speed_data
                    }
                except json.JSONDecodeError:
                    result_data = {
                        'operation': 'speedtest',
                        'command': 'speedtest-cli --json',
                        'stdout': result.stdout.strip(),
                        'stderr': result.stderr.strip(),
                        'exit_code': result.returncode,
                        'speed_data': None
                    }
            else:
                # Fallback to simple speedtest-cli without JSON
                result = subprocess.run(
                    ['speedtest-cli'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                result_data = {
                    'operation': 'speedtest',
                    'command': 'speedtest-cli',
                    'stdout': result.stdout.strip(),
                    'stderr': result.stderr.strip(),
                    'exit_code': result.returncode,
                    'speed_data': None
                }

            success = result.returncode == 0
            return ToolResult(
                success=success,
                data=result_data,
                error=result.stderr.strip() if not success else None,
                metadata={
                    'exit_code': result.returncode,
                    'has_output': bool(result.stdout.strip()),
                    'operation': 'speedtest'
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error="Speed test timed out after 120 seconds",
                metadata={'timed_out': True}
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error="speedtest-cli not installed. Install with: pip install speedtest-cli"
            )

    def _parse_ping_output(self, output: str) -> dict:
        """Parse ping command output for statistics."""
        stats = {}
        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('rtt min/avg/max/mdev ='):
                # Extract timing statistics
                timing_match = re.search(r'rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', line)
                if timing_match:
                    stats['min_rtt'] = float(timing_match.group(1))
                    stats['avg_rtt'] = float(timing_match.group(2))
                    stats['max_rtt'] = float(timing_match.group(3))
                    stats['mdev_rtt'] = float(timing_match.group(4))
            elif 'packets transmitted' in line:
                # Extract packet statistics
                packet_match = re.search(r'(\d+) packets transmitted, (\d+) received', line)
                if packet_match:
                    stats['packets_transmitted'] = int(packet_match.group(1))
                    stats['packets_received'] = int(packet_match.group(2))
                    stats['packet_loss'] = ((int(packet_match.group(1)) - int(packet_match.group(2))) / int(packet_match.group(1))) * 100
        return stats

    def _parse_traceroute_output(self, output: str) -> list:
        """Parse traceroute output for hop information."""
        hops = []
        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('traceroute to'):
                parts = line.split()
                if len(parts) > 1:
                    try:
                        hop_num = int(parts[0])
                        host = parts[1] if len(parts) > 1 else 'unknown'
                        timing = []
                        for part in parts[2:]:
                            if part.replace('.', '').replace('ms', '').isdigit():
                                timing.append(float(part.replace('ms', '')))
                        hops.append({
                            'hop': hop_num,
                            'host': host,
                            'timing': timing
                        })
                    except (ValueError, IndexError):
                        continue
        return hops

    def _parse_interfaces_output(self, output: str) -> list:
        """Parse network interfaces output."""
        interfaces = []
        current_interface = None
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith(('1:', '2:', '3:', 'eth', 'wlan', 'lo:', 'enp', 'wlp')):
                # New interface line
                if current_interface:
                    interfaces.append(current_interface)
                parts = line.split(':')
                if len(parts) >= 2:
                    current_interface = {
                        'name': parts[0].strip(),
                        'flags': parts[1].strip() if len(parts) > 1 else '',
                        'addresses': []
                    }
            elif current_interface and (line.startswith('inet ') or line.startswith('inet6 ')):
                # IP address line
                parts = line.split()
                if len(parts) >= 2:
                    addr_info = {
                        'family': 'ipv4' if line.startswith('inet ') else 'ipv6',
                        'address': parts[1].split('/')[0],
                        'prefix': parts[1].split('/')[1] if '/' in parts[1] else None
                    }
                    current_interface['addresses'].append(addr_info)
        
        if current_interface:
            interfaces.append(current_interface)
        
        return interfaces

    def _parse_connections_output(self, output: str) -> list:
        """Parse network connections output."""
        connections = []
        lines = output.strip().split('\n')
        for line in lines[1:]:  # Skip header
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 6:
                    connection = {
                        'protocol': parts[0],
                        'local_address': parts[4],
                        'foreign_address': parts[5],
                        'state': parts[1] if len(parts) > 1 else 'LISTEN'
                    }
                    connections.append(connection)
        return connections

    def _parse_dns_output(self, output: str) -> list:
        """Parse DNS resolution output."""
        addresses = []
        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            # For dig output (simple addresses)
            if line and not line.startswith((';', ';;')):
                # Basic IP validation
                if re.match(r'\d+\.\d+\.\d+\.\d+', line) or ':' in line:
                    addresses.append(line)
            # For nslookup output
            elif 'Address:' in line:
                addr = line.split('Address:')[1].strip()
                if addr:
                    addresses.append(addr)
        return list(set(addresses))  # Remove duplicates</content>
</xai:function_call">The Network Tool implementation is comprehensive, including all required operations: ping, traceroute, interfaces, connections, DNS resolution, and speed testing. It uses modern Linux networking tools (ip, ss, dig) with fallbacks to legacy tools (ifconfig, netstat, nslookup). Each operation includes proper error handling, timeout management, and structured data parsing for easy consumption.

The tool follows the established pattern from Task 2, inheriting from SyncTool and implementing the execute_sync method with parameter validation. It includes detailed parsing functions for each operation to extract meaningful statistics and data from command outputs.

Moving on to the Code Execution Tool next. This will be more complex as it needs to handle Docker container execution with multiple programming languages. Let me mark the network tool as complete and start on the code execution tool. 

<xai:function_call name="update_todo_list">
<parameter name="updates">[{"id":"implement_network_tool","status":"completed"},{"id":"implement_code_execution_tool","status":"in_progress"}]