"""Upload discovered sites to Hostinger MySQL database."""

from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    mysql = None
    MySQLError = Exception


logger = logging.getLogger(__name__)


class HostingerUploader:
    """Uploads crawler discoveries to Hostinger MySQL database."""

    def __init__(
        self,
        host: str = "localhost",
        database: str = "u230450852_retrocrawler",
        user: str = "u230450852_retrocrawler",
        password: str = "lQ$cyITcQ5K8PzeyUu5",
    ):
        """Initialize Hostinger database connection.

        Args:
            host: MySQL server host (localhost for shared hosting)
            database: Database name
            user: MySQL username
            password: MySQL password
        """
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

    def connect(self) -> bool:
        """Connect to Hostinger MySQL database."""
        if not mysql:
            logger.error("mysql-connector-python not installed. Run: pip install mysql-connector-python")
            return False

        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True,
            )
            logger.info(f"Connected to Hostinger database: {self.database}")
            return True
        except MySQLError as e:
            logger.error(f"Failed to connect to Hostinger: {e}")
            return False

    def ensure_schema(self) -> bool:
        """Create archive_pages table if it doesn't exist."""
        if not self.connection:
            logger.error("Not connected to database")
            return False

        try:
            cursor = self.connection.cursor()

            # Create archive_pages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS archive_pages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    snapshot_key VARCHAR(64) UNIQUE NOT NULL,
                    domain VARCHAR(255) NOT NULL,
                    original_url TEXT NOT NULL,
                    wayback_timestamp VARCHAR(14) NOT NULL,
                    archive_url TEXT NOT NULL,
                    local_path TEXT,
                    title TEXT DEFAULT '',
                    content_text LONGTEXT DEFAULT '',
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_url_timestamp (original_url(100), wayback_timestamp),
                    INDEX idx_domain (domain),
                    INDEX idx_timestamp (wayback_timestamp),
                    FULLTEXT INDEX ft_search (title, content_text)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            logger.info("Archive schema ensured")
            cursor.close()
            return True
        except MySQLError as e:
            logger.error(f"Failed to create schema: {e}")
            return False

    def upload_site(
        self,
        snapshot_key: str,
        domain: str,
        original_url: str,
        wayback_timestamp: str,
        archive_url: str,
        title: str = "",
        content_text: str = "",
        local_path: str = "",
    ) -> bool:
        """Upload a single discovered site to database.

        Args:
            snapshot_key: SHA256 hash of URL+timestamp
            domain: Domain name
            original_url: Original URL
            wayback_timestamp: Archive timestamp (YYYYMMDDHHMMSS)
            archive_url: Archive.org URL
            title: Page title (optional)
            content_text: Extracted text content (optional)
            local_path: Local file path (optional)

        Returns:
            True if upload successful, False otherwise
        """
        if not self.connection:
            logger.error("Not connected to database")
            return False

        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                INSERT IGNORE INTO archive_pages
                (snapshot_key, domain, original_url, wayback_timestamp, archive_url, title, content_text, local_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                snapshot_key,
                domain,
                original_url,
                wayback_timestamp,
                archive_url,
                title[:500] if title else "",  # Limit title length
                content_text[:50000] if content_text else "",  # Limit text length
                local_path or "",
            ))

            cursor.close()
            logger.debug(f"Uploaded: {domain} - {original_url}")
            return True

        except MySQLError as e:
            logger.warning(f"Failed to upload site: {e}")
            return False

    def upload_batch(self, sites: list[dict]) -> int:
        """Upload multiple sites in batch.

        Args:
            sites: List of site dicts with keys:
                - snapshot_key, domain, original_url, wayback_timestamp,
                - archive_url, title (optional), content_text (optional), local_path (optional)

        Returns:
            Number of successfully uploaded sites
        """
        if not self.connection:
            logger.error("Not connected to database")
            return 0

        uploaded = 0
        for site in sites:
            if self.upload_site(
                snapshot_key=site.get("snapshot_key", ""),
                domain=site.get("domain", ""),
                original_url=site.get("original_url", ""),
                wayback_timestamp=site.get("wayback_timestamp", ""),
                archive_url=site.get("archive_url", ""),
                title=site.get("title", ""),
                content_text=site.get("content_text", ""),
                local_path=site.get("local_path", ""),
            ):
                uploaded += 1

        logger.info(f"Batch upload: {uploaded}/{len(sites)} sites")
        return uploaded

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        self.ensure_schema()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
