# Release contract

Version `0.5.1` is the current release. It preserves the 0.5 data, identity, lifecycle, and safety contracts while completing keyboard navigation, improving setup fallbacks, and making caught-up briefing refresh explicit. Feed schema remains v2; insights remain v1; private state remains v13 with supported v1–v12 data preserved. See the [release notes](release-notes/0.5.1.md).

The README walkthrough and root marketplace preview use inspected captures from the final disposable runtime. The maintainer-controlled marketplace snapshot and exact-commit compatibility evidence remain separate from release publication; marketplace verification is not a security audit.

## Release identity

Record the working-tree status, manifest version, panel build identity, Python helper version, feed and state schemas, generated artifact SHA-256, selected Omarchy source revision, Plugin Lab ISO/base identity, exact public commit, and release tag.

The manifest, Python package, helper build, panel, changelog, and release notes identify `0.5.1`. The [0.5.1 evidence](evidence/0.5.1-local.md) records its keyboard, persistent-briefing, daily-desktop, multi-window, and disposable-desktop checks. The earlier [briefing-only](evidence/0.5.0-local.md) and [expanded 0.5](evidence/0.5.0-expanded-local.md) records remain historical.

## Publishable checklist

### Product

- `Super+Alt+N` is re-audited as free, installed only after conflict checks, reversible, and accurately documented; the separate Editor shortcut remains intact.
- An exact unmodified 0.1.3 Radar-owned block is reported as `owned-legacy`, automatically backed up and atomically replaced with `summon` by the generation loaded through a normal update rescan, and rolled back on validation failure; all free, current, edited, personal, conflicting, multiple, symlinked, or ambiguous cases remain unchanged, and the visible migration action remains a retry.
- A documented IPC route keeps the panel reachable without the shortcut.
- The explicit XDG launcher helper adds one searchable Apps-menu row with the newspaper icon, refuses modified/unrelated targets, and removes only receipt-matching files.
- Cached-first, refresh, offline, partial-source, invalid-feed, empty, and first-use states have visible recovery.
- Front Page combines a persisted brief of at most five groups with reviewed workflows, setup updates and project discoveries. Explicit **New briefing** replaces only the brief; refresh, reopening, and later arrivals never refill it. For You offers My setup and its news projection; Core, Plugins, YouTube, and Saved retain their source projections and finite local pagination. Reviewed community records remain an optional input rather than an empty dedicated section.
- The panel is a normal movable/resizable/maximizable window, participates in `Alt+Tab`, omits the unreliable minimize control, and closes through one shell lifecycle.
- `Tab`/`Shift+Tab` cycles sections during normal navigation. `F6` enters/leaves Home, My setup, or briefing controls; Tab traverses their available cards and actions, and expanded group history supports Up/Down/Home/End/Enter. Canonical sections, fixed-source disclosure, independent filters, exact resets, and arrow-key/Enter finite Load more in the other sections match the local projection model.
- No publication-diagnostics strip occupies the reading surface; a subtle collapsible **Keys** footer at the bottom of the **SECTIONS** rail starts fully collapsed as `Keys · ?` with no shortcut dump and remembers the session choice; search exposes `/` and **Check for updates** exposes `R` on hover. Wide Core and Front Page article index cards are quiet headlines; the selected compact row exposes its full body. The wide inspector puts `date · source`, the full article body, and compact actions before a collapsed Details footer.
- Section headers expose an **All** / **Unread only** chip and keyboard `f` using the persistent filter; Settings stays in sync. Keyboard `a` matches **Mark briefing read** on Front Page and the filtered **Mark all as read** action elsewhere. The Keys footer describes the applicable controls.
- Bar click, `Super+Alt+N`, and Apps launch all summon one window; closed, obscured, foreground, rapid-repeat, Alt+Tab, explicit close, and reopen states are machine-asserted with real QMP input.
- Available metrics have exact icon meanings, accessible labels, observation times, and marketplace caveats; raw metric endpoint links are absent, human plugin pages are used where applicable, and metrics cannot influence event creation or ranking.
- Every story exposes an original validated HTTPS source.
- Every story has an explicit read state: dense rows label `UNREAD` or `READ`, and quiet headlines use an unread mark. Group counts include all unread member events; ordinary selection reads only the representative. **Mark group read** and **Mark briefing read** affect only their persisted exact members, including members hidden by a temporary search or filter. New arrivals remain unread, and expired members are disclosed rather than represented as completed reads.
- A fresh source-reader open after onboarding reads exactly its first visible selection once; Home, My setup and insight details do not read hidden stories. Deliberate story selection and `u` affect only one event, and repeated summon/refresh/reprojection never mark another. The welcome screen and **Browse current stories** do not read anything. **Start from today** is an explicit explained backlog action that preserves saves and local choices.
- Section and newspaper counts use the same exact per-event predicate. The newspaper deduplicates unread IDs across the current persistent section projections and never advertises events hidden by every section. The explicit filtered-section read action includes unloaded matches, while close/refresh never bulk-mark. The newspaper adopts unread arrivals with the panel closed, uses the five-minute cadence, and retains zero-gap hiding, Tune re-enable, refresh progress, health states, and no desktop pop-ups.
- For You uses exact locally enabled IDs and explicit local follow choices; installed reasons retain their exact enabled-ID meaning. Local follow/mute choices have visible controls, a CLI route and state-v13 arrays. Legacy manual interests and section profiles remain removed. State v1–v12 migrates to v13 without losing supported read overrides, read-through time, saves, filters, or visibility; pre-v12 states skip the welcome choice, and v12 preserves its existing choice and briefing. Hidden source rails leave the nav and newspaper union; Front Page, For You, and Saved stay reachable.
- YouTube collection on Forge requires optional `YOUTUBE_API_KEY`; CI remains fixture-only and never calls the live API.
- No account, telemetry, AI summary, plugin installation action, or unsupported scraper is implied.

### Data and publication

- First marketplace bootstrap emits at most twelve listings from the prior fourteen days and no historical flood.
- Source adapters are bounded, allowlisted, deterministic, and fixture-tested. HTTP readers accept gzip with independent wire and decompressed limits, reject unsupported/corrupt/truncated encodings, preserve deadline and redirect restrictions, and keep the valid cache and validators on failed responses.
- Every plugin-event summary uses the current validated marketplace description when available; description changes enrich existing events without creating or reordering them.
- Source failure preserves prior state and cannot create mass retirement.
- Forge Laravel `news-radar:publish` is scheduled every five minutes without overlapping; live feed is `https://mtolhuijs.nl/news-radar/events.json`. GitHub Actions publication and Pages are retired.
- Every publish restores continuity state from Laravel storage (tracked transition seed only on first run); missing or invalid continuity fails closed, event first-observation timestamps are immutable, and the tracked v2 transition seed is accepted only while fresh.
- A new local brief considers unread events matching Front Page filters: critical notices, reviewed notable stories, the newest official release, official news, enabled-plugin activity, and a discovery when available. Same-plugin events share a group with each original source retained. Routine verification changes alone never consume a slot; metrics never rank candidates. The static web edition retains its existing editorial projection.
- Feed metadata and internal client state separately identify source check, collection, artifact publication, and local cache time. Normal successful reading exposes none of that pipeline telemetry as content.
- JSON, RSS, HTML, archive, and snapshot validate and are byte-stable under a fixed clock.
- Generated HTML/XML escapes hostile content and the site uses a restrictive static security policy. The web edition has an official marketplace install link, discoverable RSS, a keyboard skip link, fixed-origin canonical metadata, and escaped social SVGs under the bounded `assets/share/` path family, without scripts or tracking.
- Live feed size, event count, archive policy, and source-health metadata match the documented contract.
- Marketplace previews are restricted to the exact allowlisted `plugins.omarchy.org` path family, byte/dimension validated before publication, and retained as direct `image.sourceUrl` values; YouTube thumbnails use only the fixed `i.ytimg.com/vi/<id>/hqdefault.jpg` shape. Images remain optional on failure and are not mirrored onto the feed host.

### Runtime and safety

- Manifest and every declared entry point validate.
- Remote text remains plain data, image decoding is limited to the two validated allowlisted HTTPS image families (plus validated legacy same-origin rasters from older caches), and source opening is explicit.
- Cache/state writes are private, bounded, symlink-safe, atomic, recoverable, and serialized across panel/bar helper processes. Brief and group mutations validate the exact persisted snapshot; the first-use **Start from today** choice validates the displayed event membership under the same lock used to save feeds, rejects changed editions, and preserves explicit unread choices.
- Application launcher/icon writes are bounded, receipt-backed, symlink-safe, atomic, reversible, and never overwrite user-modified or unrelated files.
- One refresh process maximum per entry point plus a cross-instance lock; the panel tears down on close and bar refresh polling stops when hidden.
- Shortcut install/migrate/remove preserves unrelated Lua exactly and rolls back on reload or config error; the automatic update command cannot install a free chord.
- Disable and removal preserve user state; explicit purge removes only validated Radar-owned paths.
- No runtime package installation, privilege escalation, arbitrary command, or background daemon exists.
- The local path revalidates imported feed/images, advances its private source state only after complete import, never presents fixtures or rediscovered old diffs as current news, refuses a published downgrade, adopts a newer published edition on refresh, and migrates only the exact old panel-only placement. Its origin remains internal rather than persistent reader copy.

### Visual and accessibility

These are acceptance requirements; completed checks and remaining limitations belong in the exact-candidate evidence record.

- Current Omarchy tokens must drive color, spacing, typography, borders, focus, and monitor fit. Selected and unselected text, status, summaries, metadata and counts must remain distinguishable in maintained dark and light themes.
- Front Page must open its Home overview of the retained briefing, workflows, setup updates and discoveries. For You must offer My setup and its separate news view. Neither overview may show a hidden story's inspector or mark that story read.
- Wide source readers must show a compact story index and an inspector only when a story is selected. The article inspector must prioritize the full title, `date · source`, complete body and primary actions before collapsed Details. An empty reader must omit the inspector, its divider and per-story actions, and offer an explanation with a useful recovery action.
- Compact and large-text readers must expand the selected row's full title, date/source and complete body while other rows remain quiet headlines. Both layouts must share the escaped article-body renderer and validated HTTPS link path. The compact action toolbar must scroll with the content, leaving the body and read/save/source controls reachable; font or monitor changes must preserve fitting geometry and refit an overflowing floating window without taking focus.
- Normal `Tab`/`Shift+Tab` must cycle sections; `F6` must enter or leave the available Home, My setup and briefing controls, where Tab traverses cards/actions and group history supports its documented navigation. Arrow keys and `j`/`k` select cards or stories; Enter/`o` opens a card or original source; `u` and `s` operate on one selected story; Page Up/Down scrolls without changing selection, reads or saves. Empty selections must make story actions inert.
- Verify visible focus, labels, counts, source health and reduced motion, plus light/dark, narrow/wide, long-body, empty/dense, cached/refreshing/offline/invalid/partial and 200% text states. Inline body links currently use pointer activation; their dedicated original-source action remains keyboard-accessible. Do not claim keyboard traversal of individual inline links or assistive-technology support beyond the actual evidence.

### Evidence and distribution

- `make test`, `make validate`, `make feed-fixture`, and `make site` pass from a clean clone without unapproved downloads; `make collect-live` separately proves the allowlisted live build.
- Plugin Lab fresh-install, dedicated briefing, and released-0.1.3 upgrade acceptance pass for the exact candidate with inspected logs and screenshots. The briefing journey covers both welcome choices, per-event versus group read scope, explicit completion, reopen/arrival stability, offline operation, keyboard focus, and maintained light/dark layouts.
- The networked Plugin Lab preview journey renders the fixed public edition in the exact Matte Black marketing frame; the README crop matches its recorded window geometry.
- Public clean-clone installation, first-use Front Page, shortcut setup/removal, read state, and plugin removal pass for the exact remotely available 0.5.1 commit through the state-v13 journey.
- Workflow actions are pinned and permissions are least privilege.
- README, changelog, manifest, UI version, feed/state schemas, screenshots, release notes, and evidence agree on 0.5.1. Release media comes from inspected final-runtime VM captures.
- Repository contains no secrets, private state, real bindings, caches, VM disks, lab output, generated deployment tree, or machine-local paths.
- Push, tag, release, marketplace submission, domain change, and external announcement require owner authorization. GitHub Pages is not the live publication path.

## Removal contract

Document removal in this order:

1. Run the shortcut helper's `remove` command while the plugin checkout still exists.
2. Run the launcher helper's `remove` command while the plugin checkout still exists.
3. Remove the plugin through `omarchy plugin remove io.github.mtolhuys.news-radar`.
4. Optionally run the explicit purge command before removal when the user wants local cache, reading state, and saved items deleted.

Normal plugin removal does not delete local state or run repository cleanup hooks. Removing the plugin before its binding leaves a harmless unresolved shell IPC binding; removing it before launcher cleanup leaves a stale XDG row. Reinstall the exact checkout to run the corresponding helper, or remove only the documented owned files after verifying them manually.

## Owner-authorized publication procedure

Live publication is owned by Forge Laravel on the maintainer host. GitHub Actions `publication.yml` and GitHub Pages are retired as the publication path. The feed clients fetch is always `https://mtolhuijs.nl/news-radar/events.json`.

1. Push the reviewed clean candidate commit to the existing public repository at `https://github.com/mtolhuys/omarchy-news-radar`. Ensure Forge's `NEWS_RADAR_PATH` checkout can fast-forward or pull that commit before the next publish. Do not create the release or update the marketplace snapshot yet.
2. Confirm Laravel schedule lists only `news-radar:publish` (every five minutes, without overlapping). Optionally run `php artisan news-radar:publish -v` once on the Forge host and verify the public JSON, RSS, HTML, allowlisted image references, build digest, source health, collection time, and `publishedAt` at `https://mtolhuijs.nl/news-radar/`.
3. Wait for at least one successful scheduled Forge publish after the candidate is on the host checkout. Confirm continuity advanced in Laravel storage (no replay of the committed baseline as fresh news) and that public `publishedAt` matches the deployed build.
4. Advance the published-install scenario from its retained 0.4.16 contract to the reviewed candidate identity, schema, and welcome journey. In the disposable Plugin Lab, run `OMARCHY_NEWS_RADAR_PUBLIC_URL=https://github.com/mtolhuys/omarchy-news-radar OMARCHY_NEWS_RADAR_EXPECTED_COMMIT=<40-character-commit> ./bin/lab plugin tests/lab/public-install.sh`. Inspect the retained log and screenshot evidence and confirm the public clone resolved the exact intended commit.
5. Review the release checklist and evidence record against that exact commit. Only then create the release tag.
6. Use the marketplace's **Plugin verification** form with **Verify and publish a newer upstream commit**, the exact plugin ID, repository root URL, and full 40-character release SHA. The existing snapshot remains live while compatibility validation, the Automated Security Baseline, maintainer approval, testing, and deployment remain maintainer-controlled. Do not represent issue creation as promotion or as a security audit.

Normal snapshot advancement is a validated handoff in Laravel storage between successful Forge publishes. The tracked repository snapshot is only a reviewed transition/recovery seed; using it again requires a new explicit schema transition and fresh source audit rather than a silent fallback. If publication age exceeds 90 minutes, a source check lags publication materially, or continuity restoration fails, recover by inspecting the prior storage snapshot and restoring that chain before the next publish. Never bypass continuity by replaying an old repository snapshot.

## Evidence record template

```text
Release:
Commit / tag:
Manifest / panel / helper identity:
Feed / state schemas:
Local candidate or published status:
Artifact SHA-256:
Omarchy revision / ISO / lab base:

Commands:
- source:
- generation:
- lifecycle:
- product scenario:
- public install:

Timestamped evidence directories:
-

Machine assertions:
-

Visual review:
-

Performance measurements:
-

Deliberate limitations / unverified boundaries:
-
```

## 0.5.1 release gate

The [0.5.1 evidence](evidence/0.5.1-local.md) establishes the exact runtime source and complete disposable acceptance before publication. The remaining public-clone, Forge, tag, release, and marketplace gates must bind to the final remote commit in that order.

The Laravel application is a separate deployment unit. Validate real producer artifacts through its strict staging policy, verify retained links across changing editions and exercise interruption recovery before deployment. Confirm gzip, Vary, ETag, HEAD, 304, content type, cache policy and encoded-byte accounting on production application responses. Old clients continue using unchanged events.json.

## 0.5.2 release gate

The owner tested the installed candidate and approved publication. The [0.5.2 evidence](evidence/0.5.2-local.md) records source checks and focused disposable-guest acceptance. Publish the exact clean release commit only after CI, feed health, and its public-clone journey pass. Update the existing verification entry once with that full SHA; do not create another request. Marketplace approval and snapshot promotion remain maintainer-controlled.

## Automatic discovery candidate

The owner inspected the installed 0.5.3 candidate and approved publication on 2026-09-06. The [evidence](evidence/0.5.3-local.md) records the exact runtime and retained discovery checks. Publish the release preparation commit, verify its CI and public-clone journey, and fast-forward the producer while preserving its live continuity snapshot. Update the existing marketplace request and owner context in place; do not add an issue or comment. Maintainer approval remains separate.
