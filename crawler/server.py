"""Local Flask server: serves the dashboard and drives the crawler in real time."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from crawler.hostinger_config import HostingerConfig
from crawler.hostinger_upload import HostingerUploader
from crawler.orchestrate import CrawlerOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = Flask(__name__, static_folder=None)


class CrawlerState:
    """Shared, thread-safe state for the running crawler."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.thread: threading.Thread | None = None
        self.stop_requested = False
        self.started_at: float | None = None
        self.stats = {"discovered": 0, "uploaded": 0, "failed": 0, "pages_crawled": 0}
        self.logs: list[dict] = []

    def add_log(self, message: str, level: str = "info") -> None:
        with self.lock:
            self.logs.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": message,
                "level": level,
            })
            self.logs = self.logs[-200:]

    def snapshot(self) -> dict:
        with self.lock:
            elapsed = time.time() - self.started_at if self.started_at else 0
            return {
                "running": self.running,
                "elapsed_seconds": int(elapsed),
                "stats": dict(self.stats),
                "logs": list(self.logs[-100:]),
            }


state = CrawlerState()


def _run_crawler(max_pages: int, max_depth: int, domain_limit: int, seed_file: str) -> None:
    state.add_log("Starting crawler...", "info")

    uploader = HostingerUploader(**HostingerConfig.get_uploader_kwargs())
    if not uploader.connect() or not uploader.ensure_schema():
        state.add_log("Failed to connect to database", "error")
        with state.lock:
            state.running = False
        return

    state.add_log(f"Connected to database. Seeds: {seed_file}", "success")

    orchestrator = CrawlerOrchestrator(
        seed_file=seed_file,
        max_pages=max_pages,
        max_depth=max_depth,
        domain_limit=domain_limit,
        uploader=uploader,
        dry_run=False,
    )

    try:
        for candidate in orchestrator.discover_sites():
            with state.lock:
                if state.stop_requested:
                    break

            ok = orchestrator.process_candidate(candidate, title="", content_text="")
            with state.lock:
                state.stats["discovered"] = orchestrator.discovered_count
                state.stats["uploaded"] = orchestrator.uploaded_count
                state.stats["failed"] = orchestrator.failed_count
                state.stats["pages_crawled"] += 1

            if ok:
                state.add_log(f"Found: {candidate.domain}", "success")
            else:
                state.add_log(f"Failed: {candidate.domain}", "error")

        with state.lock:
            state.stats["discovered"] = orchestrator.discovered_count
            state.stats["uploaded"] = orchestrator.uploaded_count
            state.stats["failed"] = orchestrator.failed_count
        state.add_log("Crawl finished", "info")
    except Exception as exc:  # noqa: BLE001
        state.add_log(f"Crawler error: {exc}", "error")
        logger.exception("Crawler error")
    finally:
        uploader.close()
        with state.lock:
            state.running = False
            state.stop_requested = False


@app.route("/")
def index():
    return send_from_directory(PROJECT_ROOT, "dashboard.html")


@app.route("/api/status")
def api_status():
    return jsonify(state.snapshot())


@app.route("/api/sites")
def api_sites():
    limit = int(request.args.get("limit", 20))
    uploader = HostingerUploader(**HostingerConfig.get_uploader_kwargs())
    if not uploader.connect():
        return jsonify({"error": "database unavailable"}), 503

    cursor = uploader.connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT domain, original_url, wayback_timestamp, archive_url, indexed_at "
        "FROM archive_pages ORDER BY id DESC LIMIT %s",
        (limit,),
    )
    rows = cursor.fetchall()
    cursor.close()
    uploader.close()

    for row in rows:
        if row.get("indexed_at"):
            row["indexed_at"] = str(row["indexed_at"])

    return jsonify({"sites": rows})


@app.route("/api/start", methods=["POST"])
def api_start():
    body = request.get_json(silent=True) or {}
    max_pages = int(body.get("max_pages", 500))
    max_depth = int(body.get("max_depth", 2))
    domain_limit = int(body.get("domain_limit", 50))
    seed_file = body.get("seed_file", "crawler/seeds/pecs.txt")

    with state.lock:
        if state.running:
            return jsonify({"error": "already running"}), 409
        state.running = True
        state.stop_requested = False
        state.started_at = time.time()
        state.stats = {"discovered": 0, "uploaded": 0, "failed": 0, "pages_crawled": 0}
        state.logs = []

    state.thread = threading.Thread(
        target=_run_crawler,
        args=(max_pages, max_depth, domain_limit, seed_file),
        daemon=True,
    )
    state.thread.start()
    return jsonify({"ok": True})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    with state.lock:
        if not state.running:
            return jsonify({"error": "not running"}), 409
        state.stop_requested = True
    state.add_log("Stop requested", "info")
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055, debug=False)
