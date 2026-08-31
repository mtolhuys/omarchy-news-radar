# Dated contract research

This document records the environment audited while writing the initial specification. It is evidence for current decisions, not a permanent upstream guarantee. Revalidate each unstable fact before implementation and public release.

## Audit date

31 August 2026, Europe/Amsterdam.

## Local Omarchy source

- Checkout during the audit: the sibling `../../omarchy/omarchy` project relative to this repository.
- Audited branch: `quattro`
- Plugin contract: third-party `schemaVersion: 1` with `bar-widget`, `bar`, `panel`, `overlay`, `menu`, and `service` kinds.
- On-demand panel entry points are `Item`s exposing `open(payloadJson)` and `close()`.
- The shell injects current Omarchy path, shell, manifest, and registry properties where declared.
- Third-party runtime rescans use per-generation runtime snapshots; versioned QML directories are not required as cache busters.

The implementation agent must inspect the exact source revision selected by Plugin Lab because this checkout contained unrelated active development changes during research.

## Plugin lifecycle findings

Current `PluginRegistry.setEnabled` places any enabled plugin declaring `bar-widget` into the bar layout, even when that manifest also has a non-widget kind. Current `Bar.qml` `ModuleSlot` geometry, however, computes zero implicit width and height whenever the active widget root is invisible. The owner explicitly approved a default-on main-plugin newspaper after the initial panel-only candidate, so local `barVisible=false` now provides a proven no-gap hidden state while the panel remains reachable through shortcut/IPC.

Current third-party plugin installation clones a Git repository, validates the manifest, and enables through shell configuration. It intentionally does not run plugin install hooks or provide a declarative global-shortcut manifest field. Shortcut configuration must be a separate explicit user action.

## Shortcut audit

Audited default sources:

- `default/hypr/bindings/applications.lua`
- `default/hypr/bindings/clipboard.lua`
- `default/hypr/bindings/media.lua`
- `default/hypr/bindings/tiling.lua`
- `default/hypr/bindings/utilities.lua`

Audited live bindings through `hyprctl binds -j`:

- `Super+N`: unused.
- `Super+Alt+N`: unused.
- `Super+Shift+N`: Editor.
- `Super+Ctrl+N`: Toggle nightlight.

The original specification selected `Super+Shift+N` despite the known Editor default. During implementation review, the owner rejected that conflict and selected `Super+Alt+N` instead. Recheck the default source, personal override file, and disposable guest's live binding table before shipping. The helper must install only when the new chord is free, refuse personal or ambiguous conflicts, and never replace Editor or another action.

## Marketplace

Public project:

```text
https://github.com/omacom/omarchy-plugin-marketplace
```

Public site:

```text
https://plugins.omarchy.org/
```

Observed generated sources:

```text
https://raw.githubusercontent.com/omacom/omarchy-plugin-marketplace/main/registry.json
https://raw.githubusercontent.com/omacom/omarchy-plugin-marketplace/main/site/catalog.json
```

The rendered site reported 1,935 community plugins and 36 built-in plugins during the audit. The generated catalog shortly afterward contained 1,977 total entries, demonstrating that counts and source shape are live operational facts rather than constants.

Observed catalog top-level keys were `generatedAt`, `mode`, `plugins`, `stateSchemaVersion`, and `warnings`. Plugin entries exposed useful normalized fields including ID, name, description, author, version, category, tags, repository URL, listing times, verification status, release metadata, and repository status. The source adapter must feature-detect and validate the current schema rather than importing the entire upstream document into Radar’s public contract.

## Official Omarchy releases

Public source:

```text
https://github.com/basecamp/omarchy/releases
https://api.github.com/repos/basecamp/omarchy/releases
```

Use published GitHub releases only in version 1. Repository commits, discussions, and social amplification remain outside the automated source contract.

## Omarchy Weekly context

Public newsletter:

```text
https://omarchy-weekly.com/
```

The newsletter accepts community submissions and publishes RSS. Radar is not a competing newsletter dependency: it produces an independent machine-readable activity feed that a newsletter may optionally consume later.

## Name availability audit

No GitHub repository named exactly `omarchy-news-radar` was found during the audit. Several flight, weather, and satellite projects use “radar,” which supports the more specific repository name and shorter in-product label “News Radar.” Recheck before remote repository creation.

## Plugin Lab

Maintained safety boundary:

The maintained lab was the sibling `../../omarchy/plugin-lab` project relative to this repository. Discover and verify the active path through the lab runner rather than baking a machine-local absolute path into implementation code or evidence.

The lab requires product-owned scenarios for visible pointer/keyboard behavior, QMP input for global shortcuts, machine assertions paired with screenshots, same-path runtime identity proof, shell-log inspection, and timestamped evidence. Installation, enablement, shortcut mutation, Hyprland reload, visual checks, hot update, and removal must occur in its disposable guest, not on the daily host.

## Implementation revalidation — 31 August 2026

- The selected Omarchy source remained branch `quattro` at commit `83881e979b35468c3e7d60b171e319ede61a88fd`. The checkout contained unrelated active shell development changes, so implementation uses the exact selected files as the contract without modifying or claiming a clean upstream tree.
- The selected Plugin Lab was branch `fix/quiet-host-test-screenshots` at commit `259ef26e9909bd74323177d2d29e2007cf8c73db`, with its maintained local integration changes. The ISO harness was branch `plugin-lab` at commit `268bac16d351a21d867e37565738f458b11cb06c`.
- The selected image and reusable base identify as `omarchy-2026.08.27-x86_64-local`. `./bin/lab doctor` passed the ISO checksum, English/path audits, KVM check, and required source/harness/tool checks.
- Current third-party panels are still `schemaVersion: 1` `Item` entry points with `open(payloadJson)` and `close()`. The shell injects the documented properties, loads enabled panels on demand, destroys them when hidden unless `keepLoaded` is true, and loads each third-party scan from a new runtime snapshot.
- The default source still binds `SUPER + SHIFT + N` to `Editor` and contains no `SUPER + ALT + N` binding. Disposable-guest audit run `20260831-180214` proved that the new chord was absent from the live table, one temporary `SUPER + ALT + N` binding loaded cleanly, the Editor binding remained live throughout, and removing the temporary line released only the new chord. Run `20260831-162400` proved the earlier Editor-replacement design but is superseded; the earlier run `20260831-162231` failed before mutation because its host scenario resolved the wrong home directory and its overlay was discarded.
- The live marketplace catalog remained a production object with top-level `generatedAt`, `mode`, `plugins`, `stateSchemaVersion`, and `warnings`; `stateSchemaVersion` was `2`, and entries retained the fields needed by the documented adapter. It contained 1,988 entries and was 4,882,620 bytes, so the collector uses a bounded source-specific catalog limit larger than the public feed's 2 MiB client limit.
- The GitHub releases endpoint retained the required release identity, draft/prerelease, publication timestamp, tag, body, and HTTPS source fields. The historical `basecamp/omarchy` API endpoint currently resolves to the `omacom/omarchy` repository identity, so redirect validation must allow only that specific GitHub API transition while published event links remain validated HTTPS URLs.

## Visual/current-news revalidation — 31 August 2026

- The owner intentionally superseded the panel-only/no-image decisions and requested a default-on optional newspaper, visual stories, real current collection, and local interest tuning. `DECISIONS.md` D004/D005/D010/D012/D016 record the new contract.
- Omarchy source commit `83881e979b35468c3e7d60b171e319ede61a88fd` confirms `ModuleSlot.implicitWidth` becomes zero when `activeItem.visible` is false. `WidgetButton` accepts left/right/middle buttons, and third-party widget metadata exposes the plugin source directory through the bar registry. No Omarchy source file was changed.
- The marketplace catalog observed at `2026-08-31T16:35:53Z` contained 1,995 entries. Entries expose optional `previewThumbnail`, width, and height; 1,674 current thumbnails use WebP. The exact marketplace origin returned matching `image/webp` bytes. The publisher now mirrors only that fixed origin/path family after structural inspection.
- The final pre-candidate live collection at `2026-08-31T17:12:06Z` produced five current official Omarchy releases plus twelve bounded recent marketplace listings; ten listings had valid mirrored previews and no image validation failure. Production `content/community/` is intentionally empty until a genuinely reviewed source record exists; the earlier synthetic wiki item moved to test fixtures.
