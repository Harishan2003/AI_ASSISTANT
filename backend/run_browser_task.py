import asyncio
import os
import sys
from functools import wraps
from dotenv import load_dotenv
from groq import AsyncGroq
from app.agents.browser_agent import BrowserAgent

# 1. Enforce Proactor Event Loop for Playwright on Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport

        def silence_event_loop_closed(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    if "Event loop is closed" in str(e) or isinstance(e, RuntimeError):
                        return
                    raise
            return wrapper

        _ProactorBasePipeTransport.__del__ = silence_event_loop_closed(_ProactorBasePipeTransport.__del__)
    except Exception:
        pass

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found in environment or .env file.")

groq_client = AsyncGroq(api_key=api_key)


async def llm_caller(messages):
    await asyncio.sleep(0.5)
    
    # Do not enforce JSON schema mode via API to prevent model tool-call confusion
    response = await groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=messages,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


async def main():
    agent = BrowserAgent(model_caller_func=llm_caller)
    task_goal = "Find the latest release version on Python.org and return the version number."
    
    result = await agent.run_task(
        user_goal=task_goal,
        start_url="https://www.python.org",
        max_steps=6
    )
    print("\n==========================================")
    print(f"FINAL RESULT: {result}")
    print("==========================================")
    
    await asyncio.sleep(0.2)


if __name__ == "__main__":
    asyncio.run(main())