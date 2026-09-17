"""
Friday Autonomous Browser Tool
Integrates the Playwright autonomous browser controller with Friday's Tool Registry.
"""

from __future__ import annotations

import asyncio
import os
from groq import AsyncGroq
from app.agents.browser_agent import BrowserAgent


async def _run_navigation(task_goal: str, start_url: str = "https://www.google.com") -> str:
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
    Autonomously browses the internet using Playwright to interact with pages,
    click links, type into inputs, and extract live information.

    Args:
        task_goal: The specific goal or query to accomplish on the web.
        start_url: The starting webpage URL (defaults to Google).
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