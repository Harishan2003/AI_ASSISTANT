"""
Browser automation tools using Playwright (with urllib/requests fallback).
Supports URL navigation, page text extraction, and web searching.
"""

import urllib.request
import json
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class BrowserNavigateInput(BaseModel):
    url: str = Field(..., description="The URL to navigate to (e.g. 'https://www.wikipedia.org')")
    extract_text: bool = Field(default=True, description="Whether to extract and return textual content from the page")
    max_length: int = Field(default=4000, description="Max characters of text content to return")


class BrowserNavigateTool(BaseTool):
    name: str = "browser_navigate"
    description: str = "Navigates to a webpage and extracts text content, title, and metadata."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    args_schema = BrowserNavigateInput

    def run(self, url: str, extract_text: bool = True, max_length: int = 4000) -> ToolResult:
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Try Playwright if available
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=15000, wait_until="domcontentloaded")
                title = page.title()
                content = ""
                if extract_text:
                    content = page.inner_text("body") or ""
                    if len(content) > max_length:
                        content = content[:max_length] + f"\n... [Content truncated, total {len(content)} chars]"
                browser.close()

                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    data={
                        "url": url,
                        "title": title,
                        "content": content,
                        "engine": "playwright"
                    }
                )
        except Exception:
            # Fallback to standard HTTP GET
            try:
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                    
                    # Simple title regex
                    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
                    title = title_match.group(1).strip() if title_match else url

                    # Clean simple tags
                    text = re.sub(r'<script.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
                    text = re.sub(r'<style.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = ' '.join(text.split())

                    if len(text) > max_length:
                        text = text[:max_length] + f"\n... [Content truncated, total {len(text)} chars]"

                    return ToolResult(
                        tool_name=self.name,
                        success=True,
                        data={
                            "url": url,
                            "title": title,
                            "content": text,
                            "engine": "http_fallback"
                        }
                    )
            except Exception as ex:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=f"Failed to fetch '{url}': {str(ex)}",
                    error_code="BROWSER_FETCH_FAILED"
                )
