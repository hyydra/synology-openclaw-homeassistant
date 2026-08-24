"""Structured JSONL logging utilities for crawler diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

_SECRET_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "cookie",
    "authorization",
    "session",
    "api_key",
    "apikey",
    "auth",
)


def _is_secret_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return any(fragment in normalized for fragment in _SECRET_FRAGMENTS)


def sanitize_context(value: Any) -> Any:
    """Recursively redact secret-bearing mapping keys before serialization."""
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            text_key = str(key)
            sanitized[text_key] = "[REDACTED]" if _is_secret_key(text_key) else sanitize_context(item)
        return sanitized
    if isinstance(value, (list, tuple, set)):
        return [sanitize_context(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def write_log(event: str, level: str, context: dict, path: Path, run_id: str) -> None:
    """Append one sanitized JSON object to the discovery log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.lower(),
        "run_id": run_id,
        "event": event,
        "context": sanitize_context(context),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
