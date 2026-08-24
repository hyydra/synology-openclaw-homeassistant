"""SQLite persistence for discovery candidates and their evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from crawler.models import CdxSummary, DiscoveryCandidate, DiscoveryEvidence, ScoreBreakdown


def open_discovery_db(path: str | Path) -> sqlite3.Connection:
    """Open the discovery database and enable safe SQLite defaults."""
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 5000")
    return db


def ensure_schema(db: sqlite3.Connection) -> None:
    """Create discovery tables without modifying the production archive schema."""
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS discovery_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            domain TEXT NOT NULL,
            discovery_source_url TEXT NOT NULL,
            discovery_method TEXT NOT NULL,
            live_state TEXT NOT NULL DEFAULT 'unknown',
            orphan_evidence INTEGER NOT NULL DEFAULT 0,
            anchor_text TEXT NOT NULL DEFAULT '',
            nearby_text TEXT NOT NULL DEFAULT '',
            review_state TEXT NOT NULL DEFAULT 'new',
            score_pecs INTEGER NOT NULL DEFAULT 0,
            score_hungary INTEGER NOT NULL DEFAULT 0,
            score_photo INTEGER NOT NULL DEFAULT 0,
            score_orphan INTEGER NOT NULL DEFAULT 0,
            score_archive INTEGER NOT NULL DEFAULT 0,
            score_total INTEGER NOT NULL DEFAULT 0,
            score_reasons TEXT NOT NULL DEFAULT '',
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS discovery_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            referrer_url TEXT NOT NULL,
            archive_referrer_url TEXT NOT NULL DEFAULT '',
            archive_referrer_timestamp TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(candidate_id) REFERENCES discovery_candidates(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS discovery_cdx (
            candidate_id INTEGER PRIMARY KEY,
            capture_count INTEGER NOT NULL DEFAULT 0,
            first_timestamp TEXT NOT NULL DEFAULT '',
            last_timestamp TEXT NOT NULL DEFAULT '',
            representative_archive_url TEXT NOT NULL DEFAULT '',
            checked_at TEXT NOT NULL,
            FOREIGN KEY(candidate_id) REFERENCES discovery_candidates(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS discovery_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL UNIQUE,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL DEFAULT 'running'
        );
        """
    )
    db.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_candidate(db: sqlite3.Connection, candidate: DiscoveryCandidate, score: ScoreBreakdown) -> int:
    """Insert or refresh a candidate while keeping its stable row id."""
    now = _now()
    db.execute(
        """
        INSERT INTO discovery_candidates (
            url, domain, discovery_source_url, discovery_method, live_state,
            orphan_evidence, anchor_text, nearby_text, review_state,
            score_pecs, score_hungary, score_photo, score_orphan, score_archive,
            score_total, score_reasons, first_seen_at, last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            domain = excluded.domain,
            discovery_source_url = excluded.discovery_source_url,
            discovery_method = excluded.discovery_method,
            live_state = excluded.live_state,
            orphan_evidence = excluded.orphan_evidence,
            anchor_text = excluded.anchor_text,
            nearby_text = excluded.nearby_text,
            score_pecs = excluded.score_pecs,
            score_hungary = excluded.score_hungary,
            score_photo = excluded.score_photo,
            score_orphan = excluded.score_orphan,
            score_archive = excluded.score_archive,
            score_total = excluded.score_total,
            score_reasons = excluded.score_reasons,
            last_seen_at = excluded.last_seen_at
        """,
        (
            candidate.url,
            candidate.domain,
            candidate.discovery_source_url,
            candidate.discovery_method,
            candidate.live_state,
            1 if candidate.orphan_evidence else 0,
            candidate.anchor_text,
            candidate.nearby_text,
            candidate.review_state,
            score.pecs,
            score.hungary,
            score.photo,
            score.orphan,
            score.archive,
            score.total,
            " | ".join(score.reasons),
            now,
            now,
        ),
    )
    db.commit()
    row = db.execute("SELECT id FROM discovery_candidates WHERE url = ?", (candidate.url,)).fetchone()
    if row is None:
        raise RuntimeError("candidate upsert did not produce a row")
    return int(row["id"])


def record_evidence(db: sqlite3.Connection, candidate_id: int, evidence: DiscoveryEvidence) -> int:
    """Append one independent discovery-evidence record."""
    cursor = db.execute(
        """
        INSERT INTO discovery_evidence (
            candidate_id, method, referrer_url, archive_referrer_url,
            archive_referrer_timestamp, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            candidate_id,
            evidence.method,
            evidence.referrer_url,
            evidence.archive_referrer_url,
            evidence.archive_referrer_timestamp,
            _now(),
        ),
    )
    db.commit()
    return int(cursor.lastrowid)


def record_cdx(db: sqlite3.Connection, candidate_id: int, summary: CdxSummary) -> None:
    """Store the latest CDX summary for a candidate."""
    db.execute(
        """
        INSERT INTO discovery_cdx (
            candidate_id, capture_count, first_timestamp, last_timestamp,
            representative_archive_url, checked_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(candidate_id) DO UPDATE SET
            capture_count = excluded.capture_count,
            first_timestamp = excluded.first_timestamp,
            last_timestamp = excluded.last_timestamp,
            representative_archive_url = excluded.representative_archive_url,
            checked_at = excluded.checked_at
        """,
        (
            candidate_id,
            summary.capture_count,
            summary.first_timestamp,
            summary.last_timestamp,
            summary.representative_archive_url,
            _now(),
        ),
    )
    db.commit()
