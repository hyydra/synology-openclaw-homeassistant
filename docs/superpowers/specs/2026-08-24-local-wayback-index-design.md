# Local Wayback Index Design

## Goal

Turn Retro Kereső into a fast keyword search over locally indexed Wayback Machine snapshots from a curated set of Pécs and nearby websites.

The browser search must search page text, not only URLs, and normal searches must not depend on live Wayback availability.

## User-facing search

The existing single search input becomes a keyword search input. Example searches:

- `pécs`
- `zsolnay`
- `uránváros`
- `bányászat`
- `széchenyi tér`

A short description appears with the search field:

> Keress kulcsszavakra Pécs és környéke archivált weboldalain. A találatok a Wayback Machine-ből helyben indexelt oldalak szövegében keresnek.

The source list will be expanded later, so source/domain configuration must remain separate from the UI and search implementation.

## Source scope

Only domains explicitly listed as Pécs or nearby sources are indexed. The source list is manually editable in the first version and can later be replaced or augmented by an administration interface.

The indexer must never discover and index arbitrary external domains automatically merely because an archived page links to them.

## Architecture

The system has two separate execution paths:

1. **Indexer path** — an SSH/CLI process fetches Wayback metadata and snapshots, stores local copies, extracts text, and updates the SQLite full-text index.
2. **Search path** — the authenticated web API queries only the local SQLite index and returns results immediately without contacting Wayback.

This separation prevents slow or unavailable Wayback requests from blocking browser searches.

## Storage

Continue using the existing writable `data/` area and SQLite database.

Local snapshot files are stored under a non-public or HTTP-blocked archive directory, conceptually:

```text
data/
  retro.sqlite
  archive/
    <domain>/
      <timestamp>-<hash>.html
```

Each archived page has metadata including:

- source domain
- original URL
- Wayback timestamp
- Wayback archive URL
- local file path
- page title
- extracted visible text
- indexing timestamp

The implementation may normalize these names into an `archive_pages` table or equivalent schema.

## Full-text search

Use SQLite FTS5 when available on the Hostinger PHP/SQLite runtime.

The full-text index covers at least:

- title
- extracted visible page text

Search results are ranked using SQLite FTS relevance. The implementation should produce a short snippet around matching terms where feasible.

If FTS5 is unavailable on the production runtime, implementation must stop and report the environment limitation rather than silently falling back to an unbounded `%LIKE%` scan of all archived text.

## HTML processing

For each selected Wayback snapshot:

1. Download the archived HTML.
2. Save the raw HTML locally.
3. Parse the document.
4. Remove non-content elements such as `script`, `style`, `noscript`, and similar markup that should not be searchable.
5. Extract the page title.
6. Convert visible text to normalized searchable UTF-8 text.
7. Store metadata and searchable text in SQLite/FTS.

HTML parsing failures affect only the current snapshot and must not terminate the entire indexing run.

## Indexing command

The first version is manually started over SSH:

```bash
php bin/index-wayback.php
```

Automatic cron execution is explicitly deferred to a later change.

The indexer processes a configurable local-domain list. It obtains candidate snapshots from the Wayback CDX API, downloads selected HTML snapshots, and indexes them.

### Limits and politeness

The first version must use bounded work per run. Defaults should be conservative and configurable, with an intended range of roughly 100–200 new snapshot candidates per domain per run.

The indexer should:

- avoid downloading a snapshot already indexed
- use HTTP connection and total timeouts
- continue after individual CDX or snapshot failures
- pause modestly between external requests where appropriate
- print progress to stdout
- print a final summary of indexed, skipped, and failed pages

One slow or broken archived page must not block all remaining domains.

## Duplicate handling

A snapshot must have a stable uniqueness rule, based at minimum on original URL plus Wayback timestamp, or an equivalent unique identifier.

Already indexed snapshots are skipped. Re-running the indexer is therefore safe and incrementally adds only missing snapshots unless a future explicit rebuild option is introduced.

## Search API

The current authenticated search API changes from live URL/CDX lookup to local keyword search.

The API accepts a keyword or phrase and queries the FTS index. It must not prepend `https://` or otherwise treat the query as a URL.

The response contains a bounded number of ranked results with fields sufficient for the UI, including:

- title
- original URL/domain
- Wayback timestamp/date
- matching text snippet
- Wayback archive URL

The existing login/session protection remains unchanged.

If the local index is empty, the API should return a successful empty result with a user-understandable state rather than attempting a live Wayback fallback.

## Browser UI

Keep the existing compact visual direction: no large hero typography.

The search area contains:

- a keyword input
- the short explanatory description approved above
- a search button

Result cards show:

- page title, with a reasonable fallback when missing
- original URL/domain
- archive date
- matching snippet
- `Megnyitás a Waybacken` action

A local-copy viewing action is deferred. Local HTML is retained primarily as source material for indexing and future features.

## Security

The existing password/session protection remains in place.

Local raw HTML must not become anonymously browsable simply because it is stored on the server. Prefer storing it outside the public webroot when practical; otherwise explicitly deny direct HTTP access.

The indexer must treat downloaded HTML as untrusted data. It must never execute downloaded PHP, JavaScript, shell content, or server-side directives.

The browser UI must continue rendering result data through safe DOM text assignment rather than interpolating archived HTML into the live application page.

## Error handling

Browser search errors are limited to local application/database failures; normal search must not expose Wayback network timeouts because it does not contact Wayback.

Indexer errors are reported per domain/snapshot and summarized at the end. A transient Wayback failure must not corrupt previously indexed data.

Database writes should use transactions where they improve consistency.

## Migration from the current search

The current direct Wayback URL search endpoint is replaced as the primary browser search behavior.

Existing search-log/result tables may be retained, migrated, or retired as implementation dictates, but the new archive-page and FTS schema must have clear ownership and must not depend on the old live-result structure.

No automatic deletion of the current SQLite database should occur during deployment.

## Testing and verification

Implementation must include automated tests for at least:

- domain/source configuration parsing
- snapshot uniqueness / duplicate skipping
- HTML title and visible-text extraction
- FTS schema/search behavior where SQLite FTS5 is available
- keyword API contract (query is treated as text, not URL)
- empty-index behavior
- result-card fields expected by the frontend
- security contract preventing direct exposure of stored archive HTML

Production verification should include:

```bash
php -r '$db=new PDO("sqlite::memory:"); print_r($db->query("pragma compile_options")->fetchAll(PDO::FETCH_COLUMN));'
```

or an equivalent FTS5 capability check, plus PHP syntax checks and the project test suite.

## Deferred work

Not included in the first implementation:

- cron/automatic scheduled indexing
- browser-based source administration
- automatic geographic classification of arbitrary websites
- semantic/AI/vector search
- local archived-page viewer
- asset mirroring for CSS/images
- crawling links beyond configured source domains
- unlimited historical ingestion in one run

## Success criteria

The first version is successful when:

1. A configured Pécs-area domain can be indexed from Wayback using the CLI command.
2. Raw snapshot HTML is retained locally and its visible text is indexed in SQLite FTS5.
3. Re-running the indexer skips already indexed snapshots.
4. Typing a keyword such as `pécs` in the authenticated web UI searches local archived page text rather than constructing a URL.
5. Results appear as compact cards with title, URL/domain, archive date, snippet, and Wayback link.
6. Browser searches remain fast and functional even when the Wayback Machine is temporarily slow or unavailable.
