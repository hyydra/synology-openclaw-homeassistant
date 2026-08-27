"""Bounded Wayback CDX helpers for archive validation and URL enumeration."""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.parse import urlencode

from crawler.models import CdxSummary


def build_cdx_url(target: str, limit: int = 200) -> str:
    """Build a conservative CDX request with URL-level deduplication."""
    bounded = max(1, min(200, int(limit)))
    query = urlencode({
        "url": target,
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,digest,length",
        "collapse": "urlkey",
        "limit": str(bounded),
    })
    return (
        "https://web.archive.org/cdx/search/cdx?"
        + query
        + "&filter=statuscode%3A200&filter=mimetype%3Atext%2Fhtml"
    )


def _valid_rows(payload: str) -> list[list[str]]:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(decoded, list) or len(decoded) < 2:
        return []

    rows: list[list[str]] = []
    for raw in decoded[1:]:
        if not isinstance(raw, list) or len(raw) < 2:
            continue
        timestamp = str(raw[0])
        original = str(raw[1])
        if len(timestamp) != 14 or not timestamp.isdigit() or not original:
            continue
        rows.append([str(item) for item in raw])
    return rows


def parse_cdx_rows(payload: str) -> CdxSummary:
    """Summarize valid CDX rows while ignoring malformed records."""
    rows = _valid_rows(payload)
    if not rows:
        return CdxSummary()
    timestamps = sorted(row[0] for row in rows)
    first_timestamp = timestamps[0]
    last_timestamp = timestamps[-1]
    first_original = next(row[1] for row in rows if row[0] == first_timestamp)
    representative = f"https://web.archive.org/web/{first_timestamp}/{first_original}"
    return CdxSummary(
        capture_count=len(rows),
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
        representative_archive_url=representative,
    )


def validate_candidate(target: str, client: Callable[[str], str], limit: int = 200) -> CdxSummary:
    """Fetch and summarize one bounded CDX query using an injected client."""
    return parse_cdx_rows(client(build_cdx_url(target, limit)))


def enumerate_archived_urls(target: str, client: Callable[[str], str], limit: int = 200) -> list[str]:
    """Return unique archived originals from one bounded CDX query."""
    payload = client(build_cdx_url(target, limit))
    seen: set[str] = set()
    results: list[str] = []
    for row in _valid_rows(payload):
        original = row[1]
        if original in seen:
            continue
        seen.add(original)
        results.append(original)
    return results


def list_captures(target: str, client: Callable[[str], str], limit: int = 200) -> list[tuple[str, str]]:
    """Return unique (timestamp, original_url) pairs from one bounded CDX query."""
    payload = client(build_cdx_url(target, limit))
    seen: set[str] = set()
    results: list[tuple[str, str]] = []
    for row in _valid_rows(payload):
        timestamp, original = row[0], row[1]
        if original in seen:
            continue
        seen.add(original)
        results.append((timestamp, original))
    return results
