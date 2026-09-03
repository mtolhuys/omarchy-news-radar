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

**Consequence:** Durable state lives in XDG files, every panel open restores it, and every panel close terminates panel-owned work. A visible newspaper maintains one bounded due-checked timer in the existing shell process; hiding it stops network checks. D036 defines the corrected cadence and propagation contract.

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

## D010 — Keep personalization local (manual interests superseded by D028)

**Decision:** Installed-plugin matching, up to twelve explicit interests, reading state, saves, filters, and preferences stay on the device.

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

## D013 — Advance seen state to the rendered session cutoff (superseded by D027)

**Decision:** Closing advances `seenThrough` only to the greatest event timestamp captured when that session rendered a valid edition.

**Why:** Wall-clock marking can lose events that arrive during a session or while sources disagree.

**Consequence:** The plugin records a session boundary and keeps it monotonic. Saves are independent.

## D014 — No desktop notifications in version 1

**Decision:** Radar emits no desktop pop-up notifications. Reading remains pull-based through the panel, with an optional passive newspaper badge in the existing Omarchy bar.

**Why:** The product exists to reduce noise, and it has no reliable version 1 definition of an urgent user interruption.

**Consequence:** The bar may show unread count and source/publication health without interrupting the user; story details and critical labels remain in the panel. Sound, banners, notification-center entries, urgency, and notification actions require an explicit future product contract.

## D015 — Use one implementation repository, but keep the feed contract client-neutral

**Decision:** Collector, publisher, panel, helpers, fixtures, and specification live together initially.

**Why:** Atomic schema changes and one test suite matter more than premature repository boundaries.

**Consequence:** Modules remain independently testable. A future consumer or hosted feed can split out without rewriting the event contract.

## D016 — Pass through allowlisted marketplace preview URLs (supersedes same-origin mirroring)

**Decision:** An event caused by a supported marketplace fact may include the catalog's preview thumbnail as an HTTPS `sourceUrl` on the fixed marketplace image origin (`https://plugins.omarchy.org/assets/img/plugins/…`). The publisher validates type/size/dimensions at build time and does **not** mirror rasters onto the feed host. Clients load only that allowlisted origin (plus legacy same-origin `path` assets from older caches).

**Why:** Hosting hundreds of content-addressed WebPs on a small Forge VPS wastes disk and bandwidth. The official marketplace already serves bounded thumbnails; repeating them on mtolhuijs.nl adds operational risk without a proportional trust gain once the URL family is closed.

**Consequence:** Publication still uses a closed origin/path family, 1.5 MiB body limit, PNG/JPEG/WebP magic and structure checks, static-only enforcement, 4,096-pixel side/12-million-pixel bounds, and exact metadata dimension matching. SVG is forbidden. Validation failures omit the image. The public feed and static HTML reference `sourceUrl` directly; CSP allows `img-src 'self' https://plugins.omarchy.org`. Forge publish deletes any leftover `assets/images` tree and never accumulates mirrored rasters.

## D017 — Make local checkout synchronization explicit and commit-based

**Decision:** `make local-latest` installs or fast-forwards the local Omarchy plugin clone to the invoking repository's exact clean committed `HEAD`.

**Why:** A development installation should be easy to keep current without an invisible updater, a symlink outside the validated plugin contract, or an automatic pull that changes the owner's source branch.

**Consequence:** First use clones and enables this checkout; later uses preserve enablement state and update through Omarchy's official Git-managed lifecycle. Dirty source or installed trees, symlinks, missing origins, public origins, and different local origins are refused. The command never installs the optional shortcut, pulls the source repository, or runs in the background.

## D018 — Build a real private edition for an unpublished local installation (refresh behavior superseded by D029)

**Decision:** `make local-latest` collects the allowlisted production sources at invocation time and imports the publisher's validated feed and mirrored content-addressed rasters into private local cache. A digest-bound marker identifies this explicitly as “Local live edition.”

**Why:** The public Pages origin deliberately does not exist before owner-authorized publication. Leaving a deterministic acceptance fixture in a daily installation makes preferences appear broken and misrepresents synthetic/local test stories as current ecosystem news.

**Consequence:** Local import revalidates canonical feed bytes, build digest/revision, and every referenced raster before atomically replacing the feed. The client uses private file URLs only for those imported assets, suppresses the nonexistent public refresh, and explains that rerunning the make target collects the next edition. Fresh visual preferences remain on by default. The exact unmodified panel-only preview placement migrates once through Omarchy's disable/enable lifecycle to the default right-side bar; custom, duplicate, ambiguous, or deliberately disabled modern configurations are not overwritten.

## D019 — Use a normal compositor-managed window

**Decision:** The panel entry point owns a Quickshell `FloatingWindow` rather than a full-monitor layer-shell `PanelWindow`.

**Why:** A news reader is a desktop task, not a modal shell overlay. The normal XDG toplevel provides compositor resize, maximize, window close, and ordinary `Alt+Tab`; current Omarchy uses the same supported contract for its dev gallery. The owner found the hosted minimize action unreliable and explicitly removed that control.

**Consequence:** The entry point remains an on-demand `Item` with `open()`/`close()`. Window-manager close tells the shell to hide the panel, while shell close hides the window without recursive notification. After map a bounded helper requires exactly one mapped client whose current and initial title are `📰 Omarchy News Radar` and whose current and initial class are `org.quickshell`. Only when that unique client reports `floating: false` does it validate the compositor address and invoke Omarchy's current Lua float-toggle dispatcher once, with Hyprland's legacy structural dispatcher as the same bounded compatibility fallback used by Omarchy's window-pop helper. Zero matches time out harmlessly and multiple matches are refused as ambiguous. It does not edit configuration or affect an unrelated window, and an already-floating Radar is left untouched. The masthead starts system move, explicit edge handles start system resize, bounded minimum geometry preserves usability, and the title plus bundled manifest icon provide the strongest safe system identity available without globally replacing the shared Quickshell app ID. The panel exposes Maximize/Restore and Close but no minimize button.

## D020 — Enrich existing events with honest source metrics

**Decision:** Existing release and plugin events may carry optional marketplace views/hearts/command copies, catalog repository stars, and GitHub release-asset downloads with an observation timestamp and source URL.

**Why:** These counters help a reader assess activity when their semantics are precise. They do not prove installation, reach, quality, safety, or importance.

**Consequence:** Metrics use closed IDs and strict integer/URL/time validation. A successful source refresh replaces only its metric group; failure retains the prior observation. Counter changes never create events or affect identity, order, significance, curation, or Front Page composition. The UI states the marketplace caveat and calls GitHub's number “release asset downloads.”

## D021 — Keep filters independent and pagination finite

**Decision:** State v3 introduced one strict local filter per client section, and the reader reveals a maximum twelve matching events at a time through an explicit Load more control.

**Why:** Users need inspectable control over time, significance, unread/image state, and event types without turning Radar into an infinite stream or personalized server API.

**Consequence:** The options screen exposes fixed source scope and exact filter reset. Filters and limits operate after deterministic section projection, stay on device, and never change network requests. `Tab`/`Shift+Tab` cycles sections. Down from the final visible story focuses Load more with an explicit Enter label, Up returns to the story list, and Enter expands the current bounded projection by twelve up to the feed's 500-event bound without implicitly reading a newly revealed item.

## D022 — Personalize section presentation without changing editorial identity (superseded by D025)

**Decision:** State v4 lets each stable client section store a bounded display name, one icon from a closed palette, and one theme-derived background tone. Source membership remains fixed and read-only in version 1.

**Why:** Names, icons, and restrained color make a personal reader easier to scan, but arbitrary colors, markup, or source reassignment would weaken theme compatibility, validation, and the documented meaning of Core, Plugins, and Community.

**Consequence:** This state-v4 design shipped in the local preview and remains documented for migration. D025 removes its icon and tone controls after owner testing found that interchangeable visual identities damaged section clarity.

## D023 — Declare an exact hosted-window identity for companion UIs

**Decision:** Radar's manifest declares the exact compositor pair `org.quickshell` and `📰 Omarchy News Radar`. Compatible AltTab and Omadock companions may use Radar's existing local manifest name/icon only when one enabled plugin matches both fields exactly.

**Why:** Quickshell exposes only the shared process app ID for hosted `FloatingWindow` instances. Resolving `org.quickshell` through the desktop database produces a generic file/gear icon, while globally replacing that desktop entry would mislabel unrelated shell windows.

**Consequence:** Companion resolution is opt-in and fail-closed. A missing, disabled, malformed, or ambiguous declaration uses the ordinary desktop fallback. Radar does not change the process-wide app ID, inspect arbitrary titles, or claim ownership of other Quickshell windows. The separately consented Apps-menu entry in D024 does not participate in companion resolution.

## D024 — Offer one explicit receipt-backed Apps-menu entry

**Decision:** Radar ships one standard XDG desktop entry and an explicit `news-radar-launcher status|install|remove` helper. `make local-latest` installs or updates it because that make target is already an intentional owner-run desktop mutation; a public Omarchy plugin install documents the helper as a separate opt-in step.

**Why:** Omarchy's Apps provider reads standard desktop entries and provides the desired launcher icon, search, and launch feedback. The current third-party plugin lifecycle intentionally executes no repository hooks, so silently writing an entry on plugin enable or pretending normal plugin removal can clean it would be dishonest.

**Consequence:** The helper owns only `io.github.mtolhuys.news-radar.desktop`, the same-named SVG under the user icon theme, and a private path/digest receipt. Installation uses bounded source assets and atomic replacements, updates only files matching the prior receipt, and refuses symlinked, unowned, modified, unmanaged, or ambiguous targets. Removal deletes only receipt-matching files and preserves user edits. Public removal instructions run the launcher helper before deleting the plugin checkout.

## D025 — Keep section icon, order, background, and scope fixed (superseded by D030)

**Decision:** State v5 retains only a bounded local display name for each stable client section. Section icons, order, backgrounds, source membership, and projection rules are canonical code-owned identity and are not configurable.

**Why:** Owner testing found that assigning the same visual identity to multiple sections or making one section resemble another damaged scanability and suggested that editorial scope had moved. A customizable background added more state without improving the reader's factual utility.

**Consequence:** Settings offers name editing/reset, fixed-source disclosure, the immutable built-in rule, and local filters. Valid v4 state migrates atomically: names survive, while old icon and tone values are validated and discarded. Valid v1–v3 state receives canonical names as before. No hidden appearance state remains that the user cannot control.

## D026 — Remove the empty Community reader section

**Decision:** The client has five sections: Front Page, For You, Core, Plugins, and Saved. The reviewed `community-link` source/event contract remains valid, but it has no dedicated navigation destination.

**Why:** Production has no accepted reviewed records, so the Community tab was permanently empty and consumed navigation, settings, keyboard numbering, and explanation space without helping the reader. Keeping an empty placeholder is not useful product behavior.

**Consequence:** State v6 validates and atomically migrates v5, preserving saved items, seen state, global preferences, and every remaining section's name/filter while discarding only Community's profile/filter. A future reviewed record may still enter Front Page and local For You through the existing deterministic rules. Numeric navigation is `1`–`5`, Saved is `5`, and no empty Community state or settings surface remains.

## D027 — Track deliberate per-story reading instead of rendered sessions

**Decision:** State v7 supersedes D013's session-wide cutoff. Every story is explicitly `UNREAD` or `READ`; deliberate keyboard or pointer selection marks only that event read, and the inspector or `u` key can reverse it. Hover, default selection, refresh, and close never bulk-mark stories.

**Why:** A session cutoff can report an article as seen merely because it existed somewhere in an open edition. The bar count then cannot answer the user's essential question: which exact articles remain unread?

**Consequence:** The prior `seenThrough` value migrates once to a fixed `readThrough` compatibility baseline. A bounded canonical boolean override map records only decisions that differ from that baseline and prunes IDs outside the current edition on mutation. Rows, section badges, accessible names, filters, and the top-bar count consume the same predicate. Cross-process state changes are serialized so a bar preference, save, filter, or read action cannot overwrite another local mutation.

## D028 — Remove manual interests until relevance has a reliable interaction

**Decision:** State v8 removes the manual interests field, helper argument, settings control, and text-matching projection. For You uses exact enabled-plugin IDs only.

**Why:** Owner testing found that Apply interests did not provide reliable visible behavior. Keeping a hidden or partially working preference would make the section rule misleading and preserve dead state that users could no longer inspect.

**Consequence:** Valid v2–v7 interests are strictly validated during migration and then discarded; every other supported preference, filter, display name, save, and read override survives. The current state schema cannot represent interests, the CLI cannot set them, and the panel explains the one remaining automatic rule. Reintroducing broader relevance requires a new visible, tested product decision.

## D029 — Let local development editions rejoin the published stream

**Decision:** A digest-matched local edition remains readable and keeps local mirrored images, but Refresh checks the fixed Pages feed after public hosting exists. An equal or older published edition cannot replace it; a newer valid published edition atomically becomes the current cache.

**Why:** The pre-publication safety branch in D018 intentionally suppressed a nonexistent Pages origin. Once Pages became live, that branch permanently pinned users of `make local-latest` to the collection time of their last manual sync even though the public hourly feed continued advancing.

**Consequence:** Local development remains honest and cannot be downgraded, while manual and due-checked refreshes eventually transition it back to the shared published stream. Network or validation failure still preserves the complete local edition. The panel's animated refresh state reflects the actual bounded helper lifetime and keeps cached stories readable.

## D030 — Remove section profiles and keep Settings actionable

**Decision:** State v9 removes section display profiles and the helper/UI route that edited them. Names join icons, order, background, source scope, and projection semantics as canonical code-owned section identity. Settings shows the fixed source summary and only filters that change the visible story set.

**Why:** Owner review found renaming damaging for the same reason as configurable icons and backgrounds: a section could lose its recognizable scope. Explanatory muted paragraphs and a repeated filter summary added visual noise without helping the task.

**Consequence:** Valid v1–v8 profiles are strictly validated during atomic migration and then discarded; supported filters, bar/image preferences, reading state, and saves survive. The current schema and CLI cannot represent a display profile. Settings removes renaming, built-in-rule prose, filler, and the redundant local-only summary while retaining fixed sources and exact filter reset.

## D031 — Refresh plugin-addition explanations from the catalog

**Decision:** A successful marketplace refresh may replace an existing `plugin-added` summary with that plugin's current validated bounded catalog description.

**Why:** The generic “now listed” sentence repeats the headline and fails to explain what the plugin does even when the authoritative marketplace provides that fact.

**Consequence:** Description enrichment is presentation-only. It never creates an event or affects event ID, occurrence time, significance, ordering, metrics, or curation; catalog failure preserves the prior summary. All explanation text remains bounded untrusted plain text.

## D032 — Make batch reading explicit and plugin explanations useful

**Decision:** Each section exposes one **Mark all as read** action. It atomically marks every unread story matching that section's persistent Settings filters, including unloaded pages; temporary search never changes its scope. D031's catalog-description enrichment now applies to every plugin marketplace event, not additions alone.

**Why:** A long finite edition needs a deliberate way to clear a known section without pretending that opening, refreshing, searching, or closing constitutes reading. Generic version and verification sentences repeat facts already visible in the title and metadata while omitting the catalog's useful explanation of what the plugin does.

**Consequence:** The helper derives the exact bounded section projection from validated cache, enabled-plugin IDs, saved IDs, and persisted filters, then writes all required per-event overrides under the existing state lock. Other sections and nonmatching stories keep their prior state. New and retained plugin additions, releases, verification changes, and retirements use the current validated catalog description as bounded untrusted plain text; event identity, type, version, trust state, time, ordering, metrics, and curation remain unchanged.

## D033 — Treat publication as best effort and expose its real age

**Superseded (publisher):** Live publishing moved to Forge Laravel `news-radar:publish` every 10 minutes at `https://mtolhuijs.nl/news-radar/events.json`; GitHub Pages/Actions publication is retired. Stale-after-90-minutes and distinct timestamp facts still apply.

**Decision:** Keep the bounded static GitHub Pages architecture, request workflow schedules at minutes 8, 23, 38, and 53, retain manual dispatch for recovery, and define publication as stale only when artifact `publishedAt` is more than 90 minutes old. Record and present source `checkedAt`, collection `generatedAt`, artifact `publishedAt`, the documented Pages cache window, and local cache time as different facts.

**Why:** On 1 September 2026 GitHub stopped delivering the hourly schedule after 13:31 UTC while two manual runs succeeded. Collection, validation, and Pages deployment were healthy when invoked; the single best-effort trigger was the unreliable link. GitHub documents that scheduled runs may be delayed or dropped under load and recommends avoiding high-load hour boundaries. More off-peak opportunities provide recovery without another account, secret, service, or server, but cannot create a guarantee.

**Consequence:** Workflow concurrency never cancels an active publication. Clients still fetch only the fixed static feed, replace it atomically after validation, and keep last-known-good data. Old successful source states can no longer make an old artifact appear current. `R` and middle click are named **Check for updates** and report exact new/no-change/stale/offline outcomes rather than implying upstream collection. The health monitor separately checks scheduled-run continuity, publication age, Pages propagation, and source timestamps.

## D034 — Summon is activation; close remains deliberate

**Decision:** The bar, managed `Super+Alt+N` binding, and Apps entry all use `omarchy-shell shell summon`. Repeated invocation opens or raises and focuses the single Radar window; it never closes it. `Escape`, `q`, the rendered close button, and window-manager close are the supported close routes.

**Why:** Omarchy's `toggle` chooses hide whenever the plugin reports `opened`, even when its normal window is merely behind another application. The first activation therefore briefly raised the hosted window and then hid it. This was a semantic mismatch, not input duplication, so debouncing would conceal the wrong contract.

**Consequence:** An exact mapped-window helper always focuses the validated compositor address and floats only when needed. One QML `Process` instance coalesces rapid helper starts. Disposable-lab acceptance must drive the actual newspaper with QMP pointer input and the live global binding with compositor-level QMP keys across closed, obscured, foreground, rapid-repeat, Alt+Tab, close, and reopen states, while proving exactly one Radar client and no competing helper remain.

## D035 — Re-anchor keyboard selection at the viewport edge

**Decision:** Down keeps ordinary row-by-row movement while the next story is fully visible. When the next story would cross or overlap the list viewport bottom, one short eased scroll places that complete selected row at the viewport top; following keys again move through the visible rows normally. Pointer scrolling remains a direct Flickable interaction.

**Why:** `ListView.Contain` can park a variable-height selected row against the lower clip boundary, where spacing and the adjacent footer make the selection appear overlapped or incomplete. Continually pinning every selection to the top would remove useful visual context. Re-anchoring only at the crossing preserves context and creates a clear new reading block.

**Consequence:** The viewport decision uses settled selected-delegate geometry after layout, and the animation targets the exact `ListView.Beginning` position. The resulting top-row anchor is explicit panel state so an asynchronous read-state projection cannot return the selected row to the lower clip boundary. A read-only geometry probe lets disposable-lab acceptance prove that the crossing row is fully visible and top-aligned, and that the next Down changes selection without moving the viewport.

## D036 — Discover unread editions without opening the panel

**Decision:** The visible newspaper records the last real network-check attempt independently from feed age. A success schedules the next check after 15 minutes; a failure retries after five minutes. A watched atomic feed replacement immediately reloads the shared unread/health indicator, with a 30-second local-only fallback for missed filesystem events. The hidden newspaper performs no network checks.

**Why:** Using the feed's `generatedAt` as a polling clock conflated publisher time with client activity. Starting the shell just before a 30-minute boundary could then wait another full repeating interval, approaching an hour before discovery. Watching only reading state also meant a newly adopted feed could leave the visible badge stale until its fallback poll. Opening the panel appeared to fix both because it forces an immediate check and projection.

**Consequence:** Closed-panel users receive a passive unread badge within one bounded client interval after Pages serves the edition, and a successful feed adoption propagates without waiting for another timer. The private cadence file is strict, bounded, atomic, mode `0600`, purge-owned, and contains no reading data or identifiers; malformed or materially future values mean “due” rather than delaying checks. This does not add a daemon, hidden polling, desktop notification, telemetry, account, or personalized request.

## D037 — Migrate only the exact legacy shortcut, after explicit consent (superseded by D038)

**Decision:** Treat the byte-exact 0.1.3 Radar-owned managed block as `owned-legacy`. A read-only panel-open inspection may expose **Update shortcut**, but replacement with the current `summon` block occurs only when the user activates that control or explicitly runs `news-radar-shortcut install` again.

**Why:** Version 0.1.4 corrected the template but did not change an already-installed personal binding, because Omarchy plugin updates intentionally run no repository hooks. The old live `toggle` action therefore survived a normal upgrade and kept closing an obscured Radar. Classifying the old marker pair as generic ambiguity made the helper unable to repair or remove its own unmodified output. Automatic mutation during update or panel open would violate the explicit shortcut-ownership contract.

**Consequence:** Exact legacy detection requires one complete known block, one marker pair, and one matching live Radar action. Migration preserves all surrounding bytes, creates a private backup, writes atomically, reloads Hyprland, validates one current live action and no configuration error, and restores the legacy action if validation fails. Current, legacy, edited, personal, multiple, conflicting, symlinked, or otherwise ambiguous cases remain distinct; no force path exists. Disposable-lab acceptance must exercise the real 0.1.3-to-candidate update rather than only a fresh candidate installation.

## D038 — Repair an exact Radar-owned legacy block during the update rescan

**Decision:** Initial shortcut installation remains explicit. Once that action created Radar's byte-exact marked block, the bar generation loaded by Omarchy's normal plugin-update rescan invokes `migrate-owned-legacy`. The command changes only the exact unmodified 0.1.3-owned `toggle` block with one matching live action; it returns without mutation for every other state. The panel retains **Update shortcut** as a visible retry if automatic validation cannot complete.

**Why:** Version 0.1.5 made migration possible but required a second, undiscoverable action after the user had already run the advertised updater. That did not fulfill the ordinary meaning of an activation bug fix. The original explicit setup already delegated ownership of this exact marked block to Radar, and changing its action from close-on-obscured `toggle` to the promised summon-to-focus behavior is a repair of that owned output, not a new shortcut grant.

**Consequence:** The narrow command can never install a free chord, claim a lookalike, or touch personal, edited, multiple, conflicting, symlinked, or ambiguous configuration. It reuses the private backup, atomic byte-preserving replacement, Hyprland reload/config validation, and exact rollback path. Disposable-lab acceptance now proves the official update command alone repairs the live binding before Radar opens or any migration control is clicked. A future declarative Omarchy shortcut/update contract may replace this generation-load bridge.

## D039 — Preserve the live viewport across pagination and read projections

**Decision:** Projection requests declare either `reset` or `preserve` viewport semantics. Section, search, and filter changes deliberately rebuild from their canonical anchor. **Load more**, edition refresh, installed-plugin discovery, and per-story reading updates retain the stable selected event ID, its live on-screen anchor, and the current keyboard animation. A monotonic viewport revision invalidates deferred positioning from superseded navigation.

**Why:** Expanding a 12-story projection replaced the ListView model and then ran the generic anchor restoration. That anchor described an earlier viewport block, so pagination jumped upward. The selected story's asynchronous read write could immediately request another projection while the 140 ms keyboard animation was active, making multiple valid operations fight over `contentY` and producing visible oscillation.

**Consequence:** Pagination does not move or animate the retained story viewport. The next Down top-aligns the first newly revealed row when it crosses the viewport, and the following Down keeps that anchor while moving normally. Stable event identity survives a refreshed projection, active animation remains authoritative, and only explicit context changes reset the viewport. Disposable-lab acceptance continuously samples pagination geometry and asserts both post-load navigation steps.

The invariant is the rendered anchor rather than the raw `ListView.contentY` number. Pagination appends to a stable `ListModel` instead of replacing the entire JavaScript-array model, so existing delegates are not recycled. Read projections update only payloads whose validated content changed. One adjacent viewport remains instantiated so the first newly revealed row has real geometry before keyboard movement; a bounded rendered-frame preservation pass remains as a safety net for genuine asynchronous relayout. Acceptance samples the selected row's on-screen top, full visibility, and animation state rather than mistaking a compensating internal offset for visual motion.

## D040 — Keep reverse key-repeat synchronized with selection

**Decision:** Up retains ordinary row-by-row selection while the previous story is visible. When the previous story is above the viewport, Radar positions that row at the top before changing selection. The upward edge transition is immediate rather than eased because the visible highlight must remain authoritative under compositor key repeat.

**Why:** Up previously changed only `selectedIndex`; all viewport-edge logic was gated to Down. Holding Up could therefore advance through several off-screen stories while the ListView remained below them. Reusing the 140 ms eased Down animation would still let a 30–40 ms repeat cadence outrun the viewport.

**Consequence:** Reverse navigation never selects a clipped or invisible story. Held Up produces monotonic selection and one-row viewport steps, while single Up presses within the visible block do not move the viewport. Disposable-lab acceptance holds the physical Up key through QMP, samples geometry throughout the repeat interval, and requires every sampled selected row to remain fully visible.

## D041 — Advance source state from the latest successful deployment

**Superseded (publisher):** Continuity now advances in Forge Laravel storage between `news-radar:publish` runs rather than Actions/Pages deployment artifacts.

**Decision:** Every scheduled or manually dispatched publication restores the exact validated source snapshot artifact from the latest successfully completed publication run before collection. The next snapshot is uploaded under the current run ID and becomes authoritative only if the whole build and Pages deployment succeed. Repository contents remain read-only. Missing, expired, malformed, or unsupported continuity stops publication. `make local-latest` independently selects and advances a private validated source snapshot only after its matching edition imports successfully.

**Why:** The previous workflow always checked out the same manually committed baseline and merely uploaded its successor. Scheduled runs therefore rediscovered every marketplace difference since that baseline, assigned the current collection time again, and republished old changes as fresh. The manual instruction to commit a new multi-megabyte snapshot after every quarter-hour deployment was incompatible with unattended scheduling. The Front Page compounded the effect by filling a core quota with three older releases after already selecting the newest release.

**Consequence:** Source history advances exactly once per successful deployment without granting repository write access. Deterministic event IDs retain their first observation timestamps if a lagging baseline ever rediscovers them. Snapshot schema v2 performs one bounded transition from a fresh reviewed baseline, retaining only source-dated additions, official releases, and reviewed community records from the contaminated v1 ledger; unknown-time release/verification/retirement diffs restart from the current normalized source state. A pre-upload audit requires every newly appearing marketplace ID to have its addition story and refuses backwards catalog time. Front Page selects the newest official release once and fills the remaining edition with current plugin/community activity. A continuity outage yields an honestly stale last-known-good public edition instead of false new stories.

## D042 — Keep the active reading target stable across control and unread boundaries

**Decision:** Up from the focused Load more control transfers focus without reselecting or repositioning the already selected final story. Under Unread only, event IDs read during the active view form a bounded transient retention set: otherwise-matching rows remain in place and visibly become READ until section, search, or filter context changes.

**Why:** Reselecting the unchanged final story asked Qt to contain it again and could snap the ListView to its bottom, especially when rapid input followed the focus transition. Immediately removing a selected story as its asynchronous read write completed shifted the projection during the user's interaction and could make both the highlight and surrounding context disappear.

**Consequence:** Focus transitions do not mutate scroll state. The helper strictly validates at most 500 canonical event IDs and applies the exception only to Unread only's read predicate; every other section, search, time, significance, image, and type condition remains active. Persistent state and section unread counts remain authoritative, the UI labels temporarily retained rows, and no transient retention survives a view change or panel reopen.

## D043 — Keep publication operations out of the successful reading surface

**Decision:** When a validated edition exists, Radar shows the news without persistent edition-origin, source-health, publication-age, cache-age, Pages-propagation, runtime-version, or update-result copy. Checking remains visible only while active. A concise recovery message appears only when no usable edition exists. The permanent keyboard legend is removed; shortcut hints stay on relevant controls and in documentation.

**Why:** These facts are essential for build verification and operational monitoring but became content noise in the reader. A user with usable news does not need to understand whether it came from a local import, Pages, a cache, or a delayed publisher.

**Consequence:** Typed helper results, timing metadata, debug state, external health monitoring, and the bar health model remain intact. Local and published editions retain their validation and downgrade rules. Normal cached, updated, no-change, stale-publisher, partial-source, and offline-with-cache paths remain quietly readable; only a genuine no-cache failure occupies the content surface.

## D044 — Advertise only actionable unread stories

**Decision:** The top-bar newspaper counts the unique unread event IDs that survive at least one of the five current persistent section projections. It uses the same enabled-plugin IDs, filters, and canonical read predicate as the panel. Temporary search and pagination do not change the count.

**Why:** A global raw-feed count could remain nonzero after every visible section reported zero unread. In the reported production state, the Plugins **With images** filter hid eight image-less unread events while the bar still advertised all eight, leaving no visible destination for the badge.

**Consequence:** A story hidden by every persistent section filter cannot keep the badge active, overlap between sections never double-counts it, and changing a filter can reveal and begin advertising previously hidden unread stories. The bar resolves local enabled-plugin IDs before every coalesced indicator request, so an enablement change cannot leave a lifetime-stale relevance snapshot, and continues to send no private state over the network.

## D045 — Add an allowlisted YouTube lane without changing Front Page significance

**Decision:** Version 0.4.0 adds a Forge-collected YouTube Data API v3 source as a D007 exception for one allowlisted HTTPS origin (`https://www.googleapis.com/youtube/v3/...`). The client gains a sixth rail section, YouTube, between Plugins and Saved. Events use type `youtube-video`, classification section `youtube`, optional metrics `youtube-views`/`youtube-likes`, and allowlisted `https://i.ytimg.com/vi/<id>/hqdefault.jpg` thumbnails. Feed schema version 2 is required to emit YouTube events; schema version 1 never carries them. Local state schema v10 adds the YouTube filter. Views/likes/recent interleaving ranks only inside the YouTube section and never influences significance, Front Page composition, or event identity (D008/D020). Collection is fail-closed: a missing `YOUTUBE_API_KEY`, transport failure, or invalid payload records a failed `youtube` source health entry and retains the prior YouTube snapshot. CI uses fixtures only. Opening a story uses the existing browser-open path; Radar does not scrape watch pages or embed players. The empty Community reader section remains removed (D026).

**Why:** Omarchy-related videos are meaningful ecosystem activity that users already open in a browser, but they are not marketplace or release facts and must not dilute the Front Page significance model.

**Consequence:** Forge must provision `YOUTUBE_API_KEY` out of band. Clients on feed schema 1 fail closed until updated. Numeric navigation is `1`–`6`, Saved is `6`, and Settings discloses the YouTube source boundary like every other fixed section.

## D046 — Fill YouTube immediately from empty snapshots and published Forge feeds

**Decision:** The YouTube six-hour collect cadence applies only after a successful snapshot with a non-empty `videoIds` list. Missing, malformed, or empty YouTube snapshots refresh on the next collect. Fail-closed retention of prior YouTube events on key/transport/validation failure is unchanged. Separately, **Check for updates** may adopt an equal-or-older validated published edition when a digest-matched local live edition has zero `youtube-video` events and the published candidate has at least one. Ordinary D029 downgrade refusal remains for every other case.

**Why:** `make local-latest` often lacks `YOUTUBE_API_KEY`, so a newer owner-built edition can pin clients to an empty YouTube section while Forge already publishes a filled lane. The cadence gate also delayed empty→filled transitions after a first unsuccessful or empty populate.

**Consequence:** Clients rejoin the shared published YouTube lane as soon as Check for updates runs; Forge continuity (D041) and fail-closed retention are unchanged. The exception is YouTube-empty-local only and never demotes a local edition that already carries YouTube stories.

## D047 — Make the official Omarchy logo the primary application mark

**Decision:** Replace the transparent full-glyph/full-radar overlay with one visual identity in two surface roles. The exact official vector geometry published at `https://omarchy.org/brand/` appears at full strength in its `#9ece6a` green. A compact two-ring amber radar, sweep, and blip occupy its central negative space. The manifest, Apps entry, and companion UIs use a self-contained opaque dark squircle. The panel uses the same geometry without that squircle on its existing theme-native plate: official bright colors on dark themes and darker contrast-tuned green/amber on light themes.

**Why:** The previous composition treated the logo as a faint background and gave a second complete radar equal weight. It became muddy at launcher and 42-pixel header sizes, weakened brand recognition, and depended on its compositing surface. A stable badge with one dominant branded silhouette is faster to recognize and creates a more credible first impression.

**Consequence:** Every SVG retains the bounded 128-unit inert geometry contract and exact centered radar composition. Launcher-like surfaces remain independent of their compositing background; the panel variants are intentionally transparent and let its existing theme plate supply background, border, and exact header sizing. Release review renders the mark at 24, 32, 42, 64, and 128 pixels on both light and dark surfaces before Plugin Lab acceptance. The project remains a community plugin and does not imply official Omarchy status.

## D048 — Ingest official Omarchy News RSS into Core without flooding Front Page

**Decision:** Version 0.4.13 adds a Forge-collected Omarchy News RSS 2.0 source as a D007 exception for one allowlisted HTTPS URL (`https://omarchy.org/news/rss.xml`). The live document's Atom self link names that path; `/news/rss` currently mirrors it and is not separately allowlisted. Events use type `omarchy-news`, classification section `core`, and deterministic IDs derived from the item guid/path slug. Collection is fail-closed: transport or validation failure records a failed `omarchy-news` source health entry and retains the prior news snapshot. CI uses checked-in RSS fixtures only. No new client rail section is added—Core already hosts official releases.

**Why:** Official announcements belong beside releases in Core, and clients must keep fetching only the published `events.json`. Broad HTML scraping is out of scope. Marking every RSS item `notable` would break Front Page bounds because the notable lane has no per-type cap and the channel already carries many items inside the rolling window.

**Consequence:** Adapter significance stays `routine` (D008). Front Page selects at most three recent `omarchy-news` events by an explicit quota. Settings discloses Omarchy News on Front Page/Core. Feed schema version remains 2 with an extended event-type and source-id enum; local state schema remains v10 with an extended filter-type enum. No API key is required.


## D049 — Diversify Front Page news by topic cluster, keep every item in Core

**Decision:** Core continues to list every official `omarchy-news` event. Front Page still admits at most three recent news items (D048) but spends that quota on distinct deterministic topic clusters first, then backfills in freshness order. Clustering uses closed stoplist tokens from the title and leading summary sentence. No rewriting, translation, sentiment, or popularity signal is involved.

**Why:** A single-cycle Foundation/patronage announcement shipped as several RSS items and consumed the entire news quota, hiding the rest of the edition.

**Consequence:** Same-topic follow-ups remain in Core and Saved. Front Page shows one item from that cluster before other current topics. A window that contains only one topic still fills the quota by freshness.

## D050 — Local section visibility without hiding the edition

**Decision:** State v11 adds `preferences.sectionVisibility` for the hideable source rails Core, Plugins, and YouTube. Each defaults to visible. Front Page, For You, and Saved cannot be hidden. Hidden rails leave the section list, Tab cycle, number keys, Settings destination, and newspaper unread union. Saved still keeps bookmarks from a hidden rail.

**Why:** Readers asked to quiet unused lanes without losing the edition, the installed-plugin view, or bookmarks. Session-only visibility would reset on every open.

**Consequence:** Valid v10 states migrate atomically and gain the default-on profile. Tune copy stays local-display only: no language selector, engagement, clickbait, keywords, muting, duration, captions, or AI controls.

## D051 — Compact list teasers, full article in the inspector

**Decision:** The client attaches a deterministic `listSummary` (at most 220 characters of cleaned leading prose) to each projected story. List cards and their accessible names use that teaser. The wider inspector continues to render the full validated `summary`, including the official Omarchy News article body added in 0.4.14, directly after the headline. Actions follow the body; metadata and non-video metrics sit below a quiet divider. YouTube retains thumbnail and prominent metric treatment.

**Why:** Competitor reading surfaces stay scannable. Dumping an 8k body, sponsor line, or URL wall into the index makes Core and Front Page feel like sludge even when QML elides extra lines.

**Consequence:** Source content is not rewritten or discarded. YouTube cards reuse the same teaser path on already-sanitized descriptions. Feed schema is unchanged.
