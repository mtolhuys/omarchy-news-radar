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
       ├─ local read/saved/display/filter/presentation state
       ├─ exact enabled-plugin matching
       └─ explicit HTTPS source opening
```

The static feed is the integration contract. The website and Omarchy plugin are independent clients of the same validated events. There is no application server, database, account service, background daemon, or bidirectional client API. The visible bar widget owns one due-checked refresh timer inside the existing shell process.

The local-development route reuses the collector and publisher directly. `make local-latest` builds into a temporary directory from the tracked source baseline, revalidates the public feed, build digest, and every referenced raster, then atomically imports the feed plus content-addressed images into the user's private cache. A matching bounded marker makes the client project those assets as local file URLs. **Check for updates** still fetches the fixed Pages feed: it preserves an equal/newer owner-built edition and atomically adopts a newer published edition. This route is explicit and owner-run; it is not a second feed protocol or resident publisher.

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
│   ├── news-radar-shortcut
│   └── news-radar-launcher
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
│   ├── launcher.py
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
│   ├── state-v4.schema.json
│   ├── state-v5.schema.json
│   ├── state-v6.schema.json
│   ├── state-v7.schema.json
│   ├── state-v8.schema.json
│   └── state-v9.schema.json
├── share/
│   └── applications/
│       └── io.github.mtolhuys.news-radar.desktop
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── lab/
└── .github/workflows/
    ├── test.yml
    └── publication.yml
```

Generated deployment output belongs in `dist/` and stays untracked. The source snapshot is intentionally tracked because it is the deterministic baseline for future diffs; it must contain public normalized source state only, not tokens, response headers containing secrets, or deployment evidence.

## Plugin contract

Version 1 uses one third-party plugin with paired panel and bar entry points:

```json
{
  "schemaVersion": 1,
  "id": "io.github.mtolhuys.news-radar",
  "name": "Omarchy News Radar",
  "version": "0.1.6",
  "author": "Maarten Tolhuijs",
  "description": "A keyboard-first front page for meaningful Omarchy activity.",
  "icon": "assets/io.github.mtolhuys.news-radar.svg",
  "windowIdentity": { "appId": "org.quickshell", "title": "📰 Omarchy News Radar" },
  "kinds": ["panel", "bar-widget"],
  "entryPoints": { "panel": "src/Panel.qml", "barWidget": "src/BarWidget.qml" },
  "barWidget": { "defaultSection": "right", "allowMultiple": false }
}
```

This is a target manifest, not permission to create it before `src/Panel.qml` exists and validation passes. The panel entry point is an `Item`, accepts current shell-injected properties, exposes `open(payloadJson)` and `close()`, and owns a normal `FloatingWindow`. The window is compositor-managed, resizable/maximizable, and follows ordinary task switching; it is not a `PanelWindow` or layer-shell overlay. Radar omits an unreliable minimize control.

Every public activation route uses the shell's `summon` operation. Closed means create/open/focus; already open means raise and focus the same window, whether it is foreground or obscured. Repeated activation never serves as close. `Escape`, `q`, the rendered close control, and normal window-manager close remain the deliberate close routes. The panel's bounded window helper validates one exact mapped Radar client, floats it if necessary, then focuses that address; an ambiguous identity fails closed.

The bar entry point runs one bounded migration command when Omarchy creates its generation, including the generation loaded by the updater's normal rescan. That command cannot install a free chord: it mutates only when the helper identifies the byte-exact 0.1.3 Radar-owned `toggle` block and one matching live action. It backs up and atomically replaces only that owned block with `summon`, reloads and validates Hyprland, and rolls back on failure. Every other classification is a no-op. The panel still performs a read-only inspection on open and renders **Update shortcut** as a user-visible retry if the exact legacy state remains.

`windowIdentity` is a narrow companion-integration declaration for hosted normal windows. The app ID and full title must both equal the compositor values before a companion switcher or dock may use the existing local manifest name/icon. Unknown, disabled, malformed, missing, or ambiguous declarations fall back to normal desktop-entry resolution; the declaration does not alter Quickshell's process-wide app ID.

The optional Apps-menu integration is a standard XDG desktop entry, not another plugin entry point. `news-radar-launcher install` copies that fixed entry and the existing SVG mark into their user XDG data locations and stores a private digest/path receipt. `make local-latest` invokes it as part of the owner's explicit desktop synchronization. Public plugin installation documents the same explicit command because current Omarchy plugin add/remove deliberately runs no repository hooks. Removal is therefore performed through the helper while the checkout still exists.

Omit `keepLoaded`. Omarchy keeps the declared bar widget within its normal bar lifecycle, while the panel exposes the ordinary `open`/`close` contract. The bar widget loads only bounded local indicator state, runs a refresh from a separately recorded last-check deadline, and stops its refresh cadence while hidden. Neither entry point installs a service or daemon.

## Panel lifecycle

`open()` follows this order:

1. Reset transient error state without changing reading state.
2. Ask the client helper for the validated local cache and local user state.
3. Render cached events immediately with explicit per-story `isUnread` decoration.
4. Query `omarchy-shell shell listPlugins` to derive locally installed plugin IDs.
5. Start at most one bounded refresh helper.
6. Validate the candidate feed completely before atomically replacing cache or the visible current model.
7. Preserve the cached model and surface a recoverable status if refresh fails.
8. Prime keyboard focus only after the visible model exists.

Dense-list keyboard movement reads the instantiated delegate geometry before changing selection. A next row already inside the viewport uses ordinary containment; a next row crossing the bottom resolves its exact `ListView.Beginning` offset and eases `contentY` there. This keeps variable-height rows fully visible without changing pointer flicking, pagination, projection, or read-state semantics.

`close()` and component destruction must cancel or terminate owned network/model helpers, drain any already-requested per-story reading mutation, release the panel window, and leave no child process. Close never bulk-marks a session or edition. All cross-process state read/modify/write operations use one private kernel-backed lock so panel and bar mutations cannot overwrite each other.

## Client helper

The bundled Python helper is the only component that reads or writes Radar cache and state. QML invokes it with structural argument arrays and consumes one bounded JSON response. The helper has a small command surface:

```text
news-radar-client read
news-radar-client refresh
news-radar-client refresh-if-due --minimum-age <seconds>
news-radar-client indicator
news-radar-client set-read --event-id <id> --read true|false
news-radar-client mark-section-read --section <id> --installed-json <json-array>
news-radar-client toggle-saved --event-id <id>
news-radar-client set-preferences [--bar-visible true|false] [--images-visible true|false]
news-radar-client purge
```

Exact flags may be refined during implementation, but each operation remains explicit, typed, non-interactive, bounded, and independently testable. `purge` is never invoked by disablement or ordinary removal; it is a deliberate user-data action.

The helper uses a fixed production feed origin compiled into one module. Tests may inject a fixture file or loopback test server through an explicit test-only flag or environment boundary that is disabled in public runtime paths.

## Local storage

Follow XDG ownership:

| Path | Purpose |
| --- | --- |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/feed.json` | Last-known-good validated feed |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/update-check.json` | Private bounded timestamp/outcome for background check cadence; not publication freshness |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/assets/images/` | Content-addressed rasters from an explicitly imported local edition |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/local-edition.json` | Bounded digest/revision marker for local-edition projection |
| `${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-news-radar/state.json` | Read baseline/overrides, saved items, local display/filter/name preferences, and schema version |
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

The workflow requests four best-effort schedules per hour at minutes 8, 23, 38, and 53. These offsets avoid the top-of-hour load peak and provide recovery opportunities after a delayed or dropped invocation; they are not a delivery guarantee. Workflow concurrency does not cancel an in-progress publication. Each generated feed records source `checkedAt`, collection `generatedAt`, and artifact `publishedAt` separately. GitHub Pages/CDN propagation may add up to ten minutes after deployment, and each client separately reports when its validated copy was cached. A publication becomes visibly stale only when `publishedAt` is more than 90 minutes old, so normal scheduling and documented cache propagation do not create false alarms while sustained publisher lag cannot masquerade as source success.

## Installed-plugin relevance

The panel calls the maintained shell IPC and treats the returned plugin IDs as local data. Matching is exact on canonical plugin ID. Do not send installed IDs to the feed host and do not infer installation from repository names or display names.

“For You” includes only events whose entity plugin ID exactly matches an enabled local plugin. Radar does not derive or store a second manual-interest relevance path.

## Optional bar indicator

The main manifest declares one non-multiple `bar-widget`, defaulted to the right section. It renders a code-native newspaper, unread count, and publisher/source health dot; left click summons and raises the panel, middle click checks the published edition, and right click persists `barVisible=false`. The widget root binds `visible` to that preference, and current Omarchy `ModuleSlot` geometry maps an invisible item to exact zero width/height. A local state-file watch restores it when Tune Your Radar sets the preference true.

While visible, one single-shot timer checks the fixed feed at most every 15 minutes after a successful attempt and retries a failed attempt after five minutes. Cadence comes from private `update-check.json`, not the edition's collection timestamp, so loading the shell shortly before an edition becomes old cannot defer the next check for another full interval. A feed-file watch reloads the canonical unread/health indicator immediately after either entry point adopts a valid edition; a 30-second local-only fallback covers missed filesystem events. The panel does not need to be opened. This is a passive bar indicator, not a desktop notification service.

## Failure containment

- Network failure preserves cache and does not prevent panel opening.
- Malformed source input preserves the previous source snapshot.
- Malformed feed input preserves the client cache.
- One source outage does not manufacture deletions from that source.
- One corrupt local state file is quarantined with a bounded diagnostic and replaced by safe defaults; it never invalidates the feed cache.
- Shortcut setup failure restores the previous binding file and leaves the plugin usable through IPC.
- Panel close and disable terminate owned work without deleting user state.
- Window-manager close follows the same shell hide path; maximize, resize, and `Alt+Tab` do not alter panel state.
- Pagination and per-section filters operate only on the validated cache projection and cannot expand the network boundary. Down from the final visible story focuses Load more; Enter expands by twelve and returns navigation to the prior last story so the next Down reaches the first new item without an implicit read.
