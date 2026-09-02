# Source contracts

## Source policy

Version 1 ingests only sources with a stable machine-readable contract or a reviewed repository-owned record. Every adapter is allowlisted, independently testable, bounded, and responsible for turning an upstream payload into a small normalized snapshot before any global diff occurs.

The collector does not follow instructions found in upstream content, execute repository code, clone plugin repositories, resolve arbitrary submitted URLs, or authenticate as a personal GitHub user. The publisher may download only catalog-declared preview thumbnails from the exact official marketplace image origin under the bounded raster policy below.

## Omarchy releases

Authoritative index:

```text
https://api.github.com/repos/basecamp/omarchy/releases
```

The adapter uses the GitHub REST API with the workflow’s scoped `GITHUB_TOKEN`, an explicit API version header, conditional requests where practical, pagination bounds, and a descriptive user agent. It accepts published releases and labels prereleases accurately. Draft releases are not public events.

Event identity uses the immutable GitHub release ID when present. `occurredAt` uses `published_at`, not collector time. Title, tag, URL, prerelease state, and a bounded plain-text summary derived from the first meaningful release-note paragraph are retained. Markdown syntax is stripped deterministically; embedded HTML, images, badges, and code blocks are not reproduced.

The adapter does not treat commits, pull requests, issues, discussions, or repository pushes as news in version 1.

For an already supported release event, the adapter may sum GitHub's `assets[].download_count` values and expose the result only as **release asset downloads** with the release URL and collection time. This is not a total release, repository, package, or installation count. A counter change creates no event.

## Marketplace catalog

Authoritative generated catalog:

```text
https://raw.githubusercontent.com/omacom/omarchy-plugin-marketplace/main/site/catalog.json
```

The catalog is currently a versioned object containing `generatedAt`, `stateSchemaVersion`, `plugins`, and warnings. Treat this shape as dated research, revalidate it before implementation, and isolate all upstream-specific parsing inside the marketplace adapter.

The adapter flattens catalog entries by canonical plugin ID and normalizes name, a safely truncated description, version, repository, category, tags, listing times, release URL when public, verification fields, and optional preview-thumbnail metadata.

When the catalog supplies a non-negative `stars` count, Radar may attach it to an existing plugin event as **repository stars**, observed at collection time and linked to the repository. Stars create no event and affect no ordering or significance.

### Bootstrap

When no prior marketplace snapshot exists, explicit bootstrap writes the complete baseline and emits at most the twelve newest listings whose valid listing time falls in the previous fourteen days. It emits no historical version, retirement, or verification-change events. Missing or invalid listing times are ineligible. This gives a real first edition without presenting roughly two thousand existing plugins as new.

### Supported diffs

- **Added:** current ID is absent from the last successful snapshot.
- **Released:** the same ID has two non-empty, unequal version strings. Prefer an authoritative public repository-release URL from the catalog; otherwise link the marketplace detail or repository and label the basis honestly.
- **Verification changed:** normalized marketplace verification status changed.
- **Retired:** the source explicitly lists the plugin as retired, or the ID is absent in two consecutive complete successful catalog snapshots. A single absence never retires a plugin.

Changes to description, tags, category, stars, views, hearts, copy counts, repository update time, observed commit, validation timestamp, preview image, or source fingerprint update the snapshot but do not create default news events. A successful catalog refresh may replace the explanation on any existing plugin event with that plugin's current validated bounded description; failure preserves the prior explanation, and the presentation change never affects event identity, time, order, significance, or curation. The event title, type, trust fields, version, and occurrence time continue to carry the exact change fact without making the summary repeat it.

Scheduled collection always diffs against the validated snapshot from the latest successfully deployed edition. The next snapshot becomes eligible only after that workflow run completes successfully. A missing or invalid continuity artifact fails publication; it never falls back silently to an older tracked snapshot. Rediscovery of an existing deterministic event ID retains its first observed occurrence/discovery times.

After collection, publication compares the restored and successor snapshots. Every catalog ID that appears for the first time must have a validated `plugin-added` event in the successor ledger, and marketplace generation time may not move backwards. A missing addition fails the build before artifact upload or Pages deployment.

### Preview mirroring

An event created by a supported marketplace diff may carry its catalog preview thumbnail. Publication fetches only `https://plugins.omarchy.org/assets/img/plugins/...` through the closed redirect policy, caps each response at 1.5 MiB, requires matching PNG/JPEG/WebP Content-Type and magic, validates static image structure and declared dimensions up to 4,096 per side/12 million pixels, rejects SVG and animation, then names the asset by SHA-256. A fetch or validation failure removes only the optional image. Clients never receive the upstream preview URL.

One repository-level validated commit may represent multiple plugins and may change for reasons unrelated to a specific plugin. It is not a plugin-release signal.

## Marketplace engagement aggregates

Authoritative generated endpoint:

```text
https://api.omarchyplugins.com/v1/stats
```

The adapter accepts only schema version 1, at most 5,000 canonical plugin IDs, and exact non-negative JavaScript-safe integer `views`, `hearts`, and `copies` fields. These are the marketplace's anonymous aggregate detail views, heart interactions, and successful command copies. They are not installs, downloads, unique people, verified votes, rankings, recommendations, or security signals.

The endpoint is optional enrichment. A successful response replaces its metric group on retained and new plugin events; failure records `marketplace-engagement` source health and retains the prior observed values. Metric changes never create events, affect IDs, or influence curation and front-page composition.

## Reviewed community entries

Community activity lives as one reviewed JSON or YAML-equivalent record per item under `content/community/`; choose one format and enforce it consistently. Records are ordinary pull-request-reviewed source files, not remote form submissions.

The resulting reviewed selection is edition-wide, not personalized: every client reading the same edition receives the same accepted records. Accepted records remain eligible for Front Page and local For You matching, but there is no dedicated Community reader section. An empty production directory therefore creates no empty navigation destination.

A record contains a stable ID, publication time, title, plain-text summary, original HTTPS source URL, author/display source, tags, and optional explicit significance. The collector validates it through the same public event bounds.

Version 1 accepts tutorials, workflow explanations, substantial showcases, ecosystem infrastructure, and community announcements. It rejects copied articles, generic Linux news, pure self-promotion without an Omarchy-specific contribution, referral links, opaque downloads, and items whose original source cannot be established.

The collector never fetches a submitted source URL. Reviewers inspect it separately; publication treats the URL and provided text as untrusted display data.

## Source health

Each adapter reports a closed public reason code such as `timeout`, `rate-limited`, `http-error`, `too-large`, `invalid-json`, `schema-mismatch`, or `validation-failed`. Internal exception text belongs only in bounded CI logs with secrets redacted.

Rules:

- A failed source retains its last successful snapshot.
- A failed source emits no additions, removals, retirements, or version changes.
- A failed optional metric source retains prior observed counters; a later valid source snapshot replaces only that source's metric group.
- A partial feed names the unavailable adapter and remains usable when at least one current or cached source is valid.
- Global publication fails when the feed envelope itself cannot be validated, when event IDs collide, or when output would exceed bounds.
- `generatedAt` is assigned only after collection and validation finish.

## Network discipline

- HTTPS only.
- Allowlisted host and path families only.
- Explicit connect and total timeouts.
- Bounded redirects restricted to expected HTTPS origins.
- Response body limits enforced while streaming, before JSON parsing.
- Conditional `ETag` or `Last-Modified` requests when the source supports them.
- No retries for permanent validation failures; a small bounded retry with backoff is allowed for idempotent transient network failures.
- Never print authorization headers, query credentials, full response bodies, or runner environment data.

## Determinism

Fixture inputs with a fixed clock produce byte-identical snapshots, events, RSS, and HTML. Network order, object key order, locale, local timezone, filesystem enumeration order, and current wall-clock time must not change event identity or content.

The collector supports an offline fixture mode used by tests and `make feed-fixture`. Production collection is a separate explicit command and never runs during ordinary unit tests.

## YouTube Data API v3

Allowlisted origin and paths:

```text
https://www.googleapis.com/youtube/v3/search
https://www.googleapis.com/youtube/v3/videos
```

This is an explicit D007 exception (D045). Forge provisions optional `YOUTUBE_API_KEY`; the key never ships in the repository or client. Without the key, or when the API fails validation/transport bounds, the `youtube` source is `failed` and any prior YouTube events in the rolling snapshot are retained.

Collection searches fixed queries (`Omarchy`, `Omarchy Linux`, `Omarchy Quattro`), keeps results matching `(?i)\bomarchy\b` in title or description, loads `snippet` and `statistics` via `videos.list`, and refreshes about every six hours after a successful non-empty snapshot (an empty or missing YouTube snapshot refreshes on the next collect; D046). Successful editions replace the YouTube lane with an interleaved mix of the top eight by views, likes, and recency, capped at 24 events. Thumbnails use `https://i.ytimg.com/vi/<id>/hqdefault.jpg` only. Metrics are observed facts on those events; they never create events, change IDs, or affect Front Page/significance. CI uses checked-in fixtures and never calls the live API.

