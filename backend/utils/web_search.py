"""
Web search utility with graceful offline fallback.

Prefers Tavily (if TAVILY_API_KEY is set) via tavily-python client.
Returns a list of simple snippets suitable to feed into RAG synthesis.
"""

import os
from typing import List, Dict

from logger.custom_logger import CustomLogger


class WebSearch:
    def __init__(self):
        self.log = CustomLogger().get_logger(__name__)
        self.api_key = os.getenv("TAVILY_API_KEY")
        self._tavily = None
        if self.api_key:
            try:
                from tavily import TavilyClient  # type: ignore
                self._tavily = TavilyClient(api_key=self.api_key)
                self.log.info("Tavily client initialized")
            except Exception as e:
                self.log.warning("Failed to init Tavily; using offline fallback", error=str(e))
                self._tavily = None

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform a web search and return a list of {title, url, content} snippets.
        Falls back to empty list when no provider is available.
        """
        if not query:
            return []
        try:
            if self._tavily:
                res = self._tavily.search(query=query, max_results=max_results)
                results = []
                for item in res.get("results", [])[:max_results]:
                    results.append({
                        "title": item.get("title") or "",
                        "url": item.get("url") or "",
                        "content": item.get("content") or item.get("snippet") or "",
                    })
                self.log.info("Web search completed", count=len(results))
                return results
        except Exception as e:
            self.log.warning("Web search failed; offline mode", error=str(e))
        return []
