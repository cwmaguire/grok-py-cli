"""Ubuntu package management tool using apt."""

import subprocess
import shlex
from typing import Optional

from .base import SyncTool, ToolCategory, ToolResult


class AptTool(SyncTool):
    """Tool for managing Ubuntu packages using apt."""

    def __init__(self):
        super().__init__(
            name="apt",
            description="Ubuntu package management (install, remove, update, upgrade, search, show)",
            category=ToolCategory.SYSTEM
        )

    def execute_sync(
        self,
        operation: str,
        package: Optional[str] = None,
        assume_yes: bool = False
    ) -> ToolResult:
        """Execute apt package management operation.

        Args:
            operation: Operation to perform (install, remove, update, upgrade, search, show)
            package: Package name (required for install, remove, search, show)
            assume_yes: Automatically answer yes to prompts (default: False)

        Returns:
            ToolResult with operation result
        """
        try:
            # Validate operation
            valid_operations = ['install', 'remove', 'update', 'upgrade', 'search', 'show']
            if operation not in valid_operations:
                return ToolResult(
                    success=False,
                    error=f"Invalid operation: {operation}. Valid operations: {', '.join(valid_operations)}"
                )

            # Validate package requirement
            if operation in ['install', 'remove', 'search', 'show'] and not package:
                return ToolResult(
                    success=False,
                    error=f"Package name required for operation: {operation}"
                )

            # Build command
            cmd_parts = ['apt']

            if operation in ['install', 'remove', 'update', 'upgrade']:
                # These operations typically need sudo
                cmd_parts.insert(0, 'sudo')
                if assume_yes:
                    cmd_parts.append('-y')

            cmd_parts.append(operation)

            if package:
                # For search and show, package can be a pattern
                cmd_parts.append(package)

            # Special handling for upgrade (full upgrade vs safe upgrade)
            if operation == 'upgrade':
                # Use 'full-upgrade' for more comprehensive upgrade
                cmd_parts[-1] = 'full-upgrade'

            command = shlex.join(cmd_parts)

            # Execute command
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout for long operations
            )

            # Prepare result data
            result_data = {
                'operation': operation,
                'package': package,
                'command': command,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'exit_code': result.returncode
            }

            # Check success
            success = result.returncode == 0

            # For search operation, parse results
            if operation == 'search' and success:
                packages = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and not line.startswith('Sorting') and not line.startswith('Full Text Search'):
                        # Basic parsing - can be enhanced
                        parts = line.split('/', 1)
                        if len(parts) > 1:
                            packages.append(parts[0].strip())
                result_data['packages'] = packages

            return ToolResult(
                success=success,
                data=result_data,
                error=result.stderr.strip() if not success else None,
                metadata={
                    'exit_code': result.returncode,
                    'has_output': bool(result.stdout.strip()),
                    'operation': operation
                }
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Operation '{operation}' timed out after 5 minutes",
                metadata={'timed_out': True}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to execute apt operation: {str(e)}"
            )