# Architecture

## System overview

```text
Forge Laravel (news-radar:publish every 5 minutes)
  └─ Python collector on maintainer host
       ├─ Omarchy release adapter
       ├─ marketplace catalog adapter
       ├─ marketplace engagement adapter
       ├─ reviewed community adapter
       ├─ snapshot diff + normalization
       └─ bounded feed + RSS + static-site build
                        │
                        ▼
     https://mtolhuijs.nl/news-radar/events.json
                        │
                        ▼
Omarchy shell
  └─ News Radar plugin
       ├─ optional default-on bar newspaper
       ├─ on-demand compositor-managed window
       ├─ bundled Python client helper
       ├─ last-known-good cache
       ├─ local read/saved/display/filter/presentation state
       ├─ durable finite briefing and explicit first-use choice
       ├─ exact enabled-plugin matching
       └─ explicit HTTPS source opening
```

The static feed is the integration contract. The website and Omarchy plugin are independent clients of the same validated events. Live collect → build → serve is owned by Forge Laravel on the maintainer host; the plugin remains a read-only HTTPS client with no application server, database, account service, background daemon, or bidirectional client API of its own. The visible bar widget owns one due-checked refresh timer inside the existing shell process. GitHub Pages is no longer the publication path (optional legacy only).

The local-development route reuses the collector and publisher directly. `make local-latest` selects the newer of the tracked transition seed and its private validated `local-source-snapshot.json`, builds into a temporary directory, revalidates the public feed and build digest, then atomically imports the feed. Current marketplace and YouTube images remain direct URLs on their exact allowlisted origins; validated legacy content-addressed paths from older editions remain supported. Only after that complete import succeeds does it advance the private source baseline. **Check for updates** still fetches the fixed live feed at `https://mtolhuijs.nl/news-radar/events.json`: it preserves an equal/newer owner-built edition and atomically adopts a newer published edition. This route is explicit and owner-run; it is not a second feed protocol or resident publisher.

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
│   ├── briefing.py
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
│   ├── feed-v2.schema.json
│   ├── state-v1.schema.json
│   ├── state-v2.schema.json
│   ├── state-v3.schema.json
│   ├── state-v4.schema.json
│   ├── state-v5.schema.json
│   ├── state-v6.schema.json
│   ├── state-v7.schema.json
│   ├── state-v8.schema.json
│   ├── state-v9.schema.json
│   ├── state-v10.schema.json
│   ├── state-v11.schema.json
│   ├── state-v12.schema.json
│   ├── state-v13.schema.json
│   └── insights-v1.schema.json
├── share/
│   └── applications/
│       └── io.github.mtolhuys.news-radar.desktop
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── lab/
└── .github/workflows/
    └── test.yml
```

Generated deployment output belongs in `dist/` and stays untracked. The tracked source snapshot is a reviewed transition/recovery seed. Normal scheduled continuity comes from Laravel storage on the Forge host between `news-radar:publish` runs. Snapshot contents are public normalized source facts only, never tokens, response headers containing secrets, or deployment evidence.

## Plugin contract

Version 1 uses one third-party plugin with paired panel and bar entry points:

```json
{
  "schemaVersion": 1,
  "id": "io.github.mtolhuys.news-radar",
  "name": "Omarchy News Radar",
  "version": "0.5.0",
  "author": "Maarten Tolhuijs",
  "description": "A keyboard-first front page for meaningful Omarchy activity.",
  "icon": "assets/io.github.mtolhuys.news-radar.svg",
  "windowIdentity": { "appId": "org.quickshell", "title": "📰 Omarchy News Radar" },
  "kinds": ["panel", "bar-widget"],
  "entryPoints": { "panel": "src/Panel.qml", "barWidget": "src/BarWidget.qml" },
  "barWidget": { "defaultSection": "right", "allowMultiple": false }
}
```

This excerpt describes the local candidate manifest, not a published release. The panel entry point is an `Item`, accepts current shell-injected properties, exposes `open(payloadJson)` and `close()`, and owns a normal `FloatingWindow`. The window is compositor-managed, resizable/maximizable, and follows ordinary task switching; it is not a `PanelWindow` or layer-shell overlay. Radar omits an unreliable minimize control.

Every public activation route uses the shell's `summon` operation. Closed means create/open/focus; already open means raise and focus the same window, whether it is foreground or obscured. Repeated activation never serves as close. `Escape`, `q`, the rendered close control, and normal window-manager close remain the deliberate close routes. The panel's bounded window helper validates one exact mapped Radar client, floats it if necessary, then focuses that address; an ambiguous identity fails closed.

The bar entry point reloads the bounded local enabled-plugin ID set before each indicator model request. Requests are coalesced across state, feed, timer, and refresh signals rather than dropped while a helper is active. The model projects every section once through the shared persistent-filter path, then deduplicates unread event IDs across those projections, so every advertised story is reachable in the newspaper and one event appearing in multiple sections is counted once. It then runs one bounded migration command when Omarchy creates its generation, including the generation loaded by the updater's normal rescan. That command cannot install a free chord: it mutates only when the helper identifies the byte-exact 0.1.3 Radar-owned `toggle` block and one matching live action. It backs up and atomically replaces only that owned block with `summon`, reloads and validates Hyprland, and rolls back on failure. Every other classification is a no-op. The panel still performs a read-only inspection on open and renders **Update shortcut** as a user-visible retry if the exact legacy state remains.

`windowIdentity` is a narrow companion-integration declaration for hosted normal windows. The app ID and full title must both equal the compositor values before a companion switcher or dock may use the existing local manifest name/icon. Unknown, disabled, malformed, missing, or ambiguous declarations fall back to normal desktop-entry resolution; the declaration does not alter Quickshell's process-wide app ID.

The optional Apps-menu integration is a standard XDG desktop entry, not another plugin entry point. `news-radar-launcher install` copies that fixed entry and the existing SVG mark into their user XDG data locations and stores a private digest/path receipt. `make local-latest` invokes it as part of the owner's explicit desktop synchronization. Public plugin installation documents the same explicit command because current Omarchy plugin add/remove deliberately runs no repository hooks. Removal is therefore performed through the helper while the checkout still exists.

Omit `keepLoaded`. Omarchy keeps the declared bar widget within its normal bar lifecycle, while the panel exposes the ordinary `open`/`close` contract. The bar widget loads only bounded local indicator state, runs a refresh from a separately recorded last-check deadline, and stops its refresh cadence while hidden. Neither entry point installs a service or daemon.

## Panel lifecycle

`open()` follows this order:

1. Reset transient error state without changing reading state, and begin the exact pre-map placement preparation described in D059.
2. Ask the client helper for the validated local cache and local user state.
3. Render the existing cached briefing and source sections with explicit per-story `isUnread` decoration. A missing briefing waits for initialization; ordinary projections and the bar never create one.
4. Query `omarchy-shell shell listPlugins` to derive locally enabled plugin IDs, then call `ensure-briefing` once. An unavailable discovery result uses the existing fail-closed empty ID list. The command initializes only a missing snapshot and never replaces an existing or completed briefing.
5. Start at most one bounded news refresh helper and one independent optional insights refresh; neither blocks cached reading.
6. Treat a matching `304 Not Modified` as success only when a validated local feed exists; otherwise validate the candidate feed completely before atomically replacing cache or the visible current model.
7. Preserve the cached model and surface a recoverable status if refresh fails.
8. Reveal after placement and local projection are ready, or after the bounded recovery deadline exposes a recoverable state. Network freshness is not a visibility prerequisite. Prime keyboard focus only after the visible model exists.
9. Home and My setup never arm a read for hidden story content. In a visible source reader on a fresh open only, capture the first non-empty projection's selected event ID and panel-open generation, wait one brief single-shot dwell, and mark it read through the ordinary per-story helper only when that generation remains visible with the exact story still selected. Automatic opening reprojections replace the candidate and restart the dwell; explicit story interaction, Tune, Settings, the first-use choice, or close cancels it. First use cannot read a story while its welcome choice covers the reading surface.

Dense-list keyboard movement reads the instantiated delegate geometry before changing selection. A next row already inside the viewport uses ordinary containment; a next row crossing the bottom resolves its exact `ListView.Beginning` offset and eases `contentY` there. This keeps variable-height rows fully visible without changing pointer flicking, pagination, projection, or read-state semantics.

`close()` and component destruction must cancel or terminate owned network/model/briefing helpers, cancel an initial-story one-shot that has not yet reached a visible story, drain any already-requested per-story reading mutation, release the panel window, and leave no child process. Close never bulk-marks a session or edition. Re-summoning an already visible panel, refresh, and later projections do not rearm the one-shot. All cross-process state read/modify/write operations and feed replacements use one private kernel-backed state lock. Reading and first-use mutations load the current feed inside that lock, so replacement cannot change the edition halfway through the transition. The separate refresh lock still prevents overlapping network retrieval.

## Finite local briefing

`radar/briefing.py` selects a maximum of five groups from unread non-YouTube events that satisfy the persistent Front Page filters and local mutes. It prioritizes reviewed critical and notable notices, the newest official release and one official news item, exact enabled-plugin matches or explicit follows, and one discovery when available. Critical notices may consume all five places. Routine verification changes alone never consume a place. Selection uses source facts and deterministic ordering, never metrics or generated impact prose. The public site's generic Front Page remains a separate non-personalized projection.

State v13 retains the selected groups introduced in v12 as exact event IDs plus a closed reason enum and the edition's collection timestamp. Each selected plugin groups only its occurrences present in that snapshot. Projections resolve those IDs against the validated cache and retain original titles, dates, and source links; a newer occurrence for the same plugin never joins silently. Reading, filtering, refreshing, changing installed plugins, and reopening preserve membership. Only **New briefing** replaces it, leaving skipped events unread. Replacement first selects eligible unread IDs outside the current snapshot when they can form another briefing, so unfinished priority items cannot prevent the explicit next selection from advancing. With no alternative groups, it uses the ordinary unread selection. This excludes only the immediately previous snapshot and creates no growing history. The bar reads the existing snapshot but does not initialize or replace it.

The representative's `isUnread` remains its exact per-story reading fact. Group counts separately report unread members. Selecting or opening the representative reads only that event; opening another group source reads only that member. **Mark group read** and **Mark briefing read** are explicit bounded actions against the displayed snapshot digest. A stale digest is a benign no-op. Completion means every still-present member of that selected briefing has been read and no member has expired, not that the entire feed is read. Missing members receive an explicit expiration count instead of a false completion claim. Empty briefings remain empty and complete until the user requests another.

New state starts with `onboardingComplete=false`. Every valid v1–v11 migration sets it true and preserves supported reading state, saves, and preferences. **Browse current stories** completes that choice without changing reads. **Start from today** requires the digest of the exact displayed event-ID set, marks that current backlog through per-event overrides, preserves explicit unread overrides, and stores an empty completed briefing. It never advances `readThrough` or uses the wall clock. A membership change between display and activation returns `stale-edition` without changing reading state, requiring another deliberate choice; a later-discovered event with an older occurrence timestamp remains unread.

## Client helper

The bundled Python helper is the only component that reads or writes Radar cache and state. QML invokes it with structural argument arrays and consumes one bounded JSON response. The helper has a small command surface:

```text
news-radar-client read
news-radar-client refresh
news-radar-client refresh-if-due --minimum-age <seconds>
news-radar-client indicator
news-radar-client installed
news-radar-client project --section <id> --installed-json <json-array> --installed-facts-json <json-array> --installed-facts-status available|unavailable
news-radar-client insights-refresh
news-radar-client insights-project --installed-facts-json <json-array> --installed-facts-status available|unavailable
news-radar-client set-relevance --kind plugin|source|creator --id <target-id> --mode follow|mute|clear
news-radar-client ensure-briefing --installed-json <json-array>
news-radar-client new-briefing --installed-json <json-array>
news-radar-client complete-onboarding
news-radar-client start-from-today --feed-digest <64-character-sha256>
news-radar-client mark-briefing-read --briefing-id <64-character-sha256>
news-radar-client mark-briefing-group-read --briefing-id <64-character-sha256> --event-id <group-id>
news-radar-client set-read --event-id <id> --read true|false
news-radar-client mark-section-read --section <id> --installed-json <json-array>
news-radar-client toggle-saved --event-id <id>
news-radar-client set-preferences [--bar-visible true|false] [--images-visible true|false]
news-radar-client prepare-window --width <pixels> --height <pixels> --minimum-width <pixels> --minimum-height <pixels>
news-radar-client finish-window-opening --token <opening-token>
news-radar-client activate-window
news-radar-client window-state
news-radar-client toggle-window-maximized
news-radar-client remember-window
news-radar-client fit-window --minimum-width <pixels> --minimum-height <pixels>
news-radar-client purge
```

Exact flags may be refined during implementation, but each operation remains explicit, typed, non-interactive, bounded, and independently testable. `purge` is never invoked by disablement or ordinary removal; it is a deliberate user-data action.

`window-state` and `toggle-window-maximized` use actual Hyprland internal and client fullscreen modes. Hyprland 0.56.2 advertises maximized state to ordinary mapped Wayland windows to suppress client decorations, so Qt's `maximized` property alone cannot establish compositor geometry. Both helpers require one exact mapped Radar identity and a valid address. Toggle rechecks identity, address, modes and floating state inside one Lua evaluation before an addressed `hl.dsp.window.fullscreen_state` set action, then confirms the result through bounded client queries. It switches normal/maximized modes only, preserves explicit fullscreen and refuses grouped windows. It never focuses, toggles floating, installs a rule, starts a timer, writes reading state or retries an uncertain mutation. Successful responses include `address`, `mapped`, `floating`, `maximized`, `fullscreen`, `fullscreenInternal` and `fullscreenClient`; toggle outcomes are `maximized`, `restored` or `fullscreen-preserved`. Missing, ambiguous, invalid or unconfirmed state fails closed.

Every projection returns the local state, displayed feed-membership digest and matching event count, and briefing status alongside its existing section model. The first-use count and digest come from the same validated feed snapshot, so a stale cached QML model cannot describe a different backlog from the one the action targets. Briefing status distinguishes initialization, total/remaining groups, unread member events, completion, expired members, and whether more eligible unread events can form another briefing. A group row retains its original representative ID as `briefingGroupId` and exposes each available member's original source fields; none of these private facts enters a network request.

The helper uses a fixed production feed origin compiled into one module. Tests may inject a fixture file or loopback test server through an explicit test-only flag or environment boundary that is disabled in public runtime paths.

Feed requests advertise the static `Accept-Encoding: gzip` capability alongside JSON, the product user agent, and applicable HTTP validators. The standard-library HTTP helper accepts identity or gzip, including valid concatenated gzip members under one shared bound. Both transferred and decompressed feed bodies are capped independently at 2 MiB; decompression stops at one byte over the output bound, checks the total deadline between members, and rejects corrupt, truncated, trailing invalid, or unsupported encoded bodies before JSON validation. A `304` remains bodyless and reuses only a validated cached feed. Compression adds no endpoint, dependency, personalized header, or runtime process.

## Local storage

Follow XDG ownership:

| Path | Purpose |
| --- | --- |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/feed.json` | Last-known-good validated feed |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/feed-http.json` | Private bounded `ETag`/`Last-Modified` validators bound to the fixed feed URL; disposable and purge-owned |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/insights.json` | Independent last-known-good optional source coverage |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/insights-http.json` | Validators bound to the fixed companion URL |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/insights-check.json` | Independent companion check cadence |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/update-check.json` | Private bounded timestamp/outcome for background check cadence; not publication freshness |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/assets/images/` | Content-addressed rasters from an explicitly imported local edition |
| `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/local-edition.json` | Bounded digest/revision marker for local-edition projection |
| `${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-news-radar/state.json` | Read baseline/overrides, saved items, local display/filter and follow/mute preferences, first-use completion, exact briefing membership, and schema version |
| `${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-news-radar/window.json` | Bounded private placement metadata, separate from reading state |
| `${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-news-radar/diagnostics.log` | Optional bounded local diagnostics without feed bodies or private paths |

Use private directories, mode `0600` files where the platform permits, same-directory temporary files, `fsync`, and atomic rename. Refuse symlinked cache/state targets. A failed candidate never truncates or replaces good data.

An imported local marker is honored only when its SHA-256 matches the canonical cached feed. Every referenced legacy local raster is re-inspected for format, dimensions, static structure, byte bound, and content-addressed filename before the feed changes. Missing legacy local image bytes produce text fallback rather than an unvalidated upstream request; current `sourceUrl` images remain restricted to their exact allowlisted origins and paths.

## Collector

The collector is a Python standard-library application with pure source adapters and one orchestration layer. Adapters convert source-specific payloads into normalized snapshots; the diff layer converts two valid snapshots into events; the publisher validates the full envelope and emits JSON, RSS, and a static HTML projection.

Optional metric enrichment is a post-diff step. Successful source snapshots replace their own metric group; a failed optional metric source retains prior observed facts. Metrics never enter event identity, diff generation, curation, ordering, or Front Page selection.

Restoring a source snapshot validates every event, the 500-event bound, unique IDs, and exact canonical ordering without applying wall-clock retention. Rolling retention belongs to successor construction and uses that collection's explicit clock.

Collection is transactional:

1. Fetch each allowlisted source using explicit headers, timeouts, size limits, and conditional request metadata where useful.
2. Validate the complete source payload into a source-specific immutable model.
3. Produce per-source success or failure without mutating the prior snapshot.
4. Diff only successful current sources against their last successful prior state.
5. Create events deterministically and merge reviewed curation.
6. Validate the complete candidate feed.
7. Fetch only declared marketplace preview thumbnails from `https://plugins.omarchy.org`, inspect bounded PNG/JPEG/WebP bytes and dimensions, and retain successful images as direct allowlisted `sourceUrl` references without storing the raster on the feed host. Image failure omits that optional image, not its story; YouTube thumbnail URLs are separately accepted only in their fixed allowlisted shape.
8. Write generated artifacts to a temporary output tree.
9. Publish the output tree and updated successful source states only after every global invariant passes.

A partial source outage may produce a feed with explicit source-health metadata, but the unavailable source retains its previous snapshot and produces no mass deletion or retirement events.

Event identity also protects occurrence history. If a lagging source state rediscovers an event whose deterministic ID already exists in the retained ledger, its original `occurredAt` and `discoveredAt` remain authoritative; only explicitly supported description and metric enrichment may refresh.

Each Forge publish retains the restored snapshot separately through collection, then runs `audit-marketplace-additions` against the successor. The gate requires nondecreasing catalog generation time and a `plugin-added` event for every newly appearing canonical plugin ID before the public tree is swapped into place.

## Static publication

Forge Laravel `news-radar:publish` (every five minutes, without overlapping) collects and builds an immutable edition tree containing at least:

```text
dist/  (then served under /news-radar/)
├── index.html
├── events.json
├── feed.xml
├── assets/
│   └── site.css
└── archive/
```

Live feed URL: `https://mtolhuijs.nl/news-radar/events.json`. GitHub Actions `test.yml` still CI-tests the repository; `publication.yml` and GitHub Pages are retired as the publication path.

The site contains no runtime framework, cookies, analytics, user input, service worker, external font, or client-side content fetch required for the initial page. Publisher output must escape every remote string for its destination context and use a strict Content Security Policy compatible with a static site.

The public edition offers a fixed marketplace installation link, a link to the repository's desktop walkthrough, and RSS/JSON subscriptions. The expanded candidate also generates generic story, discovery and weekly pages, an independent `insights.json`, and escaped social SVGs under `assets/share/`. Page metadata uses fixed canonical destinations and context-escaped source text. A keyboard skip link targets the focusable news landmark. None of these artifacts contains a personal feed or local setup data.

The live feed contains a bounded rolling window. Monthly archives may retain older public events without increasing the plugin payload. Saved local items retain the fields needed to remain useful after an event leaves the live window.

Before collection, publish restores continuity state from Laravel storage (or a tracked transition seed on first run) and validates it before replacement. Missing or invalid state stops the build rather than replaying a stale repository seed. Each generated feed records source `checkedAt`, collection `generatedAt`, and artifact `publishedAt` separately. Publication and cache timing remain available to validation, debug state, the bounded bar-health model, and external monitoring; they do not occupy the normal reader while validated news is available.

## Installed-plugin relevance

The panel calls the maintained shell IPC and treats the returned plugin IDs as local data. Matching is exact on canonical plugin ID. Do not send installed IDs to the feed host and do not infer installation from repository names or display names.

“For You” includes events whose entity plugin ID exactly matches an enabled local plugin, plus events matching explicit local project/source/creator follows, subject to mutes. The removed free-text manual-interest path remains absent. My setup uses bounded local names and exact versions; an explicit shell `firstParty` flag excludes uncovered built-in components without guessing from ID prefixes. Successful empty discovery and unavailable discovery remain distinct.

## Optional bar indicator

The main manifest declares one non-multiple `bar-widget`, defaulted to the right section. It renders a code-native newspaper, actionable unread count, and publisher/source health dot; left click summons and raises the panel, middle click checks the published edition, and right click persists `barVisible=false`. The unread count is the unique union of unread event IDs surviving the currently visible persistent section projections, using the same enabled-plugin IDs and filters as the panel. Search and pagination remain transient and do not affect it. The widget root binds `visible` to that preference, and current Omarchy `ModuleSlot` geometry maps an invisible item to exact zero width/height. A local state-file watch restores it when Tune Your Radar sets the preference true.

While visible, one single-shot timer checks the fixed feed at most every five minutes after either a successful or failed attempt. Cadence comes from private `update-check.json`, not the edition's collection timestamp, so loading the shell shortly before an edition becomes old cannot defer the next check for another full interval. A feed-file watch reloads the canonical unread/health indicator immediately after either entry point adopts a valid edition; a 30-second local-only fallback covers missed filesystem events. The panel does not need to be opened. This is a passive bar indicator, not a desktop notification service.

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
- Returning Up from the focused Load more control transfers focus only: the already selected final row and live `contentY` remain unchanged. Under Unread only, QML sends a bounded list of event IDs read during the current view; Python validates those IDs and permits only those otherwise-matching read events through the projection. Persistent unread counts are computed without the exception, and changing section, search, or filter clears it.

## Source-backed companion and public rendering

`insights.py` validates the independent insights-v1 contract and owns strict version precedence. `insights_builder.py` selects reviewed collection members, explicit release-coverage projects, recent event projects and deterministic catalog backfill within the 100-project bound. `sources/release_notes.py` retrieves only the seven repository-owned API paths, at most 30 stable releases each, with 2 MiB responses, 15-second deadlines, no redirects and four concurrent requests. It strips active markup and code blocks deterministically. Prior valid facts are optional input; no companion data enters the news continuity snapshot.

The client companion cache has its own due checks, validators and lock. Local enabled-plugin facts join exact public IDs; a manifest read is a bounded data read, never a repository command. Projection selects setup updates, discovery cards and version-specific notes without sending local data. Explicit follow/mute targets use stable IDs, not display names.

`client.py` retains its import-compatible facade over separate feed, briefing, projection, reading, setup and insight modules; `state_schema.py` owns pure defaults and migrations. `insights.projectDetails` retains unfiltered bounded source context for reachable stories and workflow members when search or mutes hide their overview cards. `provenance.py` requires historical repository agreement before attaching current project/release notes or creator targets. Optional note failure preserves richer prior details only for the same version and source while retaining newly collected releases. Fenced and indented code examples never become extracted changes.

`publisher.py` owns the atomic artifact transaction and RSS. `site/common.py`, `site/cards.py` and `site/pages.py` compose escaped documents, reusable cards and complete pages; `site/site.css` is a readable stylesheet. `publication_images.py` applies the existing exact-origin raster inspection, with at most twelve optional companion thumbnails and four concurrent inspections. Rejected or excess images are omitted without dropping the text. The server retains prior durable pages separately from the rolling producer output.

Optional marketplace image inspection deduplicates URLs across event rows and runs at most four requests concurrently. A 60-second queue budget stops new requests; in-flight requests retain the existing 20-second timeout. Missed previews are omitted while every validated story survives. Discovery images have a separate twelve-item cap and the same bounded queue behavior. Inspection retains only small dimension records, not downloaded raster bodies.

## Desktop composition and live geometry

The panel composes separate session, reading, section, viewport, maintenance and window-lifecycle controllers. Presentation components own the Home, project details, reader, inspector, section rail and settings surfaces. The compact reader places its shared action toolbar inside the scrollable header so enlarged controls cannot consume the article viewport; wide layouts retain fixed reader controls.

`ArticleBody` is the single body renderer shared by the wide inspector and the selected compact row. It renders the complete validated summary or locally escaped article segments, never the shortened list teaser. Only that shared component uses RichText, and both layouts route its source links through `ReaderActions.openArticleLink` and the validated HTTPS helper. Compact selection expands only its current row; other rows retain their quiet headline presentation. Body geometry and plain-text diagnostics refer to the instantiated renderer so runtime checks can prove actual content beyond a teaser and exercise a rendered source link.

`WindowLifecycle` prepares the opening placement and debounces live font/minimum-size and monitor/work-area changes. `fit-window` validates the one exact mapped Radar client and current work areas, preserves a fitting user frame and clamps only when needed. It dispatches only addressed resize/move operations and never changes focus, creates rules or writes reading state. Tiled, maximized and fullscreen geometry remains compositor-managed. Close cancels fit work along with the other owned processes.

`window_rules.py` owns the exact-identity opening declaration and its token-guarded expiry. Its complete specification becomes reusable only after the declaration's Lua evaluation acknowledges success, followed by an ownership-checked confirmation. A partially accepted declaration or failed cleanup therefore cannot make the next open falsely report successful preparation. Closing disables the rule but retains its acknowledged specification; reopening with the same specification re-enables it without appending duplicate effects. Superseded one-shot timers remain armed and expire harmlessly, allowing Hyprland to release their callbacks. A late close, confirmation or expiry cannot alter a newer opening. Hyprland 0.56.2 still appends effects when a named rule's specification changes and exposes no removal/replacement API; those records last until the compositor's next normal configuration reload. Radar never reloads the compositor to reclaim them. Lua callback regressions execute where the Lua runtime is available, including Plugin Lab; ordinary Python-only environments explicitly skip those five checks.
