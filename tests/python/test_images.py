from crawler.extractors.images import classify_image, crawl_page_images, detect_format, is_image_url


def test_is_image_url():
    assert is_image_url("https://example.com/photo.jpg")
    assert is_image_url("https://example.com/photo.PNG?x=1")
    assert not is_image_url("https://example.com/page.html")


def test_detect_format():
    assert detect_format("photo.jpeg") == "jpg"
    assert detect_format("photo.gif") == "gif"
    assert detect_format("unknown") == "jpg"


def test_classify_vintage_asset():
    assert classify_image("underconstruction.gif", "") == "vintage_asset"
    assert classify_image("badge.gif", "webring member") == "vintage_asset"


def test_classify_gif_animation():
    assert classify_image("dance.gif", "dancing baby", image_format="gif") == "gif_animation"


def test_classify_logo():
    assert classify_image("logo.svg", "", image_format="svg") == "logo_icon"
    assert classify_image("x.png", "", width=50, height=50) == "logo_icon"


def test_classify_banner():
    assert classify_image("header.jpg", "site banner", width=800, height=150) == "banner_graphic"


def test_classify_default_photo():
    assert classify_image("family.jpg", "family photo", width=640, height=480) == "photo"


def test_crawl_page_images_extracts_and_classifies():
    html = """
    <html><head><title>Test Page</title>
    <meta property="og:image" content="/og.jpg">
    </head>
    <body>
      <img src="/photos/family.jpg" alt="Family photo" width="640" height="480">
      <img src="counter.gif" alt="hit counter" width="60" height="20">
      <a href="/gallery">Gallery</a>
      <a href="https://other.hu/page">External</a>
    </body></html>
    """
    result = crawl_page_images(html, "https://example.hu/", "example.hu")

    assert result.page_title == "Test Page"
    srcs = {p.src for p in result.photos}
    assert "https://example.hu/og.jpg" in srcs
    assert "https://example.hu/photos/family.jpg" in srcs

    family_photo = next(p for p in result.photos if "family" in p.src)
    assert family_photo.image_type == "photo"

    counter_photo = next(p for p in result.photos if "counter" in p.src)
    assert counter_photo.image_type == "vintage_asset"

    assert "https://example.hu/gallery" in result.discovered_links
    assert not any("other.hu" in link for link in result.discovered_links)


def test_crawl_page_images_skips_tracking_pixels():
    html = '<html><body><img src="/spacer.gif" alt=""></body></html>'
    result = crawl_page_images(html, "https://example.hu/", "example.hu")
    assert result.photos == []


def test_crawl_page_images_empty_html():
    result = crawl_page_images("", "https://example.hu/", "example.hu")
    assert result.photos == []
    assert result.discovered_links == []
