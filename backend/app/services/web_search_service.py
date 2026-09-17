"""
Fast Web Search Service
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class WebSearchService:

    BASE_URL = "https://api.tavily.com"

    async def search(
        self,
        query: str,
    ) -> dict[str, Any]:

        if not settings.tavily_api_key:
            raise RuntimeError(
                "TAVILY_API_KEY is not configured."
            )

        payload = {
            "query": query,
            "search_depth": settings.tavily_search_depth,
            "max_results": settings.tavily_max_results,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }

        headers = {
            "Authorization": (
                f"Bearer {settings.tavily_api_key}"
            ),
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(
            10.0,
            connect=5.0,
        )

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            response = await client.post(
                f"{self.BASE_URL}/search",
                headers=headers,
                json=payload,
            )

            response.raise_for_status()

            return response.json()


web_search_service = WebSearchService()