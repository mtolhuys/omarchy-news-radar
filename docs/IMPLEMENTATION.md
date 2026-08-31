# Implementation plan

This plan is ordered to retire the highest-risk contracts before visual polish. Complete every phase and its tests; do not jump directly to a convincing panel mockup backed by placeholder logic.

## Phase 0 — Revalidate the environment

1. Read `AGENTS.md` and every required document.
2. Read the current Plugin Lab contracts and run `./bin/lab doctor` before any runtime session.
3. Inspect the exact Omarchy source selected by the lab, including root `AGENTS.md`, shell development guidance, `docs/omarchy-shell.md`, `shell/services/PluginRegistry.qml`, panel loaders, current theme/UI tokens, and current default bindings.
4. Reconfirm that `Super+Alt+N` is absent from both the current default source and live binding table in the disposable guest, while the separate `Super+Shift+N` Editor action remains intact. If the chord contract changed, stop and update the decision rather than guessing.
5. Revalidate the marketplace `site/catalog.json` top-level and plugin-entry schema. Update only the source adapter and dated research unless a product contract truly changed.

**Done when:** The implementation agent records current source/lab revisions and any contract drift in `docs/RESEARCH.md` without changing the intended product silently.

## Phase 1 — Establish repository quality gates

1. Add the Python package, Makefile, test layout, fixtures, `.gitignore`, license, changelog, security reporting placeholder, and CI test workflow.
2. Implement deterministic clock and I/O abstractions used by collectors and tests.
3. Implement atomic bounded JSON read/write helpers, text/URL/time normalization, and typed exceptions.
4. Implement feed and local-state models plus manual validation for every bound in `DATA-MODEL.md`.
5. Add unit tests before network adapters.

**Done when:** `make test` and `make validate` pass offline from a clean clone and malformed fixture classes cannot replace good state.

## Phase 2 — Build the collector and publisher

1. Implement Omarchy release, marketplace catalog, and reviewed community adapters behind one interface.
2. Implement explicit marketplace bootstrap with a bounded recent backfill, normalized tracked snapshot, two-generation diff, source-health handling, deterministic IDs, and no-event metadata churn.
3. Implement curation overlay with restricted mutable fields.
4. Implement bounded feed envelope, rolling live window, saved archive inputs, RSS, escaped static HTML, and publisher-mirrored content-addressed marketplace preview rasters.
5. Implement fixture mode and `make feed-fixture`.
6. Implement an idempotent publish workflow that tests before generating a Pages artifact with least privileges.

**Done when:** A fixed two-generation fixture produces byte-stable JSON/RSS/HTML, first bootstrap emits no more than twelve recent listings, invalid images degrade to text, partial sources cannot manufacture retirements, and generated output validates itself.

## Phase 3 — Build the client helper

1. Implement fixed-origin bounded HTTPS refresh, redirect policy, candidate validation, cache locking, and atomic last-known-good replacement.
2. Implement state read, v1-to-v2 migration, session cutoff, saved toggle, private bar/image/interest preferences, indicator model, quarantine, and explicit purge.
3. Return small versioned JSON responses designed for QML rather than exposing internal exceptions.
4. Add loopback integration tests for success, timeout, redirect, oversize, truncation, invalid schema, concurrent refresh, and offline cache.

**Done when:** The helper never needs QML to parse unvalidated remote input and every failure preserves good cache/state.

## Phase 4 — Build the native panel

1. Inspect and use the current host-owned panel/window, focus, token, border, scroll, and source-opening contracts.
2. Create `src/Panel.qml` and supporting components with an explicit runtime build identity.
3. Implement cached-first open, one asynchronous refresh, section projections, installed-plugin and explicit-interest matching, deterministic front page, safe feed-image projection, search, selection, save, source opening, Tune preferences, and state labels.
4. Implement the complete keyboard map and pointer equivalents.
5. Implement responsive one/two-column presentation without changing semantic order.
6. Add `manifest.json` only after both entry points exist and validation passes.

**Done when:** Source tests prove structure and a fixture-driven component can represent every UX state without remote HTML, arbitrary image URLs, hard-coded theme values, or network-blocked opening.

## Phase 4b — Add the optional newspaper indicator

1. Implement one theme-native `bar-widget` with a code-native newspaper, unread count, and source-health dot.
2. Route left click to panel toggle, middle click to bounded refresh, and right click to the local hide preference.
3. Bind hidden state to exact invisible root geometry and watch local state so Tune in the panel can restore it.
4. Use `refresh-if-due` on startup and every 30 minutes only while visible; use the shared atomic lock to contain multi-monitor overlap.

**Done when:** Source tests and Plugin Lab geometry/pointer evidence prove default placement, zero-gap hiding, restoration, no hidden refresh cadence, and clean unload.

## Phase 5 — Build explicit shortcut setup

1. Implement `news-radar-shortcut status|install|remove` exactly within the security contract.
2. Use semantic live conflict detection, personal-override inspection, and an exact managed Lua binding block with no `hl.unbind` statement.
3. Make `status` read-only and make `install` succeed only when `Super+Alt+N` is free; never provide a force or action-replacement path.
4. Implement backup, atomic write, reload, live-action/config-error validation, rollback, idempotence, chord release, and manual fallback text.
5. Document free-chord inspection, install, custom binding, shortcut removal, unchanged Editor behavior, plugin removal, and stale-binding behavior accurately.

**Done when:** Temporary-home tests cover every mutation and rollback case, and the disposable guest can install and remove the live binding without touching unrelated configuration.

## Phase 6 — Integrate and accept in Plugin Lab

1. Create product-owned lab fixtures and `tests/lab/acceptance.sh` using lab helpers rather than another VM controller.
2. Install the exact candidate, set deterministic guest-only feed/cache fixtures, and expose source/installed/runtime identities.
3. Send `Super+Alt+N` through QMP and assert the rendered panel, not just IPC state; also prove the Editor binding remains live before, during, and after Radar setup.
4. Drive keyboard and pointer journeys, bar hide/restore, image on/off, installed and interest relevance, source opening through an inert guest shim, refresh transitions, seen cutoff, save state, themes, narrow layout, error recovery, close teardown, hot update, disable, re-enable, shortcut removal, and plugin removal.
5. Inspect shell logs and every visual checkpoint.

**Done when:** The full acceptance list in `TESTING.md` passes for one clean committed candidate and the timestamped evidence directory is recorded.

## Phase 7 — Release hardening

1. Measure resource and interaction boundaries before making numeric claims.
2. Complete keyboard, visible focus, text scaling, contrast, reduced-motion, and assistive-technology review appropriate to public claims.
3. Pin workflow actions, finish license/security files, audit generated artifacts, and prove clean-clone install when a public repository exists.
4. Align manifest version, runtime identity, README, changelog, screenshots, feed schema, release notes, and evidence.
5. Keep public publishing, tagging, marketplace submission, domain setup, and remote repository creation outside the implementation task unless explicitly authorized.

**Done when:** Every publishable checklist item in `RELEASE.md` is green or explicitly described as a limitation in pre-release language.

## Engineering expectations

- Prefer small pure functions and immutable normalized models.
- Keep adapter-specific fields inside adapters.
- Avoid booleans that hide multi-state lifecycle; use explicit enums and state objects.
- Preserve last-known-good artifacts transactionally.
- Keep diagnostics actionable and public-safe.
- Delete superseded prototypes and unused abstractions rather than retaining parallel paths.
- Write tests alongside each behavior and keep fixtures minimal enough to understand in review.
- Do not add speculative extension points for accounts, notifications, AI summaries, arbitrary feeds, or plugin installation.

## Final definition of done

The entire local implementation is complete, clean, tested, documented, and proven in the disposable guest. The only acceptable remaining blockers are actions requiring new external authority, such as creating the remote repository, enabling GitHub Pages, publishing a release, registering a domain, or submitting to the marketplace.
