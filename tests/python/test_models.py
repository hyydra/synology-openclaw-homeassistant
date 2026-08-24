from crawler.models import DiscoveryCandidate, DiscoveryEvidence, ScoreBreakdown


def test_candidate_defaults_are_safe():
    candidate = DiscoveryCandidate(
        url="https://example.hu/",
        domain="example.hu",
        discovery_source_url="https://pecs.hu/",
        discovery_method="outbound_link",
    )
    assert candidate.live_state == "unknown"
    assert candidate.orphan_evidence is False
    assert candidate.review_state == "new"


def test_score_breakdown_total_is_explicit():
    score = ScoreBreakdown(pecs=4, hungary=2, photo=3, orphan=1, archive=2, total=12, reasons=("x",))
    assert score.total == 12


def test_evidence_preserves_archived_referrer():
    evidence = DiscoveryEvidence(
        method="archive_link",
        referrer_url="https://example.hu/old",
        archive_referrer_url="https://web.archive.org/web/20010101000000/http://example.hu/old",
        archive_referrer_timestamp="20010101000000",
    )
    assert evidence.archive_referrer_timestamp == "20010101000000"
