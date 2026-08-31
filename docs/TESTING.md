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

## Unit coverage

### Feed and model

- Required fields, closed enums, UTC timestamps, URL rules, text normalization, bounds, duplicate IDs, and unsupported schema versions.
- Deterministic event ID and byte-stable serialization with fixed input and clock.
- Ordering, section projection, installed-plugin matching, front-page composition, and saved-item retention.
- Monotonic `seenThrough` and session-cutoff semantics, including events arriving during an open session.
- Corrupt state quarantine, bounds, atomic replacement, symlink refusal, and last-known-good preservation.

### Omarchy releases

- Published, prerelease, draft, paginated, unchanged, removed, malformed, rate-limited, and oversized fixtures.
- Stable GitHub release identity and deterministic plain-text release summary.
- Markdown/HTML/code/image content remains inert plain text.

### Marketplace

- Explicit baseline with zero initial event flood.
- Added plugin, non-empty version change, unchanged version with repository activity, verification transition, explicit retirement, one-run absence, two-run confirmed absence, reappearance, multi-plugin repository, schema mismatch, and warnings.
- Stars, views, commits, validation times, descriptions, tags, and preview changes do not create unsupported events.
- A failed current snapshot preserves prior state and creates no mass retirement.

### Community and curation

- Valid reviewed entry, duplicate stable ID, unsafe URL, overlong text, unknown tag, future date, copied-markup stripping, and unsupported significance.
- Curation may modify only allowed presentation fields and must reference an existing event.

### Publisher

- JSON, RSS, and HTML remain deterministic with a fixed clock.
- HTML/XML/context escaping defeats hostile titles, summaries, URLs, Unicode, quotes, angle brackets, and control characters.
- CSP and external-link attributes remain present.
- Generated-file drift fails validation.

### Client helper

- Cached-first read, successful refresh, timeout, redirect rejection, oversized response, truncated JSON, unsupported schema, future timestamp, atomic cache replacement, and no-cache failure.
- Private file modes where supported, symlink refusal, bounded diagnostics, explicit purge, and one-refresh locking.

### Shortcut helper

Use a temporary fake home and stub `hyprctl` executable to prove:

- status without mutation;
- free `Super+N` installation;
- semantic conflict refusal;
- exact idempotence;
- preservation of arbitrary surrounding Lua bytes;
- symlink and ownership refusal;
- successful reload and empty config errors;
- rollback after reload/config error;
- exact owned-block removal;
- refusal to remove an edited or ambiguous block;
- no force-overwrite path.

## Integration tests

Run the real client helper against a bounded in-process loopback server and temporary XDG roots. Assert request method, headers, redirect policy, body streaming limit, cache/state output, concurrency behavior, and absence of outbound requests beyond the fixture server.

Run a two-generation collector scenario: bootstrap a marketplace fixture, then apply core release, plugin add/version/verification/retirement, community, partial-source, and recovery changes. Validate the complete generated JSON, RSS, HTML, source snapshot, and archive.

## QML and static contract tests

Source validation proves that the manifest references existing entry points, the panel exposes `open()` and `close()`, process commands are structural arrays, remote content is not assigned to rich-text paths, and hard-coded colors/sizing do not replace Omarchy tokens.

When `qmllint` and a selected Omarchy source are available, import paths and QML syntax must pass. Static grep is supporting evidence, not runtime proof.

## Product-owned Plugin Lab acceptance

Run only inside the disposable lab:

```bash
cd "$OMARCHY_PLUGIN_LAB_ROOT"
./bin/lab doctor
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/acceptance.sh
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/public-install.sh
```

`acceptance.sh` must prove with machine assertions and supporting screenshots:

1. Source tests and manifest validation pass for the exact candidate.
2. Plugin add, enable, discovery, and panel entry-point identity match the candidate.
3. The shortcut helper detects a free binding, writes its exact managed block, reloads cleanly, and exposes `Super+N` in the live bind table.
4. QMP `press meta_l-n` opens the rendered Radar surface through the real global shortcut route.
5. Cached fixture content appears without waiting for the network, focus is visible, and the selected story fields match the validated fixture.
6. `j`, `k`, section keys, search, save, refresh, and source opening use the public rendered controls; a guest-only inert browser shim captures the exact validated HTTPS URL.
7. Installed-plugin matching places the fixture event in For You without transmitting installed IDs.
8. Refresh succeeds once, then offline, malformed, oversized, and partial-source fixtures preserve the last-known-good edition with accurate recovery labels.
9. Normal close advances `seenThrough` only to the session cutoff; an event introduced during the session remains new next time.
10. Maintained dark and light themes, narrow resolution, long text, empty section, first-use, cached, refreshing, offline, invalid, and partial states remain unclipped and understandable.
11. Escape closes the panel, no helper remains, and no shell/Hyprland/QML error occurs after the close boundary.
12. A same-path plugin update replaces the loaded panel identity and behavior.
13. Shortcut removal deletes only the owned block and live binding; plugin disable, re-enable, and removal cleanly unload runtime while preserving local state.

`public-install.sh` separately proves the eventual public GitHub URL clones the expected commit, validates and enables the panel, supports documented shortcut setup/removal, and removes through plugin ID `io.github.mtolhuys.news-radar`. Keep this scenario pending until a public repository exists; do not fake success with a local URL.

## Visual review

Review every captured state rather than merely checking that screenshots exist. Inspect clipping, overlap, reading order, focus, source labels, stale/offline disclosure, long text, contrast, scroll behavior, monitor fit, and visual hierarchy.

The release matrix includes maintained light and dark themes, 1366×768-equivalent narrow space, a normal wide display, 200% text scaling, reduced motion, keyboard-only operation, long Unicode content, 100+ event virtualization, and no-cache/offline recovery. Screenshots use synthetic public-safe content only.

## Performance and resource boundaries

- Live feed is at most 2 MiB and 500 events.
- Saved state is at most 250 items.
- At most one refresh helper runs per panel instance.
- Cached rendering does not wait for a network response.
- Closing the panel leaves no owned process or timer.
- The UI uses a bounded or virtualized visible model rather than instantiating every story card simultaneously.

Measure panel-open latency, parser time, idle resource use, dense-model navigation, and close teardown in a recorded VM context before publishing numeric performance claims. Do not turn an unmeasured target into README fact.

## Evidence records

Every release candidate records commit, manifest version and loaded identity, selected Omarchy source and lab base, exact commands, timestamped evidence directories, machine assertions, screenshots reviewed, and remaining limitations in a release-evidence document created during implementation.
