from crawler.models import CdxSummary
from crawler.orphans import can_expand_archive, classify_orphan


def test_dead_live_url_with_archive_and_referrer_is_orphan():
    orphan, reasons = classify_orphan(False, CdxSummary(capture_count=3), archived_referrers=1)
    assert orphan is True
    assert reasons


def test_live_url_is_not_orphan_solely_because_cdx_exists():
    orphan, _ = classify_orphan(True, CdxSummary(capture_count=10), archived_referrers=2)
    assert orphan is False


def test_unknown_live_state_needs_archive_referrer_and_cdx():
    orphan, _ = classify_orphan(None, CdxSummary(capture_count=2), archived_referrers=1)
    assert orphan is True


def test_archive_recursion_bounds():
    assert can_expand_archive(0, 1) is True
    assert can_expand_archive(1, 1) is False
    assert can_expand_archive(2, 3) is True
    assert can_expand_archive(3, 3) is False
    assert can_expand_archive(0, 0) is False
