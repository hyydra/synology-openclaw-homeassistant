# Source Discovery Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bounded Python crawler that discovers historically relevant Hungarian/Pécs web and photo sources, including dead/orphaned sites preserved only through archive evidence, then validates and stores candidates for the existing Retro Kereső indexer.

**Architecture:** Scrapy handles bounded crawling, queueing, retries, throttling, and normal extraction. Scrapling is isolated as fallback-only for malformed/legacy pages. Deterministic scoring ranks Pécs/Hungary/photo/orphan relevance; Wayback CDX validates archival value; SQLite stores discovery state separately from `retro.sqlite`.

**Tech Stack:** Python 3.11+, Scrapy, Scrapling, pytest, sqlite3, urllib.parse, dataclasses, standard-library JSON/logging.

**Spec:** `docs/superpowers/specs/2026-08-25-source-discovery-crawler-design.md` plus `docs/superpowers/specs/2026-08-25-orphan-site-discovery-addendum.md`

## Global Constraints

- All explanatory code comments/docstrings are English.
- Scrapy is primary; Scrapling is fallback-only.
- No retro-browser emulation.
- No Tor/onion/dark-web crawling.
- No bulk image mirroring in v1.
- No unbounded crawling or CDX enumeration.
- Core tests run offline.
- Discovery DB: `retro-data/discovery.sqlite`.
- Discovery log: `retro-data/logs/discovery.log`.
- Existing PHP indexer remains the production ingestion path.

---

### Task 1: Python skeleton and bounded CLI

**Files:**
- Create: `pyproject.toml`
- Create: `requirements-crawler.txt`
- Create: `pytest.ini`
- Create: `crawler/__init__.py`
- Create: `crawler/discover.py`
- Create: `crawler/seeds/pecs.txt`
- Test: `tests/python/test_cli.py`

**Interfaces:**
- Produces: `build_parser() -> argparse.ArgumentParser`
- Produces: `parse_args(argv: list[str]) -> argparse.Namespace`

- [ ] Write failing tests asserting defaults: `max_pages=500`, `max_depth=2`, `domain_limit=50`, `archive_depth=1`, `cdx_validate=False`, `discover_orphans=False`.
- [ ] Add tests rejecting `max_pages <= 0`, `domain_limit <= 0`, and `archive_depth` outside `0..3`.
- [ ] Run `pytest tests/python/test_cli.py -v` and verify RED.
- [ ] Implement minimal CLI with `--seed-file`, `--max-pages`, `--max-depth`, `--domain-limit`, `--cdx-validate`, `--discover-orphans`, `--archive-depth`, `--dry-run`.
- [ ] Add initial seeds: `pecs.hu`, `pte.hu`, `fotozz.hu`, `indafoto.hu`.
- [ ] Run test GREEN and commit `feat: scaffold discovery crawler`.

### Task 2: URL/domain normalization

**Files:**
- Create: `crawler/normalize.py`
- Test: `tests/python/test_normalize.py`

**Interfaces:**
- `normalize_url(url: str) -> str | None`
- `normalize_domain(url_or_domain: str) -> str | None`

- [ ] Write failing tests for host lowercasing, fragment removal, default-port stripping, dot-segment normalization, rejecting non-http schemes, and preserving unusual percent-encoded historical paths.
- [ ] Run RED.
- [ ] Implement with `urllib.parse` and deterministic normalization.
- [ ] Run GREEN and commit `feat: normalize discovery urls`.

### Task 3: Candidate and evidence models

**Files:**
- Create: `crawler/models.py`
- Test: `tests/python/test_models.py`

**Interfaces:**
- `DiscoveryCandidate` dataclass.
- `DiscoveryEvidence` dataclass.
- `ExtractedLink` dataclass.
- `CdxSummary` dataclass.
- `ScoreBreakdown` dataclass.

Required candidate fields include URL/domain, discovery source/method, live state, orphan flag, anchor/nearby text, and review state.

- [ ] Write failing construction/validation tests.
- [ ] Run RED.
- [ ] Implement dataclasses with explicit types and safe defaults.
- [ ] Run GREEN and commit `feat: model discovery candidates`.

### Task 4: Deterministic scoring

**Files:**
- Create: `crawler/scoring.py`
- Test: `tests/python/test_scoring.py`

**Interfaces:**
- `score_candidate(candidate: DiscoveryCandidate, evidence: list[DiscoveryEvidence] = []) -> ScoreBreakdown`

- [ ] Write failing test proving a `Pécsi fotógaléria / Uránváros` candidate scores above a generic `.com` page.
- [ ] Add failing accent/unaccented tests (`Pécs/Pecs`, `fotó/foto`, `Széchenyi/Szechenyi`).
- [ ] Add failing orphan test: dead URL + CDX captures + archived Pécs referrer gets positive orphan score.
- [ ] Run RED.
- [ ] Implement explainable component scores: `pecs`, `hungary`, `photo`, `orphan`, `archive`, `total`, `reasons`.
- [ ] Run GREEN and commit `feat: score historical source candidates`.

### Task 5: Structured discovery logging

**Files:**
- Create: `crawler/logging_utils.py`
- Test: `tests/python/test_logging_utils.py`

**Interfaces:**
- `sanitize_context(value: object) -> object`
- `write_log(event: str, level: str, context: dict, path: Path, run_id: str) -> None`

- [ ] Write failing recursive-redaction tests for password/token/cookie/authorization/session/api-key keys.
- [ ] Run RED.
- [ ] Implement JSONL logging with UTC timestamp, severity, run id, event and sanitized context.
- [ ] Run GREEN and commit `feat: add discovery structured logging`.

### Task 6: SQLite discovery persistence

**Files:**
- Create: `crawler/storage.py`
- Test: `tests/python/test_storage.py`

**Interfaces:**
- `open_discovery_db(path) -> sqlite3.Connection`
- `ensure_schema(db) -> None`
- `upsert_candidate(db, candidate, score) -> int`
- `record_evidence(db, candidate_id, evidence) -> int`
- `record_cdx(db, candidate_id, summary) -> None`

Tables: `discovery_candidates`, `discovery_evidence`, `discovery_cdx`, `discovery_runs`.

- [ ] Write failing schema, dedupe, evidence accumulation, and orphan evidence persistence tests.
- [ ] Run RED.
- [ ] Implement schema and upserts; store score components individually.
- [ ] Run GREEN and commit `feat: persist discovery candidates`.

### Task 7: Standard extractor + Scrapling fallback

**Files:**
- Create: `crawler/extractors/__init__.py`
- Create: `crawler/extractors/standard.py`
- Create: `crawler/extractors/scrapling_fallback.py`
- Test: `tests/python/test_fallback.py`

**Interfaces:**
- `extract_links_standard(html: str, base_url: str) -> list[ExtractedLink]`
- `should_use_scrapling(html: str, links: list[ExtractedLink]) -> bool`
- `extract_links_with_scrapling(html: str, base_url: str) -> list[ExtractedLink]`

- [ ] Write failing tests proving fallback is not used when standard extraction succeeds.
- [ ] Add failing test proving non-empty malformed/legacy HTML with zero useful links triggers fallback.
- [ ] Run RED.
- [ ] Implement standard extraction first, then isolated Scrapling adapter with local import.
- [ ] Run GREEN and commit `feat: add scrapling extraction fallback`.

### Task 8: Wayback CDX validation and bounded enumeration

**Files:**
- Create: `crawler/cdx.py`
- Test: `tests/python/test_cdx.py`

**Interfaces:**
- `build_cdx_url(target: str, limit: int = 200) -> str`
- `parse_cdx_rows(payload: str) -> CdxSummary`
- `validate_candidate(target: str, client, limit: int = 200) -> CdxSummary`
- `enumerate_archived_urls(target: str, client, limit: int = 200) -> list[str]`

- [ ] Write static-fixture tests for earliest/latest capture, malformed rows, and representative URL.
- [ ] Write failing test enforcing CDX limits `1..200`.
- [ ] Write failing bounded-enumeration test.
- [ ] Run RED.
- [ ] Implement parser/client boundary with explicit timeouts, retries and exponential backoff in runtime client.
- [ ] Run GREEN and commit `feat: validate discovery candidates with cdx`.

### Task 9: Orphan/dead-site classification

**Files:**
- Create: `crawler/orphans.py`
- Test: `tests/python/test_orphans.py`

**Interfaces:**
- `classify_orphan(live_ok: bool | None, cdx: CdxSummary, archived_referrers: int) -> tuple[bool, tuple[str, ...]]`
- `can_expand_archive(depth: int, max_archive_depth: int) -> bool`

- [ ] Write failing test: live dead + CDX captures + archived referrer => orphan true.
- [ ] Write failing test: live alive => not orphan solely because CDX exists.
- [ ] Write failing recursion-bound tests for `archive_depth=0..3`.
- [ ] Run RED.
- [ ] Implement deterministic classification and bounds.
- [ ] Run GREEN and commit `feat: classify orphaned historical sites`.

### Task 10: Scrapy spider integration

**Files:**
- Create: `crawler/settings.py`
- Create: `crawler/spiders/__init__.py`
- Create: `crawler/spiders/discovery.py`
- Modify: `crawler/discover.py`
- Test: `tests/python/test_spider.py`

**Interfaces:**
- `DiscoverySpider` consumes normalization, extraction, scoring, storage, optional CDX validation, and orphan classification.

Required Scrapy bounds:
- `DEPTH_LIMIT = max_depth`
- `CLOSESPIDER_PAGECOUNT = max_pages`
- bounded `CONCURRENT_REQUESTS_PER_DOMAIN`
- non-zero `DOWNLOAD_DELAY`
- AutoThrottle enabled

- [ ] Write failing settings tests proving the bounds are applied.
- [ ] Write failing parse test using local HTML fixture with Pécs photo links and generic links.
- [ ] Write failing archived-referrer test that emits `archive_link`/`dead_link` evidence when orphan mode is enabled.
- [ ] Run RED.
- [ ] Implement spider and orchestration.
- [ ] Run GREEN and commit `feat: crawl historical source candidates`.

### Task 11: Promotion/export boundary

**Files:**
- Create: `crawler/promotion.py`
- Test: `tests/python/test_promotion.py`

**Interfaces:**
- `eligible_for_promotion(row: Mapping[str, object]) -> bool`
- `export_approved_sources(db, path: Path) -> int`

- [ ] Write failing tests: `new` candidates never auto-export; `approved` candidate with CDX captures exports once; rejected candidate never exports.
- [ ] Run RED.
- [ ] Implement deterministic export to a plain normalized domain list consumable by the PHP indexer.
- [ ] Run GREEN and commit `feat: export approved crawler sources`.

### Task 12: Full verification and documentation

**Files:**
- Modify: `README.md`
- Modify: `.gitignore`
- Add or modify: `tests/run.php` only if needed to keep PHP suite unchanged/compatible.

- [ ] Add `retro-data/discovery.sqlite*`, `retro-data/logs/*.log`, Python caches and virtualenv files to ignore rules where repo-relative rules apply.
- [ ] Document install/run commands, crawler bounds, orphan-site semantics, Scrapy/Scrapling roles, and promotion workflow.
- [ ] Run `pytest tests/python -v`.
- [ ] Run existing PHP test suite and syntax checks.
- [ ] Run a bounded dry run: `python -m crawler.discover --max-pages 20 --max-depth 1 --discover-orphans --archive-depth 1 --dry-run`.
- [ ] Verify no production DB mutation and no secret leakage in logs.
- [ ] Commit `docs: document source discovery crawler`.

## Completion Criteria

- Python suite passes offline.
- Existing PHP suite still passes.
- Scrapy is primary and Scrapling fallback-only.
- Pécs/photo candidates rank above generic content.
- Dead/orphaned sites can be discovered from archive evidence.
- Archive recursion and CDX enumeration remain bounded.
- Discovery data and logs remain outside public webroot.
- Only approved candidates can be exported to the existing indexer.
