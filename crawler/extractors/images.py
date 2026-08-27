"""Photo/image discovery and classification, tuned for 1990s-era web pages.

Ported from the hungarian-1990s-domain-explorer project's crawler.ts, which
was built specifically to distinguish real photos from the decorative cruft
common on archived 90s pages: under-construction GIFs, webring badges, hit
counters, and tiny nav icons.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

IMAGE_EXTENSION_RE = re.compile(r"\.(jpg|jpeg|png|gif|webp|svg|bmp|ico|avif)(/.*)?$")
FORMAT_RE = re.compile(r"\.(jpg|jpeg|png|gif|webp|svg|bmp|ico|avif)$")

_VINTAGE_ASSET_TERMS = (
    "underconstruction", "construction", "counter", "netscape", "explorer",
    "webring", "button", "badge", "vintage", "retro", "bestviewed",
)
_LOGO_TERMS = ("logo", "icon", "favicon", "brand", "emblem", "cimer", "jelveny")
_BANNER_TERMS = ("banner", "header", "fejlec", "slider")
_SKIP_SRC_TERMS = ("1x1", "spacer.gif", "blank.gif", "pixel.gif", "clear.gif", "analytics", "tracker")


@dataclass
class CrawledPhoto:
    id: str
    src: str
    original_src: str
    alt: str
    source_url: str
    source_domain: str
    image_type: str
    format: str
    page_title: str = ""
    title: str = ""
    caption: str = ""
    context_text: str = ""
    width: int | None = None
    height: int | None = None
    is_wayback_archive: bool = False


@dataclass
class PageCrawlResult:
    photos: list[CrawledPhoto] = field(default_factory=list)
    discovered_links: list[str] = field(default_factory=list)
    page_title: str = ""


def is_image_url(url: str) -> bool:
    if not url:
        return False
    clean = url.split("?")[0].lower()
    return bool(IMAGE_EXTENSION_RE.search(clean))


def detect_format(url: str) -> str:
    if not url:
        return "unknown"
    clean = url.split("?")[0].lower()
    match = FORMAT_RE.search(clean)
    if match:
        fmt = match.group(1)
        return "jpg" if fmt == "jpeg" else fmt
    if "format=png" in url or "image/png" in url:
        return "png"
    if "format=jpg" in url or "image/jpeg" in url:
        return "jpg"
    if "format=webp" in url or "image/webp" in url:
        return "webp"
    if "format=gif" in url or "image/gif" in url:
        return "gif"
    return "jpg"


def classify_image(
    src: str,
    alt: str = "",
    width: int | None = None,
    height: int | None = None,
    image_format: str = "",
    context: str = "",
) -> str:
    """Classify an image as photo / gif_animation / logo_icon / banner_graphic / vintage_asset."""
    all_text = f"{src.lower()} {alt.lower()} {context.lower()}"

    small_gif = image_format == "gif" and width and height and width < 90 and height < 35
    if any(term in all_text for term in _VINTAGE_ASSET_TERMS) or small_gif:
        return "vintage_asset"

    if image_format == "gif" or src.lower().endswith(".gif"):
        return "gif_animation"

    small_square = width and height and width <= 100 and height <= 100
    if image_format in ("svg", "ico") or any(term in all_text for term in _LOGO_TERMS) or small_square:
        return "logo_icon"

    wide_short = width and height and width >= 600 and height <= 250
    if any(term in all_text for term in _BANNER_TERMS) or wide_short:
        return "banner_graphic"

    return "photo"


def resolve_absolute_url(raw_url: str | None, base_url: str) -> str | None:
    if not raw_url:
        return None
    trimmed = raw_url.strip()

    if trimmed.startswith("data:"):
        if len(trimmed) < 200 or "data:image/svg+xml;utf8,<svg" in trimmed:
            return None
        return trimmed

    if trimmed.startswith(("javascript:", "#", "mailto:")):
        return None

    try:
        absolute = urljoin(base_url, trimmed)
        scheme = urlparse(absolute).scheme
        if scheme not in ("http", "https"):
            return None
        return absolute
    except ValueError:
        return None


def _strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        parsed = int(value)
        return parsed if parsed > 0 else None
    except ValueError:
        return None


def crawl_page_images(
    html: str,
    page_url: str,
    domain: str,
    is_wayback: bool = False,
) -> PageCrawlResult:
    """Extract classified photos and same-domain links from one page's HTML."""
    result = PageCrawlResult()
    seen_srcs: set[str] = set()

    if not html.strip():
        return result

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    h1_tag = soup.find("h1")
    page_title = (title_tag.get_text(strip=True) if title_tag else "") or \
        (h1_tag.get_text(strip=True) if h1_tag else "") or domain
    result.page_title = page_title

    base_tag = soup.find("base", href=True)
    effective_base = resolve_absolute_url(base_tag["href"], page_url) if base_tag else None
    effective_base = effective_base or page_url

    def add_photo(src: str, original: str, alt: str, **kwargs) -> None:
        photo_format = kwargs.pop("format", None) or detect_format(src)
        image_type = kwargs.pop("image_type", None) or classify_image(
            src, alt, kwargs.get("width"), kwargs.get("height"), photo_format, kwargs.get("context_text", "")
        )
        result.photos.append(CrawledPhoto(
            id=f"photo_{domain}_{len(result.photos) + 1}_{uuid.uuid4().hex[:5]}",
            src=src,
            original_src=original,
            alt=alt,
            source_url=page_url,
            source_domain=domain,
            image_type=image_type,
            format=photo_format,
            page_title=page_title,
            is_wayback_archive=is_wayback,
            **kwargs,
        ))

    # 1. Open Graph / Twitter meta images
    for selector, attr in (
        ("meta[property='og:image']", "content"),
        ("meta[name='twitter:image']", "content"),
        ("link[rel='image_src']", "href"),
    ):
        tag = soup.select_one(selector)
        if not tag:
            continue
        raw = tag.get(attr)
        absolute = resolve_absolute_url(raw, effective_base)
        if absolute and absolute not in seen_srcs:
            seen_srcs.add(absolute)
            og_alt_tag = soup.select_one("meta[property='og:image:alt']")
            add_photo(
                absolute, raw,
                alt=(og_alt_tag.get("content") if og_alt_tag else "") or page_title or f"{domain} Featured Photo",
                title=page_title,
                image_type="photo",
            )

    # 2. <img> tags
    for img in soup.find_all("img"):
        raw_src = (
            img.get("src") or img.get("data-src") or img.get("data-lazy-src") or img.get("data-original")
        )
        if not raw_src and img.get("srcset"):
            raw_src = img["srcset"].split(",")[0].strip().split(" ")[0]
        if not raw_src:
            continue

        absolute = resolve_absolute_url(raw_src, effective_base)
        if not absolute or absolute in seen_srcs:
            continue

        lower = absolute.lower()
        if any(term in lower for term in _SKIP_SRC_TERMS):
            continue
        seen_srcs.add(absolute)

        alt = (img.get("alt") or "").strip()
        img_title = (img.get("title") or "").strip()
        width = _parse_int(img.get("width"))
        height = _parse_int(img.get("height"))

        caption = ""
        figure = img.find_parent("figure")
        if figure:
            figcaption = figure.find("figcaption")
            if figcaption:
                caption = figcaption.get_text(strip=True)

        context_text = ""
        parent_text = img.parent.get_text(strip=True) if img.parent else ""
        if parent_text and 5 < len(parent_text) < 200 and parent_text != alt:
            context_text = parent_text
        else:
            prev_heading = img.find_previous(("h1", "h2", "h3", "h4", "p"))
            if prev_heading:
                text = prev_heading.get_text(strip=True)
                if text and len(text) < 150:
                    context_text = text

        add_photo(
            absolute, raw_src,
            alt=alt or img_title or f"{domain} Web Asset",
            title=img_title or alt,
            caption=caption,
            context_text=context_text,
            width=width,
            height=height,
        )

    # 3. <picture><source> tags
    for source in soup.select("picture source"):
        srcset = source.get("srcset")
        if not srcset:
            continue
        first_candidate = srcset.split(",")[0].strip().split(" ")[0]
        absolute = resolve_absolute_url(first_candidate, effective_base)
        if not absolute or absolute in seen_srcs:
            continue
        seen_srcs.add(absolute)
        add_photo(absolute, first_candidate, alt=f"{domain} Graphic")

    # 4. <a> tags: direct image links, and same-domain links for further crawling
    domain_clean = _strip_www(domain.lower())
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if is_image_url(href):
            absolute = resolve_absolute_url(href, effective_base)
            if absolute and absolute not in seen_srcs:
                seen_srcs.add(absolute)
                link_text = link.get_text(strip=True) or link.get("title") or f"{domain} Linked Photo"
                add_photo(absolute, href, alt=link_text, title=link_text)
            continue

        absolute_link = resolve_absolute_url(href, effective_base)
        if not absolute_link:
            continue
        try:
            link_host = urlparse(absolute_link).hostname or ""
        except ValueError:
            continue
        link_host_clean = _strip_www(link_host.lower())
        if (
            link_host_clean == domain_clean
            and "#" not in absolute_link
            and not is_image_url(absolute_link)
            and not absolute_link.endswith((".pdf", ".zip", ".exe"))
        ):
            result.discovered_links.append(absolute_link)

    return result
