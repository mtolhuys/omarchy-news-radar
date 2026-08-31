# Omarchy News Radar

> Press one key and catch up with what changed across Omarchy.

Omarchy News Radar is a keyboard-first, source-linked activity reader for Omarchy releases, marketplace changes, and reviewed community work. It is an independent community project with a panel-only Omarchy plugin, a deterministic Python collector and publisher, a bounded static JSON/RSS/HTML edition, and a cached local reader that remains useful offline.

## Project status

Version `0.1.0` is a complete local release candidate, not a public release. The source, tests, workflows, and disposable Plugin Lab scenario are implemented. The intended GitHub repository and Pages feed do not exist yet, so the public URL, public clean-clone proof, tag, release, and marketplace submission remain deliberately pending owner authorization.

The main plugin declares only `panel`. Version 1 has no top-bar widget, hidden bar slot, daemon, notification, telemetry, account, analytics, AI summary, or plugin-management action. A future indicator remains a separate companion-plugin decision.

## What is included

- A standard-library Python collector for published Omarchy releases, bounded marketplace catalog diffs, and reviewed repository-owned community records.
- A tracked normalized source snapshot with a rolling 90-day event ledger, silent first marketplace bootstrap, two-successful-run retirement confirmation, partial-source preservation, deterministic IDs, and restricted curation overlays.
- Atomic publication of validated `events.json`, RSS, escaped static HTML/CSS, a bounded archive projection, and build digest metadata.
- A fixed-origin client helper with cached-first reads, bounded HTTPS, closed redirects, validation before replacement, one-refresh locking, atomic private XDG state, corrupt-state quarantine, save/seen state, and explicit purge.
- A theme-native QML panel with Front Page, For You, Core, Plugins, Community, Saved, search, keyboard/pointer controls, source opening, visible health/recovery states, responsive layout, and virtualized story rows.
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

For an owner-driven smoke test on the current desktop, first run the four source gates above, then explicitly install the local Git checkout and seed its cache with the synthetic fixture:

```bash
cd ~/Projects/plugins/omarchy-news-radar
omarchy plugin add "$PWD" --enable --yes
OMARCHY_NEWS_RADAR_TEST_MODE=1 \
  OMARCHY_NEWS_RADAR_TEST_FEED="$PWD/tests/fixtures/feed-valid.json" \
  ~/.config/omarchy/plugins/io.github.mtolhuys.news-radar/bin/news-radar-client refresh
~/.config/omarchy/plugins/io.github.mtolhuys.news-radar/bin/news-radar-shortcut status
~/.config/omarchy/plugins/io.github.mtolhuys.news-radar/bin/news-radar-shortcut install
```

Press `Super+Alt+N`. Because the public feed is not published yet, the seeded edition remains visible as last-known-good content while a normal background refresh reports offline. Finish the reversible smoke test in this order:

```bash
~/.config/omarchy/plugins/io.github.mtolhuys.news-radar/bin/news-radar-shortcut remove
omarchy plugin remove io.github.mtolhuys.news-radar --yes
```

The assistant-run verification never executes those owner desktop commands; all automated desktop mutation remains in the disposable guest.

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
- `r`: refresh once while preserving the last-known-good edition.
- `Escape` or `q`: close the panel.

Installed plugin IDs are read locally through Omarchy shell IPC and used only for exact `For You` matching. They are never sent to the feed host.

## Local data and removal

Radar uses:

```text
${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-news-radar/feed.json
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

The first successful marketplace run is intentionally silent for historical plugin listings. A failed adapter retains its prior normalized state and cannot manufacture additions, releases, or mass retirements.

The Pages workflow keeps repository permissions read-only. Each manual publication uploads the updated `state/source-snapshot.json` as a separate run artifact. The owner must review, validate, and commit that artifact before the next publication; otherwise the next run is intentionally not considered an advanced source baseline. Exact first-publication steps are in [`docs/RELEASE.md`](docs/RELEASE.md) and the local evidence record.

## Documentation

Start with [`AGENTS.md`](AGENTS.md). The binding product, architecture, data, source, security, testing, implementation, decision, and release contracts live under [`docs/`](docs/). [`docs/RESEARCH.md`](docs/RESEARCH.md) records the dated Omarchy, shortcut, marketplace, and Plugin Lab audits.

## Independence

Omarchy News Radar is not an official Omarchy project and does not imply endorsement, marketplace verification as a security audit, or guaranteed compatibility. Every story links its original source so readers can verify the underlying claim.
