# Dated contract research


> **Publisher note (updated 2026-09-04):** Live feed publication is now Forge Laravel `news-radar:publish` every five minutes at `https://mtolhuijs.nl/news-radar/events.json`. Historical Actions/Pages schedule findings below are retained as research context only.

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

## Window and metric revalidation — 31 August 2026

- Current Omarchy source commit `83881e979b35468c3e7d60b171e319ede61a88fd` uses Quickshell `FloatingWindow` in `shell/plugins/dev-gallery/GalleryPanel.qml` as a supported normal XDG toplevel behind an `Item` panel entry point. Quickshell exposes `minimumSize`, `minimized`, `maximized`, `startSystemMove()`, and `startSystemResize()` on that window contract. Omarchy's `omarchy-hyprland-window-pop` first attempts the Lua float toggle and retains `hyprctl dispatch togglefloating address:…` as its compatibility route. Radar uses that structural route only after a bounded client-list probe finds exactly one mapped client matching its current/initial title and Quickshell class and validates its compositor address; it never guesses with the active window or edits user configuration. This supports ordinary Hyprland task switching and supersedes Radar's full-monitor layer overlay. Owner testing later found the hosted minimize action unreliable, so Radar removed its minimize control while retaining resize, Maximize/Restore, close, and task switching.
- A hosted Quickshell `FloatingWindow` exposes the process-wide Wayland app ID `org.quickshell`; the current type contract has no per-window app-ID or icon setter. The separately installed `vbrosseau.alttab` 1.0.10 switcher and Omadock 3.0.2 both resolved that shared class before Radar's local manifest, which explains the generic Quickshell gear in the supplied screenshots. The owner authorized companion integration on 1 September 2026. Radar now declares its exact app-ID/title pair, and the local AltTab and Omadock candidates use the existing manifest icon only for one exact enabled match; they retain ordinary fallback for every ambiguous or unrelated Quickshell window. Radar still does not shadow the global `org.quickshell.desktop` entry.
- The official marketplace documentation describes anonymous aggregate detail views, successful command copies, and hearts and explicitly distinguishes them from downloads, installations, unique people, verified votes, rankings, and security signals. The fixed `https://api.omarchyplugins.com/v1/stats` endpoint exposed schema version 1 and per-plugin non-negative `views`, `copies`, and `hearts` integers during the audit.
- The fixed marketplace catalog retained an optional non-negative `stars` field. GitHub's official Releases API defines `assets[].download_count`; Radar therefore labels the sum only as “release asset downloads.” None of these observations are event or significance signals.

## Launcher and section-identity revalidation — 1 September 2026

- Current Omarchy's root menu `apps` provider consumes Quickshell `DesktopEntries.applications` through the shared AppLibrary. It carries desktop-entry image icons, keyword search, launch feedback, and the normal `gtk-launch` route, so one standard XDG desktop entry is the native app-launch integration rather than a custom Radar menu surface.
- Current third-party plugin add, enable, disable, update, and remove intentionally execute no repository hooks. Radar therefore cannot truthfully promise an automatic launcher cleanup from normal plugin removal. The chosen helper is explicit and receipt-backed; `make local-latest` may invoke it only because that command is already an intentional owner-run desktop mutation.
- On 1 September 2026 the live Pages feed was verified at `2026-09-01T07:51:46Z` with 91 events and fresh marketplace additions through `05:05:51Z`; all four sources reported current. The reported frozen-news behavior reproduced only on `make local-latest` installs: the digest-matched local marker returned before the fixed-origin fetch, a pre-publication safeguard that became a permanent pin after Pages went live. D029 replaces that early return with compare-before-replace behavior. The same owner review removed the unreliable manual-interest path (D028), required arrow-key/Enter pagination, and required a process-bound animated refresh affordance.
- Production `content/community/` remains empty. On 1 September 2026 the owner removed the always-empty dedicated Community section. The validated source/event contract remains part of the generic edition so a future accepted record can appear on Front Page or through local For You matching without restoring a dead tab.
- Owner review found configurable section names, icons, and backgrounds harmful because sections could become visually interchangeable and appear to lose editorial scope. State v9 validates and removes legacy profiles; canonical name, icon, order, background, and source scope remain fixed.

## Publication and activation incident revalidation — 1 September 2026

- The active GitHub publication workflow last received an automatic `schedule` event at `2026-09-01T13:31:59Z`; successful `workflow_dispatch` recoveries at approximately 14:45 and 16:01 UTC proved that source collection, validation, Pages artifact upload, and deployment remained functional when invoked. The deployed 16:01 edition included “Reolink Cameras joined the marketplace,” 272 events, 226 mirrored images, and four successful source states. The failed layer was schedule delivery, not collection or the static client architecture.
- GitHub's current Actions documentation says scheduled workflows can be delayed under high load, that some queued jobs may be dropped, and that the start of an hour is a high-load period to avoid. The minimum interval remains five minutes and schedules run only from the default branch. Radar therefore uses minutes 8, 23, 38, and 53 as four recovery opportunities, while explicitly treating them as best effort rather than guaranteed.
- GitHub's current Pages documentation says site changes may take up to ten minutes to publish. Production responses also expose ordinary cache headers and age, so the client and health monitor keep Pages propagation separate from source `checkedAt`, collection `generatedAt`, artifact `publishedAt`, and private cache modification time.
- Current Omarchy `shell/shell.qml` implements `toggle()` as hide whenever a panel's `opened` state is true, while `summon()` opens and focuses an existing panel. Radar's bar and managed shortcut used `toggle`, so invoking either while its normal window was behind another application followed the host's deliberate hide branch; this was not a duplicate input. The existing Apps entry already used `summon`. Version 0.1.4 makes all three routes summon and adds exact-address compositor focus after the panel becomes visible. No Omarchy source file was changed.
- The selected Omarchy contract remains branch `quattro` at `83881e979b35468c3e7d60b171e319ede61a88fd` with unrelated pre-existing shell changes left untouched. Plugin Lab doctor passed against base `omarchy-2026.08.27-x86_64-local`; version 0.1.4 acceptance records the final retained run separately.

## Activation upgrade-path revalidation — 2 September 2026

- The 0.1.4 source templates correctly use `summon`, but Omarchy's intentional no-hook plugin update contract leaves a previously installed 0.1.3 `bindings.lua` block unchanged. The 0.1.4 helper recognized only its new byte-exact block; the old marker pair therefore became `ambiguous`, so neither `install` nor `remove` could recover it. Fresh-install acceptance did not model that retained user configuration.
- Disposable Plugin Lab run `20260902-002207` constructed released 0.1.3 and 0.1.4 as consecutive local-origin commits. It reproduced both 0.1.3 close paths, proved the old QMP shortcut still closed Radar after a real 0.1.4 fast-forward, and independently proved that the updated 0.1.4 newspaper source and loaded runtime raised and retained the obscured window. The persistent installed-state defect was therefore the legacy shortcut, not duplicate pointer input or a new QML focus race.
- Version 0.1.5 retains the explicit no-hook contract. It recognizes only the exact legacy owned block, presents a user-activated migration inside Radar, and applies the normal backup/atomic reload/validation/rollback boundary. Candidate run `20260902-002806` drove that rendered action, then proved both the migrated live shortcut and the newspaper through real QMP input while another ordinary window held focus.

## Update-only activation repair revalidation — 2 September 2026

- A read-only host audit after the owner ran the normal update command found the exact released 0.1.5 commit and manifest installed, the current newspaper and desktop templates using `summon`, but the personal managed block and live `Super+Alt+N` action still using the exact 0.1.3 `toggle` form. The helper correctly reported `owned-legacy`; the defect was that the update path never invoked it.
- Current `omarchy-plugin-update` has no lifecycle hooks. After a successful fast-forward and validation it calls `omarchy-shell shell rescanPlugins`, which creates a fresh runtime generation for enabled entry points. Version 0.1.6 uses that supported rescan boundary to invoke a new narrow migration command from the bar generation.
- The command no-ops unless the existing security classifier returns `owned-legacy`. It cannot install a free chord and reuses the previously validated backup, atomic replacement, reload, live-action/config-error validation, and rollback implementation. The permanent lab journey now requires update-only repair before the panel is opened.

## Post-pagination viewport revalidation — 2 September 2026

- Released 0.1.6 used one generic projection completion path for context resets, finite pagination, edition refresh, installed-plugin discovery, and per-story read-state refresh. After **Load more** replaced 12 rows with 24, that path restored `storyViewportAnchorIndex`, which could still describe an older reading block even though `contentY` was at the former page end. The model therefore jumped upward instead of retaining the selected final row.
- Keyboard selection marks one story read asynchronously. Its completion requested another full local projection and could overlap the 140 ms viewport-edge animation. The generic restore stopped or repositioned that animation, explaining the reported rapid oscillation rather than a pointer, wheel, compositor, or network defect.
- Candidate 0.1.7 separates reset and preserve projection semantics, retains selection and the visual anchor by event ID, and uses a viewport revision to discard stale deferred positioning. Disposable Plugin Lab run `20260902-072227` passed the complete product journey. During pagination, 36 retained samples all reported selected index 11, anchor index 11, `contentY` exactly 919, and no scroll animation; the next Down fully top-aligned index 12, and the following Down selected index 13 while index 12 remained fully visible and top-aligned. The retained 44 screenshots and shell logs were reviewed, and the guest overlay was discarded.

## Reverse key-repeat viewport revalidation — 2 September 2026

- The 0.1.7 pagination candidate still gated its viewport-edge calculation to positive movement. Up changed `selectedIndex` without repositioning the ListView, so compositor key repeat could advance through rows above the clip while the visible viewport remained behind.
- Easing each upward edge crossing would retain the same race at repeat cadence: another selection can arrive before a 140 ms animation reaches its target. Radar now places an above-viewport previous row at `ListView.Beginning` before changing selection. Single Up presses inside the current viewport retain ordinary row-by-row behavior.
- Disposable Plugin Lab run `20260902-073851` held the physical Up key through QMP for 1.4 seconds. All 72 retained geometry samples reported a fully visible selection while it moved monotonically from index 13 to index 0; sampled row tops never fell below zero, no sample exceeded the 292-pixel viewport, and no scroll animation remained active. The exact 0.1.7 candidate passed the full journey with 45 reviewed screenshots, and the guest overlay was discarded.

## Publication freshness incident — 2 September 2026

- The public edition fetched at `2026-09-02T05:46:20Z` was recently built (`generatedAt 05:34:52Z`, `publishedAt 05:34:54Z`) and all four sources reported current, so client cache polling and scheduler availability were not the stale-content cause. GitHub recorded successful scheduled runs, including `33591988311` and `33590515232`, plus recovery run `33595230371`.
- The same public feed contained 413 events and stamped a large block of pre-existing marketplace version and verification differences at exactly `05:34:52Z`. The workflow checked out committed snapshot marketplace time `2026-09-01T18:26:02Z` on every run, collected against it, uploaded the next snapshot as an artifact, and never restored that artifact. Thus each scheduled run presented every still-different fact as newly discovered. Front Page separately selected the newest official release and then added three older Core releases through its source-quota loop.
- Snapshot schema v2 resets the contaminated discovery-only ledger while retaining 134 source-dated marketplace additions and five authoritative Omarchy releases from the current normalized sources observed at marketplace generation time `2026-09-02T05:44:58Z`. Scheduled publication now restores the exact artifact from the latest successful deployment with `actions: read`, and missing continuity fails the run. Local owner collection uses a private validated baseline committed only after full edition import. Rediscovery of an existing deterministic event ID cannot change its first `occurredAt` or `discoveredAt`.

## Marketplace and active-view revalidation — 2 September 2026

- The official catalog generated at `2026-09-02T06:27:42Z` contained 2,121 plugins. Radar's refreshed v2 transition snapshot knows all 2,121. The public edition generated at `06:22:33Z` already contained LocalSend, Lotus, and VNC++; GoalWatch arrived at `06:27:42Z` and is present in the refreshed candidate ledger.
- Radar's original v0.1.0 baseline knew 2,053 catalog IDs. All 68 IDs added between that baseline and the 2,121-ID candidate snapshot have retained `plugin-added` events; no new ID is absent from the event ledger. The roughly two thousand pre-baseline entries intentionally remain catalog facts rather than fabricated news under D012.
- Up from Load more redundantly reselected the already selected final row and invoked `ListView.Contain`, allowing Qt to snap the viewport at the focus boundary. Unread-only selection persisted the read state and immediately rebuilt the strict projection, which removed the active row. D042 removes the redundant focus-boundary positioning and adds bounded current-view retention for just-read IDs.
