"""Scrapling parser fallback for malformed or difficult legacy HTML."""

from __future__ import annotations

from urllib.parse import urljoin

from crawler.models import ExtractedLink


def should_use_scrapling(html: str, links: list[ExtractedLink]) -> bool:
    """Escalate only when non-empty HTML produced no useful standard links."""
    return bool(html.strip()) and not links


def extract_links_with_scrapling(html: str, base_url: str) -> list[ExtractedLink]:
    """Parse links with Scrapling while keeping the dependency isolated here."""
    if not html.strip():
        return []

    # Local import keeps the rest of the crawler independent from Scrapling internals.
    from scrapling.parser import Selector

    page = Selector(html)
    hrefs = page.css("a::attr(href)").getall()
    anchors = page.css("a::text").getall()

    results: list[ExtractedLink] = []
    for index, href in enumerate(hrefs):
        href_text = str(href).strip()
        if not href_text:
            continue
        anchor = str(anchors[index]).strip() if index < len(anchors) else ""
        results.append(ExtractedLink(url=urljoin(base_url, href_text), anchor_text=anchor, nearby_text=""))
    return results
