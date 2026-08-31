# Architecture

## System overview

```text
GitHub Actions
  └─ Python collector
       ├─ Omarchy release adapter
       ├─ marketplace catalog adapter
       ├─ marketplace engagement adapter
       ├─ reviewed community adapter
       ├─ snapshot diff + normalization
       └─ bounded feed + RSS + static-site build
                        │
                        ▼
              GitHub Pages over HTTPS
                        │
                        ▼
Omarchy shell
  └─ News Radar plugin
       ├─ optional default-on bar newspaper
       ├─ on-demand compositor-managed window
       ├─ bundled Python client helper
       ├─ last-known-good cache
       ├─ local seen/saved/preferences/filter/presentation state
       ├─ installed-plugin + private-interest matching
       └─ explicit HTTPS source opening
```

The static feed is the integration contract. The website and Omarchy plugin are independent clients of the same validated events. There is no application server, database, account service, background daemon, or bidirectional client API. The visible bar widget owns one due-checked refresh timer inside the existing shell process.

The unpublished local-development route reuses the collector and publisher directly. `make local-latest` builds into a temporary directory from the tracked source baseline, revalidates the public feed, build digest, and every referenced raster, then atomically imports the feed plus content-addressed images into the user's private cache. A matching bounded marker makes the client project those assets as local file URLs and suppresses the nonexistent Pages refresh. This route is explicit and owner-run; it is not a second feed protocol or resident publisher.

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
│   ├── filters.py
│   ├── metrics.py
│   ├── sections.py
│   ├── validation.py
│   ├── collector.py
│   ├── publisher.py
│   ├── images.py
│   ├── state.py
│   └── sources/
│       ├── omarchy_releases.py
│       ├── marketplace.py
│       ├── marketplace_engagement.py
│       └── community.py
├── src/
│   ├── Panel.qml
│   ├── BarWidget.qml
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
│   ├── state-v1.schema.json
│   ├── state-v2.schema.json
│   ├── state-v3.schema.json
│   └── state-v4.schema.json
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

Version 1 uses one third-party plugin with paired panel and bar entry points:

```json
{
  "schemaVersion": 1,
  "id": "io.github.mtolhuys.news-radar",
  "name": "Omarchy News Radar",
  "version": "0.1.0",
  "author": "Maarten Tolhuijs",
  "description": "A keyboard-first front page for meaningful Omarchy activity.",
  "icon": "assets/io.github.mtolhuys.news-radar.svg",
  "kinds": ["panel", "bar-widget"],
  "entryPoints": { "panel": "src/Panel.qml", "barWidget": "src/BarWidget.qml" },
  "barWidget": { "defaultSection": "right", "allowMultiple": false }
}
```

This is a target manifest, not permission to create it before `src/Panel.qml` exists and validation passes. The panel entry point is an `Item`, accepts current shell-injected properties, exposes `open(payloadJson)` and `close()`, and owns a normal `FloatingWindow`. The window is compositor-managed, resizable/maximizable, and follows ordinary task switching; it is not a `PanelWindow` or layer-shell overlay. Radar omits an unreliable minimize control.

Omit `keepLoaded`. Omarchy keeps the declared bar widget within its normal bar lifecycle, while the panel exposes the ordinary `open`/`close` contract. The bar widget loads only bounded local indicator state, runs a refresh only when the cache is due, and stops its refresh cadence while hidden. Neither entry point installs a service or daemon.

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
news-radar-client refresh-if-due --minimum-age <seconds>
news-radar-client indicator
news-radar-client mark-seen --through <UTC timestamp>
news-radar-client toggle-saved --event-id <id>
news-radar-client set-preferences [--bar-visible true|false] [--images-visible true|false] [--interests-json <array>]
news-radar-client purge
```

Exact flags may be refined during implementation, but each operation remains explicit, typed, non-interactive, bounded, and independently testable. `purge` is never invoked by disablement or ordinary removal; it is a deliberate user-data action.

The helper uses a fixed production feed origin compiled into one module. Tests may inject a fixture file or loopback test server through an explicit test-only flag or environment boundary that is disabled in public runtime paths.

## Local storage

Follow XDG ownership:

| Path | Purpose |
| --- | --- |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/feed.json` | Last-known-good validated feed |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/assets/images/` | Content-addressed rasters from an explicitly imported local edition |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/local-edition.json` | Bounded digest/revision marker for local-edition projection |
| `${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-news-radar/state.json` | Seen-through timestamp, saved items, local preferences/interests, and schema version |
| `${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-news-radar/diagnostics.log` | Optional bounded local diagnostics without feed bodies or private paths |

Use private directories, mode `0600` files where the platform permits, same-directory temporary files, `fsync`, and atomic rename. Refuse symlinked cache/state targets. A failed candidate never truncates or replaces good data.

An imported local marker is honored only when its SHA-256 matches the canonical cached feed. Every referenced local raster is re-inspected for format, dimensions, static structure, byte bound, and content-addressed filename before the feed changes. Missing local image bytes produce text fallback rather than a direct upstream request.

## Collector

The collector is a Python standard-library application with pure source adapters and one orchestration layer. Adapters convert source-specific payloads into normalized snapshots; the diff layer converts two valid snapshots into events; the publisher validates the full envelope and emits JSON, RSS, and a static HTML projection.

Optional metric enrichment is a post-diff step. Successful source snapshots replace their own metric group; a failed optional metric source retains prior observed facts. Metrics never enter event identity, diff generation, curation, ordering, or Front Page selection.

Collection is transactional:

1. Fetch each allowlisted source using explicit headers, timeouts, size limits, and conditional request metadata where useful.
2. Validate the complete source payload into a source-specific immutable model.
3. Produce per-source success or failure without mutating the prior snapshot.
4. Diff only successful current sources against their last successful prior state.
5. Create events deterministically and merge reviewed curation.
6. Validate the complete candidate feed.
7. Fetch only declared marketplace preview thumbnails from `https://plugins.omarchy.org`, inspect bounded PNG/JPEG/WebP bytes and dimensions, and write successful images as SHA-256-addressed same-origin assets. Image failure omits that optional image, not its story.
8. Write generated artifacts to a temporary output tree.
9. Publish the output tree and updated successful source states only after every global invariant passes.

A partial source outage may produce a feed with explicit source-health metadata, but the unavailable source retains its previous snapshot and produces no mass deletion or retirement events.

## Static publication

GitHub Actions runs tests first, then builds an immutable deployment artifact containing at least:

```text
dist/
├── index.html
├── events.json
├── feed.xml
├── assets/
│   └── images/<sha256>.<ext>
└── archive/
```

The site contains no runtime framework, cookies, analytics, user input, service worker, external font, or client-side content fetch required for the initial page. Publisher output must escape every remote string for its destination context and use a strict Content Security Policy compatible with a static site.

The live feed contains a bounded rolling window. Monthly archives may retain older public events without increasing the plugin payload. Saved local items retain the fields needed to remain useful after an event leaves the live window.

## Installed-plugin relevance

The panel calls the maintained shell IPC and treats the returned plugin IDs as local data. Matching is exact on canonical plugin ID. Do not send installed IDs to the feed host and do not infer installation from repository names or display names.

“For You” includes events whose entity plugin ID is installed plus events matching up to twelve explicit local interest words or phrases. Interests are never derived from browsing or saved history and never leave the device.

## Optional bar indicator

The main manifest declares one non-multiple `bar-widget`, defaulted to the right section. It renders a code-native newspaper, unread count, and current/partial health dot; left click toggles the panel, middle click refreshes, and right click persists `barVisible=false`. The widget root binds `visible` to that preference, and current Omarchy `ModuleSlot` geometry maps an invisible item to exact zero width/height. A local state-file watch restores it when Tune Your Radar sets the preference true.

## Failure containment

- Network failure preserves cache and does not prevent panel opening.
- Malformed source input preserves the previous source snapshot.
- Malformed feed input preserves the client cache.
- One source outage does not manufacture deletions from that source.
- One corrupt local state file is quarantined with a bounded diagnostic and replaced by safe defaults; it never invalidates the feed cache.
- Shortcut setup failure restores the previous binding file and leaves the plugin usable through IPC.
- Panel close and disable terminate owned work without deleting user state.
- Window-manager close follows the same shell hide path; maximize, resize, and `Alt+Tab` do not alter panel state.
- Pagination and per-section filters operate only on the validated cache projection and cannot expand the network boundary.
