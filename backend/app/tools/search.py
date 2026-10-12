"""
Web Search Tool

Uses Tavily for current internet information with automatic DuckDuckGo & Google News RSS fallback.
"""

from __future__ import annotations

import os
from datetime import datetime
import httpx

from app.core.config import settings
from app.services.web_search_context import fetch_ddg_search_context_sync, fetch_live_news_rss_sync


# ==================================================
# CURRENT INFORMATION KEYWORDS
# ==================================================

CURRENT_KEYWORDS = [
    "today",
    "current",
    "currently",
    "latest",
    "now",
    "right now",
    "live",
    "2026",
    "recent",
    "breaking",
    "news",
    "headlines",
]


# ==================================================
# SPECIAL CURRENT-DATA TOPICS
# ==================================================

PRICE_KEYWORDS = [
    "gold rate",
    "gold price",
    "silver rate",
    "silver price",
    "bitcoin price",
    "crypto price",
    "stock price",
    "share price",
    "exchange rate",
    "usd",
    "inr",
    "dollar rate",
]


# ==================================================
# SEARCH
# ==================================================

async def web_search(
    query: str,
    max_results: int | None = None,
) -> dict:

    if max_results is None:
        max_results = settings.tavily_max_results or 5

    original_query = query.strip()
    search_query = original_query

    now = datetime.now()
    cur_date_str = now.strftime("%B %Y")
    cur_year_str = now.strftime("%Y")

    # --------------------------------------------------
    # Detect current information request
    # --------------------------------------------------

    lower_query = original_query.lower()

    is_current = any(
        keyword in lower_query
        for keyword in CURRENT_KEYWORDS
    )

    is_price_query = any(
        keyword in lower_query
        for keyword in PRICE_KEYWORDS
    )

    if is_price_query:
        search_query = (
            f"{original_query} "
            f"India today {cur_date_str} "
            f"latest live rate"
        )
    elif is_current:
        search_query = (
            f"{original_query} "
            f"latest current information {cur_year_str}"
        )

    print(f"[WebSearch] Original query: {original_query}")
    print(f"[WebSearch] Search query: {search_query}")

    # --------------------------------------------------
    # Tavily request if configured
    # --------------------------------------------------
    tavily_key = settings.tavily_api_key or os.getenv("TAVILY_API_KEY", "")
    if tavily_key and not tavily_key.startswith("tvly-***"):
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": tavily_key,
                "query": search_query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": True,
                "include_raw_content": False,
            }

            async with httpx.AsyncClient(timeout=settings.timeout or 6.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    print(f"[WebSearch] Tavily results found: {len(results)}")
                    return {
                        "query": original_query,
                        "search_query": search_query,
                        "answer": data.get("answer"),
                        "results": results,
                    }
        except Exception as e:
            print(f"[WebSearch] Tavily search fallback triggered: {e}", flush=True)

    # --------------------------------------------------
    # High-Reliability DuckDuckGo & Live News Fallback
    # --------------------------------------------------
    ddg_context = fetch_ddg_search_context_sync(search_query, max_results=max_results)
    news_context = ""
    if any(k in lower_query for k in ["news", "headline", "today", "latest", "price", "score", "rate"]):
        news_context = fetch_live_news_rss_sync(original_query, max_items=max_results)

    combined_text = ""
    if news_context:
        combined_text += news_context + "\n\n"
    if ddg_context:
        combined_text += ddg_context

    results = []
    if ddg_context or news_context:
        results.append({
            "title": "Live Real-Time Web Intelligence",
            "url": "https://duckduckgo.com",
            "content": combined_text.strip()
        })

    return {
        "query": original_query,
        "search_query": search_query,
        "answer": combined_text.strip() if combined_text else f"Live web search data gathered for: {original_query}",
        "results": results,
    }