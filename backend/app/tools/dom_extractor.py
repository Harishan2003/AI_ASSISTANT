"""
DOM Snapshot Extractor for Autonomous Web Navigation Agent
Prunes raw HTML into a token-capped, indexed interactive tree.
"""

from typing import Dict, List, Tuple
from playwright.async_api import Page


EXTRACT_INTERACTIVE_JS = """
() => {
    const isVisible = (elem) => {
        if (!elem) return false;
        const style = window.getComputedStyle(elem);
        const rect = elem.getBoundingClientRect();
        return (
            style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            style.opacity !== '0' &&
            rect.width > 0 &&
            rect.height > 0
        );
    };

    // Gather actionable interactive elements
    const selector = 'button, a, input, select, textarea, [role="button"], [role="link"], [role="tab"]';
    const elements = Array.from(document.querySelectorAll(selector));

    const results = [];
    let idCounter = 0;

    for (const el of elements) {
        if (!isVisible(el)) continue;

        // Stop adding elements once we hit 60 to prevent TPM rate limits
        if (idCounter >= 60) break;

        el.setAttribute('data-agent-id', idCounter.toString());

        const tag = el.tagName.toLowerCase();
        let text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
        const placeholder = el.getAttribute('placeholder') || '';
        const ariaLabel = el.getAttribute('aria-label') || '';
        
        if (!text && ariaLabel) text = ariaLabel;
        if (!text && placeholder) text = `[${placeholder}]`;
        if (text.length > 50) text = text.substring(0, 50) + '...';

        results.push({
            id: idCounter,
            tag: tag,
            text: text
        });

        idCounter++;
    }

    return results;
}
"""


async def get_interactive_snapshot(page: Page) -> Tuple[str, int]:
    """Extracts a token-efficient interactive tree from the page."""
    try:
        elements: List[Dict] = await page.evaluate(EXTRACT_INTERACTIVE_JS)
    except Exception as e:
        return f"[Error extracting DOM tree: {e}]", 0

    lines = []
    for item in elements:
        element_id = item["id"]
        tag = item["tag"]
        text = item["text"]
        if text:
            lines.append(f"[{element_id}] <{tag}> {text}")

    snapshot_text = "\n".join(lines) if lines else "[No interactive elements found]"
    return snapshot_text, len(elements)