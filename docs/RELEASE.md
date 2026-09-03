# Release contract

Version `0.4.15` quiets YouTube, diversifies Front Page news by topic, adds local section visibility (state v11), turns Core and Front Page articles into a two-pane reader (quiet headline list, dominant article pane with clickable HTTPS body links, collapsed Details and Keys), and rearms the newspaper refresh timer. Version `0.4.13` adds Forge-collected official Omarchy News RSS into Core as `omarchy-news` events (D048), with fail-closed retention, a three-item Front Page quota, and no feed/state schema version bump. Version `0.4.12` replaces the layered full-glyph/full-radar overlay with one stable Omarchy-and-radar identity. The official full-strength `#9ece6a` logo is the primary silhouette; a compact amber radar occupies its central negative space. The manifest, Apps entry, and companion UIs use one opaque dark squircle. The panel uses matching transparent dark/light contrast variants on its own theme-native plate, avoiding a black box on light themes. The README uses the matching branded hero plus a current Plugin Lab walkthrough of Front Page, plugin activity, and section filters; the marketplace preview remains the branded hero exported from `assets/readme-banner.svg` to root `preview.png`. Version `0.4.11` previously used opacity-tuned full-symbol overlays and an outdated YouTube-focused README capture. No feed or state schema bump. The existing listing is maintainer-controlled; marketplace verification remains exact-commit compatibility evidence rather than a security audit.

## Candidate identity

Record one clean Git commit and tag, manifest version, panel build identity, Python helper version, feed schema, generated artifact SHA-256, selected Omarchy source revision, and Plugin Lab ISO/base identity.

## Publishable checklist

### Product

- `Super+Alt+N` is re-audited as free, installed only after conflict checks, reversible, and accurately documented; the separate Editor shortcut remains intact.
- An exact unmodified 0.1.3 Radar-owned block is reported as `owned-legacy`, automatically backed up and atomically replaced with `summon` by the generation loaded through a normal update rescan, and rolled back on validation failure; all free, current, edited, personal, conflicting, multiple, symlinked, or ambiguous cases remain unchanged, and the visible migration action remains a retry.
- A documented IPC route keeps the panel reachable without the shortcut.
- The explicit XDG launcher helper adds one searchable Apps-menu row with the newspaper icon, refuses modified/unrelated targets, and removes only receipt-matching files.
- Cached-first, refresh, offline, partial-source, invalid-feed, empty, and first-use states have visible recovery.
- Front Page, For You, Core, Plugins, and Saved match the implemented model; reviewed community records remain an optional feed input rather than an empty dedicated section.
- The panel is a normal movable/resizable/maximizable window, participates in `Alt+Tab`, omits the unreliable minimize control, and closes through one shell lifecycle.
- `Tab`/`Shift+Tab`, canonical section identity, fixed-source disclosure, independent filters, exact resets, and arrow-key/Enter finite Load more behavior match the local projection model; the focused action labels Enter explicitly.
- No publication-diagnostics strip occupies the reading surface; a subtle collapsible **Keys** footer at the bottom of the **SECTIONS** rail starts fully collapsed as `Keys · ?` with no shortcut dump and remembers the session choice; search exposes `/` and **Check for updates** exposes `R` on hover. Core and Front Page article cards are quiet headlines; the inspector puts `date · source`, the full article body, and compact actions before a collapsed Details footer.
- Section headers expose an **All** / **Unread only** chip and keyboard `f` that toggle the existing persistent `unreadOnly` filter without a schema bump; Settings keeps its **Unread only** chip in sync; keyboard `a` matches **Mark all as read**; the Keys footer includes `a`, `f`, and `?`.
- Bar click, `Super+Alt+N`, and Apps launch all summon one window; closed, obscured, foreground, rapid-repeat, Alt+Tab, explicit close, and reopen states are machine-asserted with real QMP input.
- Available metrics have exact icon meanings, accessible labels, observation times, and marketplace caveats; raw metric endpoint links are absent, human plugin pages are used where applicable, and metrics cannot influence event creation or ranking.
- Every story exposes an original validated HTTPS source.
- Every row visibly distinguishes `UNREAD` from `READ`; section and newspaper counts use the same exact per-event predicate; the newspaper deduplicates unread IDs across all current persistent section projections and never advertises stories hidden by every section; deliberate selection and `u` affect only one story; the explicit filtered-section action atomically includes unloaded matches while close/refresh never bulk-mark; the default-on newspaper adopts and displays unread arrivals with the panel closed, uses the documented 15-minute success/five-minute failure cadence, and its zero-gap hiding, Tune re-enable, animated refresh progress, health states, and no-desktop-pop-up boundary match the implementation.
- For You uses only exact locally enabled plugin IDs; manual interests and section profiles have no control, CLI route, or current state member, and v1–v10 state migrates to v11 without losing supported data. Hidden source rails leave the nav and newspaper union; Front Page, For You, and Saved stay reachable.
- YouTube collection on Forge requires optional `YOUTUBE_API_KEY`; CI remains fixture-only and never calls the live API.
- No account, telemetry, AI summary, plugin installation action, or unsupported scraper is implied.

### Data and publication

- First marketplace bootstrap emits at most twelve listings from the prior fourteen days and no historical flood.
- Source adapters are bounded, allowlisted, deterministic, and fixture-tested.
- Every plugin-event summary uses the current validated marketplace description when available; description changes enrich existing events without creating or reordering them.
- Source failure preserves prior state and cannot create mass retirement.
- Forge Laravel `news-radar:publish` is scheduled every 10 minutes without overlapping; live feed is `https://mtolhuijs.nl/news-radar/events.json`. GitHub Actions publication and Pages are retired.
- Every publish restores continuity state from Laravel storage (tracked transition seed only on first run); missing or invalid continuity fails closed, event first-observation timestamps are immutable, and the tracked v2 transition seed is accepted only while fresh.
- Front Page selects the newest official release once, then current plugin/community activity; it never fills an artificial Core quota with older releases.
- Feed metadata and internal client state separately identify source check, collection, artifact publication, and local cache time. Normal successful reading exposes none of that pipeline telemetry as content.
- JSON, RSS, HTML, archive, and snapshot validate and are byte-stable under a fixed clock.
- Generated HTML/XML escapes hostile content and the site uses a restrictive static security policy.
- Live feed size, event count, archive policy, and source-health metadata match the documented contract.
- Mirrored previews are allowlisted, byte/dimension validated, content-addressed, same-origin, and optional on failure; the public feed never carries upstream image URLs.

### Runtime and safety

- Manifest and every declared entry point validate.
- Remote text remains plain data, image decoding is limited to validated same-origin rasters, and source opening is explicit.
- Cache/state writes are private, bounded, symlink-safe, atomic, recoverable, and serialized across panel/bar helper processes.
- Application launcher/icon writes are bounded, receipt-backed, symlink-safe, atomic, reversible, and never overwrite user-modified or unrelated files.
- One refresh process maximum per entry point plus a cross-instance lock; the panel tears down on close and bar refresh polling stops when hidden.
- Shortcut install/migrate/remove preserves unrelated Lua exactly and rolls back on reload or config error; the automatic update command cannot install a free chord.
- Disable and removal preserve user state; explicit purge removes only validated Radar-owned paths.
- No runtime package installation, privilege escalation, arbitrary command, or background daemon exists.
- The local path revalidates imported feed/images, advances its private source state only after complete import, never presents fixtures or rediscovered old diffs as current news, refuses a published downgrade, adopts a newer published edition on refresh, and migrates only the exact old panel-only placement. Its origin remains internal rather than persistent reader copy.

### Visual and accessibility

- Current Omarchy tokens drive color, spacing, typography, borders, focus, and monitor fit.
- Selected and unselected primary/secondary text, status, summaries, metadata, and counts remain distinguishable from their surfaces in maintained dark and light themes.
- Light/dark, narrow/wide, long text, empty/dense, cached/refreshing/offline/invalid/partial, and 200% text states are reviewed.
- Visual columns preserve one semantic keyboard order; the SECTIONS rail is comfortably padded and capped, the center list is a compact index, and on Core/Front Page the ~60% reading pane prioritizes title, `date · source`, article body, and actions before collapsed Details.
- Keyboard-only traversal, focus visibility, labels, counts, source health, and reduced motion pass.
- Assistive-technology claims do not exceed actual evidence.

### Evidence and distribution

- `make test`, `make validate`, `make feed-fixture`, and `make site` pass from a clean clone without unapproved downloads; `make collect-live` separately proves the allowlisted live build.
- Plugin Lab fresh-install and released-0.1.3 upgrade acceptance pass for the exact candidate with inspected logs and screenshots.
- The networked Plugin Lab preview journey renders the fixed public edition in the exact Matte Black marketing frame; the README crop matches its recorded window geometry.
- Public clean-clone installation, shortcut setup/removal, update, and plugin removal pass once the remote exists.
- Workflow actions are pinned and permissions are least privilege.
- README, changelog, manifest, UI version, feed schema, screenshots, release notes, and evidence agree.
- Repository contains no secrets, private state, real bindings, caches, VM disks, lab output, generated deployment tree, or machine-local paths.
- No push, tag, release, marketplace submission, domain change, or external announcement occurs without owner authorization. GitHub Pages is not the live publication path.

## Removal contract

Document removal in this order:

1. Run the shortcut helper's `remove` command while the plugin checkout still exists.
2. Run the launcher helper's `remove` command while the plugin checkout still exists.
3. Remove the plugin through `omarchy plugin remove io.github.mtolhuys.news-radar`.
4. Optionally run the explicit purge command before removal when the user wants local cache, reading state, and saved items deleted.

Normal plugin removal does not delete local state or run repository cleanup hooks. Removing the plugin before its binding leaves a harmless unresolved shell IPC binding; removing it before launcher cleanup leaves a stale XDG row. Reinstall the exact checkout to run the corresponding helper, or remove only the documented owned files after verifying them manually.

## Owner-authorized publication procedure

Live publication is owned by Forge Laravel on the maintainer host. GitHub Actions `publication.yml` and GitHub Pages are retired as the publication path. The feed clients fetch is always `https://mtolhuijs.nl/news-radar/events.json`.

1. Push the reviewed clean candidate commit to the existing public repository at `https://github.com/mtolhuys/omarchy-news-radar`. Ensure Forge's `NEWS_RADAR_PATH` checkout can fast-forward or pull that commit before the next publish. Do not create the release or update the marketplace snapshot yet.
2. Confirm Laravel schedule lists only `news-radar:publish` (every 10 minutes, without overlapping). Optionally run `php artisan news-radar:publish -v` once on the Forge host and verify the public JSON, RSS, HTML, mirrored images, build digest, source health, collection time, and `publishedAt` at `https://mtolhuijs.nl/news-radar/`.
3. Wait for at least one successful scheduled Forge publish after the candidate is on the host checkout. Confirm continuity advanced in Laravel storage (no replay of the committed baseline as fresh news) and that public `publishedAt` matches the deployed build.
4. In the disposable Plugin Lab, run `OMARCHY_NEWS_RADAR_PUBLIC_URL=https://github.com/mtolhuys/omarchy-news-radar OMARCHY_NEWS_RADAR_EXPECTED_COMMIT=<40-character-commit> ./bin/lab plugin tests/lab/public-install.sh`. Inspect the retained log and screenshot evidence and confirm the public clone resolved the exact intended commit.
5. Review the release checklist and evidence record against that exact commit. Only then create the release tag.
6. Use the marketplace's **Plugin verification** form with **Verify and publish a newer upstream commit**, the exact plugin ID, repository root URL, and full 40-character release SHA. The existing snapshot remains live while compatibility validation, the Automated Security Baseline, maintainer approval, testing, and deployment remain maintainer-controlled. Do not represent issue creation as promotion or as a security audit.

Normal snapshot advancement is a validated handoff in Laravel storage between successful Forge publishes. The tracked repository snapshot is only a reviewed transition/recovery seed; using it again requires a new explicit schema transition and fresh source audit rather than a silent fallback. If publication age exceeds 90 minutes, a source check lags publication materially, or continuity restoration fails, recover by inspecting the prior storage snapshot and restoring that chain before the next publish. Never bypass continuity by replaying an old repository snapshot.

## Evidence record template

```text
Release:
Commit / tag:
Manifest / panel / helper identity:
Feed schema:
Artifact SHA-256:
Omarchy revision / ISO / lab base:

Commands:
- source:
- generation:
- lifecycle:
- product scenario:
- public install:

Timestamped evidence directories:
-

Machine assertions:
-

Visual review:
-

Performance measurements:
-

Deliberate limitations / unverified boundaries:
-
```
