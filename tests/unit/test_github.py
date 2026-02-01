"""Unit tests for GitHubTool."""

import pytest
from unittest.mock import patch, MagicMock
from grok_py.tools.github import GitHubTool
from grok_py.tools.base import ToolResult


class TestGitHubTool:
    """Test GitHubTool class."""

    def setup_method(self):
        """Set up test method."""
        with patch('grok_py.tools.github.os.getenv', return_value="fake_token"), \
             patch('grok_py.tools.github.Github'):
            self.tool = GitHubTool()

    @patch('grok_py.tools.github.os.getenv')
    @patch('grok_py.tools.github.Github')
    def test_init_with_token(self, mock_github_class, mock_getenv):
        """Test GitHubTool initialization with token."""
        mock_getenv.return_value = "test_token"
        mock_client = MagicMock()
        mock_github_class.return_value = mock_client

        tool = GitHubTool()

        mock_github_class.assert_called_with("test_token")
        assert tool.client == mock_client

    @patch('grok_py.tools.github.os.getenv')
    @patch('grok_py.tools.github.Github')
    def test_init_without_token(self, mock_github_class, mock_getenv):
        """Test GitHubTool initialization without token."""
        mock_getenv.return_value = None
        mock_client = MagicMock()
        mock_github_class.return_value = mock_client

        tool = GitHubTool()

        mock_github_class.assert_called_with()  # No token
        assert tool.client == mock_client

    def test_get_available_functions(self):
        """Test get_available_functions method."""
        functions = self.tool.get_available_functions()
        function_names = [f["name"] for f in functions]

        assert "create_repository" in function_names
        assert "fork_repository" in function_names
        assert "create_issue" in function_names
        assert "search_code" in function_names
        assert "get_file_content" in function_names

    @patch.object(GitHubTool, 'client')
    def test_create_repository_success(self, mock_client):
        """Test create_repository success."""
        mock_user = MagicMock()
        mock_repo = MagicMock()
        mock_repo.html_url = "https://github.com/user/repo"
        mock_repo.name = "repo"
        mock_repo.private = False

        mock_client.get_user.return_value = mock_user
        mock_user.create_repo.return_value = mock_repo

        result = self.tool.create_repository("test-repo", "Test description", private=False)

        assert result.success is True
        assert result.data["url"] == "https://github.com/user/repo"
        assert result.data["name"] == "repo"
        mock_user.create_repo.assert_called_once_with("test-repo", description="Test description", private=False)

    @patch.object(GitHubTool, 'client')
    def test_create_repository_rate_limit(self, mock_client):
        """Test create_repository rate limit."""
        from github.GithubException import RateLimitExceededException
        mock_user = MagicMock()
        mock_client.get_user.return_value = mock_user
        mock_user.create_repo.side_effect = RateLimitExceededException(403, "rate limit", None)

        # Mock rate limit reset
        mock_rate_limit = MagicMock()
        mock_rate_limit.core.reset = "reset_time"
        mock_client.get_rate_limit.return_value = mock_rate_limit

        result = self.tool.create_repository("test-repo")

        assert result.success is False
        assert "Rate limit exceeded" in result.error

    @patch.object(GitHubTool, 'client')
    def test_fork_repository_success(self, mock_client):
        """Test fork_repository success."""
        mock_repository = MagicMock()
        mock_forked = MagicMock()
        mock_forked.html_url = "https://github.com/user/forked"
        mock_forked.full_name = "user/forked"

        mock_client.get_repo.return_value = mock_repository
        mock_repository.create_fork.return_value = mock_forked

        result = self.tool.fork_repository("owner", "repo")

        assert result.success is True
        assert result.data["url"] == "https://github.com/user/forked"
        assert result.data["name"] == "user/forked"
        mock_client.get_repo.assert_called_once_with("owner/repo")
        mock_repository.create_fork.assert_called_once()

    @patch.object(GitHubTool, 'client')
    def test_get_repository_success(self, mock_client):
        """Test get_repository success."""
        mock_repository = MagicMock()
        mock_repository.name = "test-repo"
        mock_repository.full_name = "owner/test-repo"
        mock_repository.description = "Test repo"
        mock_repository.html_url = "https://github.com/owner/test-repo"
        mock_repository.clone_url = "https://github.com/owner/test-repo.git"
        mock_repository.stargazers_count = 42
        mock_repository.forks_count = 10
        mock_repository.language = "Python"
        mock_repository.private = False

        mock_client.get_repo.return_value = mock_repository

        result = self.tool.get_repository("owner", "test-repo")

        assert result.success is True
        assert result.data["name"] == "test-repo"
        assert result.data["stars"] == 42
        assert result.data["private"] is False
        mock_client.get_repo.assert_called_once_with("owner/test-repo")

    @patch.object(GitHubTool, 'client')
    def test_create_issue_success(self, mock_client):
        """Test create_issue success."""
        mock_repository = MagicMock()
        mock_issue = MagicMock()
        mock_issue.number = 123
        mock_issue.html_url = "https://github.com/owner/repo/issues/123"

        mock_client.get_repo.return_value = mock_repository
        mock_repository.create_issue.return_value = mock_issue

        result = self.tool.create_issue("owner", "repo", "Test Issue", "Issue body", ["bug"])

        assert result.success is True
        assert result.data["number"] == 123
        assert result.data["url"] == "https://github.com/owner/repo/issues/123"
        mock_repository.create_issue.assert_called_once_with(title="Test Issue", body="Issue body", labels=["bug"])

    @patch.object(GitHubTool, 'client')
    def test_update_issue_success(self, mock_client):
        """Test update_issue success."""
        mock_repository = MagicMock()
        mock_issue = MagicMock()

        mock_client.get_repo.return_value = mock_repository
        mock_repository.get_issue.return_value = mock_issue

        result = self.tool.update_issue("owner", "repo", 123, title="New Title", state="closed")

        assert result.success is True
        assert result.message == "Issue updated successfully"
        mock_issue.edit.assert_called_once_with(title="New Title", state="closed")

    @patch.object(GitHubTool, 'client')
    def test_create_pull_request_success(self, mock_client):
        """Test create_pull_request success."""
        mock_repository = MagicMock()
        mock_pr = MagicMock()
        mock_pr.number = 456
        mock_pr.html_url = "https://github.com/owner/repo/pull/456"

        mock_client.get_repo.return_value = mock_repository
        mock_repository.create_pull.return_value = mock_pr

        result = self.tool.create_pull_request("owner", "repo", "Test PR", "PR body", "feature-branch", "main")

        assert result.success is True
        assert result.data["number"] == 456
        mock_repository.create_pull.assert_called_once_with(title="Test PR", body="PR body", head="feature-branch", base="main")

    @patch.object(GitHubTool, 'client')
    def test_search_code_success(self, mock_client):
        """Test search_code success."""
        mock_results = MagicMock()
        mock_results.totalCount = 25

        mock_item = MagicMock()
        mock_item.name = "file.py"
        mock_item.path = "path/to/file.py"
        mock_item.html_url = "https://github.com/owner/repo/blob/main/path/to/file.py"
        mock_item.repository.full_name = "owner/repo"

        mock_results.__iter__ = lambda: iter([mock_item])
        mock_results.__getitem__ = lambda self, idx: mock_item if idx == slice(None, 10) else None

        mock_client.search_code.return_value = mock_results

        result = self.tool.search_code("test query", language="python")

        assert result.success is True
        assert result.data["total_count"] == 25
        assert len(result.data["results"]) == 1
        assert result.data["results"][0]["name"] == "file.py"
        mock_client.search_code.assert_called_once_with("test query language:python")

    @patch.object(GitHubTool, 'client')
    def test_get_file_content_success(self, mock_client):
        """Test get_file_content success."""
        mock_repository = MagicMock()
        mock_file = MagicMock()
        mock_file.decoded_content.decode.return_value = "file content"
        mock_file.size = 1234
        mock_file.html_url = "https://github.com/owner/repo/blob/main/path/to/file.txt"

        mock_client.get_repo.return_value = mock_repository
        mock_repository.get_contents.return_value = mock_file

        result = self.tool.get_file_content("owner", "repo", "path/to/file.txt", "main")

        assert result.success is True
        assert result.data["content"] == "file content"
        assert result.data["size"] == 1234
        mock_repository.get_contents.assert_called_once_with("path/to/file.txt", ref="main")

    @patch.object(GitHubTool, 'client')
    def test_get_file_content_directory(self, mock_client):
        """Test get_file_content when path is directory."""
        mock_repository = MagicMock()
        mock_client.get_repo.return_value = mock_repository
        mock_repository.get_contents.return_value = []  # List means directory

        result = self.tool.get_file_content("owner", "repo", "path/to/dir")

        assert result.success is False
        assert result.error == "Path is a directory"