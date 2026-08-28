"""Periodically push newly discovered sites from Synology MariaDB to Hostinger.

Run this manually (or on a schedule) whenever you want the Hostinger-hosted
search UI to pick up sites the crawler has found since the last sync:

    python -m crawler.sync_to_hostinger

It reads unsynced rows from the `archive_pages` table on the Synology
database, POSTs them in batches to Hostinger's `/api.php?action=ingest`
endpoint, and marks each row `synced_to_hostinger = 1` once accepted.
"""

from __future__ import annotations

import argparse
import logging
import os

import requests

from crawler.hostinger_config import HostingerConfig
from crawler.hostinger_upload import HostingerUploader

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    from crawler import local_secrets  # type: ignore
except ImportError:
    local_secrets = None

DEFAULT_APP_URL = os.getenv("RETRO_APP_URL", "https://pecscitythings.eu")
DEFAULT_INGEST_TOKEN = os.getenv(
    "RETRO_INGEST_TOKEN",
    getattr(local_secrets, "RETRO_INGEST_TOKEN", "") if local_secrets else "",
)


def fetch_unsynced_batch(uploader: HostingerUploader, batch_size: int) -> list[dict]:
    """Fetch up to `batch_size` rows not yet synced to Hostinger."""
    cursor = uploader.connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, domain, original_url, wayback_timestamp, archive_url, title, content_text "
        "FROM archive_pages WHERE synced_to_hostinger = 0 ORDER BY id LIMIT %s",
        (batch_size,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows


def mark_synced(uploader: HostingerUploader, ids: list[int]) -> None:
    """Mark the given row ids as synced."""
    if not ids:
        return
    cursor = uploader.connection.cursor()
    placeholders = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"UPDATE archive_pages SET synced_to_hostinger = 1 WHERE id IN ({placeholders})",
        tuple(ids),
    )
    cursor.close()


def push_batch(app_url: str, token: str, rows: list[dict], timeout: int = 20) -> bool:
    """POST one batch of records to the Hostinger ingest endpoint."""
    records = [
        {
            "domain": row["domain"],
            "original_url": row["original_url"],
            "wayback_timestamp": row["wayback_timestamp"],
            "archive_url": row["archive_url"],
            "title": row.get("title", ""),
            "content_text": row.get("content_text", ""),
        }
        for row in rows
    ]

    response = requests.post(
        f"{app_url.rstrip('/')}/api.php?action=ingest",
        json={"records": records},
        headers={"X-Ingest-Token": token},
        timeout=timeout,
    )

    if response.status_code != 200:
        logger.error(f"Ingest failed ({response.status_code}): {response.text[:300]}")
        return False

    result = response.json()
    logger.info(f"Synced batch: inserted={result.get('inserted')} skipped={result.get('skipped')}")
    return True


def run_sync(app_url: str, token: str, batch_size: int = 50) -> dict:
    """Sync all unsynced rows to Hostinger, in batches."""
    uploader = HostingerUploader(**HostingerConfig.get_uploader_kwargs())
    if not uploader.connect():
        logger.error("Failed to connect to Synology database")
        return {"synced": 0, "failed_batches": 0}

    total_synced = 0
    failed_batches = 0

    try:
        while True:
            rows = fetch_unsynced_batch(uploader, batch_size)
            if not rows:
                break

            if push_batch(app_url, token, rows):
                mark_synced(uploader, [row["id"] for row in rows])
                total_synced += len(rows)
            else:
                failed_batches += 1
                break  # Stop on first failure; retry on next run.

    finally:
        uploader.close()

    logger.info(f"Sync complete: {total_synced} rows synced, {failed_batches} batch failures")
    return {"synced": total_synced, "failed_batches": failed_batches}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync newly discovered sites to Hostinger.")
    parser.add_argument("--app-url", default=DEFAULT_APP_URL, help="Base URL of the Hostinger app")
    parser.add_argument("--token", default=DEFAULT_INGEST_TOKEN, help="Shared ingest token")
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args(argv)

    result = run_sync(args.app_url, args.token, args.batch_size)
    return 0 if result["failed_batches"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
