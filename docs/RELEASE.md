# Release contract

Version `0.1.0` is the intended first public preview. Do not describe the project as released, installable, supported, or marketplace-available until the exact public candidate meets the relevant gates.

## Candidate identity

Record one clean Git commit and tag, manifest version, panel build identity, Python helper version, feed schema, generated artifact SHA-256, selected Omarchy source revision, and Plugin Lab ISO/base identity.

## Publishable checklist

### Product

- `Super+Alt+N` is re-audited as free, installed only after conflict checks, reversible, and accurately documented; the separate Editor shortcut remains intact.
- A documented IPC route keeps the panel reachable without the shortcut.
- Cached-first, refresh, offline, partial-source, invalid-feed, empty, and first-use states have visible recovery.
- Front Page, For You, Core, Plugins, Community, and Saved match the implemented model.
- Every story exposes an original validated HTTPS source.
- The default-on newspaper indicator, zero-gap hiding, Tune re-enable, unread/health states, and no-notification boundary match the implementation.
- No account, telemetry, AI summary, plugin installation action, or unsupported scraper is implied.

### Data and publication

- First marketplace bootstrap emits at most twelve listings from the prior fourteen days and no historical flood.
- Source adapters are bounded, allowlisted, deterministic, and fixture-tested.
- Source failure preserves prior state and cannot create mass retirement.
- JSON, RSS, HTML, archive, and snapshot validate and are byte-stable under a fixed clock.
- Generated HTML/XML escapes hostile content and the site uses a restrictive static security policy.
- Live feed size, event count, archive policy, and source-health metadata match the documented contract.
- Mirrored previews are allowlisted, byte/dimension validated, content-addressed, same-origin, and optional on failure; the public feed never carries upstream image URLs.

### Runtime and safety

- Manifest and every declared entry point validate.
- Remote text remains plain data, image decoding is limited to validated same-origin rasters, and source opening is explicit.
- Cache/state writes are private, bounded, symlink-safe, atomic, and recoverable.
- One refresh process maximum per entry point plus a cross-instance lock; the panel tears down on close and bar refresh polling stops when hidden.
- Shortcut install/remove preserves unrelated Lua exactly and rolls back on reload or config error.
- Disable and removal preserve user state; explicit purge removes only validated Radar-owned paths.
- No runtime package installation, privilege escalation, arbitrary command, or background daemon exists.
- The unpublished local path identifies itself as a local live edition, revalidates imported feed/images, never presents fixtures as current news, and migrates only the exact old panel-only placement.

### Visual and accessibility

- Current Omarchy tokens drive color, spacing, typography, borders, focus, and monitor fit.
- Light/dark, narrow/wide, long text, empty/dense, cached/refreshing/offline/invalid/partial, and 200% text states are reviewed.
- Visual columns preserve one semantic keyboard order.
- Keyboard-only traversal, focus visibility, labels, counts, source health, and reduced motion pass.
- Assistive-technology claims do not exceed actual evidence.

### Evidence and distribution

- `make test`, `make validate`, `make feed-fixture`, and `make site` pass from a clean clone without unapproved downloads; `make collect-live` separately proves the allowlisted live build.
- Plugin Lab acceptance passes for the exact candidate with inspected logs and screenshots.
- Public clean-clone installation, shortcut setup/removal, update, and plugin removal pass once the remote exists.
- Workflow actions are pinned and permissions are least privilege.
- README, changelog, manifest, UI version, feed schema, screenshots, release notes, and evidence agree.
- Repository contains no secrets, private state, real bindings, caches, VM disks, lab output, generated deployment tree, or machine-local paths.
- No push, tag, GitHub Pages enablement, release, marketplace submission, domain change, or external announcement occurs without owner authorization.

## Removal contract

Document removal in this order:

1. Run the shortcut helper’s `remove` command while the plugin checkout still exists.
2. Remove the plugin through `omarchy plugin remove io.github.mtolhuys.news-radar`.
3. Optionally run the explicit purge command before removal when the user wants local cache, seen state, and saved items deleted.

Normal plugin removal does not delete local state. Removing the plugin before its binding leaves a harmless unresolved shell IPC binding that the user must remove manually from its clearly marked block.

## Owner-authorized publication procedure

These steps are deliberately external and remain pending until the owner authorizes them:

1. Create the intended public repository at `https://github.com/mtolhuys/omarchy-news-radar`, push the reviewed clean candidate commit, and configure Pages to use GitHub Actions. Do not create a release or marketplace entry yet.
2. Run the `Build and publish static edition` workflow manually with `bootstrap_marketplace` enabled only if the committed snapshot is empty. Confirm the published JSON, RSS, HTML, mirrored images, archive, build digest, and source-health metadata at the fixed Pages origin. The hourly minute-17 schedule can run after this proof.
3. Download the workflow's `source-snapshot` artifact, replace `state/source-snapshot.json` with that exact reviewed file, run all four local source gates, commit it, and push it before running publication again. For every later publication, leave bootstrap disabled and repeat this snapshot-review commit step so the repository remains the explicit source baseline.
4. In the disposable Plugin Lab, run `OMARCHY_NEWS_RADAR_PUBLIC_URL=https://github.com/mtolhuys/omarchy-news-radar OMARCHY_NEWS_RADAR_EXPECTED_COMMIT=<40-character-commit> ./bin/lab plugin tests/lab/public-install.sh`. Inspect the retained log and screenshot evidence and confirm the public clone resolved the exact intended commit.
5. Review the release checklist and evidence record against that exact commit. Only then, with separate owner authorization, create the `v0.1.0` tag and release and submit the repository to the Omarchy marketplace.

The workflow intentionally has no repository write permission. Snapshot advancement is a human-reviewed source change, not hidden CI state.

## Evidence record template

```text
Release:
Commit / tag:
Manifest / panel / helper identity:
Feed schema:
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
