"""Discovery crawler with real-time Hostinger database upload."""

from __future__ import annotations

import logging
import hashlib
from typing import Optional
from datetime import datetime

from crawler.models import DiscoveryCandidate
from crawler.hostinger_upload import HostingerUploader


logger = logging.getLogger(__name__)


class CrawlerWithUpload:
    """Wrapper that uploads sites as they're discovered."""

    def __init__(
        self,
        uploader: Optional[HostingerUploader] = None,
        enable_upload: bool = True,
    ):
        """Initialize crawler with optional upload.

        Args:
            uploader: HostingerUploader instance (creates default if None)
            enable_upload: Whether to upload discoveries
        """
        self.uploader = uploader or HostingerUploader()
        self.enable_upload = enable_upload
        self.uploaded_count = 0
        self.failed_count = 0

    def start(self) -> bool:
        """Initialize uploader and database schema."""
        if not self.enable_upload:
            logger.info("Upload disabled")
            return True

        if not self.uploader.connect():
            logger.error("Failed to connect to Hostinger")
            self.enable_upload = False
            return False

        if not self.uploader.ensure_schema():
            logger.error("Failed to create database schema")
            self.enable_upload = False
            return False

        logger.info("Uploader initialized and ready")
        return True

    def on_site_discovered(
        self,
        candidate: DiscoveryCandidate,
        title: str = "",
        content_text: str = "",
        local_path: str = "",
    ) -> bool:
        """Handle site discovery - upload to Hostinger.

        Args:
            candidate: DiscoveryCandidate with site info
            title: Page title (optional)
            content_text: Extracted text (optional)
            local_path: Local file path (optional)

        Returns:
            True if uploaded or upload disabled, False if failed
        """
        if not self.enable_upload:
            return True

        try:
            # Generate snapshot key (SHA256 of URL + timestamp)
            snapshot_key = hashlib.sha256(
                (candidate.url + "\n" + datetime.now().isoformat()).encode()
            ).hexdigest()

            # Extract timestamp from Wayback URL if available
            wayback_timestamp = self._extract_timestamp(candidate.url)

            # Upload to Hostinger
            if self.uploader.upload_site(
                snapshot_key=snapshot_key,
                domain=candidate.domain,
                original_url=candidate.url,
                wayback_timestamp=wayback_timestamp,
                archive_url=candidate.url,
                title=title,
                content_text=content_text,
                local_path=local_path,
            ):
                self.uploaded_count += 1
                logger.info(f"✓ Uploaded: {candidate.domain} (Total: {self.uploaded_count})")
                return True
            else:
                self.failed_count += 1
                logger.warning(f"✗ Failed to upload: {candidate.domain}")
                return False

        except Exception as e:
            self.failed_count += 1
            logger.error(f"Error uploading site: {e}")
            return False

    def on_batch_discovered(self, candidates: list[DiscoveryCandidate]) -> int:
        """Upload multiple discovered sites.

        Args:
            candidates: List of DiscoveryCandidate objects

        Returns:
            Number of successfully uploaded sites
        """
        if not self.enable_upload:
            return len(candidates)

        uploaded = 0
        for candidate in candidates:
            if self.on_site_discovered(candidate):
                uploaded += 1

        return uploaded

    def finish(self) -> dict:
        """Finalize uploader and return stats.

        Returns:
            Dictionary with upload statistics
        """
        if self.uploader:
            self.uploader.close()

        stats = {
            "uploaded": self.uploaded_count,
            "failed": self.failed_count,
            "total": self.uploaded_count + self.failed_count,
            "success_rate": (
                self.uploaded_count / (self.uploaded_count + self.failed_count) * 100
                if (self.uploaded_count + self.failed_count) > 0
                else 0
            ),
        }

        logger.info(f"Upload complete: {stats['uploaded']}/{stats['total']} successful")
        return stats

    @staticmethod
    def _extract_timestamp(url: str) -> str:
        """Extract Wayback timestamp from archive.org URL.

        Args:
            url: Archive URL (e.g., https://archive.org/web/20150315000000*/...)

        Returns:
            Timestamp in YYYYMMDDHHMMSS format, or current time if not found
        """
        try:
            # Look for pattern like /web/20150315000000/
            if "/web/" in url:
                parts = url.split("/web/")
                if len(parts) > 1:
                    timestamp_str = parts[1].split("/")[0].split("*")[0]
                    if len(timestamp_str) >= 14 and timestamp_str.isdigit():
                        return timestamp_str[:14]
        except Exception:
            pass

        # Fallback to current timestamp
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def get_stats(self) -> dict:
        """Get current upload statistics."""
        return {
            "uploaded": self.uploaded_count,
            "failed": self.failed_count,
            "total": self.uploaded_count + self.failed_count,
        }
