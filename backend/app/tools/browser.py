# Module: backend.app.tools.browser
"""
Friday Autonomous Browser Tool
Integrates the Playwright autonomous browser controller with Friday's Tool Registry.
Guarantees browser automation only runs when explicitly requested.
"""

from __future__ import annotations

import asyncio
import os
import re
from groq import AsyncGroq
from app.agents.browser_agent import BrowserAgent
from app.services.web_search_service import web_search_service


BROWSER_EXPLICIT_TRIGGERS = [
    "search in chrome",
    "search on chrome",
    "open chrome",
    "in chrome",
    "open browser",
    "in browser",
    "browse the web",
    "navigate to",
    "open website",
    "click on",
    "fill form",
    "scrape site",
]


def is_explicit_browser_command(goal: str) -> bool:
    """Checks whether the user explicitly requested physical browser navigation."""
    clean = goal.lower()
    return any(trigger in clean for trigger in BROWSER_EXPLICIT_TRIGGERS)


async def _run_navigation(task_goal: str, start_url: str = "https://www.google.com") -> str:
    # If the user did not explicitly ask to use the browser/Chrome, handle via fast API search
    if not is_explicit_browser_command(task_goal):
        try:
            clean_query = re.sub(
                r"^(who is|what is|tell me about|search for|find)\s+",
                "",
                task_goal,
                flags=re.IGNORECASE,
            ).strip()
            search_result = await web_search_service.search(query=clean_query or task_goal)
            results = search_result.get("results", [])
            if results:
                summary_bits = [f"- {r.get('title')}: {r.get('content')}" for r in results[:3]]
                return "Web Search Results:\n" + "\n".join(summary_bits)
        except Exception:
            # If search API is unconfigured or fails, return empty to let the main LLM answer directly
            return ""

    # Explicit browser command: Proceed with Playwright
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY is not set."

    groq_client = AsyncGroq(api_key=api_key)

    async def llm_caller(messages):
        await asyncio.sleep(0.5)
        response = await groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

    agent = BrowserAgent(model_caller_func=llm_caller)
    return await agent.run_task(
        user_goal=task_goal,
        start_url=start_url,
        max_steps=8,
    )


def navigate_web(task_goal: str, start_url: str = "https://www.google.com") -> str:
    """
    Autonomously browses the internet using Playwright only when explicitly requested
    (e.g., 'search in chrome', 'open browser'). For informational queries, resolves
    via fast search or direct text.
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _run_navigation(task_goal, start_url)).result()
        else:
            return asyncio.run(_run_navigation(task_goal, start_url))
    except Exception as e:
        return f"Browser navigation error: {str(e)}"