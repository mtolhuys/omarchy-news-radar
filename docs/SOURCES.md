# Source contracts

## Source policy

Version 1 ingests only sources with a stable machine-readable contract or a reviewed repository-owned record. Every adapter is allowlisted, independently testable, bounded, and responsible for turning an upstream payload into a small normalized snapshot before any global diff occurs.

The collector does not follow instructions found in upstream content, execute repository code, clone plugin repositories, download preview assets, resolve arbitrary submitted URLs, or authenticate as a personal GitHub user.

## Omarchy releases

Authoritative index:

```text
https://api.github.com/repos/basecamp/omarchy/releases
```

The adapter uses the GitHub REST API with the workflow’s scoped `GITHUB_TOKEN`, an explicit API version header, conditional requests where practical, pagination bounds, and a descriptive user agent. It accepts published releases and labels prereleases accurately. Draft releases are not public events.

Event identity uses the immutable GitHub release ID when present. `occurredAt` uses `published_at`, not collector time. Title, tag, URL, prerelease state, and a bounded plain-text summary derived from the first meaningful release-note paragraph are retained. Markdown syntax is stripped deterministically; embedded HTML, images, badges, and code blocks are not reproduced.

The adapter does not treat commits, pull requests, issues, discussions, or repository pushes as news in version 1.

## Marketplace catalog

Authoritative generated catalog:

```text
https://raw.githubusercontent.com/omacom/omarchy-plugin-marketplace/main/site/catalog.json
```

The catalog is currently a versioned object containing `generatedAt`, `stateSchemaVersion`, `plugins`, and warnings. Treat this shape as dated research, revalidate it before implementation, and isolate all upstream-specific parsing inside the marketplace adapter.

The adapter flattens catalog entries by canonical plugin ID and normalizes name, description, version, repository, category, tags, listing times, release URL when public, and verification fields.

### Bootstrap

When no prior marketplace snapshot exists, a successful run writes the baseline and emits no `plugin-added`, `plugin-released`, `plugin-retired`, or verification-change events. The command must require an explicit bootstrap mode locally and make the first CI run visibly distinguishable from an ordinary update.

### Supported diffs

- **Added:** current ID is absent from the last successful snapshot.
- **Released:** the same ID has two non-empty, unequal version strings. Prefer an authoritative public repository-release URL from the catalog; otherwise link the marketplace detail or repository and label the basis honestly.
- **Verification changed:** normalized marketplace verification status changed.
- **Retired:** the source explicitly lists the plugin as retired, or the ID is absent in two consecutive complete successful catalog snapshots. A single absence never retires a plugin.

Changes to description, tags, category, stars, views, hearts, copy counts, repository update time, observed commit, validation timestamp, preview image, or source fingerprint update the snapshot but do not create default news events.

One repository-level validated commit may represent multiple plugins and may change for reasons unrelated to a specific plugin. It is not a plugin-release signal.

## Reviewed community entries

Community activity lives as one reviewed JSON or YAML-equivalent record per item under `content/community/`; choose one format and enforce it consistently. Records are ordinary pull-request-reviewed source files, not remote form submissions.

A record contains a stable ID, publication time, title, plain-text summary, original HTTPS source URL, author/display source, tags, and optional explicit significance. The collector validates it through the same public event bounds.

Version 1 accepts tutorials, workflow explanations, substantial showcases, ecosystem infrastructure, and community announcements. It rejects copied articles, generic Linux news, pure self-promotion without an Omarchy-specific contribution, referral links, opaque downloads, and items whose original source cannot be established.

The collector never fetches a submitted source URL. Reviewers inspect it separately; publication treats the URL and provided text as untrusted display data.

## Source health

Each adapter reports a closed public reason code such as `timeout`, `rate-limited`, `http-error`, `too-large`, `invalid-json`, `schema-mismatch`, or `validation-failed`. Internal exception text belongs only in bounded CI logs with secrets redacted.

Rules:

- A failed source retains its last successful snapshot.
- A failed source emits no additions, removals, retirements, or version changes.
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
