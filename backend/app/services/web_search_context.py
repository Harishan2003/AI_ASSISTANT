import asyncio
import email.utils
from datetime import datetime, timezone
import html
import json
import logging
import os
import re
import socket
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dotenv import load_dotenv
import httpx

logger = logging.getLogger("friday.web_search_context")
load_dotenv()


def sanitize_text(text: str) -> str:
    """Normalizes Unicode characters, strips unencodable emojis, and replaces invisible whitespace."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    # Strip combining diacritical marks (Mn) that cause charmap encode errors on Windows cp1252
    stripped = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    # Replace narrow no-break space, non-breaking space, zero-width spaces with regular space
    cleaned = re.sub(r'[\u202f\u00a0\u2000-\u200b\u2028\u2029\u2011]', ' ', stripped)
    # Strip non-BMP characters (like emojis) that crash cp1252 consoles on Windows
    cleaned = re.sub(r'[^\u0000-\uFFFF]', '', cleaned)
    # Safely replace phonetic or exotic Unicode that cannot be encoded in cp1252
    try:
        cleaned.encode("cp1252")
    except UnicodeEncodeError:
        cleaned = cleaned.encode("cp1252", errors="replace").decode("cp1252")
    return cleaned


def extract_urls_from_text(text: str) -> list[str]:
    """Extracts all valid http/https/www URLs from query or text, preserving balanced parentheses."""
    if not text:
        return []
    pattern = r'(?:https?://|www\.)[^\s<>"\'`]+'
    matches = re.findall(pattern, str(text), flags=re.IGNORECASE)
    cleaned = []
    for u in matches:
        u = u.rstrip(".,;:!?'\"`")
        if u.endswith(")") and u.count("(") < u.count(")"):
            u = u.rstrip(")")
        if u.lower().startswith("www."):
            u = "https://" + u
        if u not in cleaned:
            cleaned.append(u)
    return cleaned


def fetch_webpage_content(url: str, max_chars: int = 3500) -> dict:
    """
    Downloads and extracts clean readable text, title, and metadata from a web URL.
    Uses realistic browser headers with robust timeout and fallback handling.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # 0. Check if URL is a Video Link (YouTube, Shorts, Direct Video)
    try:
        from app.services.video_analysis_service import analyze_video_url
        video_info = analyze_video_url(url, max_chars=max_chars)
        if video_info and video_info.get("success"):
            return {
                "url": url,
                "title": video_info.get("title") or url,
                "content": video_info.get("content") or "",
                "success": True,
                "is_video": True
            }
    except Exception as e:
        logger.debug(f"[WebContext] Video analysis check note: {e}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=7.0) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            raw_html = resp.read().decode(charset, errors="ignore")

        # Extract title
        title_m = re.search(r'<title[^>]*>(.*?)</title>', raw_html, re.IGNORECASE | re.DOTALL)
        title = html.unescape(title_m.group(1).strip()) if title_m else url

        # Extract meta description if present
        meta_desc = ""
        desc_m = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
        if desc_m:
            meta_desc = html.unescape(desc_m.group(1).strip())

        # Clean non-content HTML elements
        cleaned = re.sub(r'<!--.*?-->', '', raw_html, flags=re.DOTALL)
        cleaned = re.sub(r'<(script|style|svg|noscript|nav|footer|header|aside|form)[^>]*>.*?</\1>', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        cleaned = html.unescape(cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = sanitize_text(cleaned)

        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "\n...[Content truncated for length]..."

        if meta_desc and meta_desc not in cleaned:
            cleaned = f"Summary: {meta_desc}\n\n{cleaned}"

        return {
            "url": url,
            "title": title,
            "content": cleaned,
            "success": bool(cleaned)
        }
    except Exception as e:
        logger.warning(f"[WebContext] Failed to fetch webpage content for {url}: {e}")
        return {
            "url": url,
            "title": url,
            "content": f"Failed to retrieve content from {url} ({e}).",
            "success": False
        }


def clean_to_search_keywords(raw_query: str) -> str:
    """
    Extracts high-signal search terms from conversational queries and voice prompts.
    """
    s = sanitize_text(raw_query)
    s = re.sub(r'^(?:user|friday)\s*(?:🔊\s*Speak)?\s*[:\-\s]*', '', s, flags=re.IGNORECASE).strip()

    # If query contains explicit parenthetical reference e.g. "(regarding C. Joseph Vijay)"
    ref_m = re.search(r'\((?:regarding|referring\s+to|about|for)\s+([^\)]+)\)', s, flags=re.IGNORECASE)
    if ref_m:
        ent = ref_m.group(1).strip()
        aspect = re.sub(r'\([^\)]+\)', '', s).strip()
        aspect = re.sub(r'^(?:what\s+is|what\s+are|who\s+is|who\s+are|tell\s+me|tell\s+about)\s+(?:his|her|their|the)?\s*', '', aspect, flags=re.IGNORECASE).strip()
        return f"{ent} {aspect}".strip()

    # Strip conversational inquiry prefixes
    s = re.sub(r'^(?:is\s+there\s+(?:anything|any\s+news|any\s+update|any\s+updates|any)?\s*(?:happen(?:ing)?\s+in|happened\s+in|about|regarding)?|did\s+anything\s+happen\s+in|what\s+happened\s+in|what\s+is\s+happening\s+in|any\s+(?:updates?|news)\s+(?:on|about|in))\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^(?:where\s+did|where\s+was|where\s+is|where\s+were|when\s+did|when\s+was|when\s+is|how\s+many|how\s+much|what\s+is|whats\s+is|what\'s\s+is|what\'s|whats|which\s+is|who\s+is|who\s+was|who\s+are|why\s+is|how\s+is|tell\s+me\s+about|tell\s+me|tell\s+about|show\s+me|explain|describe|give\s+me|find|search\s+for|search)\s+(?:the|a|an|potential|specific|key|notable|current|latest|his|her|their)?\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\b(?:as\s+been|has\s+been)\b', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\b(?:featured prominently in their discussions|remain at the heart of|issue regarding|throughout|right now|currently)\b', ' ', s, flags=re.IGNORECASE)
    s = re.sub(r'[^\w\s\d\-]', ' ', s)
    s = ' '.join(s.split())
    return s or raw_query


def _format_pubdate(pub_date_str: str) -> str:
    """Parses RFC-822 / standard RSS pubDate into clean human-readable string."""
    if not pub_date_str:
        return "Recent"
    try:
        parsed_tuple = email.utils.parsedate_tz(pub_date_str)
        if parsed_tuple:
            dt = datetime.fromtimestamp(email.utils.mktime_tz(parsed_tuple), tz=timezone.utc)
            return dt.strftime("%b %d, %Y %H:%M UTC")
    except Exception:
        pass
    # Clean up raw string if parse fails
    clean_date = re.sub(r'\s*\+0000|\s*GMT', '', pub_date_str).strip()
    return clean_date or "Recent"


def fetch_ddg_search_context_sync(query: str, max_results: int = 6) -> str:
    """
    Direct zero-quota DuckDuckGo web search scraper for instant real-time ground truth.
    Uses HTML and Lite fallback endpoints.
    """
    search_candidates = []
    kw = clean_to_search_keywords(query)
    if kw:
        search_candidates.append(kw)
    raw_clean = re.sub(r'^(?:user|friday)\s*(?:🔊\s*Speak)?\s*[:\-\s]*', '', query, flags=re.IGNORECASE).strip()
    raw_clean = re.sub(r'[^\w\s\d\-]', ' ', raw_clean)
    raw_clean = ' '.join(raw_clean.split())
    if raw_clean and raw_clean not in search_candidates:
        search_candidates.append(raw_clean)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    for term in search_candidates:
        # Endpoint 1: html.duckduckgo.com
        try:
            url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(term)
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html, flags=re.DOTALL)
                titles = re.findall(r'<a[^>]*class="result__url"[^>]*>(.*?)</a>', html, flags=re.DOTALL)
                if not titles:
                    titles = re.findall(r'<a[^>]*class="result__title"[^>]*>(.*?)</a>', html, flags=re.DOTALL)
                combined = []
                for i in range(min(len(titles), len(snippets), max_results)):
                    t = re.sub(r'<.*?>', '', titles[i]).strip()
                    s = re.sub(r'<.*?>', '', snippets[i]).strip()
                    s = re.sub(r'&#x27;', "'", s)
                    s = re.sub(r'&quot;', '"', s)
                    s = re.sub(r'&amp;', '&', s)
                    if s:
                        combined.append(f"- **{t}**: {s}")
                if combined:
                    return sanitize_text("### Live Real-Time Web Intelligence Snippets:\n" + "\n".join(combined))
        except Exception:
            pass

        # Endpoint 2: lite.duckduckgo.com fallback
        try:
            url = 'https://lite.duckduckgo.com/lite/'
            data = urllib.parse.urlencode({'q': term}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                td_snippets = re.findall(r'<td class="result-snippet">\s*(.*?)\s*</td>', html, flags=re.DOTALL)
                links = re.findall(r'<a[^>]*class="result-link"[^>]*>(.*?)</a>', html, flags=re.DOTALL)
                combined = []
                for i in range(min(len(links), len(td_snippets), max_results)):
                    t = re.sub(r'<.*?>', '', links[i]).strip()
                    s = re.sub(r'<.*?>', '', td_snippets[i]).strip()
                    s = re.sub(r'&#x27;', "'", s)
                    s = re.sub(r'&quot;', '"', s)
                    s = re.sub(r'&amp;', '&', s)
                    if s:
                        combined.append(f"- **{t}**: {s}")
                if combined:
                    return sanitize_text("### Live Real-Time Web Intelligence Snippets:\n" + "\n".join(combined))
        except Exception:
            pass

    return ""


async def fetch_ddg_search_context(query: str, max_results: int = 6) -> str:
    """Asynchronous wrapper for DuckDuckGo web search scraper."""
    return await asyncio.to_thread(fetch_ddg_search_context_sync, query, max_results)


async def fetch_tavily_search_context(query: str) -> str:
    """
    Performs search via Tavily API with automatic error handling when quota exceeded.
    """
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip().strip('"').strip("'")
    if not tavily_key or tavily_key.startswith("tvly-***"):
        return ""

    search_kw = clean_to_search_keywords(query)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": search_kw,
                    "search_depth": "advanced",
                    "include_answer": True,
                    "max_results": 5
                }
            )
            if response.status_code == 200:
                data = response.json()
                sections = []
                if data.get("answer"):
                    sections.append(f"### Web Search Answer Summary:\n{data['answer']}")
                results = data.get("results", [])
                if results:
                    snippets = [f"- **{r.get('title', 'Source')}**: {r.get('content', '')}" for r in results if r.get('content')]
                    if snippets:
                        sections.append("### Detailed Web Citations & News Data:\n" + "\n".join(snippets))
                return "\n\n".join(sections)
    except Exception as e:
        print(f"[WebContext Notice]: Tavily search skipped: {e}", flush=True)
    return ""


async def fetch_wikipedia_context(query: str) -> str:
    """
    Searches official Wikipedia API for verified entity background.
    """
    def _sync_wiki() -> str:
        candidates = []
        
        # Check explicit reference e.g. (regarding X) or (referring to X)
        ref_m = re.search(r'\((?:regarding|referring\s+to|about|for)\s+([^\)]+)\)', query, flags=re.IGNORECASE)
        if ref_m:
            candidates.append(ref_m.group(1).strip())

        # Check "who is X" or "tell me about X"
        who_m = re.search(r'^(?:who\s+is|tell\s+me\s+about|about\s+actor|about\s+person|profile\s+of)\s+([^\?]+)', query, flags=re.IGNORECASE)
        if who_m:
            cand = who_m.group(1).strip()
            cand = re.sub(r'\b(?:actor|director|politician|leader)\b', '', cand, flags=re.IGNORECASE).strip()
            if cand:
                candidates.append(cand)

        # Clean search keywords
        kw = clean_to_search_keywords(query)
        if kw and kw not in candidates:
            candidates.append(kw)

        # Raw query without punctuation
        raw_clean = re.sub(r'[^\w\s\d\-]', ' ', query).strip()
        if raw_clean and raw_clean not in candidates:
            candidates.append(raw_clean)

        headers = {"User-Agent": "FridayAIAssistant/1.0 (contact@harishan.ai)"}

        for term in candidates:
            try:
                encoded_term = urllib.parse.quote(term)
                search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_term}&format=json"
                req = urllib.request.Request(search_url, headers=headers)
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    search_results = data.get("query", {}).get("search", [])
                    if search_results:
                        top_title = search_results[0].get("title")
                        page_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={urllib.parse.quote(top_title)}&format=json"
                        req_page = urllib.request.Request(page_url, headers=headers)
                        with urllib.request.urlopen(req_page, timeout=3.0) as page_resp:
                            page_data = json.loads(page_resp.read().decode("utf-8"))
                            pages = page_data.get("query", {}).get("pages", {})
                            for page_id, page_info in pages.items():
                                if "extract" in page_info and page_info["extract"].strip():
                                    return sanitize_text(f"Wikipedia Article Extract [{top_title}]: {page_info['extract'][:1500]}")
            except Exception:
                continue
        return ""

    try:
        return await asyncio.to_thread(_sync_wiki)
    except Exception:
        return ""


def _parse_rss_xml(xml_content: bytes, max_items: int = 12) -> list[str]:
    """Helper to parse RSS XML feed items into clean headline strings."""
    import xml.etree.ElementTree as ET
    headlines = []
    try:
        tree = ET.fromstring(xml_content)
        items = tree.findall('.//item')
        for item in items[:max_items]:
            title_elem = item.find('title')
            pub_elem = item.find('pubDate')
            desc_elem = item.find('description')
            source_elem = item.find('source')

            if title_elem is not None and title_elem.text:
                t = sanitize_text(title_elem.text).strip()
                # Clean HTML tags in title if any
                t = re.sub(r'<.*?>', '', t).strip()

                # Source publisher name
                source_name = ""
                if source_elem is not None and source_elem.text:
                    source_name = sanitize_text(source_elem.text).strip()
                elif " - " in t:
                    parts = t.rsplit(" - ", 1)
                    if len(parts[1]) < 35:
                        t = parts[0].strip()
                        source_name = parts[1].strip()

                # PubDate formatting
                pub_raw = pub_elem.text.strip() if (pub_elem is not None and pub_elem.text) else ""
                pub_str = _format_pubdate(pub_raw)

                # Snippet cleaning
                desc_text = ""
                if desc_elem is not None and desc_elem.text:
                    clean_desc = re.sub(r'<.*?>', '', desc_elem.text).strip()
                    clean_desc = re.sub(r'&nbsp;', ' ', clean_desc).strip()
                    clean_desc = re.sub(r'&#39;', "'", clean_desc)
                    clean_desc = re.sub(r'&quot;', '"', clean_desc)
                    clean_desc = re.sub(r'&amp;', '&', clean_desc)
                    clean_desc = sanitize_text(clean_desc)
                    if clean_desc and clean_desc != t:
                        desc_text = f" - {clean_desc[:140]}"

                source_prefix = f" [{source_name}]" if source_name else ""
                headlines.append(f"- **{t}**{source_prefix} ({pub_str}){desc_text}")
    except Exception as e:
        print(f"[WebContext RSS Parse Notice]: {e}", flush=True)
    return headlines


def fetch_live_news_rss_sync(query: str, max_items: int = 12) -> str:
    """
    Fetches real-time live breaking news headlines directly from Google News RSS feed,
    dynamically categorizing by topic (World, Tech, Business, Sports, Science, Entertainment, Nation, Local).
    Includes intelligent fallback feeds to ensure up-to-date knowledge.
    """
    try:
        q_lower = query.lower()
        clean = re.sub(r'^(?:user|friday)\s*(?:🔊\s*Speak)?\s*[:\-\s]*', '', query, flags=re.IGNORECASE).strip()
        # Fix concatenated STT voice tokens
        clean = re.sub(r'\btodaysnews\b', 'today news', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\btodaynews\b', 'today news', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\btamilnadu\b', 'tamil nadu', clean, flags=re.IGNORECASE)

        # Strip conversational questions, greetings, and request prefixes
        clean = re.sub(r'^(?:what is|what are|tell me|give me|show me|can you tell me|can you give me|explain|describe|please|share|get)\s+', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\b(?:infos?|information|details?|summary|overview|insights?|brief|feed|rss|stories|story|events?|affairs?|trending)\b', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\b(?:like|about|regarding|on|for|in|from|with|some|any|the|a|an|few|recent|currently|current|breaking|top|latest|today\'s|todays|today|now|general)\b', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\b(?:news|headlines?|updates?|bulletin)\b', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'^(?:in|from|of|about|for|to|on)\s+', '', clean, flags=re.IGNORECASE).strip()
        clean = ' '.join(clean.split()).strip()

        tokens = set(re.findall(r'\b[a-z0-9\-]+\b', q_lower))

        # Multi-source RSS feed discovery
        urls_to_try = []

        is_tn_query = any(k in q_lower for k in ["tamil nadu", "tamilnadu", "chennai", "madurai", "coimbatore", "tn news"])
        if is_tn_query:
            urls_to_try.append('https://news.google.com/rss/search?q=Tamil+Nadu+news&hl=en-IN&gl=IN&ceid=IN:en')
            urls_to_try.append('https://www.thehindu.com/news/national/tamil-nadu/feeder/default.rss')
            urls_to_try.append('https://timesofindia.indiatimes.com/rssfeeds/2950623.cms')
            urls_to_try.append('https://www.thehindu.com/news/cities/chennai/feeder/default.rss')

        # If user has a specific query, search for it in Google News first
        if clean and len(clean) >= 2 and not is_tn_query:
            urls_to_try.append(f'https://news.google.com/rss/search?q={urllib.parse.quote(clean + " when:7d")}&hl=en-IN&gl=IN&ceid=IN:en')
            urls_to_try.append(f'https://news.google.com/rss/search?q={urllib.parse.quote(clean)}&hl=en-IN&gl=IN&ceid=IN:en')

        # Generic topic feeds ONLY if general category news requested
        if tokens.intersection({"world", "international", "global", "foreign", "geopolitics"}) and (not clean or clean in {"world", "news", "international"}):
            urls_to_try.append('https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-IN&gl=IN&ceid=IN:en')
            urls_to_try.append('http://feeds.bbci.co.uk/news/world/rss.xml')
        elif tokens.intersection({"entertainment", "cinema", "movie", "film", "bollywood", "hollywood", "kollywood", "tollywood", "actor", "actress", "celebrity"}):
            urls_to_try.append('https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-IN&gl=IN&ceid=IN:en')
        elif tokens.intersection({"tech", "technology", "ai", "gadget", "software"}):
            urls_to_try.append('https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en')
            urls_to_try.append('http://feeds.bbci.co.uk/news/technology/rss.xml')
        elif tokens.intersection({"business", "finance", "stock", "stocks", "market", "economy"}):
            urls_to_try.append('https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en')
            urls_to_try.append('http://feeds.bbci.co.uk/news/business/rss.xml')
        elif tokens.intersection({"sport", "sports", "cricket", "football", "ipl"}):
            urls_to_try.append('https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-IN&gl=IN&ceid=IN:en')
            urls_to_try.append('http://feeds.bbci.co.uk/sport/rss.xml')
        elif tokens.intersection({"science", "space", "nasa", "isro"}):
            urls_to_try.append('https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-IN&gl=IN&ceid=IN:en')
        elif tokens.intersection({"india", "national", "nation"}):
            urls_to_try.append('https://news.google.com/rss/headlines/section/topic/NATION?hl=en-IN&gl=IN&ceid=IN:en')
            urls_to_try.append('https://www.thehindu.com/news/national/feeder/default.rss')
            urls_to_try.append('https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms')

        # Robust fallbacks for top headlines
        urls_to_try.append('https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en')
        urls_to_try.append('https://timesofindia.indiatimes.com/rssfeedstopstories.cms')
        urls_to_try.append('https://feeds.feedburner.com/ndtvnews-top-stories')

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }

        for url in urls_to_try:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    xml_content = resp.read()
                    headlines = _parse_rss_xml(xml_content, max_items=max_items)
                    if headlines:
                        source_label = "Tamil Nadu & Regional Feeds" if is_tn_query else "Live Breaking News"
                        return f"### Real-Time Live Headlines ({source_label}):\n" + "\n".join(headlines)
            except Exception:
                continue

        # Secondary live search fallback if RSS feeds were unreachable
        fallback_term = "Tamil Nadu news today latest" if is_tn_query else (clean or "India breaking news today")
        try:
            ddg_url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(fallback_term)
            req = urllib.request.Request(ddg_url, headers=headers)
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                html_txt = resp.read().decode('utf-8', errors='ignore')
                snips = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html_txt, flags=re.DOTALL)
                titles = re.findall(r'<a[^>]*class="result__title"[^>]*>(.*?)</a>', html_txt, flags=re.DOTALL)
                combined = []
                for i in range(min(len(titles), len(snips), 8)):
                    t_str = re.sub(r'<.*?>', '', titles[i]).strip()
                    s_str = re.sub(r'<.*?>', '', snips[i]).strip()
                    if t_str and s_str:
                        combined.append(f"- **{t_str}**: {s_str}")
                if combined:
                    return "### Real-Time Live News Reports (Web News Feed):\n" + "\n".join(combined)
        except Exception:
            pass

    except Exception as e:
        print(f"[WebContext News RSS Notice]: {e}", flush=True)
    return ""


async def fetch_live_news_rss(query: str, max_items: int = 12) -> str:
    """Asynchronous wrapper for Google News RSS scraper."""
    return await asyncio.to_thread(fetch_live_news_rss_sync, query, max_items)


async def gather_all_web_context(query: str) -> str:
    """
    Fetches verified real-time web context using Google News RSS, Tavily Search API,
    DuckDuckGo search, Wikipedia, and direct URL scraping concurrently.
    """
    try:
        # 1. Directly fetch user-provided URLs if present in query
        user_urls = extract_urls_from_text(query)
        url_contexts = []
        if user_urls:
            url_tasks = [asyncio.to_thread(fetch_webpage_content, u) for u in user_urls[:2]]
            fetched_pages = await asyncio.gather(*url_tasks, return_exceptions=True)
            for page in fetched_pages:
                if isinstance(page, dict) and page.get("content"):
                    url_contexts.append(
                        f"--- Verified Content from User-Provided Link ({page['url']}) ---\n"
                        f"Page Title: {page['title']}\n"
                        f"Extracted Page Content:\n{page['content']}"
                    )
            # If we successfully extracted content from the user's direct links (e.g. video transcripts or articles),
            # return immediately without slow general search delays.
            if url_contexts:
                return sanitize_text("\n\n".join(url_contexts).strip())

        q_lower = query.lower()
        is_news_query = any(k in q_lower for k in [
            "news", "headline", "headlines", "breaking", "what happened today", "current events",
            "latest updates", "updates on", "what's happening", "whats happening", "today's", "todays",
            "today", "yesterday", "world", "international", "global", "sports", "cricket",
            "tech", "technology", "business", "market", "sensex", "nifty", "entertainment",
            "cinema", "movie", "film", "politics", "gold rate", "stock price", "who won",
            "score", "match", "current", "tamilnadu", "tamil nadu", "chennai", "bulletin", "affairs"
        ])

        async def _safe_news():
            if not is_news_query:
                return ""
            try:
                return await asyncio.wait_for(fetch_live_news_rss(query), timeout=5.0)
            except Exception:
                return ""

        async def _safe_wiki():
            try:
                return await asyncio.wait_for(fetch_wikipedia_context(query), timeout=4.0)
            except Exception:
                return ""

        async def _safe_ddg():
            try:
                return await asyncio.wait_for(fetch_ddg_search_context(query, max_results=6), timeout=4.5)
            except Exception:
                return ""

        async def _safe_tavily():
            try:
                return await asyncio.wait_for(fetch_tavily_search_context(query), timeout=4.5)
            except Exception:
                return ""

        news_res, wiki_res, ddg_res, tavily_res = await asyncio.gather(
            _safe_news(),
            _safe_wiki(),
            _safe_ddg(),
            _safe_tavily(),
            return_exceptions=True
        )

        parts = []
        if url_contexts:
            parts.extend(url_contexts)
        if isinstance(ddg_res, str) and ddg_res:
            parts.append(f"--- Live Web Search Intelligence ---\n{ddg_res}")
        if isinstance(tavily_res, str) and tavily_res:
            parts.append(tavily_res)
        if isinstance(wiki_res, str) and wiki_res:
            parts.append(f"--- Wikipedia Knowledge Extract ---\n{wiki_res}")
        if isinstance(news_res, str) and news_res:
            parts.append(news_res)

        result = "\n\n".join(parts).strip()
        max_limit = 4500 if url_contexts else 3500
        if len(result) > max_limit:
            result = result[:max_limit] + "\n[...additional web context truncated for speed...]"
        return sanitize_text(result)
    except Exception as e:
        print(f"[WebContext Notice]: Web context gather error: {e}", flush=True)
        return ""
