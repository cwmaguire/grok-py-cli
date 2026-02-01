"""Version control integration tools for Grok CLI."""

import asyncio
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

from grok_py.tools.base import SyncTool, AsyncTool, ToolCategory, ToolResult, register_tool


class GitHelper:
    """Helper class for Git operations."""

    @staticmethod
    def run_git_command(command: List[str], cwd: Optional[str] = None,
                       capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a git command and return the result."""
        try:
            result = subprocess.run(
                ['git'] + command,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                check=False
            )
            return result
        except FileNotFoundError:
            raise Exception("Git is not installed or not in PATH")

    @staticmethod
    def is_git_repo(path: str) -> bool:
        """Check if path is a git repository."""
        result = GitHelper.run_git_command(['rev-parse', '--git-dir'], cwd=path)
        return result.returncode == 0

    @staticmethod
    def parse_status(output: str) -> Dict[str, List[str]]:
        """Parse git status output."""
        staged = []
        unstaged = []
        untracked = []

        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('M ') or line.startswith('A ') or line.startswith('D ') or line.startswith('R '):
                staged.append(line[2:].strip())
            elif line.startswith(' M') or line.startswith(' D') or line.startswith('??'):
                if line.startswith('??'):
                    untracked.append(line[3:].strip())
                else:
                    unstaged.append(line[2:].strip())

        return {
            'staged': staged,
            'unstaged': unstaged,
            'untracked': untracked
        }


@register_tool(category=ToolCategory.DEVELOPMENT, name="git_init",
               description="Initialize a new Git repository")
class GitInitTool(SyncTool):
    """Tool for initializing Git repositories."""

    def execute_sync(self, directory: str, bare: bool = False) -> ToolResult:
        """Initialize a Git repository.

        Args:
            directory: Directory to initialize
            bare: Whether to create a bare repository

        Returns:
            ToolResult: Initialization result
        """
        try:
            path = Path(directory)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)

            if GitHelper.is_git_repo(str(path)):
                return ToolResult(success=False, error=f"Directory is already a git repository: {directory}")

            command = ['init']
            if bare:
                command.append('--bare')

            result = GitHelper.run_git_command(command, cwd=str(path))

            if result.returncode == 0:
                return ToolResult(success=True, data={
                    "repository_path": str(path),
                    "bare": bare,
                    "message": "Git repository initialized successfully"
                })
            else:
                return ToolResult(success=False, error=f"Git init failed: {result.stderr}")

        except Exception as e:
            return ToolResult(success=False, error=f"Git init failed: {str(e)}")


@register_tool(category=ToolCategory.DEVELOPMENT, name="git_clone",
               description="Clone a Git repository with progress tracking")
class GitCloneTool(AsyncTool):
    """Tool for cloning Git repositories."""

    async def execute(self, repository_url: str, destination: str,
                     branch: Optional[str] = None, depth: Optional[int] = None,
                     shallow: bool = False) -> ToolResult:
        """Clone a Git repository.

        Args:
            repository_url: URL of the repository to clone
            destination: Local destination directory
            branch: Specific branch to clone
            depth: Depth for shallow clone
            shallow: Whether to do a shallow clone

        Returns:
            ToolResult: Clone operation result
        """
        try:
            dest_path = Path(destination)
            if dest_path.exists() and any(dest_path.iterdir()):
                return ToolResult(success=False, error=f"Destination directory is not empty: {destination}")

            command = ['clone', repository_url, str(dest_path)]

            if branch:
                command.extend(['--branch', branch])

            if shallow or depth:
                command.extend(['--depth', str(depth or 1)])

            # Run clone command (can be long-running)
            process = await asyncio.create_subprocess_exec(
                'git', *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(dest_path.parent) if dest_path.parent.exists() else None
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return ToolResult(success=True, data={
                    "repository_url": repository_url,
                    "local_path": str(dest_path),
                    "branch": branch,
                    "shallow": shallow or depth is not None
                })
            else:
                error_msg = stderr.decode().strip() if stderr else "Clone failed"
                return ToolResult(success=False, error=f"Git clone failed: {error_msg}")

        except Exception as e:
            return ToolResult(success=False, error=f"Git clone failed: {str(e)}")


@register_tool(category=ToolCategory.DEVELOPMENT, name="git_status",
               description="Check Git repository status")
class GitStatusTool(SyncTool):
    """Tool for checking Git repository status."""

    def execute_sync(self, directory: str) -> ToolResult:
        """Get Git repository status.

        Args:
            directory: Repository directory

        Returns:
            ToolResult: Status information
        """
        try:
            if not GitHelper.is_git_repo(directory):
                return ToolResult(success=False, error=f"Not a git repository: {directory}")

            # Get status
            result = GitHelper.run_git_command(['status', '--porcelain'], cwd=directory)
            if result.returncode != 0:
                return ToolResult(success=False, error=f"Git status failed: {result.stderr}")

            status_info = GitHelper.parse_status(result.stdout)

            # Get current branch
            branch_result = GitHelper.run_git_command(['branch', '--show-current'], cwd=directory)
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

            # Get remote info
            remote_result = GitHelper.run_git_command(['remote', '-v'], cwd=directory)
            remotes = []
            if remote_result.returncode == 0:
                for line in remote_result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            remotes.append({
                                'name': parts[0],
                                'url': parts[1],
                                'type': parts[2].strip('()') if len(parts) > 2 else 'unknown'
                            })

            return ToolResult(success=True, data={
                "repository_path": directory,
                "current_branch": current_branch,
                "status": status_info,
                "remotes": remotes,
                "clean": len(status_info['staged']) == 0 and len(status_info['unstaged']) == 0 and len(status_info['untracked']) == 0
            })

        except Exception as e:
            return ToolResult(success=False, error=f"Git status failed: {str(e)}")


@register_tool(category=ToolCategory.DEVELOPMENT, name="git_add",
               description="Add files to Git staging area")
class GitAddTool(SyncTool):
    """Tool for adding files to Git."""

    def execute_sync(self, directory: str, files: List[str], all: bool = False) -> ToolResult:
        """Add files to staging area.

        Args:
            directory: Repository directory
            files: List of files to add
            all: Whether to add all files

        Returns:
            ToolResult: Add operation result
        """
        try:
            if not GitHelper.is_git_repo(directory):
                return ToolResult(success=False, error=f"Not a git repository: {directory}")

            command = ['add']
            if all:
                command.append('--all')
            else:
                command.extend(files)

            result = GitHelper.run_git_command(command, cwd=directory)

            if result.returncode == 0:
                return ToolResult(success=True, data={
                    "repository_path": directory,
                    "added_files": files if not all else ["all files"],
                    "message": "Files added to staging area"
                })
            else:
                return ToolResult(success=False, error=f"Git add failed: {result.stderr}")

        except Exception as e:
            return ToolResult(success=False, error=f"Git add failed: {str(e)}")


@register_tool(category=ToolCategory.DEVELOPMENT, name="git_commit",
               description="Commit changes to Git repository")
class GitCommitTool(SyncTool):
    """Tool for committing changes."""

    def execute_sync(self, directory: str, message: str, all: bool = False,
                    amend: bool = False) -> ToolResult:
        """Commit changes.

        Args:
            directory: Repository directory
            message: Commit message
            all: Whether to automatically stage all modified files
            amend: Whether to amend the last commit

        Returns:
            ToolResult: Commit result
        """
        try:
            if not GitHelper.is_git_repo(directory):
                return ToolResult(success=False, error=f"Not a git repository: {directory}")

            command = ['commit', '-m', message]
            if all:
                command.append('--all')
            if amend:
                command.append('--amend')

            result = GitHelper.run_git_command(command, cwd=directory)

            if result.returncode == 0:
                return ToolResult(success=True, data={
                    "repository_path": directory,
                    "message": message,
                    "amended": amend,
                    "commit_output": result.stdout.strip()
                })
            else:
                return ToolResult(success=False, error=f"Git commit failed: {result.stderr}")

        except Exception as e:
            return ToolResult(success=False, error=f"Git commit failed: {str(e)}")


@register_tool(category=ToolCategory.DEVELOPMENT, name="git_push",
               description="Push commits to remote repository")
class GitPushTool(SyncTool):
    """Tool for pushing commits."""

    def execute_sync(self, directory: str, remote: str = "origin",
                    branch: Optional[str] = None, force: bool = False) -> ToolResult:
        """Push commits to remote.

        Args:
            directory: Repository directory
            remote: Remote name
            branch: Branch to push
            force: Whether to force push

        Returns:
            ToolResult: Push result
        """
        try:
            if not GitHelper.is_git_repo(directory):
                return ToolResult(success=False, error=f"Not a git repository: {directory}")

            command = ['push', remote]
            if branch:
                command.append(branch)
            if force:
                command.append('--force')

            result = GitHelper.run_git_command(command, cwd=directory)

            if result.returncode == 0:
                return ToolResult(success=True, data={
                    "repository_path": directory,
                    "remote": remote,
                    "branch": branch,
                    "forced": force,
                    "push_output": result.stdout.strip()
                })
            else:
                return ToolResult(success=False, error=f"Git push failed: {result.stderr}")

        except Exception as e:
            return ToolResult(success=False, error=f"Git push failed: {str(e)}")


@register_tool(category=ToolCategory.DEVELOPMENT, name="git_pull",
               description="Pull changes from remote repository")
class GitPullTool(SyncTool):
    """Tool for pulling changes."""

    def execute_sync(self, directory: str, remote: str = "origin",
                    branch: Optional[str] = None) -> ToolResult:
        """Pull changes from remote.

        Args:
            directory: Repository directory
            remote: Remote name
            branch: Branch to pull

        Returns:
            ToolResult: Pull result
        """
        try:
            if not GitHelper.is_git_repo(directory):
                return ToolResult(success=False, error=f"Not a git repository: {directory}")

            command = ['pull', remote]
            if branch:
                command.append(branch)

            result = GitHelper.run_git_command(command, cwd=directory)

            if result.returncode == 0:
                return ToolResult(success=True, data={
                    "repository_path": directory,
                    "remote": remote,
                    "branch": branch,
                    "pull_output": result.stdout.strip()
                })
            else:
                return ToolResult(success=False, error=f"Git pull failed: {result.stderr}")

        except Exception as e:
            return ToolResult(success=False, error=f"Git pull failed: {str(e)}")


@register_tool(category=ToolCategory.DEVELOPMENT, name="git_branch",
               description="Manage Git branches")
class GitBranchTool(SyncTool):
    """Tool for managing Git branches."""

    def execute_sync(self, directory: str, action: str, name: Optional[str] = None,
                    base_branch: Optional[str] = None) -> ToolResult:
        """Manage branches.

        Args:
            directory: Repository directory
            action: Action to perform (list, create, delete, switch)
            name: Branch name
            base_branch: Base branch for creation

        Returns:
            ToolResult: Branch operation result
        """
        try:
            if not GitHelper.is_git_repo(directory):
                return ToolResult(success=False, error=f"Not a git repository: {directory}")

            if action == "list":
                result = GitHelper.run_git_command(['branch', '-a'], cwd=directory)
                if result.returncode != 0:
                    return ToolResult(success=False, error=f"Git branch list failed: {result.stderr}")

                branches = []
                current_branch = None
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line.startswith('*'):
                        current_branch = line[1:].strip()
                        branches.append({"name": current_branch, "current": True})
                    else:
                        branches.append({"name": line, "current": False})

                return ToolResult(success=True, data={
                    "branches": branches,
                    "current_branch": current_branch
                })

            elif action == "create":
                if not name:
                    return ToolResult(success=False, error="Branch name required for create action")

                command = ['checkout', '-b', name]
                if base_branch:
                    command = ['checkout', '-b', name, base_branch]

                result = GitHelper.run_git_command(command, cwd=directory)
                if result.returncode == 0:
                    return ToolResult(success=True, data={
                        "action": "create",
                        "branch_name": name,
                        "base_branch": base_branch
                    })
                else:
                    return ToolResult(success=False, error=f"Git branch create failed: {result.stderr}")

            elif action == "switch":
                if not name:
                    return ToolResult(success=False, error="Branch name required for switch action")

                result = GitHelper.run_git_command(['checkout', name], cwd=directory)
                if result.returncode == 0:
                    return ToolResult(success=True, data={
                        "action": "switch",
                        "branch_name": name
                    })
                else:
                    return ToolResult(success=False, error=f"Git branch switch failed: {result.stderr}")

            elif action == "delete":
                if not name:
                    return ToolResult(success=False, error="Branch name required for delete action")

                result = GitHelper.run_git_command(['branch', '-d', name], cwd=directory)
                if result.returncode == 0:
                    return ToolResult(success=True, data={
                        "action": "delete",
                        "branch_name": name
                    })
                else:
                    return ToolResult(success=False, error=f"Git branch delete failed: {result.stderr}")

            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=f"Git branch operation failed: {str(e)}")


@register_tool(category=ToolCategory.DEVELOPMENT, name="git_log",
               description="View Git commit history")
class GitLogTool(SyncTool):
    """Tool for viewing Git commit history."""

    def execute_sync(self, directory: str, count: int = 10, author: Optional[str] = None,
                    since: Optional[str] = None) -> ToolResult:
        """View commit history.

        Args:
            directory: Repository directory
            count: Number of commits to show
            author: Filter by author
            since: Show commits since date

        Returns:
            ToolResult: Log information
        """
        try:
            if not GitHelper.is_git_repo(directory):
                return ToolResult(success=False, error=f"Not a git repository: {directory}")

            command = ['log', '--oneline', f'-{count}']
            if author:
                command.extend(['--author', author])
            if since:
                command.extend(['--since', since])

            result = GitHelper.run_git_command(command, cwd=directory)

            if result.returncode == 0:
                commits = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split(' ', 1)
                        if len(parts) == 2:
                            commits.append({
                                'hash': parts[0],
                                'message': parts[1]
                            })

                return ToolResult(success=True, data={
                    "commits": commits,
                    "count": len(commits)
                })
            else:
                return ToolResult(success=False, error=f"Git log failed: {result.stderr}")

        except Exception as e:
            return ToolResult(success=False, error=f"Git log failed: {str(e)}")
