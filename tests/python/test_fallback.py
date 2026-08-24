from crawler.extractors.scrapling_fallback import should_use_scrapling
from crawler.extractors.standard import extract_links_standard


def test_standard_extractor_returns_absolute_link_and_text():
    html = "<html><body><p>Régi pécsi képek <a href='/galeria'>Fotógaléria</a> Uránváros</p></body></html>"
    links = extract_links_standard(html, "https://example.hu/old/")
    assert len(links) == 1
    assert links[0].url == "https://example.hu/galeria"
    assert "Fotógaléria" in links[0].anchor_text


def test_fallback_not_used_when_standard_links_exist():
    links = extract_links_standard("<html><a href='/x'>x</a></html>", "https://example.hu/")
    assert should_use_scrapling("<html><a href='/x'>x</a></html>", links) is False


def test_fallback_used_for_nonempty_html_with_zero_links():
    assert should_use_scrapling("<html><body>legacy content</body></html>", []) is True


def test_fallback_not_used_for_empty_html():
    assert should_use_scrapling("   ", []) is False
