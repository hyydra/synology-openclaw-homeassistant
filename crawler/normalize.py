"""Normalize discovered HTTP URLs without destroying archival path evidence."""

from __future__ import annotations

import posixpath
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str | None:
    """Return a canonical HTTP(S) URL or ``None`` for unsupported input."""
    value = url.strip()
    if not value:
        return None

    try:
        parts = urlsplit(value)
    except ValueError:
        return None

    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        return None
    if not parts.hostname:
        return None

    host = parts.hostname.lower().rstrip(".")
    if not host:
        return None

    try:
        port = parts.port
    except ValueError:
        return None

    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = host if port is None or default_port else f"{host}:{port}"

    # Normalize only structural dot segments. Percent-encoded bytes are left untouched
    # because malformed-looking legacy paths can still contain valuable archived pages.
    raw_path = parts.path or "/"
    normalized_path = posixpath.normpath(raw_path)
    if raw_path.endswith("/") and not normalized_path.endswith("/"):
        normalized_path += "/"
    if not normalized_path.startswith("/"):
        normalized_path = "/" + normalized_path
    if normalized_path == "//":
        normalized_path = "/"

    return urlunsplit((scheme, netloc, normalized_path, parts.query, ""))


def normalize_domain(url_or_domain: str) -> str | None:
    """Normalize a URL or bare host to its lowercase domain name."""
    value = url_or_domain.strip()
    if not value:
        return None

    parsed = urlsplit(value if "://" in value else f"https://{value}")
    host = parsed.hostname
    if not host:
        return None
    return host.lower().rstrip(".") or None
