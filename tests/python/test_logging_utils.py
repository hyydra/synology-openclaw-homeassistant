import json
from pathlib import Path

from crawler.logging_utils import sanitize_context, write_log


def test_secret_keys_are_redacted_recursively():
    value = sanitize_context({
        "token": "abc",
        "nested": {"authorization": "Bearer secret", "url": "https://example.hu"},
        "session_id": "secret-session",
    })
    assert value["token"] == "[REDACTED]"
    assert value["nested"]["authorization"] == "[REDACTED]"
    assert value["nested"]["url"] == "https://example.hu"
    assert value["session_id"] == "[REDACTED]"


def test_write_log_emits_jsonl(tmp_path: Path):
    path = tmp_path / "discovery.log"
    write_log("candidate_found", "info", {"url": "https://pecs.hu/"}, path, "run-1")
    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert payload["event"] == "candidate_found"
    assert payload["run_id"] == "run-1"
    assert payload["context"]["url"] == "https://pecs.hu/"
