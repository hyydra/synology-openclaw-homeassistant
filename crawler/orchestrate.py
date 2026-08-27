"""Crawler orchestration - coordinates discovery, extraction, and upload."""

from __future__ import annotations

import logging
import hashlib
from pathlib import Path
from typing import Generator

import requests

from crawler.cdx import list_captures
from crawler.normalize import normalize_domain, normalize_url
from crawler.models import DiscoveryCandidate
from crawler.hostinger_upload import HostingerUploader
from crawler.extractors.standard import extract_links_standard
from crawler.orphans import classify_orphan
from crawler.models import CdxSummary
from crawler.sync_to_hostinger import run_sync as sync_to_hostinger, DEFAULT_APP_URL, DEFAULT_INGEST_TOKEN


logger = logging.getLogger(__name__)

# How many of a domain's own captured pages to scan for outbound links when
# --discover-orphans is on. Kept small: this is a sampling step, not a full crawl.
ORPHAN_SOURCE_PAGE_SAMPLE = 3


def _fetch_cdx(url: str, timeout: int = 15) -> str:
    """Default CDX HTTP client: GET the URL and return its body, or '' on failure."""
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "retro-kereso-crawler/1.0"})
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.warning(f"CDX request failed for {url}: {exc}")
        return ""


def _fetch_archived_html(timestamp: str, original_url: str, timeout: int = 15) -> str:
    """Fetch the raw (unrewritten) archived HTML for one Wayback capture."""
    raw_url = f"https://web.archive.org/web/{timestamp}id_/{original_url}"
    try:
        response = requests.get(raw_url, timeout=timeout, headers={"User-Agent": "retro-kereso-crawler/1.0"})
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.warning(f"Archived page fetch failed for {raw_url}: {exc}")
        return ""


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
        discover_orphans: bool = False,
        sync_every_n_uploads: int = 0,
    ):
        """Initialize crawler orchestrator.

        Args:
            seed_file: Path to seed URLs file
            max_pages: Maximum pages to crawl
            max_depth: Maximum link depth
            domain_limit: Maximum domains
            uploader: Optional HostingerUploader for syncing
            dry_run: Don't upload if True
            discover_orphans: If True, also sample outbound links from a few of
                each seed domain's own archived pages and follow up with a bounded
                CDX check on any new domain found, yielding it when it qualifies
                as an orphan (archived elsewhere but reachable only via that link)
            sync_every_n_uploads: If > 0, push newly discovered sites to the
                Hostinger-hosted search UI every time this many new sites have
                been uploaded to Synology (0 disables auto-sync)
        """
        self.seed_file = seed_file
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.domain_limit = domain_limit
        self.uploader = uploader
        self.dry_run = dry_run
        self.discover_orphans = discover_orphans
        self.sync_every_n_uploads = sync_every_n_uploads

        self.discovered_count = 0
        self.uploaded_count = 0
        self.failed_count = 0
        self.pages_crawled = 0
        self._known_domains: set[str] = set()
        self._last_synced_at_count = 0

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
        """Discover real archived pages for each seed domain via Wayback CDX.

        For each seed, queries the CDX API for that domain's captures and
        yields one DiscoveryCandidate per unique archived URL, each carrying
        its real Wayback timestamp. Link-extraction from archived pages
        (deeper than one hop) is not yet wired in here.
        """
        seeds = self.load_seeds()
        if not seeds:
            logger.warning("No seeds available for discovery")
            return

        for seed in seeds[:self.domain_limit]:
            if self.discovered_count >= self.max_pages:
                logger.info(f"Reached max pages limit: {self.max_pages}")
                break

            domain = normalize_domain(seed)
            if not domain:
                logger.warning(f"Skipping unparseable seed: {seed}")
                continue
            self._known_domains.add(domain)

            remaining = self.max_pages - self.discovered_count
            captures = list_captures(f"{domain}/*", _fetch_cdx, limit=min(200, remaining))
            if not captures:
                logger.info(f"No CDX captures found for {domain}")
                continue

            for timestamp, original in captures:
                if self.discovered_count >= self.max_pages:
                    break

                normalized = normalize_url(original)
                if not normalized:
                    continue
                url_domain = normalize_domain(normalized) or domain

                archive_url = f"https://web.archive.org/web/{timestamp}/{normalized}"
                candidate = DiscoveryCandidate(
                    url=normalized,
                    domain=url_domain,
                    discovery_source_url=archive_url,
                    discovery_method="cdx",
                    live_state="archived",
                    review_state="new",
                )

                yield candidate
                self.discovered_count += 1

            if self.discover_orphans and self.max_depth >= 1 and self.discovered_count < self.max_pages:
                yield from self._discover_orphans_from(domain, captures)

    def _discover_orphans_from(
        self,
        source_domain: str,
        captures: list[tuple[str, str]],
    ) -> Generator[DiscoveryCandidate, None, None]:
        """Sample a few archived pages from one domain and follow outbound links
        that lead to domains not already known, yielding any that qualify as
        orphans (archived elsewhere, referenced only via this old link)."""
        for timestamp, original in captures[:ORPHAN_SOURCE_PAGE_SAMPLE]:
            if self.discovered_count >= self.max_pages:
                return

            html = _fetch_archived_html(timestamp, original)
            if not html:
                continue

            for link in extract_links_standard(html, base_url=original):
                if self.discovered_count >= self.max_pages:
                    return

                normalized = normalize_url(link.url)
                if not normalized:
                    continue
                link_domain = normalize_domain(normalized)
                if not link_domain or link_domain in self._known_domains:
                    continue
                self._known_domains.add(link_domain)

                link_captures = list_captures(f"{link_domain}/*", _fetch_cdx, limit=5)
                cdx_summary = CdxSummary(capture_count=len(link_captures))
                is_orphan, reasons = classify_orphan(
                    live_ok=None,
                    cdx=cdx_summary,
                    archived_referrers=1,
                )
                if not is_orphan or not link_captures:
                    continue

                orphan_timestamp, orphan_original = link_captures[0]
                orphan_normalized = normalize_url(orphan_original)
                if not orphan_normalized:
                    continue

                archive_url = f"https://web.archive.org/web/{orphan_timestamp}/{orphan_normalized}"
                logger.info(f"Orphan found via {source_domain}: {link_domain} ({'; '.join(reasons)})")
                yield DiscoveryCandidate(
                    url=orphan_normalized,
                    domain=link_domain,
                    discovery_source_url=archive_url,
                    discovery_method="link-extraction",
                    live_state="unknown",
                    orphan_evidence=True,
                    anchor_text=link.anchor_text,
                    review_state="new",
                )
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
            # Extract Wayback timestamp from the archive URL
            wayback_timestamp = self._extract_timestamp(candidate.discovery_source_url)

            # Generate snapshot key
            snapshot_key = hashlib.sha256(
                (candidate.url + "\n" + wayback_timestamp).encode()
            ).hexdigest()

            # Upload to Hostinger if enabled
            if self.uploader and not self.dry_run:
                if self.uploader.upload_site(
                    snapshot_key=snapshot_key,
                    domain=candidate.domain,
                    original_url=candidate.url,
                    wayback_timestamp=wayback_timestamp,
                    archive_url=candidate.discovery_source_url,
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

                self._maybe_sync_to_hostinger()

        except KeyboardInterrupt:
            logger.info("Crawl interrupted by user")
        except Exception as e:
            logger.error(f"Crawl error: {e}", exc_info=True)

        self._maybe_sync_to_hostinger(force=True)
        return self.get_stats()

    def _maybe_sync_to_hostinger(self, force: bool = False) -> None:
        """Push newly uploaded sites to Hostinger every sync_every_n_uploads uploads.

        `force` triggers one final sync at the end of the run so the last
        partial batch (fewer than the threshold) still reaches Hostinger.
        """
        if self.sync_every_n_uploads <= 0 or self.dry_run:
            return

        due = self.uploaded_count - self._last_synced_at_count >= self.sync_every_n_uploads
        if not (due or (force and self.uploaded_count > self._last_synced_at_count)):
            return

        logger.info(f"Auto-sync: pushing new sites to Hostinger ({self.uploaded_count} uploaded so far)...")
        try:
            result = sync_to_hostinger(DEFAULT_APP_URL, DEFAULT_INGEST_TOKEN)
            logger.info(f"Auto-sync complete: {result['synced']} rows synced")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Auto-sync to Hostinger failed (will retry next threshold): {exc}")
            return

        self._last_synced_at_count = self.uploaded_count

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
