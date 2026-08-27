"""Crawler with real-time Hostinger sync."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from crawler.discover import build_parser as build_discover_parser
from crawler.hostinger_upload import HostingerUploader
from crawler.hostinger_config import HostingerConfig
from crawler.orchestrate import CrawlerOrchestrator


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


def run_crawler_with_sync(
    uploader: HostingerUploader | None,
    dry_run: bool = False,
    seed_file: str = "crawler/seeds/pecs.txt",
    max_pages: int = 500,
    max_depth: int = 2,
    domain_limit: int = 50,
    discover_orphans: bool = False,
    sync_every_n_uploads: int = 200,
) -> dict:
    """Run actual crawler with Hostinger sync.

    Args:
        uploader: HostingerUploader instance (None for dry-run)
        dry_run: Don't upload if True
        seed_file: Path to seed URLs file
        max_pages: Maximum pages to crawl
        max_depth: Maximum link depth
        domain_limit: Maximum domains
        discover_orphans: Also follow outbound links from archived pages to
            find orphaned sites not in the seed list
        sync_every_n_uploads: Push new sites to Hostinger every N uploads
            (0 disables auto-sync)

    Returns:
        Statistics dictionary
    """
    orchestrator = CrawlerOrchestrator(
        seed_file=seed_file,
        max_pages=max_pages,
        max_depth=max_depth,
        domain_limit=domain_limit,
        uploader=uploader,
        dry_run=dry_run,
        discover_orphans=discover_orphans,
        sync_every_n_uploads=sync_every_n_uploads,
    )

    stats = orchestrator.run()
    return stats


def main(argv: list[str] | None = None) -> int:
    """Run crawler with Hostinger sync."""
    discover_parser = build_discover_parser()

    # Add Hostinger-specific arguments
    discover_parser.add_argument("--validate-only", action="store_true", help="Only validate config")
    discover_parser.add_argument("--show-config", action="store_true", help="Show Hostinger config")

    args = discover_parser.parse_args(argv)

    if args.show_config:
        HostingerConfig.print_config()
        return 0

    if args.validate_only:
        if not validate_hostinger():
            return 1
        logger.info("✓ Configuration valid")
        return 0

    if not args.dry_run:
        if not validate_hostinger():
            return 1

    uploader = None
    try:
        if not args.dry_run:
            uploader = create_uploader()
            if not uploader:
                return 1

        stats = run_crawler_with_sync(
            uploader=uploader,
            dry_run=args.dry_run,
            seed_file=args.seed_file,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            domain_limit=args.domain_limit,
            discover_orphans=args.discover_orphans,
        )

        logger.info("\n" + "=" * 50)
        logger.info("Crawl Statistics:")
        logger.info(f"  Discovered: {stats['discovered']}")
        logger.info(f"  Uploaded: {stats['uploaded']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Pages crawled: {stats['pages_crawled']}")
        logger.info(f"  Success rate: {stats['success_rate']:.1f}%")
        logger.info("=" * 50)

        return 0 if stats['failed'] == 0 else 1

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
