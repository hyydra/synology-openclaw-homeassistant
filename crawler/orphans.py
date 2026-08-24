"""Rules for classifying historically recoverable orphaned sites."""

from __future__ import annotations

from crawler.models import CdxSummary


def classify_orphan(
    live_ok: bool | None,
    cdx: CdxSummary,
    archived_referrers: int,
) -> tuple[bool, tuple[str, ...]]:
    """Classify orphan status from live reachability and independent archive evidence."""
    if live_ok is True:
        return False, ()

    reasons: list[str] = []
    if live_ok is False:
        reasons.append("live URL is unreachable")
    elif live_ok is None:
        reasons.append("live state is unknown")

    if cdx.capture_count > 0:
        reasons.append("Wayback CDX contains historical captures")
    if archived_referrers > 0:
        reasons.append(f"referenced by {archived_referrers} archived source page(s)")

    # A dead URL needs archive proof. An unknown live state needs both archive captures
    # and at least one archived referrer so transient network failures do not create noise.
    orphan = cdx.capture_count > 0 and archived_referrers > 0
    return orphan, tuple(reasons if orphan else ())


def can_expand_archive(depth: int, max_archive_depth: int) -> bool:
    """Return whether another archived-link expansion step is allowed."""
    if max_archive_depth < 0 or max_archive_depth > 3:
        return False
    if depth < 0:
        return False
    return depth < max_archive_depth
