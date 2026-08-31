# Omarchy News Radar engineering contract

Omarchy News Radar is a keyboard-first, source-linked view of meaningful activity across Omarchy core, the plugin marketplace, and selected community work. The product is not a publication, social network, package manager, or autonomous recommender. It is a calm relevance layer over public upstream facts.

The repository starts as an implementation specification. Build the product described here and in `docs/` completely, but do not publish, push, tag, create remote repositories, change external settings, or submit to the marketplace without explicit owner authorization.

## Required reading order

Read every file in this list before changing product behavior or choosing implementation details:

1. `docs/PRODUCT.md`
2. `docs/UX.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DATA-MODEL.md`
5. `docs/SOURCES.md`
6. `docs/CURATION.md`
7. `docs/SECURITY.md`
8. `docs/DEPENDENCIES.md`
9. `docs/TESTING.md`
10. `docs/DECISIONS.md`
11. `docs/IMPLEMENTATION.md`
12. `docs/RELEASE.md`
13. `docs/RESEARCH.md`

When documents disagree, this file and `docs/DECISIONS.md` take precedence, followed by the product and architecture contracts. Update every affected document in the same change when a decision intentionally changes.

For Omarchy runtime work, also read the maintained Plugin Lab `AGENTS.md`, `README.md`, and `TESTING.md`, then inspect the exact Omarchy source checkout selected by the lab. The expected local lab is the sibling project at `../../omarchy/plugin-lab`, but discover the active paths from its runner and `.lab.env`; do not assume that a default checkout is current.

## Product invariants

- `Super+Alt+N` is the recommended primary interaction. The current Omarchy source and disposable live session leave it free; install it only after confirming that both the personal configuration and live binding table are conflict-free, and never replace another action.
- The main plugin pairs an on-demand `panel` with one default-on `bar-widget`. The newspaper shows unread/source health, right-click hides it by setting local state, hidden geometry is exactly zero, and the panel can restore it. It is not a separate companion plugin.
- Opening the panel shows a validated cached edition immediately when one exists, then refreshes without blocking the cached reading experience.
- Remote feed content, marketplace metadata, release notes, repository text, and community submissions are untrusted data. Render textual fields as bounded plain text and never execute them. Images are optional publisher-mirrored marketplace rasters: accept only validated PNG/JPEG/WebP from the fixed official image origin, publish them as content-addressed same-origin assets, and never render remote HTML, Markdown, SVG, or arbitrary image URLs.
- Every visible claim links to its original source. Radar summarizes and organizes; it does not become the source of truth.
- The plugin has no telemetry, accounts, tracking identifiers, remote read state, cookies, or personalized server requests.
- Read state, saved items, installed plugin IDs, interests, and preferences remain local. Generic feed and same-origin mirrored-image retrieval are the only normal client network requests.
- No arbitrary web scraping, X scraping, AI-generated summaries, engagement bait, notification spam, or automatic “best plugin” claims belong in version 1.
- A first collector run establishes a baseline and may backfill only the twelve newest marketplace listings from the previous fourteen days; it must not publish the whole catalog as new.
- Closing the panel stops its processes. A visible bar indicator may perform one due-checked refresh at startup and every 30 minutes; hiding the indicator stops that network cadence. No daemon is installed.
- Every state has visible feedback and deterministic recovery: first use, cached, refreshing, current, offline, empty, invalid feed, source-partial, and failed.

## Repository rules

- Write all tracked documentation, comments, diagnostics, fixtures, generated labels, and user-facing text in English.
- In Markdown, use full lines rather than hard-wrapping prose. Break lines only at structural boundaries.
- Keep business rules out of QML. Python owns collection, normalization, validation, state transitions, and deterministic rendering models; QML owns presentation and user interaction.
- Use the Python standard library and current Omarchy runtime contracts. A new dependency requires an explicit architecture and security decision.
- Treat paths, URLs, titles, descriptions, tags, release notes, and JSON fields as data. Pass process arguments structurally; never interpolate them into shell source.
- Keep network origins allowlisted, payloads bounded, timeouts explicit, redirects constrained, writes atomic, and last-known-good data intact on failure.
- Do not create `manifest.json` until every declared entry point exists and local validation can prove the manifest.
- Do not store VM images, lab evidence, host diagnostics, real user state, secrets, tokens, caches, generated deployment artifacts, or machine-local absolute paths in Git.
- Keep commits atomic and messages succinct. Preserve unrelated and pre-existing changes.
- Do not claim a feature, supported version, latency, accessibility level, or release state until the exact candidate has matching evidence.

## Host and guest boundary

Source inspection, deterministic source tests, fixture generation, and static-site builds may run on the host. Anything that installs, enables, disables, updates, removes, hot-reloads, or interacts with the plugin must run in the disposable Omarchy Plugin Lab.

Never restart the host `omarchy-shell`, reload the host Hyprland configuration, edit the host `~/.config`, install the development plugin on the daily desktop, or run broad Omarchy test entry points against the active session. Use the smallest sufficient Plugin Lab route and retain its timestamped evidence.

## Expected developer interface

The implementation must provide these stable repository commands:

```bash
make test
make validate
make feed-fixture
make site
make collect-live
make local-latest
```

`make test` must be offline and deterministic. `make validate` must cover the plugin manifest when present, tracked-English policy, generated-file drift, Python syntax/types available without network installation, shell lint when available, and QML validation against the selected Omarchy source when available.

`make local-latest` is an explicit owner-run desktop mutation, never an agent-run host test. It may install or fast-forward only the Git-managed local plugin whose origin is this exact clean checkout; it must not pull the source checkout, repoint another origin, overwrite local changes, install the shortcut, or create a watcher/daemon.

Runtime acceptance belongs in the Plugin Lab:

```bash
cd "$OMARCHY_PLUGIN_LAB_ROOT"
./bin/lab doctor
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/acceptance.sh
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/public-install.sh
```

## Completion standard

A task is complete only when the narrowest relevant source tests pass, error and cancellation paths are covered, public documentation matches the implementation, and any visible or lifecycle behavior has disposable-guest evidence. A plausible screenshot, successful clone, valid manifest, or direct IPC call is not proof of the complete user journey.
