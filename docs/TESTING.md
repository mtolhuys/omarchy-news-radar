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

`make local-latest` is not a source gate: it installs or updates the plugin and its receipt-backed Apps-menu entry, may migrate the old preview placement, and performs live network collection. It therefore belongs only in a disposable Plugin Lab run during development. The deterministic local-sync scenario injects a fully generated test edition through the explicit test boundary and must prove first install/enable, exact origin and revision, launcher discovery/action/icon, pictured local import, file-URL projection, default preferences, fast-forward update, idempotence, dirty-source refusal, exact panel-only placement migration, explicit launcher removal, and clean plugin removal.

## Unit coverage

### Feed and model

- Required fields, closed enums, UTC timestamps, URL rules, text normalization, bounds, duplicate IDs, and unsupported schema versions.
- Deterministic event ID and byte-stable serialization with fixed input and clock.
- Ordering, section projection, exact enabled-plugin matching, front-page composition, and saved-item retention.
- Explicit per-event read/unread overrides, migrated baseline semantics, one race-safe initial-story read per fresh non-empty panel open, no rearming on summon/refresh/reprojection, deduplicated actionable indicator counts across all persistent section projections, section unread counts, unread-only filtering, bounded just-read retention within the active view, read/unread reversal, bounded atomic filtered-section marking across unloaded pages, isolation from temporary search and nonmatching sections, pruning outside the current edition, and proof that close or refresh never bulk-marks unselected stories.
- State-v1-through-v8-to-v9 migration, exact legacy/current object shapes, legacy-interest/profile validation and removal, preference/filter/read-override bounds, exact removal of v5 Community preferences, per-section isolation, corrupt state quarantine, atomic replacement, symlink refusal, kernel-backed refresh-lock release after write failure or abrupt helper termination, cross-process state-mutation serialization, and last-known-good preservation.
- Local projection limits, finite load-more semantics, filtered counts, reset behavior, and proof that filters/pagination make no network request.

### Omarchy releases

- Published, prerelease, draft, paginated, unchanged, removed, malformed, rate-limited, and oversized fixtures.
- Stable GitHub release identity and deterministic plain-text release summary.
- Markdown/HTML/code/image content remains inert plain text.

### Marketplace

- Explicit baseline with a maximum twelve-item recent/fourteen-day backfill and no historical event flood.
- Added plugin, non-empty version change, unchanged version with repository activity, verification transition, explicit retirement, one-run absence, two-run confirmed absence, reappearance, multi-plugin repository, schema mismatch, and warnings.
- Stars, views, commits, validation times, descriptions, tags, and preview changes do not create unsupported events; current validated catalog descriptions may refresh every existing plugin-event explanation without changing its identity or order.
- Marketplace engagement schema/bounds, metric observation/source fields, release-asset download labels, repository stars, failed-source retention, and proof that metrics do not create or rank events.
- A failed current snapshot preserves prior state and creates no mass retirement.

### Community and curation

- Valid reviewed entry, duplicate stable ID, unsafe URL, overlong text, unknown tag, future date, copied-markup stripping, and unsupported significance.
- Curation may modify only allowed presentation fields and must reference an existing event.

### Publisher

- JSON, RSS, and HTML remain deterministic with a fixed clock.
- Source check, collection, artifact publication, and local-cache timestamps remain distinct; publication staleness is false at exactly 90 minutes and true one second later, with explicit legacy-feed fallback.
- Repository CI has read-only permissions and tests source, contracts, and deterministic generators; it has no feed-publication or Pages deployment path.
- Forge publication continuity selects Laravel's latest successfully deployed snapshot, rejects missing/invalid state, permits only the bounded fresh v1-to-v2 transition seed, and never falls back silently to stale committed state.
- Canonical source snapshots load independently from the host date; validation rejects unsorted, duplicate, and over-bound event ledgers, while successor construction prunes expired events against the explicit fixed collection clock and produces identical output across different host dates.
- Rediscovering a deterministic event through a lagging source snapshot preserves its first `occurredAt` and `discoveredAt`; Front Page includes only the newest official release rather than filling a core quota with historical releases.
- HTML/XML/context escaping defeats hostile titles, summaries, URLs, Unicode, quotes, angle brackets, and control characters.
- CSP and external-link attributes remain present.
- Generated-file drift fails validation.
- Marketplace preview origin/path, byte/content-type agreement, PNG/JPEG/WebP structure, static-only, size/dimension/pixel bounds, direct `sourceUrl` pass-through without hosted raster output, SVG rejection, graceful omission, and rejection of every non-allowlisted image URL; YouTube thumbnails are accepted only in their fixed allowlisted shape.
- Restored-to-successor marketplace coverage: nondecreasing catalog generation time and one validated addition story for every canonical plugin ID absent from the prior successful snapshot.

### Client helper

- Cached-first read, successful refresh, timeout, redirect rejection, oversized response, truncated JSON, unsupported schema, future timestamp, atomic cache replacement, benign stale per-story writes across replacement, and no-cache failure.
- Published-edition checks retain typed `updated`, `no-change`, `stale-publication`, invalid-feed, and offline results for logic and monitoring without exposing normal pipeline diagnostics in the reader when cached news is usable.
- Private file modes where supported, symlink refusal, bounded diagnostics, explicit purge, and one-refresh locking.
- Indicator unread/health output, exact enabled-plugin projection refreshed before each coalesced request, persistent-filter reachability including Saved, overlap deduplication, private last-attempt metadata, exact five-minute success/failure cadence, malformed/future metadata fail-open behavior, local bar/image preferences, fail-closed installed-plugin discovery, and no preference data in network requests.
- Local-edition build digest/revision, complete image validation before feed replacement, private file projection, marker mismatch fallback, published downgrade refusal, adoption of a newer published edition while local mode is active, and purge of imported assets.

### Shortcut helper

Use a temporary fake home and stub `hyprctl` executable to prove:

- status without mutation;
- read-only status and exact free-chord detection for `Super+Alt+N`;
- explicit installation without an unbind or action replacement;
- personal, multiple, unknown, and ambiguous conflict refusal;
- exact idempotence;
- automatic migration command no-op behavior for free, current, personal, edited, conflicting, multiple, symlinked, and ambiguous states;
- preservation of arbitrary surrounding Lua bytes;
- symlink and ownership refusal;
- successful reload and empty config errors;
- rollback after reload/config error;
- exact owned-block removal and release of `Super+Alt+N`, while the live Editor action remains intact;
- refusal to remove an edited or ambiguous block;
- no force-overwrite or action-replacement path.

### Application-launcher helper

Use temporary XDG data/state roots to prove absent/installed/modified status, bounded template validation, exact desktop action and icon identity, atomic idempotent install/update, private digest receipt, symlink/unowned/unmanaged/modified target refusal, receipt-matching removal, and preservation of user-modified files.

## Integration tests

Run the real client helper against a bounded in-process loopback server and temporary XDG roots. Assert request method, headers, redirect policy, body streaming limit, cache/state output, concurrency behavior, and absence of outbound requests beyond the fixture server.

Run a two-generation collector scenario: bootstrap a marketplace fixture, then apply core release, plugin add/version/verification/retirement, community, partial-source, and recovery changes. Validate the complete generated JSON, RSS, HTML, source snapshot, and archive.

Run local-source continuity through tracked-first, private-newer, invalid-private, post-import commit, and explicit purge cases. A failed edition import must never advance the private source baseline.

## QML and static contract tests

Source validation proves that the manifest references both existing entry points, the panel exposes `open()` and `close()`, owns a `FloatingWindow` rather than a layer-shell `PanelWindow`, the bar exposes exact visibility-driven geometry and fixed pointer actions, process commands are structural arrays, remote text is not assigned to rich-text paths, image sources come only from helper-projected feed paths, selected secondary text uses an explicit selection foreground, and hard-coded colors/sizing do not replace Omarchy tokens.

When `qmllint` and a selected Omarchy source are available, every QML file is checked through a temporary `qs` import namespace that resolves the selected source's `Commons` and `Ui` modules. Omarchy singleton members and host-injected context properties do not ship compiler type descriptions, so only their resulting `missing-property`, `unqualified`, and `signal-handler-parameters` categories are excluded; every other warning category is fatal. Static grep is supporting evidence, not runtime proof.

## Product-owned Plugin Lab acceptance

Run only inside the disposable lab:

```bash
cd "$OMARCHY_PLUGIN_LAB_ROOT"
./bin/lab doctor
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/acceptance.sh
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/activation-upgrade.sh
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/local-latest.sh
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/public-install.sh
./bin/lab plugin /absolute/path/to/omarchy-news-radar/tests/lab/release-preview.sh
```

`acceptance.sh` must prove with machine assertions and supporting screenshots:

1. Source tests and manifest validation pass for the exact candidate.
2. Plugin add, enable, discovery, and panel entry-point identity match the candidate.
3. The default right-section newspaper renders at native cross-axis size with unread and publisher/source health states; with the panel closed its due-checked helper adopts a new fixture and the watched badge count changes, left click summons or raises the panel, middle click checks the published edition, right click hides it with exact zero slot geometry, and Tune restores it.
4. The shortcut helper reports `Super+Alt+N` as free, writes its exact managed bind-only block, reloads cleanly, exposes exactly one Radar action on that chord, and leaves the separate Editor action live.
5. QMP `press meta_l-alt-n` opens the rendered Radar surface through the real global shortcut route; QMP pointer activation of the newspaper and the global shortcut each raise an obscured Radar, foreground and rapid repeated activation retain exactly one focused window, and no competing helper remains.
6. Cached fixture content and its validated legacy same-origin raster appear without waiting for the network, focus is visible, image-off fallback is complete, selected story fields match the validated fixture, and a fresh open persists exactly that first visible selection as read without any follow-up input while another story remains unread.
7. The normal window resizes by a real edge gesture, maximizes/restores, survives `Alt+Tab` away and back, and a window-manager close follows the shell lifecycle without leaving helpers.
8. `Tab` and `Shift+Tab` cycle the five sections; the Settings cogwheel shows fixed sources and only actionable filters, exposes no renaming/profile path or low-value explanatory filler, and independently resets filters. Selecting under Unread only persists the read state and count while retaining the active row in place until context changes. In a dense list, crossing the viewport bottom anchors the complete selected row at the top, the following Down continues without moving the viewport or clipping the row, and held Up never lets repeated selection escape above the viewport; retained geometry proves all three facts. Down from the final loaded story focuses Load more with an explicit Enter label; Up returns focus without changing selection or `contentY`; Enter expands it without another feed request while continuous samples prove the selected row remains fully visible at the same on-screen position with no animation before the next Down continues into the new page.
9. Icon metrics, accessible metric labels, observed time, marketplace caveat, and a human-facing plugin detail link render from the validated fixture; raw metric endpoint links are absent and metrics do not change Front Page order.
10. `j`, `k`, section keys, search, save, read/unread toggle, filtered-section **Mark all as read**, **Check for updates**, Tune, and source opening use rendered controls; the batch action includes unloaded matches but not nonmatching stories, no permanent keyboard or publication-diagnostics strip occupies the reader, the update control exposes `R` on hover, every story row visibly states `UNREAD` or `READ`, section badges expose unread counts, and a guest-only inert browser shim captures the exact validated HTTPS URL.
11. Exact enabled-plugin matching places fixture events in For You without transmitting private inputs; no manual-interest UI, CLI argument, or current state field exists.
12. The published-edition check proves updated/new-story-count, no-change/publication-age, stale-publisher, offline, malformed, oversized, and partial-source states while preserving the last-known-good edition where required.
13. Normal close does not change unselected stories; an event introduced during an already open session remains unread until the next fresh open visibly selects it, that open persists only the selected event as read, and `u` can make it unread again before the rendered action restores read state.
14. Maintained dark and light themes, narrow resolution, long text, empty section, first-use, cached, animated-refreshing, offline, invalid, and partial states remain unclipped and understandable; successful cached/local/published states show no edition-mode, source-health, publication-age, cache, version, or keyboard-legend noise; selected and unselected headlines, summaries, metadata, metrics, and meaningful secondary copy remain readable in both themes, and no empty Community destination is present.
15. AltTab and Omadock companion candidates resolve Radar's exact enabled `windowIdentity` to its local manifest name/icon, render the newspaper asset in their visible UI, and fall back for disabled, malformed, missing, or ambiguous declarations without relabeling unrelated Quickshell windows.
16. Escape closes the panel, no panel helper remains, the hidden bar performs no network refresh, and no shell/Hyprland/QML error occurs after the close boundary.
17. A same-path plugin update replaces the loaded panel and bar identities/behavior.
18. Installing the receipt-backed XDG launcher makes **Omarchy News Radar** searchable with its newspaper icon in the real Apps menu; selecting that visible row summons Radar, and explicit launcher removal makes the row disappear without touching another application.
19. Shortcut removal deletes only the owned block, releases `Super+Alt+N`, and leaves the live Editor action intact; plugin disable, re-enable, and removal cleanly unload runtime while preserving local state.

`activation-upgrade.sh` separately constructs an exact local Git history from released 0.1.3 and the current candidate. It must install the 0.1.3 managed shortcut, reproduce the released background-window close through both real QMP routes, fast-forward through Omarchy's official plugin updater, and—without opening Radar or clicking any migration control—prove that the updater's normal rescan backs up and replaces only the exact retained legacy block. The resulting live shortcut and current newspaper must each raise one obscured Radar window while foreground repeats keep it open. It must also prove empty Hyprland configuration errors and exact shortcut removal. The panel's visible migration control remains separately source/unit tested as the rollback-safe retry path.

`public-install.sh` separately proves the public GitHub URL clones the expected commit, validates and enables the panel, loads the fixed Forge edition, exposes durable per-story read state, supports documented launcher and shortcut setup/removal, and removes through plugin ID `io.github.mtolhuys.news-radar`.

`release-preview.sh` is a separate networked release-only journey. It installs the local candidate only in the disposable guest, refreshes the fixed public Forge edition, requires a validated direct allowlisted marketplace/YouTube image, applies Omarchy's Matte Black theme, records exact `1240×740` window geometry below the desktop bar, captures the frame, and removes the candidate. Crop the retained `1280×800` console image by the recorded `[20,40]` origin; deterministic acceptance remains independent of this marketing proof.

## Visual review

Review every captured state rather than merely checking that screenshots exist. Inspect clipping, overlap, reading order, focus, source labels, stale/offline disclosure, long text, contrast, scroll behavior, monitor fit, and visual hierarchy.

The acceptance matrix includes maintained light and dark themes, 1366×768-equivalent narrow space, a normal wide display, 200% text scaling, reduced motion, keyboard-only operation, long Unicode content, 100+ event virtualization, and no-cache/offline recovery. Acceptance screenshots use synthetic public-safe content; the separately identified release preview uses only the validated public edition.

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
