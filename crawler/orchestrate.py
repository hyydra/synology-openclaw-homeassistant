"""Crawler orchestration - coordinates discovery, extraction, and upload."""

from __future__ import annotations

import logging
import hashlib
from pathlib import Path
from typing import Generator

from crawler.models import DiscoveryCandidate
from crawler.hostinger_upload import HostingerUploader


logger = logging.getLogger(__name__)


class CrawlerOrchestrator:
    """Coordinates the complete crawl workflow."""

    def __init__(
        self,
        seed_file: str = "crawler/seeds/pecs.txt",
        max_pages: int = 500,
        max_depth: int = 2,
        domain_limit: int = 50,
        uploader: HostingerUploader | None = None,
        dry_run: bool = False,
    ):
        """Initialize crawler orchestrator.

        Args:
            seed_file: Path to seed URLs file
            max_pages: Maximum pages to crawl
            max_depth: Maximum link depth
            domain_limit: Maximum domains
            uploader: Optional HostingerUploader for syncing
            dry_run: Don't upload if True
        """
        self.seed_file = seed_file
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.domain_limit = domain_limit
        self.uploader = uploader
        self.dry_run = dry_run

        self.discovered_count = 0
        self.uploaded_count = 0
        self.failed_count = 0
        self.pages_crawled = 0

    def load_seeds(self) -> list[str]:
        """Load seed URLs from file."""
        seed_path = Path(self.seed_file)
        if not seed_path.exists():
            logger.warning(f"Seed file not found: {self.seed_file}")
            return []

        try:
            with open(seed_path) as f:
                seeds = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            logger.info(f"Loaded {len(seeds)} seeds from {self.seed_file}")
            return seeds
        except Exception as e:
            logger.error(f"Failed to load seeds: {e}")
            return []

    def discover_sites(self) -> Generator[DiscoveryCandidate, None, None]:
        """Generate discovered sites (placeholder for actual discovery logic).

        In production, this would:
        1. Fetch Wayback Machine index (CDX)
        2. Extract links from archived pages
        3. Validate candidates
        4. Apply scoring
        """
        seeds = self.load_seeds()
        if not seeds:
            logger.warning("No seeds available for discovery")
            return

        # Placeholder: Generate candidates from seeds
        # TODO: Integrate with actual CDX fetcher, link extractor, etc.
        for i, seed_url in enumerate(seeds[:self.domain_limit]):
            if self.discovered_count >= self.max_pages:
                logger.info(f"Reached max pages limit: {self.max_pages}")
                break

            domain = seed_url.split("//")[-1].split("/")[0]

            candidate = DiscoveryCandidate(
                url=seed_url,
                domain=domain,
                discovery_source_url="https://archive.org",
                discovery_method="seed",
                live_state="archived",
                review_state="new",
            )

            yield candidate
            self.discovered_count += 1

    def process_candidate(
        self,
        candidate: DiscoveryCandidate,
        title: str = "",
        content_text: str = "",
    ) -> bool:
        """Process a discovered candidate - extract and upload.

        Args:
            candidate: DiscoveryCandidate to process
            title: Extracted page title
            content_text: Extracted text content

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate snapshot key
            snapshot_key = hashlib.sha256(
                (candidate.url + "\n" + candidate.discovery_source_url).encode()
            ).hexdigest()

            # Extract Wayback timestamp from URL if available
            wayback_timestamp = self._extract_timestamp(candidate.url)

            # Upload to Hostinger if enabled
            if self.uploader and not self.dry_run:
                if self.uploader.upload_site(
                    snapshot_key=snapshot_key,
                    domain=candidate.domain,
                    original_url=candidate.url,
                    wayback_timestamp=wayback_timestamp,
                    archive_url=candidate.url,
                    title=title,
                    content_text=content_text,
                ):
                    self.uploaded_count += 1
                    logger.info(f"✓ {candidate.domain} ({self.uploaded_count} total)")
                    return True
                else:
                    self.failed_count += 1
                    logger.warning(f"✗ Failed to upload {candidate.domain}")
                    return False
            else:
                self.uploaded_count += 1
                logger.info(f"{'[DRY-RUN] '}Would upload: {candidate.domain}")
                return True

        except Exception as e:
            self.failed_count += 1
            logger.error(f"Error processing candidate {candidate.domain}: {e}")
            return False

    def run(self) -> dict:
        """Run the complete crawl workflow.

        Returns:
            Statistics dictionary
        """
        logger.info("Starting crawler orchestration...")
        logger.info(f"  Max pages: {self.max_pages}")
        logger.info(f"  Max depth: {self.max_depth}")
        logger.info(f"  Domain limit: {self.domain_limit}")
        logger.info(f"  Dry-run: {self.dry_run}")

        try:
            for candidate in self.discover_sites():
                # TODO: In production, extract title and content from archived page
                self.process_candidate(candidate, title="", content_text="")

                self.pages_crawled += 1
                if self.pages_crawled % 10 == 0:
                    logger.info(f"Progress: {self.pages_crawled} pages, {self.discovered_count} discovered")

        except KeyboardInterrupt:
            logger.info("Crawl interrupted by user")
        except Exception as e:
            logger.error(f"Crawl error: {e}", exc_info=True)

        return self.get_stats()

    def get_stats(self) -> dict:
        """Get crawl statistics."""
        return {
            "discovered": self.discovered_count,
            "uploaded": self.uploaded_count,
            "failed": self.failed_count,
            "pages_crawled": self.pages_crawled,
            "success_rate": (
                self.uploaded_count / (self.uploaded_count + self.failed_count) * 100
                if (self.uploaded_count + self.failed_count) > 0
                else 0
            ),
        }

    @staticmethod
    def _extract_timestamp(url: str) -> str:
        """Extract Wayback timestamp from URL."""
        try:
            if "/web/" in url:
                parts = url.split("/web/")
                if len(parts) > 1:
                    timestamp = parts[1].split("/")[0].split("*")[0]
                    if len(timestamp) >= 14 and timestamp.isdigit():
                        return timestamp[:14]
        except Exception:
            pass
        return ""
