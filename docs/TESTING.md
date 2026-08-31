# Test contract

Radar tests must prove deterministic data handling and the real shortcut-to-panel journey without activating code on the daily host.

## Source gate

The repository provides:

```bash
make test
make validate
make feed-fixture
make site
```

`make test` is offline, deterministic, creates only temporary synthetic state, and covers all Python, publisher, helper, shortcut, and pure presentation-model tests. `make validate` checks repository and plugin contracts without enabling the plugin.

`make local-latest` is not a source gate: it installs or updates the plugin, may migrate the old preview placement, and performs live network collection. It therefore belongs only in a disposable Plugin Lab run during development. The deterministic local-sync scenario injects a fully generated test edition through the explicit test boundary and must prove first install/enable, exact origin and revision, pictured local import, file-URL projection, default preferences, fast-forward update, idempotence, dirty-source refusal, exact panel-only placement migration, and clean removal.

## Unit coverage

### Feed and model

- Required fields, closed enums, UTC timestamps, URL rules, text normalization, bounds, duplicate IDs, and unsupported schema versions.
- Deterministic event ID and byte-stable serialization with fixed input and clock.
- Ordering, section projection, installed-plugin/private-interest matching, front-page composition, and saved-item retention.
- Monotonic `seenThrough` and session-cutoff semantics, including events arriving during an open session.
- State-v1/v2/v3-to-v4 migration, preference/interest/filter/profile bounds, closed icon/tone vocabularies, per-section isolation, corrupt state quarantine, atomic replacement, symlink refusal, and last-known-good preservation.
- Local projection limits, finite load-more semantics, filtered counts, reset behavior, and proof that filters/pagination make no network request.

### Omarchy releases

- Published, prerelease, draft, paginated, unchanged, removed, malformed, rate-limited, and oversized fixtures.
- Stable GitHub release identity and deterministic plain-text release summary.
- Markdown/HTML/code/image content remains inert plain text.

### Marketplace

- Explicit baseline with a maximum twelve-item recent/fourteen-day backfill and no historical event flood.
- Added plugin, non-empty version change, unchanged version with repository activity, verification transition, explicit retirement, one-run absence, two-run confirmed absence, reappearance, multi-plugin repository, schema mismatch, and warnings.
- Stars, views, commits, validation times, descriptions, tags, and preview changes do not create unsupported events.
- Marketplace engagement schema/bounds, metric observation/source fields, release-asset download labels, repository stars, failed-source retention, and proof that metrics do not create or rank events.
- A failed current snapshot preserves prior state and creates no mass retirement.

### Community and curation

- Valid reviewed entry, duplicate stable ID, unsafe URL, overlong text, unknown tag, future date, copied-markup stripping, and unsupported significance.
- Curation may modify only allowed presentation fields and must reference an existing event.

### Publisher

- JSON, RSS, and HTML remain deterministic with a fixed clock.
- HTML/XML/context escaping defeats hostile titles, summaries, URLs, Unicode, quotes, angle brackets, and control characters.
- CSP and external-link attributes remain present.
- Generated-file drift fails validation.
- Marketplace preview origin/path, byte/content-type agreement, PNG/JPEG/WebP structure, static-only, size/dimension/pixel bounds, SHA-256 naming, same-origin projection, SVG rejection, graceful omission, and no upstream URL in public feed.

### Client helper

- Cached-first read, successful refresh, timeout, redirect rejection, oversized response, truncated JSON, unsupported schema, future timestamp, atomic cache replacement, and no-cache failure.
- Private file modes where supported, symlink refusal, bounded diagnostics, explicit purge, and one-refresh locking.
- Indicator unread/health output, due-check age bounds, local bar/image preferences, interests, and no preference data in network requests.
- Local-edition build digest/revision, complete image validation before feed replacement, private file projection, marker mismatch fallback, no public refresh while local mode is active, and purge of imported assets.

### Shortcut helper

Use a temporary fake home and stub `hyprctl` executable to prove:

- status without mutation;
- read-only status and exact free-chord detection for `Super+Alt+N`;
- explicit installation without an unbind or action replacement;
- personal, multiple, unknown, and ambiguous conflict refusal;
- exact idempotence;
- preservation of arbitrary surrounding Lua bytes;
- symlink and ownership refusal;
- successful reload and empty config errors;
- rollback after reload/config error;
- exact owned-block removal and release of `Super+Alt+N`, while the live Editor action remains intact;
- refusal to remove an edited or ambiguous block;
- no force-overwrite or action-replacement path.

## Integration tests

Run the real client helper against a bounded in-process loopback server and temporary XDG roots. Assert request method, headers, redirect policy, body streaming limit, cache/state output, concurrency behavior, and absence of outbound requests beyond the fixture server.

Run a two-generation collector scenario: bootstrap a marketplace fixture, then apply core release, plugin add/version/verification/retirement, community, partial-source, and recovery changes. Validate the complete generated JSON, RSS, HTML, source snapshot, and archive.

## QML and static contract tests

Source validation proves that the manifest references both existing entry points, the panel exposes `open()` and `close()`, owns a `FloatingWindow` rather than a layer-shell `PanelWindow`, the bar exposes exact visibility-driven geometry and fixed pointer actions, process commands are structural arrays, remote text is not assigned to rich-text paths, image sources come only from helper-projected feed paths, selected secondary text uses an explicit selection foreground, and hard-coded colors/sizing do not replace Omarchy tokens.

When `qmllint` and a selected Omarchy source are available, import paths and QML syntax must pass. Static grep is supporting evidence, not runtime proof.

## Product-owned Plugin Lab acceptance

Run only inside the disposable lab:

```bash
cd "$OMARCHY_PLUGIN_LAB_ROOT"
./bin/lab doctor
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/acceptance.sh
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/local-latest.sh
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/public-install.sh
```

`acceptance.sh` must prove with machine assertions and supporting screenshots:

1. Source tests and manifest validation pass for the exact candidate.
2. Plugin add, enable, discovery, and panel entry-point identity match the candidate.
3. The default right-section newspaper renders at native cross-axis size with unread and health states; left click opens the panel, middle click refreshes, right click hides it with exact zero slot geometry, and Tune restores it.
4. The shortcut helper reports `Super+Alt+N` as free, writes its exact managed bind-only block, reloads cleanly, exposes exactly one Radar action on that chord, and leaves the separate Editor action live.
5. QMP `press meta_l-alt-n` opens the rendered Radar surface through the real global shortcut route.
6. Cached fixture content and its same-origin raster appear without waiting for the network, focus is visible, image-off fallback is complete, and selected story fields match the validated fixture.
7. The normal window resizes by a real edge gesture, maximizes/restores, survives `Alt+Tab` away and back, and a window-manager close follows the shell lifecycle without leaving helpers.
8. `Tab` and `Shift+Tab` cycle sections; the Settings cogwheel renames one section, selects a large semantic icon and theme-derived background, displays its fixed sources and built-in rule, independently resets appearance and filters, and Load more expands a dense local projection without another feed request.
9. Icon metrics, accessible metric labels, observed time, marketplace caveat, and a human-facing plugin detail link render from the validated fixture; raw metric endpoint links are absent and metrics do not change Front Page order.
10. `j`, `k`, section keys, search, save, refresh, Tune, and source opening use rendered controls; a guest-only inert browser shim captures the exact validated HTTPS URL.
11. Installed-plugin and explicit-interest matching place fixture events in For You without transmitting private inputs.
12. Refresh succeeds once, then offline, malformed, oversized, and partial-source fixtures preserve the last-known-good edition with accurate recovery labels.
13. Normal close advances `seenThrough` only to the session cutoff; an event introduced during the session remains new next time.
14. Maintained dark and light themes, narrow resolution, long text, empty section, first-use, cached, refreshing, offline, invalid, and partial states remain unclipped and understandable; selected headlines, summaries, metadata, and metrics remain readable in both themes.
15. Escape closes the panel, no panel helper remains, the hidden bar performs no network refresh, and no shell/Hyprland/QML error occurs after the close boundary.
16. A same-path plugin update replaces the loaded panel and bar identities/behavior.
17. Shortcut removal deletes only the owned block, releases `Super+Alt+N`, and leaves the live Editor action intact; plugin disable, re-enable, and removal cleanly unload runtime while preserving local state.

`public-install.sh` separately proves the eventual public GitHub URL clones the expected commit, validates and enables the panel, supports documented shortcut setup/removal, and removes through plugin ID `io.github.mtolhuys.news-radar`. Keep this scenario pending until a public repository exists; do not fake success with a local URL.

## Visual review

Review every captured state rather than merely checking that screenshots exist. Inspect clipping, overlap, reading order, focus, source labels, stale/offline disclosure, long text, contrast, scroll behavior, monitor fit, and visual hierarchy.

The release matrix includes maintained light and dark themes, 1366×768-equivalent narrow space, a normal wide display, 200% text scaling, reduced motion, keyboard-only operation, long Unicode content, 100+ event virtualization, and no-cache/offline recovery. Screenshots use synthetic public-safe content only.

## Performance and resource boundaries

- Live feed is at most 2 MiB and 500 events.
- Saved state is at most 250 items.
- At most one refresh helper runs per entry-point instance, with a cross-instance atomic lock.
- Cached rendering does not wait for a network response.
- Closing the panel leaves no panel-owned process or timer; hiding the bar stops its refresh timer while retaining only the bounded local status check needed to observe re-enable.
- The UI uses a bounded or virtualized visible model rather than instantiating every story card simultaneously.

Measure panel-open latency, parser time, idle resource use, dense-model navigation, and close teardown in a recorded VM context before publishing numeric performance claims. Do not turn an unmeasured target into README fact.

## Evidence records

Every release candidate records commit, manifest version and loaded identity, selected Omarchy source and lab base, exact commands, timestamped evidence directories, machine assertions, screenshots reviewed, and remaining limitations in a release-evidence document created during implementation.
