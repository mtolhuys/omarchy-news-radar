# Product contract

## Promise

Omarchy News Radar gives a typical Omarchy user one memorable action—`Super+Alt+N`—to understand what changed, why it may matter, and where the original information lives.

The product converts scattered public activity into a compact edition. It does not ask users to follow repository notifications, social accounts, discussions, release pages, and a marketplace independently.

## Problem

The ecosystem already contains plenty of information. The failure is fragmentation and relevance:

- Omarchy core changes live in releases, commits, documentation, and discussions.
- Plugin discovery lives in a rapidly growing marketplace.
- Plugin changes live across many independent repositories.
- Tutorials and showcases appear in social posts, Reddit, GitHub, and personal sites.
- Popularity does not reliably indicate maintenance, fit, safety, or novelty.

A larger stream would increase the problem. Radar must reduce cognitive load.

## Target user

The primary user runs Omarchy Quattro, installs community plugins, and occasionally wants to catch up on releases, plugins, community links, and Omarchy-related YouTube videos without becoming an ecosystem maintainer. The user is comfortable with keyboard shortcuts but should not need GitHub expertise.

Maintainers, newsletter authors, and external feed consumers are secondary users. Their needs must not make the local reading experience heavier.

## Version 1 journey

1. The user installs and enables the plugin through the normal Omarchy plugin flow. A small newspaper appears in the right bar section by default.
2. The user may install Radar's explicit XDG launcher entry, which adds **Omarchy News Radar** with its newspaper mark to Omarchy's normal Apps menu without touching unrelated entries.
3. The user may run the explicit shortcut helper. It installs `Super+Alt+N` only when the personal configuration and live binding table both show that the chord is free; otherwise it refuses the change. Because an earlier explicit setup made its byte-exact marked block Radar-managed, an update rescan may automatically migrate only that exact unmodified 0.1.3 `toggle` block to `summon`. Every edited, personal, conflicting, multiple, symlinked, or ambiguous case remains unchanged, and **Update shortcut** remains a visible retry if automatic validation cannot complete.
4. Launching the Apps entry, pressing `Super+Alt+N`, or left-clicking the newspaper summons the same window: closed Radar opens; an existing foreground or obscured Radar is raised and focused without toggling closed. Omarchy's `Super+Shift+N` Editor action remains unchanged.
5. While its optional newspaper is visible, Radar checks one bounded static published edition from the last real attempt without blocking the cached edition; successful checks are at most every 15 minutes and failures retry after five. An adopted edition updates the passive unread badge with the panel closed. The badge deduplicates unread stories across the current persistent section projections, so every advertised story is reachable in the newspaper. It never implies that the desktop action collects upstream sources.
6. The front page and section rail show exactly how many stories remain unread; every row says `UNREAD` or `READ`, and any accepted reviewed link joins that finite edition without creating a separate empty lane. Under Unread only, a just-read row remains stable and visibly READ for the active view while the true count decreases, then leaves after a section, search, or filter change.
7. The normal resizable window participates in `Alt+Tab`; the user navigates by keyboard or pointer through Front Page, For You, Core, Plugins, and Saved, with `Tab` and `Shift+Tab` cycling sections and Down/Enter reaching finite pagination.
8. Deliberately selecting an item marks only that story read and exposes its type, date, source, trust metadata, compatibility information when known, one concise factual summary, and any available source-labelled aggregate metrics. The inspector and `u` shortcut can mark it unread again; a separate explicit section action marks every unread story matching that section's persistent Settings filters read in one atomic transition.
9. Opening a source launches the default browser only after explicit activation.
10. Closing the panel never bulk-marks the edition. Stories the user did not deliberately select remain unread across close, refresh, and restart.
11. Offline or failed checks preserve the last-known-good edition without displacing news with publisher diagnostics. A concise recovery message appears only when no usable edition exists; operational monitoring separately distinguishes source checks, publication, Pages propagation, and client cache age.
12. The user can inspect each section's fixed source scope, add local filters, and reveal further matching stories in finite twelve-item steps.
13. Right-clicking the newspaper hides it with no remaining bar gap. Tune Your Radar inside the panel restores it and controls story images.

An owner deliberately running the local checkout may use `make local-latest`. That command collects the same allowlisted public facts and imports the complete validated edition and mirrored images into private cache. The client retains its validated local-origin marker for downgrade protection without placing that implementation detail in the normal reader. Test fixtures must never masquerade as live news.

## Version 1 capabilities

### Activity

- Official Omarchy GitHub releases.
- New plugin listings from the official marketplace catalog.
- Plugin version changes when the catalog exposes a changed non-empty version.
- Plugin retirement only after an explicit retirement signal or repeated confirmed absence.
- Marketplace verification status changes.
- Manually reviewed community tutorials, showcases, and project announcements.
- Publisher-mirrored marketplace preview images when an official preview passes the fixed format, size, dimension, and origin checks.

### Relevance

- “For You” matches events against exact locally enabled plugin IDs.
- Category and tag filters operate locally.
- Saved items and bounded per-story read overrides remain local.
- Time, significance, unread, image, and story-type filters are independently stored per section and remain local.
- Names, icons, order, and source scope are canonical section identity and are not user-editable; only the filters that change which stories are shown persist per section.
- Front Page ordering is deterministic and auditable.
- Manually notable items are visibly distinguished from routine activity.

### Reading

- Cached-first rendering.
- Keyboard-first selection and source opening.
- Plain-text summaries with source attribution; every plugin-event explanation uses the current validated marketplace description when available.
- Light and dark theme support using current Omarchy tokens, with meaningful secondary text derived from the panel foreground rather than an ambient low-contrast muted token.
- Useful empty, offline, partial-source, and invalid-feed states.
- Optional source imagery with plain-text alternatives and graceful image-free fallback.
- A restrained bar newspaper with unread count and source-health dot.
- A compositor-managed resizable/maximizable window with ordinary task switching, summon-to-focus activation, smooth unclipped viewport-edge story selection, explicit arrow-key/Enter finite load-more controls, a hover-visible **Check for updates** shortcut, restrained check progress, and selected/secondary text contrast across maintained themes.
- Explicit `UNREAD`/`READ` row labels, section unread badges, a per-story toggle, an explicit filtered-section **Mark all as read** action, and durable private reading state.
- Optional official marketplace interaction aggregates, catalog repository stars, and GitHub release-asset download counts with compact colored icons, accessible labels, and observation times. Raw metric URLs remain feed provenance rather than reader actions; plugin stories expose the human marketplace detail page.

## What “interesting” means

An item is interesting when it changes what a user can do, affects compatibility or trust, introduces a meaningfully distinct project, or teaches a reusable Omarchy workflow. A repository commit, star or interaction-count change, metadata touch, or repeated clone of an existing idea is not automatically news.

Automated activity and editorial significance are separate facts. The collector may prove that an event occurred; only an explicit rule or reviewed curation record may call it notable.

## Quality attributes

- **Calm:** the product favors a small readable edition over an infinite stream.
- **Fast:** cached content appears without waiting for the network.
- **Honest:** missing sources, stale cache, unknown compatibility, and verification boundaries are visible.
- **Native:** the panel follows Omarchy shell styling, focus, lifecycle, and keyboard conventions.
- **Independent:** the project works from public sources under its owner’s repository and hosting.
- **Private:** personalization and reading state do not leave the machine.
- **Recoverable:** a broken network response never replaces valid cache or state.
- **Source-linked:** every event remains traceable to an original public URL.

## Non-goals for version 1

- A Laravel News-style editorial business, original reporting operation, advertising product, job board, or sponsorship system.
- Accounts, comments, reactions, follows, cloud bookmarks, analytics, telemetry, or recommendation profiles.
- A general-purpose RSS reader or social-media client.
- Automatic scraping of X, Reddit, arbitrary websites, or GitHub discussions.
- AI-written summaries, autonomous editorial judgment, sentiment analysis, or generated safety conclusions.
- Installing, updating, enabling, disabling, ranking, or removing third-party plugins from a news item.
- Mandatory top-bar presence, desktop notifications, polling while the newspaper is hidden, or a resident daemon.
- Claiming that marketplace verification is a complete security audit.
- Treating views, hearts, command copies, stars, or release-asset downloads as installs, unique users, votes, rankings, safety, or editorial significance.
- Mirroring entire articles, release notes, arbitrary screenshots, or repository content. Only bounded official marketplace preview thumbnails are mirrored.

## Milestone success criterion

The first release succeeds when a clean Omarchy Quattro guest can install the plugin, see a correctly sized newspaper indicator, hide it without a gap, restore it from the panel, confirm that `Super+Alt+N` is free, install Radar's exact managed binding without changing the Editor shortcut, open a polished image-capable cached front page, distinguish every read story from every unread story, mark one story read and unread without changing its neighbors, close without bulk-marking the edition, see bounded refresh progress, load another page entirely by keyboard, identify an installed-plugin match, open an original HTTPS source, survive offline and malformed-feed states without losing good data, close cleanly, remove its managed binding so the chord is free again, and uninstall without shell or Hyprland errors.
