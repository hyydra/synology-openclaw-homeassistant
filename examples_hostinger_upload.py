"""Examples of uploading discovered sites to Hostinger."""

from crawler.hostinger_upload import HostingerUploader
from crawler.crawler_with_upload import CrawlerWithUpload
from crawler.hostinger_config import HostingerConfig
from crawler.models import DiscoveryCandidate
import logging


logging.basicConfig(level=logging.INFO)


def example_1_single_site():
    """Upload a single site."""
    print("\n=== Example 1: Single Site Upload ===")

    with HostingerUploader() as uploader:
        success = uploader.upload_site(
            snapshot_key="abc123def456",
            domain="pecs-city.hu",
            original_url="https://pecs-city.hu",
            wayback_timestamp="20150315120000",
            archive_url="https://archive.org/web/20150315120000/https://pecs-city.hu",
            title="Pécs City History",
            content_text="Historical information about Pécs city...",
        )
        print(f"Upload successful: {success}")


def example_2_batch_upload():
    """Upload multiple sites at once."""
    print("\n=== Example 2: Batch Upload ===")

    sites = [
        {
            "snapshot_key": "key1",
            "domain": "zsolnay.hu",
            "original_url": "https://zsolnay.hu",
            "wayback_timestamp": "20140822120000",
            "archive_url": "https://archive.org/web/20140822120000/https://zsolnay.hu",
            "title": "Zsolnay Porcelain",
            "content_text": "Information about Zsolnay porcelain factory...",
        },
        {
            "snapshot_key": "key2",
            "domain": "urunvaros.hu",
            "original_url": "https://urunvaros.hu",
            "wayback_timestamp": "20130511120000",
            "archive_url": "https://archive.org/web/20130511120000/https://urunvaros.hu",
            "title": "Ürményes District",
            "content_text": "Information about Ürményes district...",
        },
    ]

    with HostingerUploader() as uploader:
        uploaded = uploader.upload_batch(sites)
        print(f"Uploaded: {uploaded}/{len(sites)} sites")


def example_3_crawler_integration():
    """Upload as crawler discovers sites."""
    print("\n=== Example 3: Crawler Integration ===")

    crawler = CrawlerWithUpload(enable_upload=True)
    if not crawler.start():
        print("Failed to start uploader")
        return

    # Simulate discovered sites
    candidates = [
        DiscoveryCandidate(
            url="https://archive.org/web/20150315120000/https://pecs-city.hu",
            domain="pecs-city.hu",
            discovery_source_url="https://archive.org",
            discovery_method="seed",
        ),
        DiscoveryCandidate(
            url="https://archive.org/web/20140822120000/https://zsolnay.hu",
            domain="zsolnay.hu",
            discovery_source_url="https://archive.org",
            discovery_method="cdx-discovery",
        ),
    ]

    for candidate in candidates:
        crawler.on_site_discovered(
            candidate,
            title=f"Page from {candidate.domain}",
            content_text="Sample extracted text...",
        )

    stats = crawler.finish()
    print(f"\nUpload Statistics:")
    print(f"  Successful: {stats['uploaded']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Success rate: {stats['success_rate']:.1f}%")


def example_4_config_validation():
    """Validate Hostinger configuration."""
    print("\n=== Example 4: Configuration Validation ===")

    HostingerConfig.print_config()

    is_valid, errors = HostingerConfig.validate()
    if is_valid:
        print("\n✓ Configuration is valid")
    else:
        print("\n✗ Configuration errors:")
        for error in errors:
            print(f"  - {error}")


if __name__ == "__main__":
    print("Hostinger Upload Examples")
    print("=" * 50)

    # Validate config first
    example_4_config_validation()

    # Try examples (comment out if credentials not set)
    try:
        example_1_single_site()
        example_2_batch_upload()
        example_3_crawler_integration()
    except Exception as e:
        print(f"\nNote: Examples require mysql-connector-python installed:")
        print(f"  pip install -r requirements.txt")
        print(f"\nError: {e}")
