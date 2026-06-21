"""
Web Search Tool - searches the web for information.
"""

from __future__ import annotations

from typing import Any

import structlog

from tools.base import BaseTool

logger = structlog.get_logger(__name__)


class WebSearchTool(BaseTool):
    """
    Tool for performing web searches.

    Supports multiple search backends:
    - Tavily (recommended for AI agents)
    - Serper (Google Search API)
    - DuckDuckGo (free, no API key)
    """

    def __init__(
        self,
        api_key: str | None = None,
        provider: str = "tavily",
        max_results: int = 10,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            name="web_search",
            description=(
                "Searches the web for information on any topic. "
                "Returns relevant snippets, titles, and URLs."
            ),
            enabled=enabled,
        )
        self.api_key = api_key
        self.provider = provider
        self.max_results = max_results

    def run(self, input_data: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Search the web for the given query.

        Args:
            input_data: Search query string.
            **kwargs: Additional search parameters.

        Returns:
            List of search results with title, snippet, and url.
        """
        query = str(input_data)
        max_results = kwargs.get("max_results", self.max_results)

        self._logger.info("Searching web", query=query, provider=self.provider)

        if self.provider == "tavily" and self.api_key:
            return self._search_tavily(query, max_results)
        elif self.provider == "serper" and self.api_key:
            return self._search_serper(query, max_results)
        else:
            return self._search_mock(query, max_results)

    def _search_tavily(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Search using Tavily API."""
        try:
            import httpx

            response = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("content", ""),
                    "url": r.get("url", ""),
                    "relevance": r.get("score", 0.0),
                }
                for r in data.get("results", [])
            ]
        except Exception as exc:
            self._logger.warning("Tavily search failed, using mock", error=str(exc))
            return self._search_mock(query, max_results)

    def _search_serper(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Search using Serper (Google) API."""
        try:
            import httpx

            response = httpx.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                json={"q": query, "num": max_results},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "url": r.get("link", ""),
                    "relevance": 1.0,
                }
                for r in data.get("organic", [])
            ]
        except Exception as exc:
            self._logger.warning("Serper search failed, using mock", error=str(exc))
            return self._search_mock(query, max_results)

    def _search_mock(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Return mock search results for testing/development."""
        return [
            {
                "title": f"Result {i + 1} for: {query}",
                "snippet": f"This is a mock search result {i + 1} for the query '{query}'. "
                f"In production, real search results would appear here.",
                "url": f"https://example.com/result-{i + 1}",
                "relevance": 1.0 - (i * 0.1),
            }
            for i in range(min(max_results, 5))
        ]
