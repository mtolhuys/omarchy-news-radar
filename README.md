# Omarchy News Radar

> Press one key and catch up with what changed across Omarchy.

Omarchy News Radar is a keyboard-first activity reader for meaningful Omarchy core releases, plugin additions and releases, verification changes, and selected community work. It turns a scattered ecosystem into a calm, source-linked “newspaper” without requiring another busy status-bar icon.

## Project status

This repository currently contains the complete product and engineering specification. The implementation has not been built or released yet. Commands and installation examples described in the documentation are target contracts until the corresponding code and disposable-guest evidence exist.

## Intended experience

The recommended shortcut is `Super+Shift+N`. Omarchy Quattro currently assigns that chord to Editor, so Radar treats setup as a deliberate reassignment rather than pretending the key is free. The helper requires explicit authorization, accepts only the exact audited default Editor case, refuses personal or ambiguous conflicts, and makes removal reveal the original default again.

Pressing the shortcut opens a theme-native front page:

- **Front Page** presents a small edition of the most consequential changes.
- **For You** relates events to plugins installed on the current machine.
- **Core** contains official Omarchy releases and compatibility-relevant changes.
- **Plugins** contains new plugins, version changes, retirements, and verification changes.
- **Community** contains manually accepted tutorials, showcases, and projects.
- **Saved** contains local bookmarks.

The panel renders cached data first, refreshes in the background, works offline with its last-known-good edition, and opens original sources only after an explicit user action.

## Why a panel rather than another bar widget?

Omarchy desktops are already shortcut-heavy and top bars are often crowded. The version 1 plugin is therefore an on-demand `panel`, not a `bar-widget`. There is no required or invisible bar slot. A separate, truly optional indicator may be designed later if real usage proves it valuable.

## System shape

```text
Official releases ───────┐
Marketplace catalog ─────┼── deterministic collector ── versioned static feed
Reviewed community links ┘                                  │
                                                            ├── Omarchy panel
                                                            ├── static website
                                                            └── RSS/JSON consumers
```

The collector and static publisher are owned by this repository. The plugin consumes one bounded feed and keeps personal read state on the local machine. No cooperation from Omarchy core, the marketplace maintainers, or a newsletter operator is required for the product to work.

## Design principles

- Facts before volume.
- Original sources before copied content.
- Deterministic summaries before generated prose.
- Local relevance before popularity.
- Cached usefulness before network dependency.
- Explicit setup before hidden system mutation.
- Keyboard access before ornamental chrome.
- Honest trust labels before unsupported safety claims.

## Documentation map

- [`AGENTS.md`](AGENTS.md) — binding engineering contract for coding agents.
- [`BUILD-PROMPT.md`](BUILD-PROMPT.md) — copy-ready handoff prompt for the implementation agent.
- [`docs/PRODUCT.md`](docs/PRODUCT.md) — promise, scope, user journey, and non-goals.
- [`docs/UX.md`](docs/UX.md) — newspaper interaction, keyboard model, states, and accessibility.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — plugin, collector, publisher, local state, and lifecycle.
- [`docs/DATA-MODEL.md`](docs/DATA-MODEL.md) — versioned feed, event, and local-state schemas.
- [`docs/SOURCES.md`](docs/SOURCES.md) — source adapters, diff semantics, failure handling, and bootstrap.
- [`docs/CURATION.md`](docs/CURATION.md) — what counts as notable and how summaries remain trustworthy.
- [`docs/SECURITY.md`](docs/SECURITY.md) — trust boundaries, URL handling, cache safety, and shortcut mutation.
- [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md) — allowed runtime, development, and CI dependencies.
- [`docs/TESTING.md`](docs/TESTING.md) — deterministic tests and disposable desktop acceptance.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — settled architectural and product decisions.
- [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) — ordered build plan and definitions of done.
- [`docs/RELEASE.md`](docs/RELEASE.md) — evidence-driven release contract.
- [`docs/RESEARCH.md`](docs/RESEARCH.md) — dated audit of current Omarchy and marketplace contracts.

## Independence

The intended public repository is `github.com/mtolhuys/omarchy-news-radar`, with a GitHub Pages deployment generated from the same source. An official domain or organization transfer may happen later, but is not part of the architecture and is not required for launch.

Omarchy News Radar is intended as an independent community project and must not imply official affiliation unless that status is explicitly granted later.
