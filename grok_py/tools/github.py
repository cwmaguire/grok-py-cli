"""GitHub API tool for repository operations, issue management, and pull requests."""

import os
from typing import Optional, Dict, Any, List

from github import Github, Repository, Issue, PullRequest
from github.GithubException import GithubException, RateLimitExceededException

from .base import SyncTool, ToolCategory, ToolResult


class GitHubTool(SyncTool):
    name = "github"
    description = "GitHub API integration for repository operations, issue management, pull requests, and code search"
    category = ToolCategory.DEVELOPMENT

    def __init__(self):
        super().__init__()
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_ACCESS_TOKEN")
        if token:
            self.client = Github(token)
        else:
            self.client = Github()  # public access only

    def get_available_functions(self) -> List[Dict[str, Any]]:
        return [
            # Repository operations
            {
                "name": "create_repository",
                "description": "Create a new GitHub repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Repository name"},
                        "description": {"type": "string", "description": "Repository description", "default": ""},
                        "private": {"type": "boolean", "description": "Whether the repository is private", "default": False},
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "fork_repository",
                "description": "Fork a GitHub repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "name": "delete_repository",
                "description": "Delete a GitHub repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "name": "get_repository",
                "description": "Get information about a GitHub repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                    },
                    "required": ["owner", "repo"],
                },
            },
            # Issue management
            {
                "name": "create_issue",
                "description": "Create a new GitHub issue",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "title": {"type": "string", "description": "Issue title"},
                        "body": {"type": "string", "description": "Issue body", "default": ""},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "Issue labels", "default": []},
                    },
                    "required": ["owner", "repo", "title"],
                },
            },
            {
                "name": "update_issue",
                "description": "Update a GitHub issue",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "number": {"type": "integer", "description": "Issue number"},
                        "title": {"type": "string", "description": "New title"},
                        "body": {"type": "string", "description": "New body"},
                        "state": {"type": "string", "enum": ["open", "closed"], "description": "Issue state"},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "Issue labels"},
                    },
                    "required": ["owner", "repo", "number"],
                },
            },
            {
                "name": "comment_on_issue",
                "description": "Add a comment to a GitHub issue",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "number": {"type": "integer", "description": "Issue number"},
                        "body": {"type": "string", "description": "Comment body"},
                    },
                    "required": ["owner", "repo", "number", "body"],
                },
            },
            # Pull request operations
            {
                "name": "create_pull_request",
                "description": "Create a new GitHub pull request",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "title": {"type": "string", "description": "PR title"},
                        "body": {"type": "string", "description": "PR body", "default": ""},
                        "head": {"type": "string", "description": "Head branch"},
                        "base": {"type": "string", "description": "Base branch", "default": "main"},
                    },
                    "required": ["owner", "repo", "title", "head"],
                },
            },
            {
                "name": "merge_pull_request",
                "description": "Merge a GitHub pull request",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "number": {"type": "integer", "description": "PR number"},
                        "merge_method": {"type": "string", "enum": ["merge", "squash", "rebase"], "description": "Merge method", "default": "merge"},
                    },
                    "required": ["owner", "repo", "number"],
                },
            },
            # Code search and file retrieval
            {
                "name": "search_code",
                "description": "Search for code in GitHub repositories",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "language": {"type": "string", "description": "Programming language"},
                        "repo": {"type": "string", "description": "Repository to search in (owner/repo)"},
                        "filename": {"type": "string", "description": "Filename to search in"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_file_content",
                "description": "Get the content of a file from a GitHub repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "path": {"type": "string", "description": "File path"},
                        "ref": {"type": "string", "description": "Branch or commit SHA", "default": "main"},
                    },
                    "required": ["owner", "repo", "path"],
                },
            },
        ]

    def _handle_rate_limit(self, e: RateLimitExceededException) -> ToolResult:
        reset_time = self.client.get_rate_limit().core.reset
        return ToolResult(success=False, error=f"Rate limit exceeded. Resets at {reset_time}")

    def create_repository(self, name: str, description: str = "", private: bool = False) -> ToolResult:
        try:
            user = self.client.get_user()
            repo = user.create_repo(name, description=description, private=private)
            return ToolResult(success=True, data={"url": repo.html_url, "name": repo.name, "private": repo.private})
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))

    def fork_repository(self, owner: str, repo: str) -> ToolResult:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            forked = repository.create_fork()
            return ToolResult(success=True, data={"url": forked.html_url, "name": forked.full_name})
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))

    def delete_repository(self, owner: str, repo: str) -> ToolResult:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            repository.delete()
            return ToolResult(success=True, message="Repository deleted successfully")
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))

    def get_repository(self, owner: str, repo: str) -> ToolResult:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            return ToolResult(success=True, data={
                "name": repository.name,
                "full_name": repository.full_name,
                "description": repository.description,
                "url": repository.html_url,
                "clone_url": repository.clone_url,
                "stars": repository.stargazers_count,
                "forks": repository.forks_count,
                "language": repository.language,
                "private": repository.private,
            })
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))

    def create_issue(self, owner: str, repo: str, title: str, body: str = "", labels: List[str] = None) -> ToolResult:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            issue = repository.create_issue(title=title, body=body, labels=labels or [])
            return ToolResult(success=True, data={"number": issue.number, "url": issue.html_url})
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))

    def update_issue(self, owner: str, repo: str, number: int, title: Optional[str] = None,
                     body: Optional[str] = None, state: Optional[str] = None, labels: Optional[List[str]] = None) -> ToolResult:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            issue = repository.get_issue(number)
            update_kwargs = {}
            if title is not None:
                update_kwargs["title"] = title
            if body is not None:
                update_kwargs["body"] = body
            if state is not None:
                update_kwargs["state"] = state
            if labels is not None:
                update_kwargs["labels"] = labels
            issue.edit(**update_kwargs)
            return ToolResult(success=True, message="Issue updated successfully")
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))

    def comment_on_issue(self, owner: str, repo: str, number: int, body: str) -> ToolResult:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            issue = repository.get_issue(number)
            comment = issue.create_comment(body)
            return ToolResult(success=True, data={"id": comment.id, "url": comment.html_url})
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))

    def create_pull_request(self, owner: str, repo: str, title: str, body: str = "", head: str = "", base: str = "main") -> ToolResult:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            pr = repository.create_pull(title=title, body=body, head=head, base=base)
            return ToolResult(success=True, data={"number": pr.number, "url": pr.html_url})
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))

    def merge_pull_request(self, owner: str, repo: str, number: int, merge_method: str = "merge") -> ToolResult:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            pr = repository.get_pull(number)
            merge_commit = pr.merge(merge_method=merge_method)
            return ToolResult(success=True, data={"merged": merge_commit.merged, "sha": merge_commit.sha if merge_commit else None})
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))

    def search_code(self, query: str, language: Optional[str] = None, repo: Optional[str] = None, filename: Optional[str] = None) -> ToolResult:
        try:
            search_query = f"{query}"
            if language:
                search_query += f" language:{language}"
            if repo:
                search_query += f" repo:{repo}"
            if filename:
                search_query += f" filename:{filename}"
            results = self.client.search_code(search_query)
            items = []
            for item in results[:10]:  # Limit to 10 results
                items.append({
                    "name": item.name,
                    "path": item.path,
                    "html_url": item.html_url,
                    "repository": item.repository.full_name,
                })
            return ToolResult(success=True, data={"results": items, "total_count": results.totalCount})
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))

    def get_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> ToolResult:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            file_content = repository.get_contents(path, ref=ref)
            if isinstance(file_content, list):
                return ToolResult(success=False, error="Path is a directory")
            content = file_content.decoded_content.decode('utf-8')
            return ToolResult(success=True, data={"content": content, "size": file_content.size, "url": file_content.html_url})
        except RateLimitExceededException as e:
            return self._handle_rate_limit(e)
        except GithubException as e:
            return ToolResult(success=False, error=str(e))