"""Bash command execution tool."""

import asyncio
import os
import shlex
from typing import Optional

from .base import AsyncTool, ToolCategory, ToolResult


class BashTool(AsyncTool):
    """Tool for executing bash commands with full output capture and async support."""

    def __init__(self):
        super().__init__(
            name="bash",
            description="Execute bash commands with proper output capture, error handling, and safety checks",
            category=ToolCategory.SYSTEM
        )

    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[float] = 30.0,
        shell: bool = False
    ) -> ToolResult:
        """Execute a bash command asynchronously.

        Args:
            command: The command to execute
            cwd: Working directory for command execution (default: current directory)
            timeout: Timeout in seconds (default: 30.0)
            shell: Whether to execute via shell (default: False for security)

        Returns:
            ToolResult with command output and exit code
        """
        try:
            # Validate command
            if not command or not command.strip():
                return ToolResult(
                    success=False,
                    error="Command cannot be empty"
                )

            # Safety check: prevent potentially dangerous commands
            dangerous_commands = ['rm -rf /', 'dd if=', 'mkfs', 'fdisk', 'format']
            for dangerous in dangerous_commands:
                if dangerous in command.lower():
                    return ToolResult(
                        success=False,
                        error=f"Command contains potentially dangerous operation: {dangerous}"
                    )

            # Prepare command execution
            if shell:
                # Use shell=True for complex commands
                process_cmd = command
                shell_flag = True
            else:
                # Parse command for exec-style execution
                try:
                    process_cmd = shlex.split(command)
                    shell_flag = False
                except ValueError as e:
                    return ToolResult(
                        success=False,
                        error=f"Invalid command syntax: {str(e)}"
                    )

            # Set working directory
            working_dir = cwd or os.getcwd()

            # Execute command
            process = await asyncio.create_subprocess_exec(
                *process_cmd if not shell_flag else ['bash', '-c', command],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                shell=shell_flag
            )

            try:
                # Wait for completion with timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                # Decode output
                stdout_str = stdout.decode('utf-8', errors='replace').strip()
                stderr_str = stderr.decode('utf-8', errors='replace').strip()

                # Prepare result data
                result_data = {
                    'stdout': stdout_str,
                    'stderr': stderr_str,
                    'exit_code': process.returncode,
                    'command': command,
                    'working_directory': working_dir
                }

                # Check if command succeeded
                success = process.returncode == 0

                return ToolResult(
                    success=success,
                    data=result_data,
                    error=stderr_str if not success else None,
                    metadata={
                        'exit_code': process.returncode,
                        'has_stderr': bool(stderr_str),
                        'has_stdout': bool(stdout_str)
                    }
                )

            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout} seconds",
                    metadata={'timed_out': True}
                )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to execute command: {str(e)}"
            )