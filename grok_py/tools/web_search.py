"""Web search tool using Tavily API for current information."""

import os
from typing import Optional

from tavily import TavilyClient
from tavily import InvalidAPIKeyError, UsageLimitExceededError

from .base import SyncTool, ToolCategory, ToolResult


class WebSearchTool(SyncTool):
    """Tool for web search using Tavily API."""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for current information, documentation, news (requires TAVILY_API_KEY)",
            category=ToolCategory.WEB
        )

        # Initialize Tavily client
        self.api_key = os.getenv('TAVILY_API_KEY')
        self.client = None
        if self.api_key:
            try:
                self.client = TavilyClient(api_key=self.api_key)
            except Exception as e:
                self.logger.warning(f"Failed to initialize Tavily client: {e}")

    def execute_sync(
        self,
        query: str,
        max_results: Optional[int] = None,
        search_depth: Optional[str] = None,
        topic: Optional[str] = None
    ) -> ToolResult:
        """Perform web search using Tavily API.

        Args:
            query: The search query - be specific and descriptive for best results
            max_results: Maximum number of results to return (1-20, default: 5)
            search_depth: Search depth: 'basic' for faster results, 'advanced' for comprehensive search
            topic: Topic category to focus the search (general, news, finance)

        Returns:
            ToolResult with search results
        """
        try:
            # Check if API key is available
            if not self.api_key:
                return ToolResult(
                    success=False,
                    error="TAVILY_API_KEY environment variable not set. Please set your Tavily API key."
                )

            if not self.client:
                return ToolResult(
                    success=False,
                    error="Tavily client not initialized. Check your API key."
                )

            # Validate parameters
            if not query or not query.strip():
                return ToolResult(
                    success=False,
                    error="Query cannot be empty"
                )

            # Set defaults
            max_results = max_results or 5
            search_depth = search_depth or "basic"
            topic = topic or "general"

            # Validate max_results
            if not (1 <= max_results <= 20):
                return ToolResult(
                    success=False,
                    error="max_results must be between 1 and 20"
                )

            # Validate search_depth
            if search_depth not in ['basic', 'advanced']:
                return ToolResult(
                    success=False,
                    error="search_depth must be 'basic' or 'advanced'"
                )

            # Validate topic
            valid_topics = ['general', 'news', 'finance']
            if topic not in valid_topics:
                return ToolResult(
                    success=False,
                    error=f"topic must be one of: {', '.join(valid_topics)}"
                )

            # Perform search
            search_params = {
                'query': query.strip(),
                'max_results': max_results,
                'search_depth': search_depth,
                'topic': topic
            }

            self.logger.debug(f"Performing web search with params: {search_params}")

            # Call Tavily API
            response = self.client.search(**search_params)

            # Process results
            results = []
            if 'results' in response:
                for result in response['results']:
                    result_item = {
                        'title': result.get('title', ''),
                        'url': result.get('url', ''),
                        'content': result.get('content', ''),
                        'score': result.get('score', 0.0)
                    }
                    results.append(result_item)

            # Prepare result data
            result_data = {
                'query': query,
                'max_results': max_results,
                'search_depth': search_depth,
                'topic': topic,
                'results': results,
                'total_results': len(results),
                'response_time': response.get('response_time', 0),
                'answer': response.get('answer', '') if 'answer' in response else None
            }

            # Check if we got any results
            success = len(results) > 0

            return ToolResult(
                success=success,
                data=result_data,
                error=None if success else "No search results found",
                metadata={
                    'has_results': len(results) > 0,
                    'result_count': len(results),
                    'search_depth': search_depth,
                    'topic': topic,
                    'query_length': len(query)
                }
            )

        except InvalidAPIKeyError:
            return ToolResult(
                success=False,
                error="Invalid TAVILY_API_KEY. Please check your API key."
            )
        except UsageLimitExceededError:
            return ToolResult(
                success=False,
                error="Tavily API usage limit exceeded. Please check your account."
            )
        except Exception as e:
            error_msg = f"Web search failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ToolResult(
                success=False,
                error=error_msg
            )

    def is_available(self) -> bool:
        """Check if the web search tool is available (API key set and client initialized)."""
        return self.api_key is not None and self.client is not None

    def get_api_status(self) -> dict:
        """Get API key status and availability."""
        return {
            'api_key_set': self.api_key is not None,
            'client_initialized': self.client is not None,
            'available': self.is_available()
        }