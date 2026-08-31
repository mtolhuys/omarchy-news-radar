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

The primary user runs Omarchy Quattro, installs community plugins, and occasionally wants to catch up without becoming an ecosystem maintainer. The user is comfortable with keyboard shortcuts but should not need GitHub expertise.

Maintainers, newsletter authors, and external feed consumers are secondary users. Their needs must not make the local reading experience heavier.

## Version 1 journey

1. The user installs and enables the panel plugin through the normal Omarchy plugin flow.
2. The user runs the explicit shortcut helper. It installs `Super+Alt+N` only when the personal configuration and live binding table both show that the chord is free; otherwise it refuses the change.
3. Pressing `Super+Alt+N` opens the latest cached edition immediately when available, while Omarchy's `Super+Shift+N` Editor action remains unchanged.
4. Radar refreshes one bounded static feed without blocking the cached edition.
5. The front page explains how many core, plugin, and community changes occurred since the last completed reading session.
6. The user navigates by keyboard or pointer through Front Page, For You, Core, Plugins, Community, and Saved.
7. Selecting an item exposes its type, date, source, trust metadata, compatibility information when known, and one concise factual summary.
8. Opening a source launches the default browser only after explicit activation.
9. Closing the panel records the newest event timestamp that was actually present in that session. Events arriving later remain new.
10. Offline or failed refreshes preserve the last-known-good edition and clearly label its age.

## Version 1 capabilities

### Activity

- Official Omarchy GitHub releases.
- New plugin listings from the official marketplace catalog.
- Plugin version changes when the catalog exposes a changed non-empty version.
- Plugin retirement only after an explicit retirement signal or repeated confirmed absence.
- Marketplace verification status changes.
- Manually reviewed community tutorials, showcases, and project announcements.

### Relevance

- “For You” matches plugin events against locally installed plugin IDs.
- Category and tag filters operate locally.
- Saved items and seen-through state remain local.
- Front Page ordering is deterministic and auditable.
- Manually notable items are visibly distinguished from routine activity.

### Reading

- Cached-first rendering.
- Keyboard-first selection and source opening.
- Plain-text summaries with source attribution.
- Light and dark theme support using current Omarchy tokens.
- Useful empty, offline, partial-source, and invalid-feed states.

## What “interesting” means

An item is interesting when it changes what a user can do, affects compatibility or trust, introduces a meaningfully distinct project, or teaches a reusable Omarchy workflow. A repository commit, star change, metadata touch, or repeated clone of an existing idea is not automatically news.

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
- Mandatory top-bar presence, desktop notifications, background polling, or a resident daemon.
- Claiming that marketplace verification is a complete security audit.
- Mirroring entire articles, release notes, screenshots, or repository content.

## Milestone success criterion

The first release succeeds when a clean Omarchy Quattro guest can install the plugin, confirm that `Super+Alt+N` is free, install Radar's exact managed binding without changing the Editor shortcut, open a polished cached front page with `Super+Alt+N`, refresh from a deterministic fixture, identify an update for an installed plugin, open an original HTTPS source, survive offline and malformed-feed states without losing good data, close cleanly, remove its managed binding so the chord is free again, and uninstall without shell or Hyprland errors.
