"""
Web Search Tool using Tavily Search API with DuckDuckGo and Google News RSS fallback.
"""

import os
import urllib.request
import urllib.parse
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.services.web_search_context import fetch_ddg_search_context_sync, fetch_live_news_rss_sync


class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query (e.g. 'latest python 3.12 release notes')")
    max_results: int = Field(default=5, ge=1, le=10, description="Max number of search results to return")


class TavilyWebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Performs real-time web search for facts, news, and technical documentation."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = WebSearchInput

    def run(self, query: str, max_results: int = 5) -> ToolResult:
        api_key = os.environ.get("TAVILY_API_KEY", "").strip().strip('"').strip("'")

        # If Tavily API Key is available
        if api_key and not api_key.startswith("tvly-***"):
            try:
                url = "https://api.tavily.com/search"
                payload = json.dumps({
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results
                }).encode('utf-8')

                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    results = []
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", "")
                        })
                    if results:
                        return ToolResult(
                            tool_name=self.name,
                            success=True,
                            data={
                                "provider": "tavily",
                                "query": query,
                                "total_results": len(results),
                                "results": results
                            }
                        )
            except Exception:
                pass

        # DuckDuckGo HTML & RSS live fallback
        try:
            ddg_snippets = fetch_ddg_search_context_sync(query, max_results=max_results)
            news_snippets = ""
            if any(k in query.lower() for k in ["news", "headline", "breaking", "today", "latest", "score", "rate"]):
                news_snippets = fetch_live_news_rss_sync(query, max_items=max_results)

            combined = []
            if news_snippets:
                combined.append({
                    "title": "Live Google News RSS",
                    "url": "https://news.google.com",
                    "content": news_snippets
                })
            if ddg_snippets:
                combined.append({
                    "title": "DuckDuckGo Web Intelligence",
                    "url": "https://duckduckgo.com",
                    "content": ddg_snippets
                })

            if combined:
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    data={
                        "provider": "live_web_fallback",
                        "query": query,
                        "total_results": len(combined),
                        "results": combined
                    }
                )

            # DuckDuckGo Instant Answer API as ultimate fallback
            params = urllib.parse.urlencode({
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            })
            url = f"https://api.duckduckgo.com/?{params}"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Friday-AI-Assistant/1.0'}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                ddg_data = json.loads(response.read().decode('utf-8'))
                results = []
                abstract = ddg_data.get("AbstractText")
                if abstract:
                    results.append({
                        "title": ddg_data.get("Heading", query),
                        "url": ddg_data.get("AbstractURL", ""),
                        "content": abstract
                    })

                for topic in ddg_data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("Text", "")[:60],
                            "url": topic.get("FirstURL", ""),
                            "content": topic.get("Text", "")
                        })

                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    data={
                        "provider": "duckduckgo_fallback",
                        "query": query,
                        "total_results": len(results),
                        "results": results if results else [{"title": query, "url": "", "content": f"No instant abstract available for '{query}'"}]
                    }
                )
        except Exception as ex:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Web search failed: {str(ex)}",
                error_code="SEARCH_FAILED"
            )
