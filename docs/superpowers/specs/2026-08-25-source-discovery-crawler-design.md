# Retro Kereső Source Discovery Crawler Design

## Purpose

Add a Python-based source-discovery subsystem that finds historically relevant Hungarian/Pécs websites and archived photo-community pages, validates them against Wayback CDX, ranks them, and stores candidates for later ingestion by the existing Retro Kereső PHP/SQLite indexer.

The crawler is a discovery layer, not a replacement for the existing indexer.

## Goals

- Discover long-gone Hungarian websites related to Pécs and Baranya.
- Find old photo boards, galleries, community sites, blogs, forums, and free-hosted personal pages that may contain historically useful Pécs imagery or discussion.
- Use Scrapy as the primary crawl engine.
- Use Scrapling only as a fallback extractor when normal HTML parsing is insufficient.
- Validate discovered URLs/domains against the Wayback CDX API.
- Score candidates for Pécs relevance, Hungarian relevance, photo/gallery likelihood, and archival value.
- Store discovery results in a separate SQLite database outside the public webroot.
- Keep all explanatory source-code comments and docstrings in English.
- Use structured logging and never log secrets or full sensitive request payloads.

## Non-goals for v1

- No retro-browser emulation.
- No JavaScript browser rendering for every page.
- No bulk mirroring of all discovered images.
- No automatic promotion of every discovered domain into production indexing.
- No replacement of the current PHP Wayback indexer.
- No machine-learning model requirement.

## Architecture

```text
Seeds + existing indexed pages
        |
        v
      Scrapy
        |
        +--> normal HTML/link extraction
        |
        +--> Scrapling fallback when extraction quality is poor
        |
        v
URL/domain normalization + deduplication
        |
        v
Pécs/Hungary/photo relevance scoring
        |
        v
Wayback CDX validation
        |
        v
retro-data/discovery.sqlite
        |
        v
reviewed/approved candidates
        |
        v
existing PHP CDX -> SQLite/FTS indexer
```

## Source classes

The initial crawler should understand these source families without hard-coding them as trusted production sources:

- Hungarian photography communities such as FOTÓZZ!hu and Indafotó.
- Old Pécs/Baranya blogs and local portals.
- Old Hungarian free-hosting platforms such as freeweb.hu, uw.hu, extra.hu, and similar historical hosts.
- Forum threads and community pages that link to external Pécs photographs or galleries.
- Existing pages already stored in the local Retro Kereső archive; outbound links from known-good Pécs pages are strong discovery signals.
- Curated seed URLs/domains maintained in version-controlled text/YAML files.

## Candidate model

Each discovered candidate should preserve at least:

- normalized URL
- normalized domain
- discovery source URL
- discovery method (`seed`, `outbound_link`, `archive_link`, `manual`)
- anchor text
- nearby text snippet
- first-seen timestamp in the discovery database
- last-seen timestamp in the discovery database
- Pécs relevance score
- Hungary relevance score
- photo/gallery score
- combined priority score
- CDX capture count
- first archived year
- last archived year
- validation state
- review state (`new`, `approved`, `rejected`)

## Relevance scoring

The initial scorer should be deterministic and testable.

Positive Pécs/Baranya terms include variants such as:

- `pécs`, `pecs`
- `baranya`
- `zsolnay`
- `uránváros`, `uranvaros`
- `mecsek`
- `tettye`
- `széchenyi tér`, `szechenyi ter`
- `kiraly utca`, `király utca`

Photo/gallery signals include:

- `fotó`, `foto`, `photo`
- `galéria`, `galeria`, `gallery`
- `album`
- `kép`, `kep`, `images`
- URL paths containing `foto`, `photo`, `gallery`, `galeria`, `album`, `image`, or historical gallery-style query parameters

Hungarian signals include `.hu` domains and Hungarian text indicators.

Scores must remain explainable. Store the score components so a reviewer can understand why a candidate ranked highly.

## Scrapy responsibilities

Scrapy is responsible for:

- crawl queue management
- concurrency
- retries
- request throttling
- duplicate request filtering
- response handling
- extracting links, anchor text, and nearby text from standard HTML
- emitting normalized discovery items

The crawler must enforce bounded crawl depth and per-domain request limits.

## Scrapling responsibilities

Scrapling is a fallback extractor only.

Use it when one or more of the following is true:

- Scrapy/standard selectors produce no useful links from an HTML response that appears non-empty.
- malformed legacy HTML prevents normal extraction.
- meaningful metadata is present but standard extraction fails.

Scrapling must not be invoked automatically for every response.

The fallback decision must be isolated behind an adapter so Scrapling can be upgraded or removed without changing crawler orchestration.

## Wayback/CDX validation

The discovery subsystem queries Wayback CDX for candidate domains/URLs to establish archival value before promotion.

Validation records should include:

- whether archived captures exist
- capture count where practical
- earliest timestamp/year
- latest timestamp/year
- representative archived URL

CDX requests must use conservative limits, retries, backoff, and explicit timeouts.

The crawler should not download archived page bodies during discovery unless needed for a bounded follow-up probe. Production content downloading remains the existing indexer's responsibility.

## Storage

Use a separate SQLite database:

```text
retro-data/discovery.sqlite
```

It must remain outside the public webroot.

Suggested tables:

- `discovery_candidates`
- `discovery_evidence`
- `discovery_cdx`
- `discovery_runs`

The discovery database must not modify `retro.sqlite` directly.

## Promotion boundary

Discovery and production indexing remain separate.

A candidate can be promoted only after it meets deterministic minimum criteria or has been manually approved. Promotion should produce a normalized source/domain list that the existing PHP indexer can consume.

This protects production indexing from noisy crawler discoveries.

## Logging

Python logging should follow the same principles as the PHP logger:

- structured JSON lines
- timestamp
- severity
- run id
- event name
- sanitized context
- no passwords, cookies, authorization headers, tokens, or full sensitive request bodies

Recommended location:

```text
retro-data/logs/discovery.log
```

## CLI

Initial CLI entry point:

```bash
python -m crawler.discover --seed-file crawler/seeds/pecs.txt --max-pages 500 --max-depth 2
```

Useful bounded options:

- `--seed-file`
- `--max-pages`
- `--max-depth`
- `--domain-limit`
- `--cdx-validate`
- `--dry-run`

Defaults must be conservative.

## Testing

Use pytest and test-first development.

Required test areas:

- URL normalization
- domain normalization
- deterministic relevance scoring
- photo/gallery signal detection
- Hungarian/Pécs keyword handling with accents and unaccented variants
- candidate deduplication
- Scrapy extraction behavior
- Scrapling fallback decision logic
- CDX response parsing
- SQLite persistence
- promotion rules
- structured log secret redaction
- CLI bounds and argument validation

Network tests should be isolated from unit tests. Core tests must run without internet access.

## Dependencies

Python dependencies should be explicit and pinned to compatible major versions in project metadata.

Primary dependencies:

- Scrapy
- Scrapling
- pytest

Prefer the Python standard library for SQLite, URL handling, logging helpers, and dataclasses where practical.

## Security and operational constraints

- No credentials in repository files.
- No crawler database or log files committed to Git.
- No unbounded crawling.
- Respect configured crawl delays and domain limits.
- Do not expose discovery logs or databases through the public webroot.
- Preserve the existing `/404`-only archive quality rule in the PHP indexer; this subsystem must not reintroduce rejection of historically valuable malformed URLs.

## Success criteria

The first production-ready version is successful when it can:

1. start from a small Pécs/Hungary seed set and existing indexed pages;
2. discover outbound candidate domains/URLs;
3. rank clearly relevant Pécs/photo candidates above generic pages;
4. validate candidates against Wayback CDX;
5. persist deduplicated candidates to `discovery.sqlite`;
6. produce an approved source list consumable by the existing indexer;
7. complete a bounded run with useful structured logs and no secret leakage;
8. pass the full existing PHP test suite plus the new Python test suite.
