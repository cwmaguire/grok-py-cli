"""Unit tests for WebSearchTool."""

import pytest
from unittest.mock import patch, MagicMock
from tavily import InvalidAPIKeyError, UsageLimitExceededError

from grok_py.tools.web_search import WebSearchTool


class TestWebSearchTool:
    """Test suite for WebSearchTool."""

    @pytest.fixture
    def web_search_tool(self):
        """Fixture to create a WebSearchTool instance."""
        return WebSearchTool()

    def test_web_search_success(self):
        """Test successful web search."""
        mock_client = MagicMock()
        mock_response = {
            'results': [
                {
                    'title': 'Test Title',
                    'url': 'https://example.com',
                    'content': 'Test content',
                    'score': 0.9
                }
            ],
            'response_time': 1.2,
            'answer': 'Test answer'
        }
        mock_client.search.return_value = mock_response

        with patch('os.getenv', return_value='fake_api_key'):
            with patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client):
                tool = WebSearchTool()
                result = tool.execute_sync(query="test query")

                assert result.success is True
                assert len(result.data['results']) == 1
                assert result.data['results'][0]['title'] == 'Test Title'
                assert result.data['query'] == "test query"
                assert result.data['max_results'] == 5
                assert result.data['search_depth'] == "basic"
                assert result.data['topic'] == "general"
                assert result.data['response_time'] == 1.2
                assert result.data['answer'] == 'Test answer'
                assert result.metadata['has_results'] is True
                assert result.metadata['result_count'] == 1

    def test_web_search_no_api_key(self, web_search_tool):
        """Test missing API key."""
        with patch('os.getenv', return_value=None):
            tool = WebSearchTool()
            result = tool.execute_sync(query="test")

            assert result.success is False
            assert "TAVILY_API_KEY environment variable not set" in result.error

    def test_web_search_no_client(self):
        """Test failed client initialization."""
        with patch('os.getenv', return_value='fake_key'):
            with patch('grok_py.tools.web_search.TavilyClient', side_effect=Exception("Init failed")):
                tool = WebSearchTool()
                result = tool.execute_sync(query="test")

                assert result.success is False
                assert "Tavily client not initialized" in result.error

    def test_web_search_empty_query(self):
        """Test empty query."""
        mock_client = MagicMock()
        with patch('os.getenv', return_value='fake_api_key'):
            with patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client):
                tool = WebSearchTool()
                result = tool.execute_sync(query="")

                assert result.success is False
                assert "Query cannot be empty" in result.error

    def test_web_search_invalid_max_results(self):
        """Test invalid max_results."""
        mock_client = MagicMock()
        with patch('os.getenv', return_value='fake_api_key'):
            with patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client):
                tool = WebSearchTool()
                result = tool.execute_sync(query="test", max_results=25)

                assert result.success is False
                assert "max_results must be between 1 and 20" in result.error

    def test_web_search_invalid_search_depth(self):
        """Test invalid search_depth."""
        mock_client = MagicMock()
        with patch('os.getenv', return_value='fake_api_key'):
            with patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client):
                tool = WebSearchTool()
                result = tool.execute_sync(query="test", search_depth="invalid")

                assert result.success is False
                assert "search_depth must be 'basic' or 'advanced'" in result.error

    def test_web_search_invalid_topic(self):
        """Test invalid topic."""
        mock_client = MagicMock()
        with patch('os.getenv', return_value='fake_api_key'):
            with patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client):
                tool = WebSearchTool()
                result = tool.execute_sync(query="test", topic="invalid")

                assert result.success is False
                assert "topic must be one of: general, news, finance" in result.error

    def test_web_search_no_results(self):
        """Test no search results."""
        mock_client = MagicMock()
        mock_response = {
            'results': [],
            'response_time': 0.5
        }
        mock_client.search.return_value = mock_response

        with patch('os.getenv', return_value='fake_api_key'):
            with patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client):
                tool = WebSearchTool()
                result = tool.execute_sync(query="test")

                assert result.success is False
                assert "No search results found" in result.error
                assert result.data['total_results'] == 0
                assert result.metadata['has_results'] is False

    def test_web_search_invalid_api_key(self):
        """Test InvalidAPIKeyError."""
        mock_client = MagicMock()
        mock_client.search.side_effect = InvalidAPIKeyError("Invalid API key")

        with patch('os.getenv', return_value='fake_api_key'):
            with patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client):
                tool = WebSearchTool()
                result = tool.execute_sync(query="test")

                assert result.success is False
                assert "Invalid TAVILY_API_KEY" in result.error

    def test_web_search_usage_limit(self):
        """Test UsageLimitError."""
        mock_client = MagicMock()
        mock_client.search.side_effect = UsageLimitExceededError("Usage limit")

        with patch('os.getenv', return_value='fake_api_key'):
            with patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client):
                tool = WebSearchTool()
                result = tool.execute_sync(query="test")

                assert result.success is False
                assert "Tavily API usage limit exceeded" in result.error

    def test_web_search_rate_limit(self):
        """Test RateLimitError."""
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Rate limit")

        with patch('os.getenv', return_value='fake_api_key'):
            with patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client):
                tool = WebSearchTool()
                result = tool.execute_sync(query="test")

                assert result.success is False
                assert "Web search failed: Rate limit" in result.error

    def test_web_search_other_exception(self):
        """Test other exceptions."""
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Network error")

        with patch('os.getenv', return_value='fake_api_key'):
            with patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client):
                tool = WebSearchTool()
                result = tool.execute_sync(query="test")

                assert result.success is False
                assert "Web search failed: Network error" in result.error