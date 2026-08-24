"""Typed data structures shared by discovery crawler components."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DiscoveryCandidate:
    url: str
    domain: str
    discovery_source_url: str
    discovery_method: str
    live_state: str = "unknown"
    orphan_evidence: bool = False
    anchor_text: str = ""
    nearby_text: str = ""
    review_state: str = "new"


@dataclass(slots=True)
class DiscoveryEvidence:
    method: str
    referrer_url: str
    archive_referrer_url: str = ""
    archive_referrer_timestamp: str = ""


@dataclass(slots=True)
class ExtractedLink:
    url: str
    anchor_text: str = ""
    nearby_text: str = ""


@dataclass(slots=True)
class CdxSummary:
    capture_count: int = 0
    first_timestamp: str = ""
    last_timestamp: str = ""
    representative_archive_url: str = ""


@dataclass(slots=True)
class ScoreBreakdown:
    pecs: int
    hungary: int
    photo: int
    orphan: int
    archive: int
    total: int
    reasons: tuple[str, ...] = ()
