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

Current `PluginRegistry.setEnabled` places any enabled plugin declaring `bar-widget` into the bar layout, even when that manifest also has a non-widget kind. This makes a same-manifest “optional but absent” bar indicator an awkward hidden lifecycle state.

The version 1 decision is therefore a `panel`-only main plugin and no top-bar slot. A future indicator is a separate installable companion.

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
- `Super+Shift+N`: Editor.
- `Super+Ctrl+N`: Toggle nightlight.

`Super+N` is the recommended opt-in binding. Recheck both default source and the disposable guest’s live binding table before shipping. The helper must refuse personal conflicts regardless of defaults.

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
