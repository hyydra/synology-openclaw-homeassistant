"""Crawler with real-time Hostinger sync."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from crawler.discover import parse_args as parse_discover_args
from crawler.hostinger_upload import HostingerUploader
from crawler.hostinger_config import HostingerConfig
from crawler.models import DiscoveryCandidate


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_hostinger():
    """Validate Hostinger configuration."""
    is_valid, errors = HostingerConfig.validate()
    if not is_valid:
        logger.error("Hostinger configuration invalid:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    return True


def create_uploader() -> HostingerUploader | None:
    """Create and test Hostinger uploader."""
    logger.info("Initializing Hostinger uploader...")

    uploader = HostingerUploader(**HostingerConfig.get_uploader_kwargs())

    if not uploader.connect():
        logger.error("Failed to connect to Hostinger database")
        return None

    if not uploader.ensure_schema():
        logger.error("Failed to create database schema")
        uploader.close()
        return None

    logger.info("✓ Hostinger uploader ready")
    return uploader


def simulate_discovery_with_sync(uploader: HostingerUploader, dry_run: bool = False):
    """Simulate discovery and sync to Hostinger.

    In production, this would be replaced with actual crawler discovery logic.
    """
    logger.info("Starting simulated discovery with Hostinger sync...")

    # Simulated discoveries
    sites = [
        {
            "snapshot_key": "pecs001",
            "domain": "pecs-city.hu",
            "original_url": "https://pecs-city.hu",
            "wayback_timestamp": "20150315120000",
            "archive_url": "https://archive.org/web/20150315120000/https://pecs-city.hu",
            "title": "Pécs City - Historical Information",
            "content_text": "Welcome to Pécs, a historic city in southern Hungary...",
            "local_path": "",
        },
        {
            "snapshot_key": "zsolnay001",
            "domain": "zsolnay.hu",
            "original_url": "https://zsolnay.hu",
            "wayback_timestamp": "20140822120000",
            "archive_url": "https://archive.org/web/20140822120000/https://zsolnay.hu",
            "title": "Zsolnay Porcelain Factory",
            "content_text": "The Zsolnay Porcelain Manufactory is a historic...",
            "local_path": "",
        },
        {
            "snapshot_key": "urunvaros001",
            "domain": "urunvaros.hu",
            "original_url": "https://urunvaros.hu",
            "wayback_timestamp": "20130511120000",
            "archive_url": "https://archive.org/web/20130511120000/https://urunvaros.hu",
            "title": "Ürményes District",
            "content_text": "The Ürményes district is a historic area...",
            "local_path": "",
        },
    ]

    uploaded = 0
    failed = 0

    for site in sites:
        if dry_run:
            logger.info(f"[DRY-RUN] Would upload: {site['domain']}")
        else:
            if uploader.upload_site(
                snapshot_key=site["snapshot_key"],
                domain=site["domain"],
                original_url=site["original_url"],
                wayback_timestamp=site["wayback_timestamp"],
                archive_url=site["archive_url"],
                title=site["title"],
                content_text=site["content_text"],
                local_path=site["local_path"],
            ):
                uploaded += 1
                logger.info(f"✓ Uploaded: {site['domain']}")
            else:
                failed += 1
                logger.warning(f"✗ Failed: {site['domain']}")

    logger.info(f"\nSync complete: {uploaded} uploaded, {failed} failed")
    return uploaded, failed


def main(argv: list[str] | None = None) -> int:
    """Run crawler with Hostinger sync."""
    parser = argparse.ArgumentParser(
        description="Discover historical Hungarian/Pécs web sources with Hostinger sync"
    )
    parser.add_argument("--validate-only", action="store_true", help="Only validate config")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without uploading")
    parser.add_argument("--show-config", action="store_true", help="Show Hostinger config")

    args = parser.parse_args(argv)

    if args.show_config:
        HostingerConfig.print_config()
        return 0

    if args.validate_only or not (args.dry_run):
        if not validate_hostinger():
            return 1

    if args.validate_only:
        logger.info("✓ Configuration valid")
        return 0

    uploader = None
    try:
        if not args.dry_run:
            uploader = create_uploader()
            if not uploader:
                return 1

        uploaded, failed = simulate_discovery_with_sync(uploader, dry_run=args.dry_run)

        if args.dry_run:
            logger.info("Dry-run complete (no data uploaded)")
        else:
            logger.info(f"Discovery sync complete: {uploaded} sites uploaded")

        return 0 if failed == 0 else 1

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    finally:
        if uploader:
            uploader.close()


if __name__ == "__main__":
    sys.exit(main())
