# Architecture and product decisions

## D001 — Use the product and repository name Omarchy News Radar

**Decision:** The repository is `omarchy-news-radar`, the user-facing product is “Omarchy News Radar,” and the plugin ID is `io.github.mtolhuys.news-radar`.

**Why:** “News Radar” communicates monitoring and relevance rather than a full editorial publication, while distinguishing the project from existing flight and weather radar plugins.

**Consequence:** Use one name consistently in manifest, UI, generated site, feeds, documentation, and release artifacts. Include an independent-community disclaimer until official status is explicitly granted.

## D002 — Make `Super+Shift+N` the recommended primary interaction

**Decision:** Offer `Super+Shift+N` as an explicit opt-in global shortcut that deliberately replaces Omarchy's audited default Editor chord.

**Why:** It is memorable, quick, and visually communicates a more deliberate action than a single-modifier chord. The owner accepts that this changes the default Editor shortcut; Radar must disclose that trade-off honestly.

**Consequence:** Re-audit before implementation and release. A plain install previews and refuses the existing Editor action. A separately named replacement option may proceed only when source, live binding, and personal configuration prove the exact unmodified default. Every other conflict is refused.

## D003 — Manage the shortcut explicitly, never through hidden installation side effects

**Decision:** Ship a dedicated `install`, `status`, and `remove` helper that owns one delimited block in the user’s `bindings.lua`; the replacement path requires an explicit `--replace-default-editor` authorization.

**Why:** The current third-party manifest has no declarative global-shortcut contract, and normal plugin installation intentionally does not execute install hooks. User configuration deserves explicit consent and reversible mutation.

**Consequence:** Public installation has a separate shortcut step and names the lost Editor chord before mutation. The managed block unbinds the default and binds Radar; deleting that exact block restores the upstream Editor behavior automatically. Plugin removal instructions remove the block first. Symlinked, personal, modified, conflicting, ambiguous, or invalid configuration is refused and falls back to documented manual guidance.

## D004 — Ship an on-demand panel without a resident service

**Decision:** Version 1 manifest declares only `panel` and omits `keepLoaded`.

**Why:** The shortcut can summon a panel directly. Cached-first loading provides speed without background CPU, timers, network activity, or another singleton in the long-running shell.

**Consequence:** Durable state lives in XDG files, every open restores it, and every close terminates owned work.

## D005 — Do not ship a top-bar widget in version 1

**Decision:** No `bar-widget` kind or invisible bar placeholder belongs in the main plugin.

**Why:** Many Omarchy bars are already crowded. The current enable contract places a bar widget into the layout, so a supposedly optional same-manifest indicator would create awkward lifecycle and hidden-state coupling.

**Consequence:** If demand is proven, build a separate optional companion plugin with independent installation, geometry, pointer, and lifecycle evidence.

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

**Decision:** Installed-plugin matching, seen state, saves, filters, and preferences stay on the device.

**Why:** Server personalization is unnecessary for a generic public feed and would create accounts, identifiers, storage, and trust obligations.

**Consequence:** The server cannot provide cross-device sync or global unread counts. The plugin sends the same generic feed request for every user.

## D011 — Use Python standard library plus native QML

**Decision:** Python owns deterministic data logic and QML owns native presentation. No third-party runtime dependency is approved.

**Why:** Current Omarchy already ships Python and the plugin shell. This keeps installation offline, reviewable, and small.

**Consequence:** Implement small focused utilities rather than importing web, feed, HTTP, schema, or UI frameworks. Any exception needs a recorded review.

## D012 — Establish a silent baseline before publishing marketplace diffs

**Decision:** The first successful marketplace collection records state and emits no historical plugin events.

**Why:** Treating an existing catalog of roughly two thousand items as new would destroy trust immediately.

**Consequence:** Bootstrap is explicit and auditable. A baseline reset is a maintenance operation and cannot happen silently in CI.

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
