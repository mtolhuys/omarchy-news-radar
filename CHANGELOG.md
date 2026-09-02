# Changelog

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
