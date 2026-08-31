# Omarchy News Radar

> Press one key and catch up with what changed across Omarchy.

Omarchy News Radar is a visual, keyboard-first, source-linked activity reader for Omarchy releases, marketplace changes, and reviewed community work. It is an independent community project with an optional newspaper status widget, a full panel, a deterministic Python collector/publisher, a bounded static JSON/RSS/HTML edition with safe mirrored previews, and a cached local reader that remains useful offline.

## Project status

Version `0.1.0` is a complete local release candidate, not a public release. The source, tests, workflows, and disposable Plugin Lab scenario are implemented. The intended GitHub repository and Pages feed do not exist yet, so the public URL, public clean-clone proof, tag, release, and marketplace submission remain deliberately pending owner authorization.

The main plugin declares `panel` and `bar-widget`. Its newspaper is visible by default, shows unread/source status, and is optional: right-click hides it with zero remaining bar geometry, while Tune in the panel restores it. Version 1 still has no daemon, desktop notification, telemetry, account, analytics, AI summary, or plugin-management action.

## What is included

- A standard-library Python collector for published Omarchy releases, bounded marketplace catalog diffs, and reviewed repository-owned community records.
- A tracked normalized source snapshot with a rolling 90-day event ledger, bounded 12-item/14-day first marketplace backfill, two-successful-run retirement confirmation, partial-source preservation, deterministic IDs, and restricted curation overlays.
- Atomic publication of validated `events.json`, RSS, escaped static HTML/CSS, bounded archives, build digest metadata, and allowlisted marketplace previews mirrored to same-origin content-addressed raster assets.
- A fixed-origin client helper with cached-first reads, bounded HTTPS, closed redirects, validation before replacement, one-refresh locking, atomic private XDG state, corrupt-state quarantine, save/seen state, and explicit purge.
- A theme-native QML panel with images, Front Page, For You, Core, Plugins, Community, Saved, private interests, local image/bar preferences, search, keyboard/pointer controls, source opening, visible health/recovery states, responsive layout, and virtualized story rows.
- A theme-native bar newspaper with unread count and health dot, default-on placement, zero-gap local hiding, due-checked refresh, and panel-based restoration.
- A narrowly scoped shortcut helper that installs `Super+Alt+N` only when the personal configuration and live binding table show that it is free; it never displaces Editor or another action.
- Offline unit/integration tests, pinned least-privilege workflows, and disposable Plugin Lab journeys for local-candidate and eventual public-clone acceptance.

## Review the local candidate

The four source gates are offline and do not activate desktop integration:

```bash
make test
make validate
make feed-fixture
make site
```

Generated site output is written to ignored `dist/`. Desktop installation, enabling, shortcut changes, Hyprland reloads, rendered interaction, hot updates, and removal belong only in the disposable Omarchy Plugin Lab during development; see [`docs/TESTING.md`](docs/TESTING.md).

### Test the unpublished checkout locally

The safest complete test uses the disposable Omarchy Plugin Lab and does not touch the daily desktop:

```bash
cd ~/Projects/omarchy/plugin-lab
./bin/lab doctor
./bin/lab plugin ~/Projects/plugins/omarchy-news-radar/tests/lab/acceptance.sh
```

The Lab scenario seeds a deterministic guest-only feed, installs the conflict-free `Super+Alt+N` binding, drives the real bar and panel, captures screenshots, checks zero-gap hide/restore and local interests, then removes the owned shortcut and plugin. Keep automated development and acceptance in the disposable VM; the command below is an explicit owner-run opt-in for intentional daily use, not a test route.

### Keep an intentional local installation current

When you deliberately want to run this checkout on your daily desktop, use:

```bash
make local-latest
```

The first run validates, clones, and enables the current committed checkout. It then collects a real edition from the live allowlisted Omarchy release and marketplace sources, validates and mirrors eligible marketplace images, and atomically imports the edition and image assets into Radar's private cache. Later runs fast-forward the installed clone, rescan it, and collect a new local edition. The panel labels this mode “Local live edition” because the public Pages feed does not exist yet; rerun the command whenever you want newer news.

“Latest” means this repository's current committed `HEAD` plus a collection performed at command time. The command never runs `git pull`, refuses uncommitted source or installed changes, preserves a deliberately disabled modern installation, leaves `Super+Alt+N` untouched, and refuses to repoint an installation from another checkout or public URL. A one-time migration recognizes only the exact unmodified panel-only preview placement, moves that owned entry through Omarchy's supported lifecycle to the default right-side newspaper, and restores the new visual defaults. Ambiguous or customized placement is refused rather than overwritten. It is intentionally not a background updater.

## Install after publication

These commands become usable only after the owner creates and publishes the intended repository:

```bash
omarchy plugin add https://github.com/mtolhuys/omarchy-news-radar --enable --yes
```

The panel is always reachable without changing a shortcut:

```bash
omarchy-shell shell toggle io.github.mtolhuys.news-radar
```

### Explicit shortcut setup

Radar uses `Super+Alt+N`; Omarchy's `Super+Shift+N` Editor/Neovim shortcut remains unchanged. First inspect the personal configuration and live binding table without mutation:

```bash
~/.config/omarchy/plugins/io.github.mtolhuys.news-radar/bin/news-radar-shortcut status
```

If `status` reports `classification: free`, install the owned Radar binding:

```bash
~/.config/omarchy/plugins/io.github.mtolhuys.news-radar/bin/news-radar-shortcut install
```

The helper refuses personal, multiple, unknown, symlinked, unowned, or ambiguous configuration. It creates a timestamped backup, writes one clearly marked bind-only Radar block, reloads Hyprland, validates the live action and config errors, and rolls back on failure. There is no unbind, Editor replacement, or force flag.

To choose another free chord, skip the helper and add your own reviewed line to `~/.config/hypr/bindings.lua`, for example:

```lua
o.bind("SUPER + SHIFT + R", "Omarchy News Radar", "omarchy-shell shell toggle io.github.mtolhuys.news-radar")
```

## Panel controls

- `1`–`6`: Front Page, For You, Core, Plugins, Community, Saved.
- `j` / `k` or arrow keys: move the selected story.
- `Home` / `End`: first or last story.
- `/`: focus local search; `Escape` returns to panel navigation.
- `o` or `Enter`: open the selected validated HTTPS source.
- `s`: save or unsave the selected story locally.
- `r`: refresh the published feed once while preserving the last-known-good edition; an unpublished local edition instead explains that `make local-latest` collects the next update.
- `Escape` or `q`: close the panel.
- `Tune`: enable/disable the top-bar newspaper and images, and save up to twelve comma-separated private interests.

Installed plugin IDs and explicit interests are used only for local `For You` matching. They are never sent to the feed host.

## Newspaper controls

- Left click: open or close the News Radar panel.
- Middle click: request one bounded refresh.
- Right click: hide the newspaper immediately; its bar slot collapses to zero.
- Restore: press `Super+Alt+N` (or use shell IPC), choose Tune, then set “Top-bar newspaper” to On.

The visible widget requests a refresh only when the cache is at least 30 minutes old. Hiding it stops that cadence. There are no desktop notifications.

## Local data and removal

Radar uses:

```text
${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/feed.json
${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/assets/images/
${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/local-edition.json
${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-news-radar/state.json
```

Normal disablement and removal preserve the cache, seen cutoff, and saved items. Remove in this order while the helper still exists:

```bash
~/.config/omarchy/plugins/io.github.mtolhuys.news-radar/bin/news-radar-shortcut remove
omarchy plugin remove io.github.mtolhuys.news-radar --yes
```

Removing the exact owned block releases `Super+Alt+N`; Editor was never changed. If you also want to delete Radar-owned cache, state, diagnostics, and quarantined state, run the explicit purge before removing the plugin:

```bash
~/.config/omarchy/plugins/io.github.mtolhuys.news-radar/bin/news-radar-client purge
```

If the plugin is removed before its shortcut, the marked block is a harmless unresolved shell IPC action; remove only the block between the `OMARCHY NEWS RADAR MANAGED SHORTCUT` markers or reinstall the same plugin checkout and run `remove`.

## Collection and publication

Production collection is explicit and networked; ordinary tests never run it:

```bash
python3 -m radar collect --bootstrap-marketplace  # first successful baseline only
python3 -m radar collect                          # later editions
```

The first successful marketplace run publishes at most twelve genuinely recent listings from the previous fourteen days, then records the complete baseline. It never treats the historical catalog as new. A failed adapter retains its prior normalized state and cannot manufacture additions, releases, or mass retirements.

The Pages workflow runs hourly at minute 17 and also supports manual dispatch. It keeps repository permissions read-only and uploads the updated `state/source-snapshot.json` as a run artifact. The owner must periodically review, validate, and commit that artifact so multi-run retirement confirmation and baseline advancement remain explicit. Exact first-publication steps are in [`docs/RELEASE.md`](docs/RELEASE.md) and the local evidence record.

## Documentation

Start with [`AGENTS.md`](AGENTS.md). The binding product, architecture, data, source, security, testing, implementation, decision, and release contracts live under [`docs/`](docs/). [`docs/RESEARCH.md`](docs/RESEARCH.md) records the dated Omarchy, shortcut, marketplace, and Plugin Lab audits.

## Independence

Omarchy News Radar is not an official Omarchy project and does not imply endorsement, marketplace verification as a security audit, or guaranteed compatibility. Every story links its original source so readers can verify the underlying claim.
