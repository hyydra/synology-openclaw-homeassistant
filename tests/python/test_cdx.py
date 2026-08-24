import json

from crawler.cdx import build_cdx_url, enumerate_archived_urls, parse_cdx_rows


def sample_payload():
    return json.dumps([
        ["timestamp", "original", "statuscode", "mimetype", "digest", "length"],
        ["20010101000000", "http://dead.hu/pecs", "200", "text/html", "A", "100"],
        ["20030505000000", "http://dead.hu/galeria", "200", "text/html", "B", "200"],
        ["bad", "", "200", "text/html", "C", "1"],
    ])


def test_parse_cdx_rows_summarizes_valid_captures():
    summary = parse_cdx_rows(sample_payload())
    assert summary.capture_count == 2
    assert summary.first_timestamp == "20010101000000"
    assert summary.last_timestamp == "20030505000000"
    assert "20010101000000" in summary.representative_archive_url


def test_build_cdx_url_contains_urlkey_collapse_and_bound():
    url = build_cdx_url("dead.hu/*", 50)
    assert "collapse=urlkey" in url
    assert "limit=50" in url


def test_cdx_limit_is_clamped_to_1_200():
    assert "limit=1" in build_cdx_url("dead.hu/*", 0)
    assert "limit=200" in build_cdx_url("dead.hu/*", 999)


def test_enumerate_archived_urls_uses_fixture_client():
    calls = []

    def client(url: str) -> str:
        calls.append(url)
        return sample_payload()

    urls = enumerate_archived_urls("dead.hu/*", client, limit=20)
    assert urls == ["http://dead.hu/pecs", "http://dead.hu/galeria"]
    assert calls
