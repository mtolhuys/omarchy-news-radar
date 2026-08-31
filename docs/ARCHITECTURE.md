# Architecture

## System overview

```text
GitHub Actions
  └─ Python collector
       ├─ Omarchy release adapter
       ├─ marketplace catalog adapter
       ├─ reviewed community adapter
       ├─ snapshot diff + normalization
       └─ bounded feed + RSS + static-site build
                        │
                        ▼
              GitHub Pages over HTTPS
                        │
                        ▼
Omarchy shell
  └─ News Radar on-demand panel
       ├─ bundled Python client helper
       ├─ last-known-good cache
       ├─ local seen/saved state
       ├─ installed-plugin matching
       └─ explicit HTTPS source opening
```

The static feed is the integration contract. The website and Omarchy panel are independent clients of the same validated events. There is no application server, database, account service, background daemon, or bidirectional client API.

## Target repository layout

The implementation should converge on this shape without preserving empty or redundant directories merely to match the diagram:

```text
omarchy-news-radar/
├── manifest.json
├── Makefile
├── AGENTS.md
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── bin/
│   ├── news-radar-client
│   └── news-radar-shortcut
├── radar/
│   ├── __init__.py
│   ├── model.py
│   ├── validation.py
│   ├── collector.py
│   ├── publisher.py
│   ├── state.py
│   └── sources/
│       ├── omarchy_releases.py
│       ├── marketplace.py
│       └── community.py
├── src/
│   ├── Panel.qml
│   ├── Model.js
│   └── components/
├── content/
│   ├── community/
│   └── curation/
├── state/
│   └── source-snapshot.json
├── site/
│   ├── templates/
│   └── static/
├── schemas/
│   ├── feed-v1.schema.json
│   └── state-v1.schema.json
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── lab/
└── .github/workflows/
    ├── test.yml
    └── publish.yml
```

Generated deployment output belongs in `dist/` and stays untracked. The source snapshot is intentionally tracked because it is the deterministic baseline for future diffs; it must contain public normalized source state only, not tokens, response headers containing secrets, or deployment evidence.

## Plugin contract

Version 1 uses a single third-party `panel` plugin:

```json
{
  "schemaVersion": 1,
  "id": "io.github.mtolhuys.news-radar",
  "name": "Omarchy News Radar",
  "version": "0.1.0",
  "author": "Maarten Tolhuijs",
  "description": "A keyboard-first front page for meaningful Omarchy activity.",
  "kinds": ["panel"],
  "entryPoints": { "panel": "src/Panel.qml" }
}
```

This is a target manifest, not permission to create it before `src/Panel.qml` exists and validation passes. The panel entry point is an `Item`, accepts current shell-injected properties, and exposes `open(payloadJson)` and `close()`.

Omit `keepLoaded` in version 1. The panel is loaded on summon and destroyed on hide. It must restore all durable user state from XDG files, terminate any owned helper on destruction, and never require a resident service merely to feel fast.

## Panel lifecycle

`open()` follows this order:

1. Establish one session identity and reset transient error state.
2. Ask the client helper for the validated local cache and local user state.
3. Render cached events immediately when available and capture `sessionThrough` from that exact model.
4. Query `omarchy-shell shell listPlugins` to derive locally installed plugin IDs.
5. Start at most one bounded refresh helper.
6. Validate the candidate feed completely before atomically replacing cache or the visible current model.
7. Preserve the cached model and surface a recoverable status if refresh fails.
8. Prime keyboard focus only after the visible model exists.

`close()` and component destruction must cancel or terminate the owned refresh helper, persist `seenThrough` no later than the captured session boundary, persist saved items atomically, release the panel window, and leave no child process.

## Client helper

The bundled Python helper is the only component that reads or writes Radar cache and state. QML invokes it with structural argument arrays and consumes one bounded JSON response. The helper has a small command surface:

```text
news-radar-client read
news-radar-client refresh
news-radar-client state mark-seen --through <UTC timestamp>
news-radar-client state toggle-saved --event-id <id>
news-radar-client state purge
```

Exact flags may be refined during implementation, but each operation remains explicit, typed, non-interactive, bounded, and independently testable. `purge` is never invoked by disablement or ordinary removal; it is a deliberate user-data action.

The helper uses a fixed production feed origin compiled into one module. Tests may inject a fixture file or loopback test server through an explicit test-only flag or environment boundary that is disabled in public runtime paths.

## Local storage

Follow XDG ownership:

| Path | Purpose |
| --- | --- |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/feed.json` | Last-known-good validated feed |
| `${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-news-radar/state.json` | Seen-through timestamp, saved items, and schema version |
| `${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-news-radar/diagnostics.log` | Optional bounded local diagnostics without feed bodies or private paths |

Use private directories, mode `0600` files where the platform permits, same-directory temporary files, `fsync`, and atomic rename. Refuse symlinked cache/state targets. A failed candidate never truncates or replaces good data.

## Collector

The collector is a Python standard-library application with pure source adapters and one orchestration layer. Adapters convert source-specific payloads into normalized snapshots; the diff layer converts two valid snapshots into events; the publisher validates the full envelope and emits JSON, RSS, and a static HTML projection.

Collection is transactional:

1. Fetch each allowlisted source using explicit headers, timeouts, size limits, and conditional request metadata where useful.
2. Validate the complete source payload into a source-specific immutable model.
3. Produce per-source success or failure without mutating the prior snapshot.
4. Diff only successful current sources against their last successful prior state.
5. Create events deterministically and merge reviewed curation.
6. Validate the complete candidate feed.
7. Write generated artifacts to a temporary output tree.
8. Publish the output tree and updated successful source states only after every global invariant passes.

A partial source outage may produce a feed with explicit source-health metadata, but the unavailable source retains its previous snapshot and produces no mass deletion or retirement events.

## Static publication

GitHub Actions runs tests first, then builds an immutable deployment artifact containing at least:

```text
dist/
├── index.html
├── events.json
├── feed.xml
├── assets/
└── archive/
```

The site contains no runtime framework, cookies, analytics, user input, service worker, external font, or client-side content fetch required for the initial page. Publisher output must escape every remote string for its destination context and use a strict Content Security Policy compatible with a static site.

The live feed contains a bounded rolling window. Monthly archives may retain older public events without increasing the plugin payload. Saved local items retain the fields needed to remain useful after an event leaves the live window.

## Installed-plugin relevance

The panel calls the maintained shell IPC and treats the returned plugin IDs as local data. Matching is exact on canonical plugin ID. Do not send installed IDs to the feed host and do not infer installation from repository names or display names.

“For You” includes events whose entity plugin ID is installed. It may also include explicitly declared compatibility events affecting all plugins, but version 1 does not guess related interests from browsing or saved history.

## Optional bar indicator

The version 1 repository does not declare `bar-widget`. If a later indicator is approved, implement it as a separate installable plugin and repository identity consuming the public feed and opening Radar through documented IPC. Do not turn a zero-width hidden widget into a lifecycle dependency for the main panel.

## Failure containment

- Network failure preserves cache and does not prevent panel opening.
- Malformed source input preserves the previous source snapshot.
- Malformed feed input preserves the client cache.
- One source outage does not manufacture deletions from that source.
- One corrupt local state file is quarantined with a bounded diagnostic and replaced by safe defaults; it never invalidates the feed cache.
- Shortcut setup failure restores the previous binding file and leaves the plugin usable through IPC.
- Panel close and disable terminate owned work without deleting user state.
