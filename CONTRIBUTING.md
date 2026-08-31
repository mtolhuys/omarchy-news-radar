# Contributing

Omarchy News Radar is contract-first and evidence-driven. Start with [`AGENTS.md`](AGENTS.md), then read the complete documentation set it requires before changing behavior.

## Principles

- Keep changes small, reviewable, and source-linked.
- Add or update tests with every behavior change.
- Preserve deterministic output and last-known-good state.
- Keep remote content inert and bounded.
- Prefer current Omarchy and Python standard-library contracts over new dependencies.
- Write all tracked text in English and avoid hard-wrapping Markdown prose.
- Do not turn routine activity, popularity, or automated verification into unsupported editorial or security claims.

## Local source work

The repository exposes:

```bash
make test
make validate
make feed-fixture
make site
```

Tests must remain offline and operate on committed synthetic fixtures or temporary XDG roots. Do not use a developer’s real cache, state, Hyprland bindings, installed-plugin list, or Home paths as fixtures.

## Runtime work

Plugin installation, enablement, shortcut setup, Hyprland reload, rendered interaction, hot update, and removal belong in the disposable Omarchy Plugin Lab. Never activate a development candidate on the daily host as part of automated work.

## Community entries

Community records must link an original HTTPS source, state a specific Omarchy contribution, use concise factual English, and meet `docs/CURATION.md`. A submission is not automatically notable.

## External actions

Do not push, tag, publish, enable Pages, create releases, change repository settings, submit to the marketplace, buy or configure a domain, or announce on someone’s behalf without explicit owner authorization.
