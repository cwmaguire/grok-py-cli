"""Unit tests for NewsTool."""

import pytest
from unittest.mock import patch, MagicMock
from grok_py.tools.news import NewsTool
from grok_py.tools.base import ToolResult


class TestNewsTool:
    """Test NewsTool class."""

    def setup_method(self):
        """Set up test method."""
        self.tool = NewsTool()
        # Mock the client for tests that need it
        self.tool.client = MagicMock()

    @patch('grok_py.tools.news.os.getenv')
    @patch('grok_py.tools.news.NewsApiClient')
    @patch('grok_py.tools.news.httpx.Client')
    def test_init_with_api_key(self, mock_httpx, mock_client_class, mock_getenv):
        """Test NewsTool initialization with API key."""
        mock_getenv.return_value = "test_key"
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        tool = NewsTool()

        assert tool.api_key == "test_key"
        assert tool.client == mock_client_instance
        mock_client_class.assert_called_once_with(api_key="test_key")
        mock_httpx.assert_called_once_with(timeout=30.0)

    @patch('grok_py.tools.news.os.getenv')
    @patch('grok_py.tools.news.NewsApiClient')
    def test_init_without_api_key(self, mock_client_class, mock_getenv):
        """Test NewsTool initialization without API key."""
        mock_getenv.return_value = None

        tool = NewsTool()

        assert tool.api_key is None
        assert tool.client is None
        mock_client_class.assert_not_called()

    @patch('grok_py.tools.news.os.getenv')
    @patch('grok_py.tools.news.NewsApiClient')
    def test_init_client_exception(self, mock_client_class, mock_getenv):
        """Test NewsTool initialization with client exception."""
        mock_getenv.return_value = "test_key"
        mock_client_class.side_effect = Exception("Client error")

        tool = NewsTool()

        assert tool.api_key == "test_key"
        assert tool.client is None

    def test_get_available_functions(self):
        """Test get_available_functions method."""
        functions = self.tool.get_available_functions()
        assert len(functions) == 3
        assert functions[0]["name"] == "search_news"
        assert functions[1]["name"] == "get_headlines"
        assert functions[2]["name"] == "get_sources"

    def test_execute_sync_no_client(self):
        """Test execute_sync without initialized client."""
        tool = NewsTool()
        tool.client = None  # Override the mock

        result = tool.execute_sync(action="search", query="test")

        assert result.success is False
        assert "NewsAPI client not initialized" in result.error

    @patch.object(NewsTool, '_search_news')
    def test_execute_sync_search(self, mock_search):
        """Test execute_sync with search action."""
        mock_result = ToolResult(success=True, data={"articles": []})
        mock_search.return_value = mock_result

        result = self.tool.execute_sync(action="search", query="test query")

        mock_search.assert_called_once_with(
            query="test query",
            sources=None,
            domains=None,
            from_date=None,
            to_date=None,
            language="en",
            sort_by="publishedAt",
            page_size=20,
            page=1,
            summarize=False
        )
        assert result == mock_result

    @patch.object(NewsTool, '_get_headlines')
    def test_execute_sync_headlines(self, mock_headlines):
        """Test execute_sync with headlines action."""
        mock_result = ToolResult(success=True, data={"articles": []})
        mock_headlines.return_value = mock_result

        result = self.tool.execute_sync(action="headlines", sources="bbc-news")

        mock_headlines.assert_called_once_with(
            country=None,
            category=None,
            sources="bbc-news",
            q=None,
            page_size=20,
            page=1,
            summarize=False
        )
        assert result == mock_result

    @patch.object(NewsTool, '_get_sources')
    def test_execute_sync_sources(self, mock_sources):
        """Test execute_sync with sources action."""
        mock_result = ToolResult(success=True, data={"sources": []})
        mock_sources.return_value = mock_result

        result = self.tool.execute_sync(action="sources", language="en")

        mock_sources.assert_called_once_with(
            category=None,
            language="en",
            country=None
        )
        assert result == mock_result

    def test_execute_sync_unknown_action(self):
        """Test execute_sync with unknown action."""
        result = self.tool.execute_sync(action="unknown")

        assert result.success is False
        assert "Unknown action: unknown" in result.error

    def test_execute_sync_exception(self):
        """Test execute_sync with general exception."""
        self.tool.client.get_everything.side_effect = Exception("API error")

        result = self.tool.execute_sync(action="search", query="test")

        assert result.success is False
        assert result.error == "Search failed: API error"

    def test_search_news_success(self):
        """Test _search_news method success."""
        mock_articles = {
            "totalResults": 2,
            "articles": [
                {"title": "Test Article 1", "description": "Desc 1", "url": "url1"},
                {"title": "Test Article 2", "description": "Desc 2", "url": "url2"}
            ]
        }
        self.tool.client.get_everything.return_value = mock_articles

        result = self.tool._search_news(query="test query")

        assert result.success is True
        assert result.data["total_results"] == 2
        assert len(result.data["articles"]) == 2
        self.tool.client.get_everything.assert_called_once_with(
            q="test query",
            sources=None,
            domains=None,
            from_param=None,
            to=None,
            language="en",
            sort_by="publishedAt",
            page_size=20,
            page=1
        )

    def test_search_news_exception(self):
        """Test _search_news method exception."""
        self.tool.client.get_everything.side_effect = Exception("Search error")

        result = self.tool._search_news(query="test")

        assert result.success is False
        assert "Search failed: Search error" in result.error

    def test_get_headlines_success(self):
        """Test _get_headlines method success."""
        mock_headlines = {
            "totalResults": 1,
            "articles": [{"title": "Headline 1"}]
        }
        self.tool.client.get_top_headlines.return_value = mock_headlines

        result = self.tool._get_headlines(sources="cnn")

        assert result.success is True
        assert result.data["total_results"] == 1
        self.tool.client.get_top_headlines.assert_called_once_with(
            country=None,
            category=None,
            sources="cnn",
            q=None,
            page_size=20,
            page=1
        )

    def test_get_sources_success(self):
        """Test _get_sources method success."""
        mock_sources = {"sources": [{"id": "bbc-news", "name": "BBC News"}]}
        self.tool.client.get_sources.return_value = mock_sources

        result = self.tool._get_sources(language="en")

        assert result.success is True
        assert result.data["sources"] == [{"id": "bbc-news", "name": "BBC News"}]
        self.tool.client.get_sources.assert_called_once_with(
            category=None,
            language="en",
            country=None
        )

    def test_format_articles_without_summary(self):
        """Test _format_articles without summarization."""
        articles = [
            {
                "title": "Test Title",
                "description": "Test Description",
                "url": "http://example.com",
                "source": {"name": "Test Source"},
                "publishedAt": "2023-01-01T00:00:00Z",
                "author": "Test Author",
                "urlToImage": "http://example.com/image.jpg"
            }
        ]

        result = self.tool._format_articles(articles, summarize=False)

        assert len(result) == 1
        assert result[0]["title"] == "Test Title"
        assert result[0]["description"] == "Test Description"
        assert result[0]["url"] == "http://example.com"
        assert result[0]["source"] == "Test Source"
        assert result[0]["published_at"] == "2023-01-01T00:00:00Z"
        assert result[0]["author"] == "Test Author"
        assert result[0]["url_to_image"] == "http://example.com/image.jpg"
        assert "summary" not in result[0]

    def test_format_articles_with_summary(self):
        """Test _format_articles with summarization."""
        articles = [
            {
                "title": "Test Title",
                "url": "http://example.com"
            }
        ]

        result = self.tool._format_articles(articles, summarize=True)

        assert len(result) == 1
        assert result[0]["summary"] == "Summary not yet implemented - would extract key points from article"

    def test_summarize_article(self):
        """Test _summarize_article method."""
        summary = self.tool._summarize_article("http://example.com")

        assert summary == "Summary not yet implemented - would extract key points from article"