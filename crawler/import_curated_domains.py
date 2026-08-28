"""Import the curated Hungarian 1990s domain dataset as pre-populated archive entries.

Source: hungarian-1990s-domain-explorer (a separate research project cataloguing
notable early Hungarian domains with verified Wayback captures and historical
context). Rather than waiting for the crawler to rediscover these well-known
sites, this script inserts them directly as rich, searchable archive_pages rows.

Usage:
    python -m crawler.import_curated_domains                  # upload to Synology MariaDB
    python -m crawler.import_curated_domains --ingest-to-app http://192.168.1.2:8080
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import requests

from crawler.hostinger_config import HostingerConfig
from crawler.hostinger_upload import HostingerUploader
from crawler.sync_to_hostinger import DEFAULT_INGEST_TOKEN

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).parent / "seeds" / "hungarian_1990s_domains.json"
TIMESTAMP_RE = re.compile(r"/web/(\d{14})/")


def load_dataset() -> list[dict]:
    with open(DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_record(entry: dict) -> dict | None:
    """Convert one curated dataset entry into an archive_pages-shaped record."""
    wayback_url = entry.get("waybackUrl", "")
    timestamp_match = TIMESTAMP_RE.search(wayback_url)

    if timestamp_match:
        timestamp = timestamp_match.group(1)
        archive_url = wayback_url
    elif entry.get("earliestWaybackYear"):
        timestamp = f"{entry['earliestWaybackYear']}0101000000"
        archive_url = f"https://web.archive.org/web/{timestamp}/{entry['primaryUrl']}"
    else:
        logger.warning(f"Skipping {entry.get('domain')}: no usable Wayback timestamp")
        return None

    content_parts = [
        entry.get("description", ""),
        entry.get("historicalSignificance", ""),
        entry.get("notableMilestone", ""),
        f"Alapította: {entry.get('originalFounderOrOrg', '')}" if entry.get("originalFounderOrOrg") else "",
        f"Technológia: {entry.get('techSnapshot90s', '')}" if entry.get("techSnapshot90s") else "",
        "Címkék: " + ", ".join(entry.get("tags", [])) if entry.get("tags") else "",
    ]
    content_text = " ".join(part for part in content_parts if part)

    return {
        "domain": entry["domain"],
        "original_url": entry["primaryUrl"],
        "wayback_timestamp": timestamp,
        "archive_url": archive_url,
        "title": entry.get("name", entry["domain"]),
        "content_text": content_text,
    }


def upload_to_synology(records: list[dict]) -> tuple[int, int]:
    """Upload curated records directly to Synology MariaDB."""
    uploader = HostingerUploader(**HostingerConfig.get_uploader_kwargs())
    if not uploader.connect() or not uploader.ensure_schema():
        logger.error("Failed to connect to Synology database")
        return 0, len(records)

    uploaded = 0
    failed = 0
    for record in records:
        snapshot_key = f"curated-{record['domain']}-{record['wayback_timestamp']}"
        import hashlib
        snapshot_key = hashlib.sha256(snapshot_key.encode()).hexdigest()

        if uploader.upload_site(
            snapshot_key=snapshot_key,
            domain=record["domain"],
            original_url=record["original_url"],
            wayback_timestamp=record["wayback_timestamp"],
            archive_url=record["archive_url"],
            title=record["title"],
            content_text=record["content_text"],
        ):
            uploaded += 1
        else:
            failed += 1

    uploader.close()
    return uploaded, failed


def ingest_to_app(app_url: str, token: str, records: list[dict]) -> tuple[int, int]:
    """Push curated records directly into a running app's local archive via /api.php?action=ingest."""
    response = requests.post(
        f"{app_url.rstrip('/')}/api.php?action=ingest",
        json={"records": records},
        headers={"X-Ingest-Token": token},
        timeout=30,
    )
    if response.status_code != 200:
        logger.error(f"Ingest failed ({response.status_code}): {response.text[:300]}")
        return 0, len(records)

    result = response.json()
    return result.get("inserted", 0), result.get("skipped", 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import curated Hungarian 1990s domains.")
    parser.add_argument("--ingest-to-app", help="Also POST records to this app's /api.php?action=ingest")
    parser.add_argument("--ingest-token", default=DEFAULT_INGEST_TOKEN)
    parser.add_argument("--skip-synology", action="store_true", help="Skip uploading to Synology MariaDB")
    args = parser.parse_args(argv)

    entries = load_dataset()
    records = [r for r in (build_record(e) for e in entries) if r is not None]
    logger.info(f"Loaded {len(entries)} entries, {len(records)} have usable Wayback timestamps")

    if not args.skip_synology:
        uploaded, failed = upload_to_synology(records)
        logger.info(f"Synology MariaDB: {uploaded} uploaded, {failed} failed")

    if args.ingest_to_app:
        inserted, skipped = ingest_to_app(args.ingest_to_app, args.ingest_token, records)
        logger.info(f"{args.ingest_to_app}: {inserted} inserted, {skipped} skipped")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
