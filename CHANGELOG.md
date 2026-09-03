# Changelog

## Unreleased

### Documentation
- Refresh the README walkthrough with the current 0.4.14 public edition, full official Omarchy News detail, real plugin activity and metrics, section filters, and a Matte Black/Catppuccin Latte theme switch without unreviewed story imagery.

## 0.4.14 — 2026-09-03

- Omarchy News stories now carry the official RSS article body (plain text, up to 8k) in the detail pane; list rows still elide to a teaser.
- Existing news items refresh their article text on the next collect without becoming new stories.
- Bar widget scheduled refresh interval is 5 minutes so clients pick up Forge publishes faster.

## 0.4.13 — 2026-09-03

### Added
- Forge-collected official Omarchy News RSS (`https://omarchy.org/news/rss.xml`) as Core events of type `omarchy-news`, with deterministic guid-based IDs, fail-closed snapshot retention, and CI fixtures only (D048).

### Changed
- Front Page admits at most three recent Omarchy News items by quota; news stays `routine` so blanket notability cannot flood the edition (D008/D048).
- Settings source disclosure for Front Page and Core names Omarchy News beside releases.
- Extend feed schema v2 and state schema v10 enums for the new event type and source id without a schema version bump.

## 0.4.12 — 2026-09-03

### Changed
- Make the official Omarchy logo the full-strength primary application mark, with a compact two-ring amber radar integrated into its central negative space rather than placing two complete symbols over each other.
- Keep one opaque, self-contained dark squircle for the manifest, Apps entry, and companion UIs, while the panel uses transparent light/dark contrast variants on its own theme-native plate instead of showing a black box in light themes.
- Add an evergreen branded hero and replace the outdated YouTube-focused animation with a current product walkthrough covering Front Page, plugin activity, and section filters; keep the root `preview.png` as the marketplace preview.

No feed or local-state schema bump.

## 0.4.11 — 2026-09-02

### Fixed
- Panel header icon chip on Lupine light: keep opaque `Color.popups.background` plate and add a visible `Color.popups.border` so the squircle reads as a chip (not same-color-as-header wash).
- Light themes (popup bg luminance > ~0.5) load `assets/io.github.mtolhuys.news-radar-light.svg` with Omarchy green glyph opacity ~0.80 and slightly stronger amber; dark/Matte Black keep the 0.4.10 transparent SVG.

### Changed
- Apps-menu / XDG launcher still use the manifest dark-tuned transparent SVG (unchanged; acceptable compositing).

No feed or local-state schema bump.


## 0.4.10 — 2026-09-02

### Fixed
- Light-theme contrast on Lupine and similar popup surfaces: luminance-aware secondary (≥0.82) and quiet (≥0.64) text floors; dark keeps ~0.72 / ~0.52 so Matte Black stays intentional.
- Modal Tune/Settings scrims dim with foreground alpha (light 0.22 / dark 0.45) instead of `Color.background` @ 0.82 white-wash on light.
- Keys idle chrome rides the raised quiet floor on light (≥0.64).
- Panel header mark no longer paints an opaque `#111` squircle: SVG is transparent; an opaque `Color.popups.background` rounded badge sits behind the Image so light/dark themes tint the icon.

### Changed
- Apps-menu / XDG launcher still ships the single transparent SVG (best-effort compositing; no QML theme fill there). Panel and companions that draw the asset can supply their own opaque theme badge.

No feed or local-state schema bump.

## 0.4.9 — 2026-09-02

### Changed
- Drop the outer amber rect stroke on the Apps-menu icon so the mark is a cleaner black-fill squircle with the green Omarchy glyph (`scale(0.078)`) and amber radar only.

### Fixed
- Ignore local `.tmp/` scratch (icon/preview rasters) so untracked files no longer block `make local-latest`.

### Notes
- No feed or local-state schema bump. Community plugin; not an official Omarchy project (Omarchy mark pending TM).

## 0.4.8 — 2026-09-02

### Changed
- Replace the ASCII Apps-menu icon with a high-contrast radar mark: amber rim, bold concentric rings/sweep/blip, and a larger Omarchy brand logo (#9ece6a) blended under the radar (readable at small sizes; no ASCII text).

### Notes
- No feed or local-state schema bump. Community plugin; not an official Omarchy project (Omarchy mark pending TM).

## 0.4.7 — 2026-09-02

### Fixed
- YouTube's six-hour collect cadence no longer blocks the first populate: an empty or missing `videoIds` snapshot refreshes immediately while fail-closed retention of prior events is unchanged.
- **Check for updates** on a newer local live edition that lacks YouTube adopts the published Forge feed when it already has `youtube-video` events (narrow D029 exception; D046), so clients fill the YouTube section ASAP.

### Notes
- No feed or local-state schema bump. Icon contrast remains the 0.4.6 asset.

## 0.4.6 — 2026-09-02

### Changed
- Raise icon contrast: brighter masthead (`#c8c8c8`), paper (`#9a9a9a`), and amber (`#e0a04a`) fills so the ASCII Omarchy radar is readable in the Apps menu (was invisibly dim in 0.4.5).

### Notes
- No feed or local-state schema bump.

## 0.4.5 — 2026-09-02

### Changed
- Refresh the plugin icon to an ASCII-art radar face with an **Omarchy** masthead for the Apps menu and marketplace listing.

### Notes
- No feed or local-state schema bump.

## 0.4.4 — 2026-09-02

### Changed
- Soften the SECTIONS-rail **Keys** legend: drop boxed keycaps and the heavy toggle chrome for quiet typography that matches Matte Black.
- Trim the SECTIONS rail slightly (preferred 15% → 14% wide, max 184 → 176) and slim the center list (48% → 45%) so the detail inspector widens (31% → 36%) for reading the selected story.

### Notes
- No feed or local-state schema bump.

## 0.4.3 — 2026-09-02

### Changed
- Move the collapsible **Keys** legend to the bottom of the left **SECTIONS** rail (not under the story list).
- Widen the SECTIONS rail slightly (preferred 13% → 15% wide / 20% → 22% narrow, max 168 → 184) for comfortable labels+counts without returning to large gutters.
- Slim the center story list (52% → 48% wide / 74% → 72% narrow) and give the freed width to the detail inspector (27% → 31%) so the news itself reads roomier.

### Added
- Keyboard `a` marks all unread stories matching the current section's Settings as read (same as the header **Mark all as read** control); no-ops when nothing is unread or Settings/preferences/search are editing.

### Notes
- No feed or local-state schema bump.

## 0.4.2 — 2026-09-02

### Changed
- Tighten the left **SECTIONS** rail (lower preferred width, min/max caps) so labels and unread counts fit without large empty gutters on wide windows.
- Give the center story list more of the freed width; the detail inspector shrinks slightly but keeps actions and metadata readable.
- Narrow breakpoint still hides the inspector and keeps a usable sections share; no feed or local-state schema bump.

## 0.4.1 — 2026-09-02

### Added
- Per-section **All ↔ Unread only** toggle in the panel section header (next to Mark all / Settings), reusing the existing `unreadOnly` filter with no schema change.
- Keyboard `f` flips the same unread filter when Settings, preferences, and search are not editing.
- Subtle collapsible **Keys** footer under the story list (compact keycaps · muted captions) listing the real bindings including `f`; `?` or the **Keys** control toggles it. Collapse is session-only.

### Notes
- The Settings **Unread only** chip remains; header and Settings stay in sync through the shared section filter.
- No feed or local-state schema bump.

## 0.4.0 — 2026-09-02

### Added
- YouTube section for Omarchy-related videos collected through the allowlisted YouTube Data API v3 (Forge-only `YOUTUBE_API_KEY`).
- Feed schema version 2 and local state schema version 10 with a `youtube` client section (keys `1`–`6`).
- Optional `youtube-views` / `youtube-likes` metrics and allowlisted `i.ytimg.com` thumbnails.

### Changed
- Ranking for views/likes/recent applies only inside the YouTube section; Front Page, significance, and identity stay unchanged (D045 / D008 / D020).

### Fixed
- Truncate or fall back YouTube descriptions when building summaries so long/empty API descriptions do not fail the whole YouTube source.
- Prefix YouTube entity IDs with `yt:` so Data API video IDs that start with `_` or `-` satisfy entity ID validation.

### Notes
- Missing or failed YouTube collection fails closed and retains the prior YouTube snapshot. CI uses fixtures only—no live YouTube API.

## 0.3.0 — 2026-09-02

- Point `FEED_URL` at the rate-limited Laravel feed `https://mtolhuijs.nl/news-radar/events.json`.
- Pass through allowlisted marketplace preview HTTPS URLs (`image.sourceUrl`) instead of mirroring rasters onto the feed host; clients load `https://plugins.omarchy.org/assets/img/plugins/…` only.
- Update RSS/HTML edition links to `https://mtolhuijs.nl/news-radar/` and allow that marketplace origin in the static CSP `img-src`.
- Forge `news-radar:publish` keeps writing a minimal public tree (no `assets/images`) and purges leftover mirrored rasters.

## 0.2.3 — 2026-09-02

- Serve the live JSON/RSS/HTML edition from `https://mtolhuijs.nl/storage/news-radar/` so Forge owns collect → build → serve.
- Point `FEED_URL` / `FEED_ORIGIN` and RSS channel links at mtolhuijs.nl instead of GitHub Pages.
- Keep `publication.yml` as an optional backup path; scheduled delivery no longer requires Actions or Pages.


## 0.2.2 — 2026-09-02

- Make the top-bar unread badge count the deduplicated union of stories reachable through the current persistent section projections instead of every unread event in the raw feed.
- Reload exact enabled-plugin IDs before each coalesced bar indicator request, keeping Front Page and For You projection membership aligned after plugin enablement changes.
- Add a regression for unread stories hidden by every section filter so an `8 unread` badge can never lead to a newspaper whose sections all report zero.

## 0.2.1 — 2026-09-02

- Keep the successful reading surface focused on news by removing persistent edition-mode, source-health, publication-age, cache, and version diagnostics.
- Remove the always-visible keyboard legend; shortcuts remain available through focused controls, tooltips, and the documented keyboard map.
- Simplify search and section summary copy while preserving filter state, story counts, unread counts, and the temporary just-read explanation when it is actually relevant.
- Show a concise update failure only when Radar has no usable cached news; cached last-known-good stories remain quietly readable through transient publisher or network problems.
- Correct the public README release state and installation heading so the documented command matches the current release.
- Append newly paginated stories to a stable rendered model, retain unchanged row delegates during read projections, and preload the adjacent viewport so **Load more** and both following Down presses remain visually deterministic.
- Settle explicit viewport anchors across rendered frames and cancel pending preservation on close, preventing virtualized delegates or asynchronous read updates from leaving the selected row offset or out of sight.

## 0.2.0 — 2026-09-02

- Adopt newer validated editions in an already-open panel when the background updater replaces the cache, without resetting the reader's selection or viewport.
- Keep the final story and exact viewport unchanged when Up returns from the keyboard-focused **Load more** action.
- Retain stories read during the active **Unread only** view in place with an explicit just-read label until section, search, or filter context changes; persistent unread counts remain exact.
- Reconcile the live marketplace against Radar's source baseline and event ledger, confirming complete addition coverage since the original baseline rather than treating the full catalog as news.
- Fail publication before artifact upload when restored-to-successor source state omits an addition story for any new marketplace plugin ID or moves catalog time backwards.
- Keep the exact story and `contentY` stable while **Load more** replaces the bounded ListView model, instead of restoring an older keyboard anchor and visibly jumping upward.
- Preserve live keyboard animation across asynchronous per-story read projections, while section, search, and filter changes retain deliberate reset semantics.
- Invalidate stale deferred viewport work and retain selection by stable event ID so overlapping projection completions cannot fight the current navigation request.
- Extend disposable-VM acceptance with continuous pagination geometry samples plus first- and second-Down assertions after the newly revealed page.
- Keep reverse key-repeat synchronized with the viewport: when Up crosses the top edge, the viewport moves before the selection changes so the highlighted story never disappears above the clip.
- Restore collection state from the latest successfully deployed edition before every scheduled build, fail closed when continuity is unavailable, and keep a private advancing baseline for repeated `make local-latest` collections.
- Stop replaying old marketplace diffs with a new timestamp, preserve the first observation of deterministic event IDs, reset contaminated discovery-only history, and keep older Omarchy releases off the Front Page after the newest release is selected.

## 0.1.6 — 2026-09-02

- Make the normal Omarchy plugin update path repair the background-window shortcut defect: the bar generation loaded by the updater's plugin rescan automatically migrates only the byte-exact, unmodified Radar-owned 0.1.3 `toggle` block to `summon`.
- Keep fresh shortcut installation explicit and conflict-free. The automatic migration command cannot install a free chord and leaves personal, edited, multiple, conflicting, symlinked, or ambiguous configuration unchanged.
- Change the permanent disposable-VM upgrade regression to prove update-only repair before Radar is opened or any migration control is clicked, while retaining the visible panel action as a rollback-safe fallback.

## 0.1.5 — 2026-09-02

- Repair the missed 0.1.3 upgrade path: an exact Radar-owned `toggle` shortcut is now identified as legacy instead of ambiguous and can be explicitly migrated to `summon` with the same private backup, atomic reload validation, and rollback guarantees.
- Surface that migration inside Radar with a focused **Update shortcut** action; opening the panel remains read-only and edited, personal, conflicting, or ambiguous bindings are still never changed.
- Add a permanent disposable-VM upgrade journey that installs 0.1.3, proves its failure mode, fast-forwards to the candidate, drives the rendered migration action, and verifies real QMP shortcut and newspaper activation while obscured and foreground.

## 0.1.4 — 2026-09-01

- Replace the single hourly GitHub schedule with four off-peak best-effort opportunities per hour, record artifact publication time, and distinguish publisher lag, source checks, Pages propagation, and local cache age with a 90-minute stale-publication threshold.
- Make `R` and the middle-click action honestly **Check for updates**, reporting adopted new-story counts, no newer edition, stale publication, invalid data, and offline last-known-good results.
- Use summon-to-focus activation for the bar, `Super+Alt+N`, and Apps entry so an already-open background Radar raises once and stays open; repeated foreground and rapid activation keep one deterministic window while explicit close routes remain unchanged.
- Smooth dense-list keyboard navigation: when Down crosses the viewport bottom, the complete selected story eases to the top and subsequent movement continues normally without a clipped bottom row.
- Make closed-panel unread discovery dependable: the visible newspaper now checks from a private last-attempt timestamp every 15 minutes after success, retries failures after five minutes, and watches adopted feed changes so its badge updates immediately without opening Radar.

## 0.1.3 — 2026-09-01

- Add an atomic **Mark all as read** action for every unread story matching the current section's persistent Settings filters, including stories beyond the loaded page; temporary search never changes its scope.
- Use each plugin's current validated marketplace description as the useful explanation for additions, releases, verification changes, and retirements instead of repeating the event headline.
- Treat a per-story read write made stale by a concurrent feed replacement as a benign no-op instead of turning the whole reader into a failed state.

## 0.1.2 — 2026-09-01

- Make keyboard pagination unmistakable: Down focuses **Load more**, its focused label says exactly what Enter will do, and the next Down continues into newly revealed stories.
- Move the complete keyboard guide below search and expose the existing `R` Refresh shortcut on hover.
- Remove section renaming, hidden profile state, built-in-rule filler, and redundant muted settings copy; state v9 strictly migrates v1–v8 while preserving filters, display preferences, reading state, and saves.
- Derive meaningful secondary text from the panel foreground so summaries, status, metadata, and counts remain readable in maintained light and dark themes.
- Refresh retained plugin-addition explanations from the current validated marketplace description without creating or reordering events.
- Re-record the README preview in the disposable lab under Omarchy's Matte Black theme, with the complete window below the desktop bar.

## 0.1.1 — 2026-09-01

- Fix local development editions becoming permanently pinned: Refresh now keeps an equal/newer owner-built edition, checks the live published feed, and atomically transitions back when publication advances.
- Make **Load more** a visible arrow-key focus stop; Enter expands the list and Down continues into the first newly loaded story.
- Add an animated, process-bound refresh indicator while cached stories remain readable.
- Remove the broken interests UI, helper flag, projection branch, and current state field; state v8 validates and discards legacy v2–v7 interests while preserving reading state, saves, display preferences, names, and filters.

## 0.1.0 — 2026-09-01

- Implement the deterministic release, marketplace, and reviewed-community collector.
- Publish a bounded JSON feed, RSS projection, archive, and framework-free static site.
- Add the cached-first image-capable Omarchy window and state-v7 local preferences/interests/per-section-filter/name helper with atomic v1-through-v6 migration; the prior seen cutoff becomes a compatibility baseline, v4 names survive while configurable icons and backgrounds are deliberately retired, and v5 Community preferences are removed without disturbing remaining local state.
- Replace session-wide seen marking with bounded per-story read overrides, explicit `UNREAD`/`READ` rows, section unread badges, inspector and `u` toggles, exact indicator counts, and serialized cross-process state mutations.
- Make the window movable, resizable, maximizable, monitor-bounded with reachable wrapping controls at large text sizes, and available through normal `Alt+Tab`; remove its unreliable minimize control, add a bundled application mark and newspaper-prefixed compositor title, and add `Tab` section cycling, wrapping narrow actions, finite Load more controls, and contrast-safe selected text.
- Add strictly validated icon-based marketplace interaction, repository-star, and release-asset-download metrics without changing event identity or ranking; keep raw metric endpoints out of the reader and link plugin stories to human marketplace pages.
- Keep bounded per-section display names with exact reset, while fixing each section's icon, order, and source scope; expose visible read-only source membership through the clearly named Settings control.
- Remove the permanently empty Community reader section; reviewed `community-link` records remain eligible for Front Page and local For You matching without creating a dead navigation destination.
- Add the default-on optional newspaper bar indicator with unread/health state, zero-gap hiding, panel restoration, and due-checked refresh.
- Mirror bounded official marketplace thumbnails to content-addressed same-origin assets and replace fixture-built local output with a real production collection.
- Add an explicit, reversible helper for conflict-free `Super+Alt+N` setup without replacing Editor.
- Add an explicit, receipt-backed XDG launcher helper and an Omarchy Apps-menu entry with the bundled newspaper mark.
- Add `make local-latest` for safe checkout synchronization, live local collection, validated private image import, and one-time panel-only newspaper migration through Omarchy's supported lifecycle.
- Add offline source tests and disposable Plugin Lab acceptance scenarios.
