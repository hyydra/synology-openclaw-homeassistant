"""Deterministic, explainable scoring for historical source candidates."""

from __future__ import annotations

import unicodedata

from crawler.models import DiscoveryCandidate, DiscoveryEvidence, ScoreBreakdown

PECS_TERMS = (
    "pecs", "baranya", "zsolnay", "uranvaros", "mecsek", "tettye",
    "szechenyi ter", "kiraly utca",
)
PHOTO_TERMS = ("foto", "photo", "galeria", "gallery", "album", "kep", "images", "image")
HUNGARIAN_TERMS = ("regi", "kepek", "varos", "utca", "ter", "magyar", "baranya")


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _contains_any(haystack: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term in haystack]


def score_candidate(
    candidate: DiscoveryCandidate,
    evidence: list[DiscoveryEvidence] | None = None,
) -> ScoreBreakdown:
    """Score one candidate using transparent keyword and archive-evidence rules."""
    evidence = evidence or []
    text = _fold(" ".join((candidate.url, candidate.domain, candidate.anchor_text, candidate.nearby_text)))

    pecs_hits = _contains_any(text, PECS_TERMS)
    photo_hits = _contains_any(text, PHOTO_TERMS)
    hungarian_hits = _contains_any(text, HUNGARIAN_TERMS)

    pecs = min(12, len(pecs_hits) * 3)
    photo = min(10, len(photo_hits) * 2)
    hungary = 3 if candidate.domain.lower().endswith(".hu") else 0
    hungary += min(4, len(hungarian_hits))

    archived_referrers = sum(1 for item in evidence if item.archive_referrer_url)
    orphan = 0
    if candidate.orphan_evidence:
        orphan += 2
    if candidate.live_state == "dead":
        orphan += 2
    orphan += min(4, archived_referrers * 2)

    archive = min(4, archived_referrers)

    reasons: list[str] = []
    if pecs_hits:
        reasons.append("Pécs/Baranya signals: " + ", ".join(pecs_hits))
    if photo_hits:
        reasons.append("Photo/gallery signals: " + ", ".join(photo_hits))
    if candidate.domain.lower().endswith(".hu"):
        reasons.append("Hungarian .hu domain")
    if hungarian_hits:
        reasons.append("Hungarian text signals: " + ", ".join(hungarian_hits))
    if orphan:
        reasons.append("Orphan/archive evidence")

    total = pecs + hungary + photo + orphan + archive
    return ScoreBreakdown(
        pecs=pecs,
        hungary=hungary,
        photo=photo,
        orphan=orphan,
        archive=archive,
        total=total,
        reasons=tuple(reasons),
    )
