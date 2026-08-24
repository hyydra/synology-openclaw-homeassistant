from pathlib import Path

from crawler.models import CdxSummary, DiscoveryCandidate, DiscoveryEvidence
from crawler.scoring import score_candidate
from crawler.storage import ensure_schema, open_discovery_db, record_cdx, record_evidence, upsert_candidate


def make_candidate() -> DiscoveryCandidate:
    return DiscoveryCandidate(
        url="https://dead.hu/galeria/pecs",
        domain="dead.hu",
        discovery_source_url="https://pecs.hu/regi-linkek",
        discovery_method="archive_link",
        live_state="dead",
        orphan_evidence=True,
        anchor_text="Pecs foto",
        nearby_text="Regi kepek",
    )


def test_schema_and_candidate_dedupe(tmp_path: Path):
    db = open_discovery_db(tmp_path / "discovery.sqlite")
    ensure_schema(db)
    c = make_candidate()
    score = score_candidate(c)
    first = upsert_candidate(db, c, score)
    second = upsert_candidate(db, c, score)
    assert first == second
    assert db.execute("SELECT COUNT(*) FROM discovery_candidates").fetchone()[0] == 1


def test_evidence_accumulates_for_same_candidate(tmp_path: Path):
    db = open_discovery_db(tmp_path / "discovery.sqlite")
    ensure_schema(db)
    c = make_candidate()
    candidate_id = upsert_candidate(db, c, score_candidate(c))
    one = DiscoveryEvidence("archive_link", "https://pecs.hu/a", "https://web.archive.org/a", "20010101000000")
    two = DiscoveryEvidence("directory", "https://pecs.hu/b", "https://web.archive.org/b", "20020101000000")
    record_evidence(db, candidate_id, one)
    record_evidence(db, candidate_id, two)
    assert db.execute("SELECT COUNT(*) FROM discovery_evidence").fetchone()[0] == 2


def test_cdx_summary_persists(tmp_path: Path):
    db = open_discovery_db(tmp_path / "discovery.sqlite")
    ensure_schema(db)
    c = make_candidate()
    candidate_id = upsert_candidate(db, c, score_candidate(c))
    record_cdx(db, candidate_id, CdxSummary(4, "20010101000000", "20051231000000", "https://web.archive.org/web/20010101000000/https://dead.hu/"))
    row = db.execute("SELECT capture_count, first_timestamp, last_timestamp FROM discovery_cdx WHERE candidate_id = ?", (candidate_id,)).fetchone()
    assert tuple(row) == (4, "20010101000000", "20051231000000")
