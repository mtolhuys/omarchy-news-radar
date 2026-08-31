# Architecture and product decisions

## D001 — Use the product and repository name Omarchy News Radar

**Decision:** The repository is `omarchy-news-radar`, the user-facing product is “Omarchy News Radar,” and the plugin ID is `io.github.mtolhuys.news-radar`.

**Why:** “News Radar” communicates monitoring and relevance rather than a full editorial publication, while distinguishing the project from existing flight and weather radar plugins.

**Consequence:** Use one name consistently in manifest, UI, generated site, feeds, documentation, and release artifacts. Include an independent-community disclaimer until official status is explicitly granted.

## D002 — Make `Super+Alt+N` the recommended primary interaction

**Decision:** Offer `Super+Alt+N` as an explicit opt-in global shortcut only while the personal configuration and live binding table prove that it is free.

**Why:** It remains memorable and quick without competing with Omarchy's `Super+Shift+N` Editor/Neovim action. The selected Omarchy source and disposable live audit currently leave the new chord unused.

**Consequence:** Re-audit before release because defaults can change. `status` is read-only, `install` succeeds only for a free chord, every conflict is refused, and no force or action-replacement path exists.

## D003 — Manage the shortcut explicitly, never through hidden installation side effects

**Decision:** Ship a dedicated `install`, `status`, and `remove` helper that owns one delimited Radar binding block in the user’s `bindings.lua`.

**Why:** The current third-party manifest has no declarative global-shortcut contract, and normal plugin installation intentionally does not execute install hooks. User configuration deserves explicit consent and reversible mutation.

**Consequence:** Public installation has a separate shortcut step. The managed block contains no `hl.unbind`; deleting the exact block releases only Radar's chord. Plugin removal instructions remove the block first. Symlinked, personal, modified, conflicting, ambiguous, or invalid configuration is refused and falls back to documented manual guidance.

## D004 — Ship an on-demand panel without a daemon

**Decision:** Version 1 omits `keepLoaded` and installs no service or daemon. The panel remains on-demand; the approved bar widget uses only the existing shell lifecycle.

**Why:** Cached-first loading provides speed without another singleton or system service. The visible status indicator needs a bounded due-checked timer, which can live in the bar widget already hosted by Omarchy.

**Consequence:** Durable state lives in XDG files, every panel open restores it, and every panel close terminates panel-owned work. A visible newspaper checks locally every 30 seconds and requests a refresh only when at least 30 minutes old; hiding it stops refresh polling.

## D005 — Pair the panel with an optional default-on bar newspaper

**Decision:** The main manifest declares one non-multiple `bar-widget` in the right section. It is visible by default, opens the panel on left click, refreshes on middle click, and hides on right click. Tune Your Radar restores it.

**Why:** The owner explicitly chose a small visual news-status affordance. Current Omarchy `ModuleSlot` sizing maps an invisible widget to exact zero geometry, and XDG state plus a file watch gives the panel and widget one reversible preference without a phantom slot.

**Consequence:** The earlier separate-companion boundary is superseded. Acceptance must prove default placement, orientation, unread/health states, left/middle/right pointer behavior, zero-gap hiding, panel re-enable, and no refresh cadence while hidden.

## D006 — Own a versioned static feed

**Decision:** A repository-controlled collector publishes bounded JSON, RSS, and static HTML through GitHub Pages.

**Why:** The product must work independently without write access to Omarchy core, the marketplace, or a newsletter. A static feed is cheap, inspectable, cacheable, and reusable.

**Consequence:** There is no application server, database, account system, or write API. Hosting migration changes configuration, not the feed contract.

## D007 — Use official releases, marketplace catalog diffs, and reviewed records only

**Decision:** Version 1 does not scrape social media, arbitrary websites, commits, discussions, or repository activity.

**Why:** Stable machine contracts support deterministic facts. Broad scraping adds noise, breakage, moderation load, copyright risk, and weak provenance.

**Consequence:** Community discovery enters through reviewed repository files. Missing social content is an explicit scope tradeoff, not an adapter bug.

## D008 — Separate automated activity from reviewed significance

**Decision:** Source adapters prove events; reviewed curation assigns `notable` or `critical` status.

**Why:** Recency, stars, views, and metadata churn do not establish importance.

**Consequence:** Front-page ordering is auditable, and routine events remain available without being marketed as recommendations.

## D009 — Use deterministic summaries, not AI prose

**Decision:** Generate factual summaries from structured fields or reviewed community text. Do not call an LLM in collection, CI, publication, or client runtime.

**Why:** The product’s value is trust and reduction of noise. Generated prose would add cost, nondeterminism, attribution questions, and another prompt-injection boundary.

**Consequence:** Summaries may be less literary but remain reproducible and source-linked. A future editorial workflow requires a new decision.

## D010 — Keep personalization local

**Decision:** Installed-plugin matching, up to twelve explicit interests, seen state, saves, filters, and preferences stay on the device.

**Why:** Server personalization is unnecessary for a generic public feed and would create accounts, identifiers, storage, and trust obligations.

**Consequence:** The server cannot provide cross-device sync or global unread counts. The plugin sends the same generic feed request for every user.

## D011 — Use Python standard library plus native QML

**Decision:** Python owns deterministic data logic and QML owns native presentation. No third-party runtime dependency is approved.

**Why:** Current Omarchy already ships Python and the plugin shell. This keeps installation offline, reviewable, and small.

**Consequence:** Implement small focused utilities rather than importing web, feed, HTTP, schema, or UI frameworks. Any exception needs a recorded review.

## D012 — Establish a baseline with a bounded recent backfill

**Decision:** The first successful marketplace collection records the complete state and may emit only the twelve newest listings with valid timestamps inside the prior fourteen days.

**Why:** Treating an existing catalog of roughly two thousand items as new would destroy trust, while a completely empty marketplace section makes a real first run look mocked and hides the ecosystem's current activity.

**Consequence:** Bootstrap is explicit and auditable. Invalid or missing listing timestamps are excluded, historical version/verification/retirement changes never backfill, and the twelve-item cap is tested. A baseline reset remains a maintenance operation.

## D013 — Advance seen state to the rendered session cutoff

**Decision:** Closing advances `seenThrough` only to the greatest event timestamp captured when that session rendered a valid edition.

**Why:** Wall-clock marking can lose events that arrive during a session or while sources disagree.

**Consequence:** The plugin records a session boundary and keeps it monotonic. Saves are independent.

## D014 — No desktop notifications in version 1

**Decision:** Radar is pull-based through the shortcut.

**Why:** The product exists to reduce noise, and it has no reliable version 1 definition of an urgent user interruption.

**Consequence:** Source health, critical labels, and unread counts appear only when Radar is opened. Notifications require an explicit future product contract.

## D015 — Use one implementation repository, but keep the feed contract client-neutral

**Decision:** Collector, publisher, panel, helpers, fixtures, and specification live together initially.

**Why:** Atomic schema changes and one test suite matter more than premature repository boundaries.

**Consequence:** Modules remain independently testable. A future consumer or hosted feed can split out without rewriting the event contract.

## D016 — Mirror only official marketplace preview rasters

**Decision:** An event caused by a supported marketplace fact may include the catalog's preview thumbnail after publication mirrors it to a same-origin SHA-256 path. No arbitrary or direct remote image URL reaches clients.

**Why:** Images make ecosystem activity immediately legible, but direct third-party loads create privacy, availability, tracking, and decoder boundaries. The official marketplace already provides bounded thumbnails and dimensions.

**Consequence:** The publisher uses a closed origin/path family, 1.5 MiB body limit, PNG/JPEG/WebP magic and structure checks, static-only enforcement, 4,096-pixel side/12-million-pixel bounds, and exact metadata dimension matching. SVG is forbidden. Image failures are visible build warnings and degrade to a complete text-only story.

## D017 — Make local checkout synchronization explicit and commit-based

**Decision:** `make local-latest` installs or fast-forwards the local Omarchy plugin clone to the invoking repository's exact clean committed `HEAD`.

**Why:** A development installation should be easy to keep current without an invisible updater, a symlink outside the validated plugin contract, or an automatic pull that changes the owner's source branch.

**Consequence:** First use clones and enables this checkout; later uses preserve enablement state and update through Omarchy's official Git-managed lifecycle. Dirty source or installed trees, symlinks, missing origins, public origins, and different local origins are refused. The command never installs the optional shortcut, pulls the source repository, or runs in the background.

## D018 — Build a real private edition for an unpublished local installation

**Decision:** `make local-latest` collects the allowlisted production sources at invocation time and imports the publisher's validated feed and mirrored content-addressed rasters into private local cache. A digest-bound marker identifies this explicitly as “Local live edition.”

**Why:** The public Pages origin deliberately does not exist before owner-authorized publication. Leaving a deterministic acceptance fixture in a daily installation makes preferences appear broken and misrepresents synthetic/local test stories as current ecosystem news.

**Consequence:** Local import revalidates canonical feed bytes, build digest/revision, and every referenced raster before atomically replacing the feed. The client uses private file URLs only for those imported assets, suppresses the nonexistent public refresh, and explains that rerunning the make target collects the next edition. Fresh visual preferences remain on by default. The exact unmodified panel-only preview placement migrates once through Omarchy's disable/enable lifecycle to the default right-side bar; custom, duplicate, ambiguous, or deliberately disabled modern configurations are not overwritten.

## D019 — Use a normal compositor-managed window

**Decision:** The panel entry point owns a Quickshell `FloatingWindow` rather than a full-monitor layer-shell `PanelWindow`.

**Why:** A news reader is a desktop task, not a modal shell overlay. The normal XDG toplevel provides compositor resize, minimize, maximize, window close, and ordinary `Alt+Tab`; current Omarchy uses the same supported contract for its dev gallery.

**Consequence:** The entry point remains an on-demand `Item` with `open()`/`close()`. Window-manager close tells the shell to hide the panel, while shell close hides the window without recursive notification. After map a bounded helper requires exactly one mapped client whose current and initial title are `Omarchy News Radar` and whose current and initial class are `org.quickshell`. Only when that unique client reports `floating: false` does it validate the compositor address and invoke Omarchy's current Lua float-toggle dispatcher once, with Hyprland's legacy structural dispatcher as the same bounded compatibility fallback used by Omarchy's window-pop helper. Zero matches time out harmlessly and multiple matches are refused as ambiguous. It does not edit configuration or affect an unrelated window, and an already-floating Radar is left untouched. The masthead starts system move, explicit edge handles start system resize, and bounded minimum geometry preserves usability.

## D020 — Enrich existing events with honest source metrics

**Decision:** Existing release and plugin events may carry optional marketplace views/hearts/command copies, catalog repository stars, and GitHub release-asset downloads with an observation timestamp and source URL.

**Why:** These counters help a reader assess activity when their semantics are precise. They do not prove installation, reach, quality, safety, or importance.

**Consequence:** Metrics use closed IDs and strict integer/URL/time validation. A successful source refresh replaces only its metric group; failure retains the prior observation. Counter changes never create events or affect identity, order, significance, curation, or Front Page composition. The UI states the marketplace caveat and calls GitHub's number “release asset downloads.”

## D021 — Keep filters independent and pagination finite

**Decision:** State v3 introduced one strict local filter per client section, and the reader reveals a maximum twelve matching events at a time through an explicit Load more control.

**Why:** Users need inspectable control over time, significance, unread/image state, and event types without turning Radar into an infinite stream or personalized server API.

**Consequence:** The options screen always exposes the immutable built-in rule and exact reset. Filters and limits operate after deterministic section projection, stay on device, and never change network requests. `Tab`/`Shift+Tab` cycles sections; Load more expands the current bounded projection by twelve up to the feed's 500-event bound.

## D022 — Personalize section presentation without changing editorial identity

**Decision:** State v4 lets each stable client section store a bounded display name, one icon from a closed palette, and one theme-derived background tone. Source membership remains fixed and read-only in version 1.

**Why:** Names, icons, and restrained color make a personal reader easier to scan, but arbitrary colors, markup, or source reassignment would weaken theme compatibility, validation, and the documented meaning of Core, Plugins, and Community.

**Consequence:** The cogwheel screen shows appearance controls, exact appearance reset, the dictated source summary, built-in rule, and filters together. Stable section IDs continue to drive projection, counts, keys, source membership, and filter storage. Profiles are local-only, strictly validated, independently resettable, and migrated atomically from v1–v3 state.
