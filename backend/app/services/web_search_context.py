"""
Friday AI Assistant - Web Search & External Context Service
Fetches real-time web context from Tavily Search API, verified Wikipedia articles, and Google News RSS feeds.
"""

import asyncio
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
import feedparser
import httpx


async def fetch_tavily_search_context(query: str) -> str:
    """
    What does this function do:
    Performs an asynchronous web search via Tavily API and compiles top web results
    with titles and contents to inject real-time internet knowledge into Friday's LLM context.
    
    Args:
        query (str): The search query string.
        
    Returns:
        str: Formatted string containing bulleted titles and content snippets, or empty string.
    """
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip().strip('"').strip("'")
    if not tavily_key:
        return ""
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": 3
                }
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                context_texts = [f"- {r.get('title')}: {r.get('content')}" for r in results]
                return "\n".join(context_texts)
    except (urllib.error.URLError, socket.timeout, Exception) as e:
        print(f"[WebContext Notice]: Tavily search skipped: {e}", flush=True)
    return ""


async def fetch_wikipedia_context(query: str) -> str:
    """
    What does this function do:
    Searches the official Wikipedia API for factual entity definitions and returns
    the verified introductory extract of the top matched encyclopedia article.
    
    Args:
        query (str): The entity or concept to search for.
        
    Returns:
        str: Extracted Wikipedia introduction paragraph or empty string if not found.
    """
    def _sync_wiki() -> str:
        try:
            clean_term = re.sub(
                r"^(who is|who was|what is|what are|tell me about|tell more about|explain|describe)\s+",
                "",
                query,
                flags=re.IGNORECASE
            ).strip()
            search_term = clean_term or query
                
            encoded_query = urllib.parse.quote(search_term)
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_query}&format=json"
            headers = {"User-Agent": "FridayAIAssistant/1.0"}
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                search_results = data.get("query", {}).get("search", [])
                if search_results:
                    top_title = search_results[0].get("title")
                    page_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={urllib.parse.quote(top_title)}&format=json"
                    req_page = urllib.request.Request(page_url, headers=headers)
                    with urllib.request.urlopen(req_page, timeout=2.5) as page_resp:
                        page_data = json.loads(page_resp.read().decode("utf-8"))
                        pages = page_data.get("query", {}).get("pages", {})
                        for page_id, page_info in pages.items():
                            if "extract" in page_info and page_info["extract"].strip():
                                return f"Wikipedia Verified Article [{top_title}]: {page_info['extract'][:1500]}"
        except Exception:
            pass
        return ""

    try:
        return await asyncio.to_thread(_sync_wiki)
    except Exception:
        return ""


async def fetch_live_news_rss(query: str) -> str:
    """
    What does this function do:
    Fetches real-time RSS headlines from Google News search feed matching the user query
    to give Friday up-to-the-minute awareness of ongoing current events and breaking news.
    
    Args:
        query (str): The search keywords for recent news.
        
    Returns:
        str: Formatted list of news headlines and publication times.
    """
    try:
        encoded_query = urllib.parse.quote_plus(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(
            rss_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        xml_data = await asyncio.to_thread(
            lambda: urllib.request.urlopen(req, timeout=5.0).read()
        )
        feed = await asyncio.to_thread(feedparser.parse, xml_data)
        entries = feed.entries[:3]
        if entries:
            headlines = [f"- {entry.title} ({getattr(entry, 'published', 'Recent')})" for entry in entries]
            return "--- Live News RSS Feeds ---\n" + "\n".join(headlines)
    except Exception as e:
        print(f"[WebContext Notice]: RSS Fetch skipped: {e}", flush=True)
    return ""


async def gather_all_web_context(query: str) -> str:
    """
    What does this function do:
    Concurrently runs Tavily, Wikipedia, and Google News RSS fetchers, aggregating all
    external intelligence into a single structured context block for Friday's reasoning engine.
    
    Args:
        query (str): The user query requiring external verification.
        
    Returns:
        str: Aggregated multi-source external context string.
    """
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                fetch_tavily_search_context(query),
                fetch_wikipedia_context(query),
                fetch_live_news_rss(query),
                return_exceptions=True
            ),
            timeout=4.0
        )
        tavily_res = results[0] if isinstance(results[0], str) else ""
        wiki_res = results[1] if isinstance(results[1], str) else ""
        rss_res = results[2] if isinstance(results[2], str) else ""
        
        parts = []
        if tavily_res:
            parts.append(f"--- Tavily Web Search ---\n{tavily_res}")
        if wiki_res:
            parts.append(f"--- Wikipedia Knowledge ---\n{wiki_res}")
        if rss_res:
            parts.append(rss_res)
        return "\n\n".join(parts).strip()
    except Exception as e:
        print(f"[WebContext Notice]: Web context gather timeout or error: {e}", flush=True)
        return ""
