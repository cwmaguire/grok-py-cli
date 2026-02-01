import pytest
from unittest.mock import MagicMock, patch

from grok_py.tools.web_search import WebSearchTool
from grok_py.tools.base import ToolResult


class TestWebSearchToolIntegration:
    @pytest.fixture
    def tool(self):
        return WebSearchTool()

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_successful_search_basic(self, tool, mocker):
        # Mock the TavilyClient
        mock_client = MagicMock()
        mock_response = {
            'results': [
                {
                    'title': 'Test Result 1',
                    'url': 'https://example.com/1',
                    'content': 'This is test content 1',
                    'score': 0.9
                },
                {
                    'title': 'Test Result 2',
                    'url': 'https://example.com/2',
                    'content': 'This is test content 2',
                    'score': 0.8
                }
            ],
            'response_time': 1.2,
            'answer': 'This is a generated answer'
        }
        mock_client.search.return_value = mock_response

        # Patch the client initialization
        mocker.patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client)

        # Re-initialize tool to pick up the mock
        tool.__init__()

        result = tool.execute_sync('test query', max_results=5, search_depth='basic', topic='general')

        assert result.success == True
        assert result.data['query'] == 'test query'
        assert result.data['max_results'] == 5
        assert result.data['search_depth'] == 'basic'
        assert result.data['topic'] == 'general'
        assert len(result.data['results']) == 2
        assert result.data['results'][0]['title'] == 'Test Result 1'
        assert result.data['total_results'] == 2
        assert result.data['response_time'] == 1.2
        assert result.data['answer'] == 'This is a generated answer'
        assert result.metadata['has_results'] == True
        assert result.metadata['result_count'] == 2

        # Verify API call
        mock_client.search.assert_called_once_with(
            query='test query',
            max_results=5,
            search_depth='basic',
            topic='general'
        )

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_search_with_no_results(self, tool, mocker):
        mock_client = MagicMock()
        mock_response = {
            'results': [],
            'response_time': 0.5
        }
        mock_client.search.return_value = mock_response

        mocker.patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client)
        tool.__init__()

        result = tool.execute_sync('empty query')

        assert result.success == False
        assert result.error == "No search results found"
        assert result.data['total_results'] == 0
        assert result.metadata['has_results'] == False

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_search_with_invalid_api_key(self, tool, mocker):
        from tavily import InvalidAPIKeyError

        mock_client = MagicMock()
        mock_client.search.side_effect = InvalidAPIKeyError("Invalid key")

        mocker.patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client)
        tool.__init__()

        result = tool.execute_sync('test query')

        assert result.success == False
        assert "Invalid TAVILY_API_KEY" in result.error

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_search_with_usage_limit(self, tool, mocker):
        from tavily import UsageLimitError

        mock_client = MagicMock()
        mock_client.search.side_effect = UsageLimitError("Limit exceeded")

        mocker.patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client)
        tool.__init__()

        result = tool.execute_sync('test query')

        assert result.success == False
        assert "usage limit exceeded" in result.error

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_search_with_rate_limit(self, tool, mocker):
        from tavily import RateLimitError

        mock_client = MagicMock()
        mock_client.search.side_effect = RateLimitError("Rate limit exceeded")

        mocker.patch('grok_py.tools.web_search.TavilyClient', return_value=mock_client)
        tool.__init__()

        result = tool.execute_sync('test query')

        assert result.success == False
        assert "rate limit exceeded" in result.error

    def test_search_without_api_key(self, tool):
        # Ensure no API key
        with patch.dict('os.environ', {}, clear=True):
            tool.__init__()

        result = tool.execute_sync('test query')

        assert result.success == False
        assert "TAVILY_API_KEY environment variable not set" in result.error

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'invalid_key'})
    def test_client_initialization_failure(self, tool, mocker):
        mocker.patch('grok_py.tools.web_search.TavilyClient', side_effect=Exception("Init failed"))
        tool.__init__()

        result = tool.execute_sync('test query')

        assert result.success == False
        assert "Tavily client not initialized" in result.error

    def test_parameter_validation_empty_query(self, tool):
        with patch.dict('os.environ', {'TAVILY_API_KEY': 'test'}):
            tool.__init__()

        result = tool.execute_sync('')

        assert result.success == False
        assert "Query cannot be empty" in result.error

    def test_parameter_validation_invalid_max_results(self, tool):
        with patch.dict('os.environ', {'TAVILY_API_KEY': 'test'}):
            tool.__init__()

        result = tool.execute_sync('query', max_results=0)

        assert result.success == False
        assert "max_results must be between 1 and 20" in result.error

    def test_parameter_validation_invalid_search_depth(self, tool):
        with patch.dict('os.environ', {'TAVILY_API_KEY': 'test'}):
            tool.__init__()

        result = tool.execute_sync('query', search_depth='invalid')

        assert result.success == False
        assert "search_depth must be 'basic' or 'advanced'" in result.error

    def test_parameter_validation_invalid_topic(self, tool):
        with patch.dict('os.environ', {'TAVILY_API_KEY': 'test'}):
            tool.__init__()

        result = tool.execute_sync('query', topic='invalid')

        assert result.success == False
        assert "topic must be one of: general, news, finance" in result.error

    def test_is_available(self, tool):
        # Without API key
        assert tool.is_available() == False

        # With API key but no client
        tool.api_key = 'test'
        tool.client = None
        assert tool.is_available() == False

        # With both
        tool.client = MagicMock()
        assert tool.is_available() == True

    def test_get_api_status(self, tool):
        tool.api_key = None
        tool.client = None
        status = tool.get_api_status()
        assert status['api_key_set'] == False
        assert status['client_initialized'] == False
        assert status['available'] == False

        tool.api_key = 'test'
        tool.client = MagicMock()
        status = tool.get_api_status()
        assert status['api_key_set'] == True
        assert status['client_initialized'] == True
        assert status['available'] == True