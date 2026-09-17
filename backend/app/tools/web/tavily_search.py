"""
Web Search Tool using Tavily Search API with DuckDuckGo fallback.
"""

import os
import urllib.request
import urllib.parse
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query (e.g. 'latest python 3.12 release notes')")
    max_results: int = Field(default=5, ge=1, le=10, description="Max number of search results to return")


class TavilyWebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Performs real-time web search for facts, news, and technical documentation."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = WebSearchInput

    def run(self, query: str, max_results: int = 5) -> ToolResult:
        api_key = os.environ.get("TAVILY_API_KEY")

        # If Tavily API Key is available
        if api_key:
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
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    results = []
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title"),
                            "url": item.get("url"),
                            "content": item.get("content")
                        })
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
            except Exception as e:
                # Proceed to fallback
                pass

        # DuckDuckGo HTML/Instant Answer fallback
        try:
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
            with urllib.request.urlopen(req, timeout=10) as response:
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
