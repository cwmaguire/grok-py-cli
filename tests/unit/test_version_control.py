"""Unit tests for VersionControlTool and related classes."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from grok_py.tools.version_control import (
    GitHelper,
    GitInitTool,
    GitCloneTool,
    GitStatusTool,
    GitAddTool,
    GitCommitTool
)
from grok_py.tools.base import ToolResult


class TestGitHelper:
    """Test GitHelper static methods."""

    @patch('grok_py.tools.version_control.subprocess.run')
    def test_run_git_command_success(self, mock_run):
        """Test run_git_command with success."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = GitHelper.run_git_command(['status'])

        assert result == mock_result
        mock_run.assert_called_once_with(
            ['git', 'status'],
            cwd=None,
            capture_output=True,
            text=True,
            check=False
        )

    @patch('grok_py.tools.version_control.subprocess.run')
    def test_run_git_command_git_not_found(self, mock_run):
        """Test run_git_command when git is not found."""
        mock_run.side_effect = FileNotFoundError

        with pytest.raises(Exception, match="Git is not installed"):
            GitHelper.run_git_command(['status'])

    @patch('grok_py.tools.version_control.subprocess.run')
    def test_is_git_repo_true(self, mock_run):
        """Test is_git_repo returns True."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        assert GitHelper.is_git_repo("/path/to/repo") is True
        mock_run.assert_called_once_with(
            ['git', 'rev-parse', '--git-dir'],
            cwd="/path/to/repo",
            capture_output=True,
            text=True,
            check=False
        )

    @patch('grok_py.tools.version_control.subprocess.run')
    def test_is_git_repo_false(self, mock_run):
        """Test is_git_repo returns False."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        assert GitHelper.is_git_repo("/path/to/repo") is False

    def test_parse_status(self):
        """Test parse_status method."""
        output = """M  file1.txt
 M file2.txt
?? untracked.txt
A  staged.txt
D  deleted.txt
"""

        status = GitHelper.parse_status(output)

        assert "file1.txt" in status["staged"]
        assert "staged.txt" in status["staged"]
        assert "deleted.txt" in status["staged"]
        assert "file2.txt" in status["unstaged"]
        assert "untracked.txt" in status["untracked"]


class TestGitInitTool:
    """Test GitInitTool."""

    def setup_method(self):
        """Set up test method."""
        self.tool = GitInitTool()

    @patch('grok_py.tools.version_control.Path.mkdir')
    @patch('grok_py.tools.version_control.Path.exists')
    @patch('grok_py.tools.version_control.GitHelper.is_git_repo')
    @patch('grok_py.tools.version_control.GitHelper.run_git_command')
    def test_execute_sync_success(self, mock_run, mock_is_git, mock_exists, mock_mkdir):
        """Test execute_sync success."""
        mock_exists.return_value = False
        mock_is_git.return_value = False
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = self.tool.execute_sync("/path/to/repo")

        assert result.success is True
        assert result.data["repository_path"] == "/path/to/repo"
        assert result.data["bare"] is False
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_run.assert_called_once_with(['init'], cwd="/path/to/repo")

    @patch('grok_py.tools.version_control.GitHelper.is_git_repo')
    def test_execute_sync_already_repo(self, mock_is_git):
        """Test execute_sync when directory is already a git repo."""
        mock_is_git.return_value = True

        result = self.tool.execute_sync("/path/to/repo")

        assert result.success is False
        assert "already a git repository" in result.error

    @patch('grok_py.tools.version_control.Path.exists')
    @patch('grok_py.tools.version_control.GitHelper.run_git_command')
    def test_execute_sync_git_init_failed(self, mock_run, mock_exists):
        """Test execute_sync when git init fails."""
        mock_exists.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Init failed"
        mock_run.return_value = mock_result

        result = self.tool.execute_sync("/path/to/repo")

        assert result.success is False
        assert "Git init failed: Init failed" in result.error


class TestGitStatusTool:
    """Test GitStatusTool."""

    def setup_method(self):
        """Set up test method."""
        self.tool = GitStatusTool()

    @patch('grok_py.tools.version_control.GitHelper.is_git_repo')
    def test_execute_sync_not_repo(self, mock_is_git):
        """Test execute_sync when not a git repo."""
        mock_is_git.return_value = False

        result = self.tool.execute_sync("/path/to/repo")

        assert result.success is False
        assert "Not a git repository" in result.error

    @patch('grok_py.tools.version_control.GitHelper.is_git_repo')
    @patch('grok_py.tools.version_control.GitHelper.run_git_command')
    def test_execute_sync_success(self, mock_run, mock_is_git):
        """Test execute_sync success."""
        mock_is_git.return_value = True

        # Mock status command
        status_result = MagicMock()
        status_result.returncode = 0
        status_result.stdout = "M  file1.txt\n?? file2.txt"

        # Mock branch command
        branch_result = MagicMock()
        branch_result.returncode = 0
        branch_result.stdout = "main"

        # Mock remote command
        remote_result = MagicMock()
        remote_result.returncode = 0
        remote_result.stdout = "origin\thttps://github.com/user/repo.git (fetch)\norigin\thttps://github.com/user/repo.git (push)"

        mock_run.side_effect = [status_result, branch_result, remote_result]

        result = self.tool.execute_sync("/path/to/repo")

        assert result.success is True
        assert result.data["current_branch"] == "main"
        assert result.data["status"]["staged"] == ["file1.txt"]
        assert result.data["status"]["untracked"] == ["file2.txt"]
        assert len(result.data["remotes"]) == 1
        assert result.data["remotes"][0]["name"] == "origin"


class TestGitAddTool:
    """Test GitAddTool."""

    def setup_method(self):
        """Set up test method."""
        self.tool = GitAddTool()

    @patch('grok_py.tools.version_control.GitHelper.is_git_repo')
    def test_execute_sync_not_repo(self, mock_is_git):
        """Test execute_sync when not a git repo."""
        mock_is_git.return_value = False

        result = self.tool.execute_sync("/path/to/repo", ["file.txt"])

        assert result.success is False
        assert "Not a git repository" in result.error

    @patch('grok_py.tools.version_control.GitHelper.is_git_repo')
    @patch('grok_py.tools.version_control.GitHelper.run_git_command')
    def test_execute_sync_success(self, mock_run, mock_is_git):
        """Test execute_sync success."""
        mock_is_git.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = self.tool.execute_sync("/path/to/repo", ["file1.txt", "file2.txt"])

        assert result.success is True
        assert result.data["added_files"] == ["file1.txt", "file2.txt"]
        mock_run.assert_called_once_with(['add', 'file1.txt', 'file2.txt'], cwd="/path/to/repo")

    @patch('grok_py.tools.version_control.GitHelper.is_git_repo')
    @patch('grok_py.tools.version_control.GitHelper.run_git_command')
    def test_execute_sync_add_all(self, mock_run, mock_is_git):
        """Test execute_sync with add all."""
        mock_is_git.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = self.tool.execute_sync("/path/to/repo", [], all=True)

        assert result.success is True
        assert result.data["added_files"] == ["all files"]
        mock_run.assert_called_once_with(['add', '--all'], cwd="/path/to/repo")


class TestGitCommitTool:
    """Test GitCommitTool."""

    def setup_method(self):
        """Set up test method."""
        self.tool = GitCommitTool()

    @patch('grok_py.tools.version_control.GitHelper.is_git_repo')
    def test_execute_sync_not_repo(self, mock_is_git):
        """Test execute_sync when not a git repo."""
        mock_is_git.return_value = False

        result = self.tool.execute_sync("/path/to/repo", "Commit message")

        assert result.success is False
        assert "Not a git repository" in result.error

    @patch('grok_py.tools.version_control.GitHelper.is_git_repo')
    @patch('grok_py.tools.version_control.GitHelper.run_git_command')
    def test_execute_sync_success(self, mock_run, mock_is_git):
        """Test execute_sync success."""
        mock_is_git.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "commit message"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = self.tool.execute_sync("/path/to/repo", "Test commit")

        assert result.success is True
        assert result.data["message"] == "Test commit"
        assert result.data["amended"] is False
        mock_run.assert_called_once_with(['commit', '-m', 'Test commit'], cwd="/path/to/repo")

    @patch('grok_py.tools.version_control.GitHelper.is_git_repo')
    @patch('grok_py.tools.version_control.GitHelper.run_git_command')
    def test_execute_sync_amend(self, mock_run, mock_is_git):
        """Test execute_sync with amend."""
        mock_is_git.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = self.tool.execute_sync("/path/to/repo", "Amended commit", amend=True)

        assert result.success is True
        assert result.data["amended"] is True
        mock_run.assert_called_once_with(['commit', '-m', 'Amended commit', '--amend'], cwd="/path/to/repo")