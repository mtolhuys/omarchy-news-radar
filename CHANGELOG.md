# Changelog

## 0.1.0 — Unreleased preview

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
