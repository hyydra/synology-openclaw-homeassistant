from crawler.models import DiscoveryCandidate, DiscoveryEvidence
from crawler.scoring import score_candidate


def candidate(url: str, anchor: str = "", nearby: str = "", **kwargs) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        url=url,
        domain=kwargs.pop("domain", ""),
        discovery_source_url="https://pecs.hu/",
        discovery_method=kwargs.pop("discovery_method", "outbound_link"),
        anchor_text=anchor,
        nearby_text=nearby,
        **kwargs,
    )


def test_pecs_photo_candidate_scores_above_generic_page():
    high = score_candidate(candidate(
        "https://example.hu/galeria/pecs-2004",
        "Pécsi fotógaléria",
        "Régi képek Uránvárosból",
        domain="example.hu",
    ))
    low = score_candidate(candidate("https://example.com/about", "About", "Company profile", domain="example.com"))
    assert high.total > low.total
    assert high.pecs > 0
    assert high.photo > 0
    assert high.hungary > 0


def test_unaccented_hungarian_variants_score():
    result = score_candidate(candidate(
        "https://x.hu/foto/pecs",
        "Pecs foto",
        "Szechenyi ter",
        domain="x.hu",
    ))
    assert result.pecs > 0
    assert result.photo > 0


def test_orphan_archive_evidence_adds_score_without_auto_approval():
    c = candidate(
        "https://dead.hu/galeria/pecs",
        "Pecs foto",
        "Regi kepek",
        domain="dead.hu",
        live_state="dead",
        orphan_evidence=True,
    )
    evidence = [DiscoveryEvidence(
        method="archive_link",
        referrer_url="https://pecs.hu/regi-linkek",
        archive_referrer_url="https://web.archive.org/web/20020101000000/http://pecs.hu/regi-linkek",
        archive_referrer_timestamp="20020101000000",
    )]
    result = score_candidate(c, evidence)
    assert result.orphan > 0
    assert result.total > 0
    assert c.review_state == "new"
