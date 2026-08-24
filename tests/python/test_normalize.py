from crawler.normalize import normalize_domain, normalize_url


def test_normalize_url_removes_fragment_and_normalizes_host():
    assert normalize_url("HTTP://WWW.Example.HU:80/a/../b#x") == "http://www.example.hu/b"


def test_normalize_domain_accepts_hu_domain():
    assert normalize_domain("https://Fotozz.hu/path") == "fotozz.hu"


def test_normalize_url_rejects_non_http_scheme():
    assert normalize_url("javascript:alert(1)") is None


def test_normalize_url_preserves_unusual_percent_encoded_path():
    assert normalize_url("https://example.hu/%EF%BF%BC/gallery") == "https://example.hu/%EF%BF%BC/gallery"
