"""Disk usage monitoring and management tool."""

import os
import subprocess
import shlex
from typing import Optional
from pathlib import Path

from .base import SyncTool, ToolCategory, ToolResult


class DiskTool(SyncTool):
    """Tool for disk usage monitoring and management."""

    def __init__(self):
        super().__init__(
            name="disk",
            description="Disk usage monitoring and cleanup suggestions",
            category=ToolCategory.SYSTEM
        )

    def execute_sync(
        self,
        operation: str,
        path: Optional[str] = None,
        size: Optional[str] = None
    ) -> ToolResult:
        """Execute disk monitoring operation.

        Args:
            operation: Operation to perform (usage, free, du, large-files, cleanup)
            path: Path to check (for usage, du, large-files)
            size: Minimum file size for large-files (e.g., '100M', '1G')

        Returns:
            ToolResult with disk information
        """
        try:
            # Validate operation
            valid_operations = ['usage', 'free', 'du', 'large-files', 'cleanup']
            if operation not in valid_operations:
                return ToolResult(
                    success=False,
                    error=f"Invalid operation: {operation}. Valid operations: {', '.join(valid_operations)}"
                )

            if operation in ['usage', 'du', 'large-files'] and not path:
                path = '/'  # Default to root

            result_data = {
                'operation': operation,
                'path': path,
                'size': size
            }

            if operation == 'usage':
                # Get disk usage with df
                cmd = ['df', '-h', path or '/']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    return ToolResult(success=False, error=result.stderr.strip())

                # Parse df output
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    header = lines[0]
                    data = lines[1].split()
                    if len(data) >= 6:
                        result_data.update({
                            'filesystem': data[0],
                            'size': data[1],
                            'used': data[2],
                            'available': data[3],
                            'use_percent': data[4],
                            'mount_point': data[5]
                        })

            elif operation == 'free':
                # Get memory and swap usage with free
                cmd = ['free', '-h']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    return ToolResult(success=False, error=result.stderr.strip())

                result_data['output'] = result.stdout.strip()

            elif operation == 'du':
                # Get directory usage with du
                cmd = ['du', '-sh', path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    return ToolResult(success=False, error=result.stderr.strip())

                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    result_data.update({
                        'size': parts[0],
                        'path': parts[1]
                    })

            elif operation == 'large-files':
                # Find large files
                min_size = size or '100M'
                cmd = ['find', path, '-type', 'f', '-size', f'+{min_size}', '-exec', 'ls', '-lh', '{}', ';']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

                if result.returncode != 0:
                    return ToolResult(success=False, error=result.stderr.strip())

                files = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 9:
                            files.append({
                                'permissions': parts[0],
                                'size': parts[4],
                                'modified': ' '.join(parts[5:8]),
                                'path': ' '.join(parts[8:])
                            })

                result_data['large_files'] = files
                result_data['count'] = len(files)

            elif operation == 'cleanup':
                # Provide cleanup suggestions
                suggestions = []

                # Check for large files in common directories
                common_dirs = ['/var/log', '/tmp', '/var/cache', '/home']
                for dir_path in common_dirs:
                    if os.path.exists(dir_path):
                        try:
                            # Get top 5 largest files in directory
                            cmd = ['find', dir_path, '-type', 'f', '-size', '+10M', '-print0', '|', 'xargs', '-0', 'ls', '-lhS', '|', 'head', '-5']
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                            if result.returncode == 0 and result.stdout.strip():
                                suggestions.append(f"Large files in {dir_path}:\n{result.stdout.strip()}")
                        except:
                            pass

                # Check disk usage
                cmd = ['df', '-h', '/']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    suggestions.append(f"Current disk usage:\n{result.stdout.strip()}")

                result_data['cleanup_suggestions'] = suggestions

            return ToolResult(
                success=True,
                data=result_data,
                metadata={'operation': operation}
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Operation '{operation}' timed out",
                metadata={'timed_out': True}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to execute disk operation: {str(e)}"
            )