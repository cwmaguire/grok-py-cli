"""Systemd service management tool."""

import subprocess
import shlex
from typing import Optional

from .base import SyncTool, ToolCategory, ToolResult


class SystemctlTool(SyncTool):
    """Tool for managing systemd services."""

    def __init__(self):
        super().__init__(
            name="systemctl",
            description="Systemd service management (start, stop, restart, enable, disable, status checking)",
            category=ToolCategory.SYSTEM
        )

    def execute_sync(
        self,
        operation: str,
        service: str
    ) -> ToolResult:
        """Execute systemctl service management operation.

        Args:
            operation: Operation to perform (start, stop, restart, status, enable, disable, is-active, is-enabled)
            service: Service name (e.g., nginx, docker, ssh)

        Returns:
            ToolResult with operation result
        """
        try:
            # Validate operation
            valid_operations = ['start', 'stop', 'restart', 'status', 'enable', 'disable', 'is-active', 'is-enabled']
            if operation not in valid_operations:
                return ToolResult(
                    success=False,
                    error=f"Invalid operation: {operation}. Valid operations: {', '.join(valid_operations)}"
                )

            # Validate service name
            if not service or not service.strip():
                return ToolResult(
                    success=False,
                    error="Service name cannot be empty"
                )

            # Build command
            cmd_parts = ['systemctl']

            # Operations that modify services need sudo
            if operation in ['start', 'stop', 'restart', 'enable', 'disable']:
                cmd_parts.insert(0, 'sudo')

            cmd_parts.extend([operation, service])

            command = shlex.join(cmd_parts)

            # Execute command
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )

            # Prepare result data
            result_data = {
                'operation': operation,
                'service': service,
                'command': command,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'exit_code': result.returncode
            }

            # For status operations, success depends on service state
            if operation in ['is-active', 'is-enabled']:
                # These return 0 if true, 3 if false (inactive/disabled)
                success = result.returncode == 0
                result_data['state'] = 'active' if operation == 'is-active' and success else \
                                     'enabled' if operation == 'is-enabled' and success else \
                                     'inactive' if operation == 'is-active' else 'disabled'
            elif operation == 'status':
                # Status command returns 0 if service exists and can be queried
                success = result.returncode == 0
                # Parse status output for more details
                if success:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.startswith('Active:'):
                            result_data['active_state'] = line.split(':', 1)[1].strip()
                        elif line.startswith('Loaded:'):
                            result_data['loaded_state'] = line.split(':', 1)[1].strip()
            else:
                # For control operations (start, stop, etc.), success means exit code 0
                success = result.returncode == 0

            return ToolResult(
                success=success,
                data=result_data,
                error=result.stderr.strip() if result.stderr.strip() else None,
                metadata={
                    'exit_code': result.returncode,
                    'has_output': bool(result.stdout.strip()),
                    'operation': operation,
                    'service': service
                }
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Operation '{operation}' on service '{service}' timed out",
                metadata={'timed_out': True}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to execute systemctl operation: {str(e)}"
            )