"""
Web Search Tool

Uses Tavily for current internet information.
"""

from __future__ import annotations

import httpx

from app.core.config import settings


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

    if not settings.tavily_api_key:
        raise RuntimeError(
            "TAVILY_API_KEY is not configured."
        )

    if max_results is None:
        max_results = settings.tavily_max_results

    original_query = query.strip()

    search_query = original_query

    # --------------------------------------------------
    # Detect current information request
    # --------------------------------------------------

    lower_query = original_query.lower()

    is_current = any(
        keyword in lower_query
        for keyword in CURRENT_KEYWORDS
    )

    # --------------------------------------------------
    # Improve price searches
    # --------------------------------------------------

    is_price_query = any(
        keyword in lower_query
        for keyword in PRICE_KEYWORDS
    )

    if is_price_query:

        search_query = (
            f"{original_query} "
            f"India today August 2026 "
            f"latest live rate"
        )

    elif is_current:

        search_query = (
            f"{original_query} "
            f"latest current information 2026"
        )

    print(
        f"[WebSearch] Original query: {original_query}"
    )

    print(
        f"[WebSearch] Search query: {search_query}"
    )

    # --------------------------------------------------
    # Tavily request
    # --------------------------------------------------

    url = "https://api.tavily.com/search"

    payload = {
        "api_key": settings.tavily_api_key,
        "query": search_query,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": True,
        "include_raw_content": True,
    }

    async with httpx.AsyncClient(
        timeout=settings.timeout
    ) as client:

        response = await client.post(
            url,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

    # --------------------------------------------------
    # Normalize response
    # --------------------------------------------------

    results = data.get("results", [])

    print(
        f"[WebSearch] Results found: {len(results)}"
    )

    return {
        "query": original_query,
        "search_query": search_query,
        "answer": data.get("answer"),
        "results": results,
    }