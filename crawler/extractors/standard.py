"""Standard-library HTML link extraction used before any Scrapling fallback."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin

from crawler.models import ExtractedLink


class _LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[ExtractedLink] = []
        self._href: str | None = None
        self._anchor_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        if href:
            self._href = href
            self._anchor_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            text = " ".join(data.split())
            if text:
                self._anchor_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        absolute = urljoin(self.base_url, self._href)
        anchor = " ".join(self._anchor_parts).strip()
        self.links.append(ExtractedLink(url=absolute, anchor_text=anchor, nearby_text=""))
        self._href = None
        self._anchor_parts = []


def extract_links_standard(html: str, base_url: str) -> list[ExtractedLink]:
    """Extract ordinary anchor links from HTML using the standard library."""
    if not html.strip():
        return []
    parser = _LinkParser(base_url)
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Legacy HTML can be malformed. Returning an empty list deliberately allows
        # the caller to escalate to the isolated Scrapling fallback.
        return []
    return parser.links
