# Orphan-Site Discovery Addendum

This addendum extends `2026-08-25-source-discovery-crawler-design.md`.

## Definition

In Retro Kereső, a "hidden" site means a site hidden from modern search/navigation because it is dead, unlinked, moved, or only preserved in web archives. It does **not** mean Tor/onion/dark-web services.

## Discovery methods

The crawler should discover orphaned Hungarian/Pécs sites through bounded historical evidence:

- outbound links extracted from archived versions of known Pécs/Baranya pages;
- dead links on historical pages that still have Wayback CDX captures;
- old Hungarian portal directories, blogrolls, webrings, forum posts, and link collections;
- historical free-hosting user/sub-site references (`freeweb.hu`, `uw.hu`, `extra.hu`, and similar hosts);
- bounded CDX path/domain enumeration around high-confidence Pécs seeds;
- repeated references to the same dead site from multiple independent archived pages.

## Candidate evidence

Extend discovery evidence with:

- `discovery_method`: add `dead_link`, `directory`, and `cdx_enumeration`;
- `live_state`: `unknown`, `alive`, or `dead`;
- `orphan_evidence`: boolean;
- `orphan_score`: integer component;
- `archive_referrer_url`: the archived page that exposed the candidate;
- `archive_referrer_timestamp`: capture timestamp when available.

## Scoring

Give positive orphan/archive-evidence weight when:

- a live URL is dead but CDX has captures;
- an archived Pécs page references the candidate;
- several independent archived sources reference the same candidate;
- the candidate belongs to a known vanished historical hosting family.

Orphan evidence never bypasses Pécs/Hungary relevance checks.

## Bounds

Add CLI options:

```text
--discover-orphans
--archive-depth
```

`--archive-depth` must default to `1`, be independently bounded from live crawl depth, and reject values outside `0..3`.

CDX enumeration remains limited to high-confidence seeds and must never become an unbounded `.hu` crawl.

## Tests

Add offline tests for:

- dead-link + CDX-capture classification;
- orphan evidence persistence;
- archive recursion depth bounds;
- duplicate orphan evidence from multiple referrers;
- scoring a dead archived Pécs photo gallery above an unrelated dead domain.
