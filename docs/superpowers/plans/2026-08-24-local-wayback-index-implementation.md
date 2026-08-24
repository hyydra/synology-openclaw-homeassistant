# Local Wayback Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace live browser-side Wayback URL lookup with fast keyword search over locally stored and SQLite FTS5-indexed Wayback snapshots from a curated set of Pécs-area domains.

**Architecture:** A CLI indexer fetches CDX metadata and archived HTML for configured source domains, saves raw snapshots locally, extracts visible text, and stores searchable metadata in SQLite with FTS5. The authenticated web API queries only the local index; the browser UI submits plain keywords and renders ranked cards with snippets and Wayback links.

**Tech Stack:** PHP 8+, PDO SQLite, SQLite FTS5, cURL, DOMDocument/DOMXPath, vanilla JavaScript, HTML/CSS.

**Spec:** `docs/superpowers/specs/2026-08-24-local-wayback-index-design.md`

## Global Constraints

- Keep the existing password/session protection unchanged.
- Normal browser searches must not contact the Wayback Machine.
- Index only explicitly configured Pécs/nearby source domains.
- Keep raw archived HTML non-public.
- Use SQLite FTS5; if unavailable in production, stop and report the limitation instead of silently falling back to unbounded `%LIKE%` scans.
- Keep indexer work bounded per run; intended default range is roughly 100–200 new snapshot candidates per domain.
- Do not automatically delete the existing SQLite database during deployment.
- First version is manually started with `php bin/index-wayback.php`; cron is deferred.
- Keep the compact UI; no large hero typography.
- Browser result rendering must use safe DOM text assignment, never archived HTML injection.

---

## File Structure

- Create `lib/archive.php` — shared SQLite schema, FTS capability checks, HTML text extraction, source parsing, archive-path helpers, and local search functions.
- Create `config/sources.php` — curated, manually editable source-domain list and indexer limits.
- Create `bin/index-wayback.php` — CLI orchestration for CDX discovery, snapshot downloading, local storage, deduplication, and progress reporting.
- Modify `api.php` — replace live Wayback search action with authenticated local keyword search.
- Modify `index.php` — change copy/input semantics from URL search to keyword search and add the approved explanatory description.
- Modify `app.js` — stop prepending `https://`; submit keyword query and render title/domain/date/snippet/Wayback link.
- Modify `styles.css` — small styles for description/snippet/domain fields while preserving compact layout.
- Modify `.gitignore` — ensure local snapshot files and generated SQLite files remain untracked.
- Modify `README.md` — document FTS5 check, source configuration, indexing command, storage location, and verification steps.
- Create focused tests under `tests/` for source config, extraction, schema/FTS, duplicate handling, API contract, UI contract, and archive exposure.

---

### Task 1: Shared archive library and FTS schema

**Files:**
- Create: `lib/archive.php`
- Test: `tests/archive_schema_test.php`
- Test: `tests/html_extract_test.php`

**Interfaces:**
- Produces: `retroArchiveDatabase(?string $path = null): PDO`
- Produces: `retroRequireFts5(PDO $db): void`
- Produces: `retroEnsureArchiveSchema(PDO $db): void`
- Produces: `retroExtractArchivedPage(string $html): array{title:string,text:string}`
- Produces: `retroArchiveSnapshotKey(string $originalUrl, string $timestamp): string`

- [ ] **Step 1: Write the failing FTS/schema test**

Create `tests/archive_schema_test.php` that opens a temporary SQLite database, calls the planned schema helpers, asserts an `archive_pages` table exists, asserts a unique rule covers original URL + timestamp, and verifies an FTS5 table can be queried.

- [ ] **Step 2: Run the schema test and verify it fails**

Run: `php tests/archive_schema_test.php`

Expected: FAIL because `lib/archive.php` and its functions do not exist yet.

- [ ] **Step 3: Write the failing HTML extraction test**

Create `tests/html_extract_test.php` with sample HTML containing `<title>`, visible text, `<script>`, `<style>`, and `<noscript>`. Assert title is extracted, visible text remains, and script/style/noscript content is absent.

- [ ] **Step 4: Run the extraction test and verify it fails**

Run: `php tests/html_extract_test.php`

Expected: FAIL because extraction helpers do not exist yet.

- [ ] **Step 5: Implement the minimal shared library**

In `lib/archive.php`, add:

- database opening with PDO exception mode
- `retroRequireFts5()` using a minimal temporary FTS5 table probe or equivalent explicit capability check
- schema creation for `archive_pages`
- FTS5 virtual table linked to searchable title/text fields, with a synchronization strategy that is simple and explicit
- a stable snapshot key / unique constraint using original URL + timestamp
- DOM-based extraction that removes non-content nodes before normalized UTF-8 text extraction

Keep the file focused; do not add network fetching yet.

- [ ] **Step 6: Run both tests and verify they pass**

Run:

```bash
php tests/archive_schema_test.php
php tests/html_extract_test.php
php -l lib/archive.php
```

Expected: both tests print PASS and syntax check reports no errors.

- [ ] **Step 7: Commit**

Commit message: `feat: add local archive schema and text extraction`

---

### Task 2: Source configuration and validation

**Files:**
- Create: `config/sources.php`
- Modify: `lib/archive.php`
- Test: `tests/source_config_test.php`

**Interfaces:**
- Consumes: shared archive library from Task 1.
- Produces: `retroLoadSources(string $path): array`
- Produces: normalized source entries with at least `domain` and per-run `limit` values.

- [ ] **Step 1: Write the failing source config test**

Create `tests/source_config_test.php` that loads a temporary/config fixture and asserts:

- valid domains normalize consistently
- blank/invalid entries are rejected
- duplicate domains are deduplicated or rejected deterministically
- per-domain limit stays bounded

- [ ] **Step 2: Run the test and verify it fails**

Run: `php tests/source_config_test.php`

Expected: FAIL because source parsing is not implemented.

- [ ] **Step 3: Add the initial source config**

Create `config/sources.php` as a plain PHP array. Start with a deliberately small curated list rather than pretending coverage is complete. Keep all sources in one editable file so they can be expanded later without UI changes.

- [ ] **Step 4: Implement parsing/validation**

Add `retroLoadSources()` to `lib/archive.php`. Normalize domains to lowercase ASCII where possible, reject schemes/paths in domain fields, enforce sensible integer limits, and return deterministic entries.

- [ ] **Step 5: Run test and syntax checks**

Run:

```bash
php tests/source_config_test.php
php -l config/sources.php
php -l lib/archive.php
```

Expected: PASS and no syntax errors.

- [ ] **Step 6: Commit**

Commit message: `feat: add curated archive source configuration`

---

### Task 3: Snapshot persistence and duplicate skipping

**Files:**
- Modify: `lib/archive.php`
- Test: `tests/archive_storage_test.php`

**Interfaces:**
- Consumes: `retroEnsureArchiveSchema()`, `retroExtractArchivedPage()`, snapshot key helper.
- Produces: `retroArchivePath(string $baseDir, string $domain, string $timestamp, string $originalUrl): string`
- Produces: `retroSnapshotExists(PDO $db, string $originalUrl, string $timestamp): bool`
- Produces: `retroStoreSnapshot(PDO $db, array $metadata, string $html, string $archiveBaseDir): int`

- [ ] **Step 1: Write the failing persistence test**

Create `tests/archive_storage_test.php` using temporary directories/database. Assert that storing one snapshot:

- writes one HTML file
- inserts one metadata row
- populates FTS content
- returns/skips safely when the exact URL+timestamp is stored again
- creates no executable `.php` archive files

- [ ] **Step 2: Run it and verify it fails**

Run: `php tests/archive_storage_test.php`

Expected: FAIL because persistence helpers do not exist.

- [ ] **Step 3: Implement snapshot persistence**

In `lib/archive.php`, implement deterministic safe filenames, directory creation, raw HTML writing, metadata insertion, and FTS synchronization inside a transaction where appropriate. Never derive an executable extension from the source URL; use `.html` only.

- [ ] **Step 4: Run test and syntax check**

Run:

```bash
php tests/archive_storage_test.php
php -l lib/archive.php
```

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: persist archived snapshots locally`

---

### Task 4: Wayback CLI indexer

**Files:**
- Create: `bin/index-wayback.php`
- Modify: `lib/archive.php`
- Test: `tests/indexer_contract_test.php`

**Interfaces:**
- Consumes: source configuration, archive schema, duplicate check, snapshot storage.
- Produces: CLI command `php bin/index-wayback.php`
- Produces: bounded CDX query builder and snapshot URL builder helpers suitable for contract testing.

- [ ] **Step 1: Write the failing indexer contract test**

Create `tests/indexer_contract_test.php` that verifies source-domain CDX queries:

- request HTML snapshots only
- use bounded `limit`
- include wildcard/domain scope deliberately
- do not contain user browser search text
- use a duplicate-friendly deterministic timestamp/original URL result shape

Also assert the CLI script references configured sources and local archive storage rather than browser/session code.

- [ ] **Step 2: Run it and verify it fails**

Run: `php tests/indexer_contract_test.php`

Expected: FAIL because the indexer does not exist.

- [ ] **Step 3: Implement network helpers**

In `lib/archive.php`, add small helpers for:

- CDX URL construction per configured domain
- cURL JSON fetch with connect/total timeouts
- archived snapshot fetch with connect/total timeouts
- Wayback archive URL construction

Return structured errors instead of exiting inside helpers.

- [ ] **Step 4: Implement the CLI orchestration**

In `bin/index-wayback.php`:

- refuse non-CLI execution
- load config
- verify FTS5 before network work
- iterate sources
- fetch bounded candidate rows
- skip duplicates before snapshot download
- download HTML snapshots one at a time
- save/index valid HTML
- continue after per-item failures
- print progress plus final indexed/skipped/failed counts
- pause modestly between external requests

Do not add cron behavior.

- [ ] **Step 5: Run contract test and syntax checks**

Run:

```bash
php tests/indexer_contract_test.php
php -l bin/index-wayback.php
php -l lib/archive.php
```

Expected: PASS and no syntax errors.

- [ ] **Step 6: Perform a dry production capability check on Hostinger**

Run:

```bash
php -r '$db=new PDO("sqlite::memory:"); $db->exec("CREATE VIRTUAL TABLE t USING fts5(body)"); echo "FTS5 OK\n";'
```

Expected: `FTS5 OK`. If this fails, stop implementation rollout and report the hosting limitation.

- [ ] **Step 7: Commit**

Commit message: `feat: add bounded Wayback archive indexer`

---

### Task 5: Local full-text search service

**Files:**
- Modify: `lib/archive.php`
- Test: `tests/local_search_test.php`

**Interfaces:**
- Consumes: FTS schema and stored archive pages.
- Produces: `retroSearchArchive(PDO $db, string $query, int $limit = 20): array`
- Result fields: `title`, `original`, `domain`, `timestamp`, `snippet`, `archiveUrl`.

- [ ] **Step 1: Write the failing local search test**

Seed a temporary archive database with multiple pages, including accented Hungarian text. Assert:

- `pécs` matches page text
- irrelevant pages are excluded
- result count is bounded
- each result exposes required fields
- snippet contains useful nearby text
- no network access is required

- [ ] **Step 2: Run it and verify it fails**

Run: `php tests/local_search_test.php`

Expected: FAIL because `retroSearchArchive()` does not exist.

- [ ] **Step 3: Implement local FTS search**

Use FTS5 `MATCH`, ranking (e.g. `bm25()`), and `snippet()`/equivalent safe result extraction. Normalize or safely construct query syntax so ordinary user punctuation does not create SQL/FTS errors. Keep a hard result limit.

- [ ] **Step 4: Run test and syntax check**

Run:

```bash
php tests/local_search_test.php
php -l lib/archive.php
```

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add local full text archive search`

---

### Task 6: Replace live search API with keyword API

**Files:**
- Modify: `api.php`
- Test: `tests/keyword_api_contract_test.php`
- Modify or retire where appropriate: `tests/wayback_query_test.php`, `tests/fast_wayback_mode_test.php`

**Interfaces:**
- Consumes: `retroArchiveDatabase()`, `retroSearchArchive()`.
- Browser request: `GET /api.php?action=search&q=<keyword>` (or an equally explicit keyword parameter chosen consistently across API and frontend).
- Produces JSON: `{ "query": "...", "results": [...] }`.

- [ ] **Step 1: Write the failing API contract test**

Assert source code/isolated endpoint behavior shows:

- query is treated as text, not URL
- API does not prepend `https://`
- search action does not call Wayback/cURL
- unauthenticated access remains 401
- empty local index returns 200 with `results: []`

- [ ] **Step 2: Run it and verify it fails**

Run: `php tests/keyword_api_contract_test.php`

Expected: FAIL because `api.php` still performs live CDX lookup.

- [ ] **Step 3: Replace the search branch**

Keep login/logout/session code intact. For `action=search`, validate a bounded plain-text query, open the local archive database, run `retroSearchArchive()`, and return results. Remove temporary upstream diagnostic fields and live Wayback cURL logic from browser search.

- [ ] **Step 4: Update obsolete Wayback-browser tests**

Delete or rewrite tests whose contract explicitly requires live browser CDX querying. Preserve indexer-specific CDX tests under Task 4 instead.

- [ ] **Step 5: Run API/auth tests**

Run:

```bash
php tests/keyword_api_contract_test.php
php tests/auth_test.php
php tests/security_contract_test.php
php -l api.php
```

Expected: all PASS and no syntax errors.

- [ ] **Step 6: Commit**

Commit message: `feat: search local archive index from api`

---

### Task 7: Keyword-search UI and result cards

**Files:**
- Modify: `index.php`
- Modify: `app.js`
- Modify: `styles.css`
- Test: `tests/keyword_ui_test.php`
- Modify: `tests/simple_app_ui_test.php`

**Interfaces:**
- Consumes API result fields from Task 6.
- Produces compact keyword search UI with approved description and result cards.

- [ ] **Step 1: Write the failing UI contract test**

Create `tests/keyword_ui_test.php` asserting `index.php` contains:

- keyword-oriented label/placeholder
- approved description exactly: `Keress kulcsszavakra Pécs és környéke archivált weboldalain. A találatok a Wayback Machine-ből helyben indexelt oldalak szövegében keresnek.`
- no URL-specific example placeholder such as `example.com/*`

Assert `app.js`:

- does not prepend `https://`
- sends the keyword parameter
- renders title, URL/domain, timestamp/date, snippet, and Wayback action using DOM text properties

- [ ] **Step 2: Run it and verify it fails**

Run: `php tests/keyword_ui_test.php`

Expected: FAIL because current UI is URL-oriented.

- [ ] **Step 3: Update `index.php` copy and semantics**

Keep the compact top bar and authentication view. Change the search label/input to keyword semantics and add the approved description near the field.

- [ ] **Step 4: Update `app.js` request and rendering**

Remove URL normalization. Submit plain trimmed keyword text. Render:

- fallback title when empty
- original URL/domain
- formatted archive date
- snippet as text
- Wayback link

Keep current loading/empty/error handling concise.

- [ ] **Step 5: Add minimal styles**

Add only the CSS needed for description and snippet hierarchy. Preserve small typography and current responsive card layout.

- [ ] **Step 6: Run UI tests**

Run:

```bash
php tests/keyword_ui_test.php
php tests/simple_app_ui_test.php
php tests/login_minimal_test.php
php -l index.php
```

Expected: all PASS.

- [ ] **Step 7: Commit**

Commit message: `feat: add keyword archive search interface`

---

### Task 8: Protect local archive files and ignore generated data

**Files:**
- Modify: `.gitignore`
- Create or modify: `data/.htaccess`
- Test: `tests/archive_security_test.php`

**Interfaces:**
- Consumes: archive storage path from Tasks 1–3.
- Produces: generated snapshots excluded from Git and denied direct HTTP access when stored under webroot.

- [ ] **Step 1: Write the failing security test**

Assert:

- `.gitignore` excludes `data/archive/`
- `data/.htaccess` denies access broadly enough to cover SQLite and archived HTML
- no application route directly serves arbitrary `local_path` files

- [ ] **Step 2: Run it and verify it fails**

Run: `php tests/archive_security_test.php`

Expected: FAIL until explicit archive protections are present.

- [ ] **Step 3: Add ignore and HTTP-deny rules**

Keep generated SQLite patterns and add `data/archive/`. Add Apache deny rules compatible with Hostinger so direct requests to `data/` cannot expose raw HTML/database content.

- [ ] **Step 4: Run security tests**

Run:

```bash
php tests/archive_security_test.php
php tests/security_contract_test.php
```

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `security: protect local archive storage`

---

### Task 9: Documentation and end-to-end production verification

**Files:**
- Modify: `README.md`
- Test: full project test suite

**Interfaces:**
- Documents all operator commands and production expectations.

- [ ] **Step 1: Update README**

Document:

- what local indexing does
- how to edit `config/sources.php`
- FTS5 requirement/check
- `php bin/index-wayback.php`
- generated archive/SQLite locations
- that browser searches are local and do not call Wayback
- how to expand sources later
- security note that `data/` must not be publicly browsable

- [ ] **Step 2: Pull/deploy on Hostinger**

Run:

```bash
cd ~/domains/pecscitythings.eu/public_html
git pull
```

- [ ] **Step 3: Verify FTS5 and PHP syntax in production**

Run:

```bash
php -r '$db=new PDO("sqlite::memory:"); $db->exec("CREATE VIRTUAL TABLE t USING fts5(body)"); echo "FTS5 OK\n";'
php -l lib/archive.php
php -l bin/index-wayback.php
php -l api.php
php -l index.php
```

Expected: `FTS5 OK` and no syntax errors.

- [ ] **Step 4: Run the complete project test suite**

Run all `tests/*.php` tests explicitly or via a simple shell loop, for example:

```bash
for test in tests/*.php; do echo "== $test =="; php "$test" || exit 1; done
```

Expected: every test exits 0.

- [ ] **Step 5: Run a deliberately small first index**

Temporarily keep source limits conservative in `config/sources.php`, then run:

```bash
php bin/index-wayback.php
```

Expected: progress output and a final indexed/skipped/failed summary; at least one configured domain should store one or more pages if Wayback has usable captures.

- [ ] **Step 6: Re-run the indexer to verify duplicate skipping**

Run again:

```bash
php bin/index-wayback.php
```

Expected: previously stored URL+timestamp snapshots are reported/skipped instead of downloaded and inserted again.

- [ ] **Step 7: Verify browser search while Wayback is irrelevant**

Log in to the site and search a term known to exist in the indexed sample (for example `pécs` if present). Verify cards show title, URL/domain, date, snippet, and Wayback link. Then verify the API response comes from local SQLite even if no live Wayback request is made.

- [ ] **Step 8: Commit documentation**

Commit message: `docs: document local Wayback indexing workflow`

---

## Completion Gate

Before declaring the feature complete:

- all automated tests pass on the deployment environment
- FTS5 is confirmed available on Hostinger
- at least one configured source has been successfully indexed
- duplicate re-run behavior is verified
- keyword browser search returns locally indexed content
- browser search makes no live Wayback/CDX network request
- `data/` and raw snapshots are not directly accessible over HTTP
- existing login/logout/session behavior still works
