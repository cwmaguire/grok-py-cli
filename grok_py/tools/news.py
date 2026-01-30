"""News API tool for real-time news aggregation, search, and summarization."""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json

from newsapi import NewsApiClient
import httpx

from .base import SyncTool, ToolCategory, ToolResult


class NewsTool(SyncTool):
    """Tool for news aggregation and search from multiple sources."""

    def __init__(self):
        super().__init__(
            name="news",
            description="Real-time news aggregation, topic-based search, and article summarization",
            category=ToolCategory.WEB
        )

        # API key from environment
        self.api_key = os.getenv("NEWSAPI_KEY")
        self.client = None
        self.http_client = httpx.Client(timeout=30.0)

        if self.api_key:
            try:
                self.client = NewsApiClient(api_key=self.api_key)
            except Exception as e:
                self.logger.warning(f"Failed to initialize NewsAPI client: {e}")
        else:
            self.logger.warning("NEWSAPI_KEY not found in environment variables")

    def get_available_functions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "search_news",
                "description": "Search for news articles using keywords, topics, or phrases",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query (keywords, phrases)"},
                        "sources": {"type": "string", "description": "Comma-separated list of news sources"},
                        "domains": {"type": "string", "description": "Comma-separated list of domains"},
                        "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                        "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                        "language": {"type": "string", "description": "Language code", "default": "en"},
                        "sort_by": {"type": "string", "enum": ["publishedAt", "relevancy", "popularity"], "description": "Sort order", "default": "publishedAt"},
                        "page_size": {"type": "integer", "description": "Number of results per page", "default": 20, "minimum": 1, "maximum": 100},
                        "page": {"type": "integer", "description": "Page number", "default": 1, "minimum": 1},
                        "summarize": {"type": "boolean", "description": "Whether to include article summaries", "default": False}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_headlines",
                "description": "Get top headlines from news sources",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sources": {"type": "string", "description": "Comma-separated list of news sources"},
                        "q": {"type": "string", "description": "Keywords or phrases to search for in headlines"},
                        "page_size": {"type": "integer", "description": "Number of results per page", "default": 20, "minimum": 1, "maximum": 100},
                        "page": {"type": "integer", "description": "Page number", "default": 1, "minimum": 1},
                        "summarize": {"type": "boolean", "description": "Whether to include article summaries", "default": False}
                    },
                    "required": []
                }
            },
            {
                "name": "get_sources",
                "description": "Get list of available news sources",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "News category"},
                        "language": {"type": "string", "description": "Language code", "default": "en"},
                        "country": {"type": "string", "description": "Country code"}
                    },
                    "required": []
                }
            }
        ]

    def execute_sync(
        self,
        action: str,
        query: Optional[str] = None,
        sources: Optional[str] = None,
        domains: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: Optional[str] = "en",
        sort_by: Optional[str] = "publishedAt",
        page_size: Optional[int] = 20,
        page: Optional[int] = 1,
        summarize: Optional[bool] = False
    ) -> ToolResult:
        """Execute news operations.

        Args:
            action: Action to perform ('search', 'headlines', 'sources')
            query: Search query for news
            sources: Comma-separated list of news sources
            domains: Comma-separated list of domains
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            language: Language code (en, es, fr, etc.)
            sort_by: Sort by ('publishedAt', 'relevancy', 'popularity')
            page_size: Number of results per page (max 100)
            page: Page number
            summarize: Whether to summarize articles

        Returns:
            ToolResult with news data
        """
        if not self.client:
            return ToolResult(
                success=False,
                error="NewsAPI client not initialized. Please set NEWSAPI_KEY environment variable."
            )

        try:
            if action == "search":
                return self._search_news(
                    query=query,
                    sources=sources,
                    domains=domains,
                    from_date=from_date,
                    to_date=to_date,
                    language=language,
                    sort_by=sort_by,
                    page_size=page_size,
                    page=page,
                    summarize=summarize
                )
            elif action == "headlines":
                return self._get_headlines(
                    country=None,  # Will use sources instead
                    category=None,
                    sources=sources,
                    q=query,
                    page_size=page_size,
                    page=page,
                    summarize=summarize
                )
            elif action == "sources":
                return self._get_sources(
                    category=None,
                    language=language,
                    country=None
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}. Use 'search', 'headlines', or 'sources'."
                )
        except Exception as e:
            self.logger.error(f"News API error: {e}")
            return ToolResult(success=False, error=str(e))

    def _search_news(
        self,
        query: str,
        sources: Optional[str] = None,
        domains: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 20,
        page: int = 1,
        summarize: bool = False
    ) -> ToolResult:
        """Search for news articles."""
        try:
            articles = self.client.get_everything(
                q=query,
                sources=sources,
                domains=domains,
                from_param=from_date,
                to=to_date,
                language=language,
                sort_by=sort_by,
                page_size=min(page_size, 100),
                page=page
            )

            result_data = {
                "total_results": articles.get("totalResults", 0),
                "articles": self._format_articles(articles.get("articles", []), summarize)
            }

            return ToolResult(success=True, data=result_data)
        except Exception as e:
            return ToolResult(success=False, error=f"Search failed: {str(e)}")

    def _get_headlines(
        self,
        country: Optional[str] = None,
        category: Optional[str] = None,
        sources: Optional[str] = None,
        q: Optional[str] = None,
        page_size: int = 20,
        page: int = 1,
        summarize: bool = False
    ) -> ToolResult:
        """Get top headlines."""
        try:
            headlines = self.client.get_top_headlines(
                country=country,
                category=category,
                sources=sources,
                q=q,
                page_size=min(page_size, 100),
                page=page
            )

            result_data = {
                "total_results": headlines.get("totalResults", 0),
                "articles": self._format_articles(headlines.get("articles", []), summarize)
            }

            return ToolResult(success=True, data=result_data)
        except Exception as e:
            return ToolResult(success=False, error=f"Headlines fetch failed: {str(e)}")

    def _get_sources(
        self,
        category: Optional[str] = None,
        language: Optional[str] = None,
        country: Optional[str] = None
    ) -> ToolResult:
        """Get available news sources."""
        try:
            sources = self.client.get_sources(
                category=category,
                language=language,
                country=country
            )

            return ToolResult(success=True, data={"sources": sources.get("sources", [])})
        except Exception as e:
            return ToolResult(success=False, error=f"Sources fetch failed: {str(e)}")

    def _format_articles(self, articles: List[Dict], summarize: bool = False) -> List[Dict]:
        """Format articles for display."""
        formatted = []
        for article in articles:
            formatted_article = {
                "title": article.get("title"),
                "description": article.get("description"),
                "url": article.get("url"),
                "source": article.get("source", {}).get("name"),
                "published_at": article.get("publishedAt"),
                "author": article.get("author"),
                "url_to_image": article.get("urlToImage")
            }

            if summarize and article.get("url"):
                # Basic summarization - could be enhanced with AI
                summary = self._summarize_article(article.get("url"))
                if summary:
                    formatted_article["summary"] = summary

            formatted.append(formatted_article)

        return formatted

    def _summarize_article(self, url: str) -> Optional[str]:
        """Basic article summarization (placeholder for AI summarization)."""
        # TODO: Implement AI-powered summarization using OpenAI or similar
        try:
            # For now, return the description as summary
            # In future, fetch article content and summarize
            return "Summary not yet implemented - would extract key points from article"
        except Exception:
            return None