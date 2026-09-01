# Security model

Omarchy News Radar ingests public remote metadata and renders it inside a long-running desktop shell. Its main security job is to ensure that remote text remains inert data, network failure cannot destroy good local state, and optional shortcut setup cannot damage user configuration.

## Trust boundaries

- GitHub API responses, marketplace catalogs, marketplace engagement aggregates, preview rasters, release notes, repository metadata, community records, generated feeds, titles, summaries, counters, tags, author names, and URLs are untrusted.
- The published feed is owned by this project but remains untrusted at the client boundary because hosting, transport endpoints, build pipelines, or stored artifacts can fail.
- Installed plugin IDs and local reading state are private local data.
- `~/.config/hypr/bindings.lua` is user-owned configuration and may contain arbitrary valid Lua, comments, custom formatting, or symlinks.
- The Omarchy shell is an unsandboxed user process. Radar must keep remote content away from code, QML source, shell evaluation, rich text, and file paths.

## Remote-content invariants

- Render remote strings as plain text only. Do not interpret HTML, Markdown, SVG, upstream image URLs, ANSI escapes, QML, JavaScript, terminal sequences, or link markup.
- Render optional images only from validated content-addressed paths in the feed's fixed origin. The publisher accepts only bounded static PNG/JPEG/WebP from the exact marketplace image origin, verifies Content-Type/magic/structure/dimensions, rejects SVG and animation, and omits failures.
- Enforce feed size, event count, string length, tag count, URL length, nesting, and timestamp bounds before a candidate reaches QML.
- Accept source links only when they parse as public HTTPS URLs without credentials or control characters.
- Opening a source requires an explicit user action and passes the validated URL as one structural process argument to the maintained desktop launcher and `xdg-open`.
- The collector fetches only allowlisted machine sources. It does not fetch arbitrary community or event source URLs and cannot be turned into an SSRF client.
- Feed content cannot request another fetch, change settings, install code, run a command, alter ranking rules, or grant permission.
- Metric values are inert bounded integers with fixed labels, timestamps, and HTTPS provenance URLs. They cannot create events or drive ranking. The QML projection strips raw metric URLs, renders only icon/value/accessible-label facts plus the marketplace caveat, and constructs human plugin pages from the fixed marketplace route and validated entity ID.
- Section names, icons, order, backgrounds, and source membership are code-owned canonical identities. Local settings contain only strict filter enums/booleans and cannot introduce text, markup, colors, URLs, scope changes, or network requests.

## Client fetch

The production feed origin is fixed in one module. Collector machine inputs are likewise fixed to the GitHub release API, marketplace catalog, and `https://api.omarchyplugins.com/v1/stats`. Normal UI settings do not accept arbitrary feed, image, or metric URLs. The helper:

- uses HTTPS with certificate verification;
- uses explicit connect and total timeouts;
- constrains redirects to the expected production origin family;
- sends no cookies, authorization, installed-plugin IDs, saved IDs, read timestamps, machine identifiers, or custom tracking values;
- streams into a bounded temporary file and aborts before exceeding 2 MiB;
- validates the complete candidate before same-directory atomic replacement;
- preserves the last-known-good cache on every failure.

Tests may inject a fixture file or loopback endpoint through an explicit test boundary unavailable to ordinary production calls.

## Local files

Cache and state directories are private to the current user. Create files with restrictive permissions, refuse symlink targets, validate ownership where practical, write through a same-directory temporary file, flush, and atomically rename. The bounded `update-check.json` cache record contains only a schema version, UTC attempt timestamp, and `success`/`failed` outcome; malformed or materially future metadata is ignored so it can never postpone a check.

The state parser accepts only its own bounded schema. Per-story read overrides are keyed only by validated event IDs, capped at the feed bound, and never transmitted. A corrupt state file is renamed to a bounded quarantine name and replaced by safe defaults. Never include full feed bodies, source responses, environment dumps, usernames, hostnames, tokens, or private paths in diagnostics.

Section filters are validated local state. They select only from closed enums and booleans, never become query parameters, and never alter collector or feed requests. Load more changes only a bounded local projection limit.

Saved items and cache are preserved on plugin disable or normal removal. A separate explicit purge action may remove only paths owned by Radar after resolving and validating their exact XDG locations.

The optional application launcher uses one fixed desktop-entry name and one fixed icon name under `XDG_DATA_HOME`. Installation records the exact target paths and SHA-256 digests in a private receipt, writes the icon before the desktop entry through same-directory atomic replacements, and refuses symlinked, unowned, modified, ambiguous, or unrelated targets. Removal deletes only files that still match the receipt and preserves any user-modified target. The helper is explicit because Omarchy's third-party plugin lifecycle does not execute install or removal hooks.

## Process execution

QML launches only fixed bundled helpers and maintained Omarchy desktop commands. Arguments are arrays, never interpolated shell strings. Remote values never choose an executable, flag name, environment variable, output path, or shell fragment.

At most one refresh helper belongs to one panel or bar instance, and a kernel-backed advisory lock on a private, owned regular file rejects cross-monitor overlap. A separate private lock serializes every state read/modify/write transition across panel and bar helpers, preventing a concurrent read toggle, save, filter, or visibility change from overwriting another mutation. The kernel releases both locks if a helper exits abruptly. The bar uses `refresh-if-due` only while its local visibility preference is true: a successful attempt schedules 15 minutes later and a failed attempt schedules a five-minute retry. Hiding it stops that cadence. Helpers refuse UID `0` and never use sudo, polkit, a package manager, or systemd.

## Local checkout synchronization

`make local-latest` is an explicit owner action, not an automatic updater. It validates a clean source checkout and then uses Omarchy's Git-managed plugin lifecycle to install or fast-forward only an installation whose local origin resolves to that exact checkout. It refuses dirty source or installed trees, symlinks, non-Git installs, missing origins, public origins, different local origins, or a modified/unrelated application launcher target. It never pulls or rewrites the source branch, repoints an installation, installs the optional shortcut, enables a deliberately disabled modern installation, or creates a background process. It does install or update the exact receipt-backed Apps-menu entry because the owner explicitly invoked the local desktop synchronization command.

The same command collects one edition into a private temporary directory using only the ordinary allowlisted publisher sources. Import requires canonical validated feed bytes, exact build digest and source revision, and complete byte/format/dimension/hash validation for every referenced raster before the cached feed changes. The one-time panel-only preview migration acts only on one exact unmodified owned `plugins[]` entry with no bar entry; it uses Omarchy disable/enable commands, restores the newly introduced bar/image defaults once, and refuses custom, duplicate, or ambiguous placement.

## Shortcut installer

Global shortcut setup is an explicit user action and is not run by plugin installation, enablement, panel opening, refresh, or update.

`news-radar-shortcut install` must:

1. Refuse UID `0`.
2. Resolve the expected user config path without following a symlink; if the file is symlinked or unusually owned, stop and provide the manual binding line.
3. Query the live binding table through `hyprctl binds -j` and detect `Super+Alt+N` semantically, not by fragile source grep alone.
4. Inspect the user's personal override file. Classify the chord as `free`, `owned`, `personal-conflict`, or `ambiguous`; fail closed when classification is uncertain.
5. Mutate only when the chord is `free`; refuse personal, unknown, multiple, or ambiguous bindings without an override or force path.
6. Be idempotent when its exact managed binding already exists.
7. Add one clearly delimited managed block containing only Radar's `o.bind("SUPER + ALT + N", ...)` statement without reformatting any other byte of the file.
8. Create a private timestamped backup before change.
9. Write atomically.
10. Run `hyprctl reload`, then require empty `hyprctl configerrors` and exactly one live Radar action for the chord.
11. Restore the backup and reload again when validation fails.
12. Report the exact changed file, binding, backup, and recovery result.

`status` is read-only. `remove` deletes only an exact unmodified managed block, uses the same backup/atomic/reload/rollback process, refuses ambiguous or user-edited blocks, and verifies that `Super+Alt+N` is free again. It also leaves the separate `Super+Shift+N` Editor action untouched. Removing the plugin before removing the binding leaves a harmless unresolved IPC action; public removal instructions must tell users to remove the shortcut first.

Never expose a force-overwrite or action-replacement flag in version 1. Users with any conflict receive manual guidance for choosing and configuring a different free key.

## Static site

Publisher output contextually escapes all strings. Generated HTML contains no raw remote HTML and no inline event handlers. Use a restrictive Content Security Policy, local static assets, safe `rel` attributes for external links, no forms, no analytics, no third-party script, and no service worker.

RSS/XML generation escapes every remote value and uses canonical HTTPS links. XML parsers used in tests must disable external entity resolution where relevant.

## Privacy

The feed host receives ordinary generic feed and same-origin image GET requests and therefore sees network metadata inherent to HTTPS hosting, such as source IP and user agent. Radar adds no identifier or personalization. Local installed-plugin matching, filters, saves, and per-story reading state never leave the machine.

The project must not claim perfect anonymity, sandboxing, or security auditing.

## Supply chain

- Runtime uses the current Omarchy/Arch environment and Python standard library only.
- GitHub Actions are pinned to immutable commit SHAs before public release.
- Workflow permissions are least privilege: read source by default and grant Pages/deployment permission only to the publish job.
- Production publication runs only after source tests and artifact validation.
- Generated artifacts record source revision and a SHA-256 digest; clients do not treat a digest from the same origin as an independent signature.
- No remote code, package, or font is downloaded. The publication build downloads only allowlisted marketplace preview rasters under the strict mirroring policy; runtime downloads only the project feed and its same-origin content-addressed raster assets.

## Vulnerability reporting

Before public release, add a root `SECURITY.md` with private reporting instructions. Reports must not include real user binding files, tokens, browsing data, private plugins, or host diagnostics in public issues.
