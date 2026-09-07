# UX contract

## Character

Radar should feel like unfolding a compact morning paper inside Omarchy: editorial hierarchy, generous rhythm, sharp typography, and a finite edition. It must not resemble a notification drawer, package manager, analytics dashboard, or dense GitHub activity log.

The newspaper metaphor is visual and organizational, not nostalgic decoration. Avoid fake paper textures, ornamental ink noise, novelty page turns, and inaccessible multi-column reading order.

## Primary invocation

The recommended global shortcut is `Super+Alt+N` for “news.” Audited Omarchy Quattro defaults and the disposable live binding set leave that chord free, while `Super+Shift+N` remains the Editor launcher. Radar never displaces Editor or any other action.

Shortcut installation is a separate, explicit setup action after plugin enablement. `status` performs a read-only inspection. `install` may add one managed Radar binding only when the live binding table and personal override file both show that `Super+Alt+N` is free. Because that initial action explicitly creates a Radar-managed block, version 0.1.6 and later may automatically migrate only its byte-exact unmodified 0.1.3 form from `toggle` to `summon` when Omarchy reloads the widget after an update. The migration creates a private backup, atomically reloads and validates Hyprland, and rolls back on failure; it cannot install a free chord or touch edited, personal, conflicting, multiple, symlinked, or ambiguous configuration. **Update shortcut** remains a visible retry when automatic validation cannot complete. Removing either exact current or legacy block releases `Super+Alt+N`; the Editor binding is unchanged throughout.

The plugin must remain openable through documented shell IPC even without the shortcut:

```bash
omarchy-shell shell summon io.github.mtolhuys.news-radar
```

An optional XDG application entry exposes **Omarchy News Radar** with its bundled newspaper mark in Omarchy's normal Apps menu. Its action summons the same panel through shell IPC. The shortcut, Apps row, and newspaper all share one state model: closed opens and focuses; already foreground stays open and focused; choosing another window dismisses Radar and a later summon reopens it with retained local reading state. Repeated foreground activation is never a close gesture. `Escape`, `q`, the close control, window-manager close, and focus transfer are consistent shell-lifecycle close routes. Installation and removal are explicit because the current third-party plugin lifecycle runs no hooks; the helper may mutate only its receipt-backed desktop entry and icon.

## Surface

Version 1 is an on-demand normal desktop window paired with a default-on, optional top-bar newspaper. The panel entry point creates a compositor-managed `FloatingWindow` with a bounded minimum size. It is movable, resizable, maximizable, and visible to ordinary task switching while active. Because Hyprland keeps floating windows visually above tiled windows, transferring focus dismisses Radar through the same state/process teardown as `Escape`; this lets the chosen app become both active and unobscured. Radar does not expose a minimize button because that action is unreliable in the supported hosted-window lifecycle.

Wide source-reader views have four visual zones when a story is selected; Home and My setup use the overview described below, and empty readers omit the inspector:

1. **Masthead:** Omarchy News Radar and compact window/update actions.
2. **Section rail:** Front Page, For You, Core, Plugins, YouTube, and Saved with bounded counts; a compact capped rail so labels and counts fit without empty gutters; the collapsible **Keys** legend lives at the bottom of this rail as `Keys · ?` and starts fully collapsed with no shortcut dump.
3. **Edition:** Core, and Front Page Omarchy News / Core-tagged stories, are quiet headlines—title plus a human date, with an unread mark allowed and no teaser, metric strip, or plugin thumbnail. Plugins, YouTube, and For You may keep denser teaser/metric/thumbnail cards. In wide readers the list is a compact index beside the selected story's reading surface.
4. **Story inspector:** the dominant reading pane beside a selected story. Article stories (`omarchy-news` and other Core long-text items) lead with a large title, one quiet `date · source` line, a divider, and the full article body immediately, then compact read/save/source actions. Validated HTTPS links inside that body render as accent-colored labels and open through the same helper as **Original source**. TYPE/TRUST/AUDIT/COMPAT and the raw URL live in a collapsed **Details** footer. YouTube may keep its validated thumbnail and compact metrics above the description because those facts are part of scanning a video.

Wide readers use an index and inspector beside the section rail, with one canonical keyboard order. Narrow and large-text layouts use one content column beside the rail, place masthead/window controls on a reachable second row, and keep the full story body and primary reading actions reachable. Preferred and minimum window dimensions clamp to the active screen dimensions. The section rail scrolls when its content exceeds the available height, and keyboard section changes reveal the selected control. When the rail fits, Keys remains at its bottom.

In a compact reader, the selected row expands to the full title, human date and source, and untruncated body; other rows remain quiet headlines. Its body uses the same escaped article-segment renderer and validated HTTPS link actions as the wide inspector, with a plain-text fallback for other story types. The shared read/save/context/source toolbar scrolls with the reading content and an already-loaded footer does not reserve the remaining viewport. Enlarging text while the window is open must leave a usable article viewport and reachable controls. Font and monitor changes preserve a fitting user placement and automatically refit an out-of-bounds floating frame without taking focus; normal tiling and maximization remain controlled by the compositor.

The reading surface does not carry publication telemetry. A subtle collapsible **Keys** footer at the bottom of the left **SECTIONS** rail shows the real bindings as quiet unboxed key·action pairs (no heavy keycap chrome) only after it is opened; collapsed state is the single `Keys · ?` label with no shortcut preview. It remembers open/closed only for the session (no schema). **Keys · ?** or keyboard `?` toggles it. Search includes its `/` hint, **Check for updates** repeats `R` on hover, focused controls expose their actions, and the documented keyboard map remains complete. Meaningful secondary text uses a contrast-preserving tier derived from the panel foreground in both light and dark themes; the ambient muted token is not used for reader content.

## Front page composition

Front Page contains a persistent local briefing of at most five groups alongside its Home discoveries and setup updates. The briefing is selected once after cached news and locally enabled plugin IDs are available. It groups eligible unread occurrences of the same plugin without replacing their original titles, IDs, timestamps, or sources. A plain reason explains each selection. In the briefing reader, narrow layouts use the briefing notice as their heading and counts, avoiding a duplicate section heading and default summary; active filter and retained-read explanations remain visible. See D055 and the curation contract for the deterministic allocation.

Wide Home and My setup views use balanced two-column newspaper rows. Cards in a row share its height, and an unpaired final card spans the full row instead of leaving an empty cell. Briefing actions stay directly beneath their status copy. Project and workflow details use a centered bounded reading measure; workflow members become descriptive project cards, hero images are narrower than that measure, release notes are distinct bordered entries, and follow/mute scopes form balanced cards. Narrow views collapse these grids to one column.

- Reading, refreshing, filtering, search, closing, and reopening preserve the exact snapshot. They do not refill its slots. New briefing explicitly replaces it from currently unread eligible stories; skipped stories remain unread.
- The notice reports remaining groups and completion for this briefing only. Other sections remain available. An expired member is disclosed and does not imply that it was read; a new briefing can replace the expired snapshot.
- Show updates exposes every retained original event in a plugin group. Selecting the representative reads only that event; Mark group read and Mark briefing read are separate exact-membership actions.
- Narrow layouts place the group controls in the scrollable story list header; long group histories have their own bounded viewport. One lead item may receive the largest treatment on dense cards.
- Core and Front Page article index rows are quiet headlines (title + human date). Plugin rows on Front Page may keep a short cleaned teaser; YouTube stays in its own section. Selecting an article exposes the full official body after a `date · source` line and divider: in the wide inspector before its actions and collapsed Details, or within the selected compact row beneath the shared reading toolbar.
- Dense cards state `UNREAD` or `READ`; quiet headlines use an unread mark instead of a kicker. Section badges expose unread counts, and the inspector exposes the exact selected-story toggle.
- No autoplay, carousel, ticker, infinite scroll, or continuously moving decoration is allowed. In sections other than Front Page, a visible Load more control may reveal the next twelve matches from the already downloaded edition, up to the feed bound.

## Keyboard model

Primary navigation and reading actions must remain reachable without a pointer:

| Key | Action |
| --- | --- |
| `Super+Alt+N` | Summon or raise Radar after explicit conflict-free setup |
| `Escape` | Leave details or an open control surface, then close Radar |
| `q` | Close Radar during normal navigation |
| `j` / `Down` | Select next overview card or story; crossing the story viewport bottom anchors that complete row at the top |
| `k` / `Up` | Select previous overview card or story; crossing the story viewport top keeps that row visibly anchored |
| `Left` / `Right` | Move to the overview card beside the current card when that visual row has one |
| `Enter` or `o` | Open the selected overview card, or the selected original source in a reader |
| `s` | Save or unsave selected story locally |
| `u` | Mark the selected story read or unread locally |
| `a` | Mark this briefing read on Front Page; elsewhere mark unread stories matching this section's Settings read |
| `F6` | Enter or leave Home, My setup, or briefing controls; Tab / Shift+Tab cycles their available cards and actions |
| `Up` / `Down`, `Home` / `End`, `Enter` in group history | Choose a source occurrence, then open its original source |
| `f` | Toggle this section's **Unread only** filter (same as the header chip) |
| `?` | Show or hide the collapsible Keys legend |
| `/` | Focus search/filter input |
| `r` | Check the published edition; **Check for updates** repeats this shortcut on hover |
| `Tab` / `Shift+Tab` | Cycle to the next / previous primary section |
| `1`–`N` | Switch between the currently visible primary sections |
| `Home` / `End` | Select first or last card or story in the current view |
| `Page Up` / `Page Down` | Scroll the current overview or reading surface without changing selection, read state, or saves |

Shortcuts must not fire while a text field is actively editing, except `Escape` to leave or close in the documented order. Primary controls must have keyboard routes and visible focus treatment. Inline body links currently activate by pointer; Enter/`o` and the dedicated source control provide keyboard access to the story's original source. Individual inline-link keyboard traversal is not implemented and must not be claimed as accepted accessibility support.

## Section settings, filters, and pagination

Each section exposes a cogwheel named **Settings**. Names, icons, order, background, and source scope remain canonical so two sections cannot look interchangeable or imply that their editorial scope moved. The screen visibly lists that fixed source membership, then offers only actionable local refinements for time window, significance, unread-only, images-only, and relevant event types. YouTube labels that same period control **TIME RANGE**. There is no renaming control or explanatory filler.

Filters apply only to that section, persist in private state, never alter the public feed, and can be reset exactly. Counts reflect each section's active filter; search further narrows only the current visible projection. Under **Unread only**, a story deliberately read during the current view remains in its existing position: dense rows change to **READ**, while quiet headlines lose their unread mark. The section explains that read stories are temporarily retained until the user changes section, search, or filters. The true unread count decreases immediately; a later view excludes the read story normally.

Each section header exposes an **All** / **Unread only** chip and **Settings**. Front Page uses the briefing notice's exact **Mark briefing read** action; other sections expose **Mark all as read**. The chip mirrors the Settings **Unread only** control: selected when `unreadOnly` is on, labels **Unread only** when filtering and **All** when not, and calls the same persistent `updateFilter("unreadOnly", …)` path. Keyboard `f` flips that flag when Settings, preferences, and search are not editing. **Mark all as read** remains available while that filtered section has unread stories; keyboard `a` triggers the same action and no-ops when nothing is unread or a mutation is already pending. It marks every unread story matching the section's persistent Settings filters, including stories beyond the loaded page, through one atomic local-state update. Temporary search does not change the batch scope. The control is disabled while another reading/state mutation is pending and reports completion before the projection reloads.

The initial projection contains at most twelve stories. Keyboard movement never leaves the selected row outside the viewport: when Down crosses the bottom edge, a short eased scroll anchors the complete selected row at the top; when Up crosses the top edge, the viewport moves before selection so held key-repeat cannot outrun the highlight. Ordinary row-by-row movement continues while the next row remains visible. Load more increases the local limit by twelve, never performs a network request, and states when all matching stories are loaded. Down from the final loaded story focuses the control and changes its label to the explicit Enter action. Because that story remains selected, Up only returns navigation focus and preserves the exact viewport; Enter expands the page while preserving the prior selection, and the next Down reaches the first newly revealed story.

## Read and saved semantics

Every projected story has one explicit local `isUnread` fact; a grouped row additionally shows the number of unread members, which can remain positive after its representative was read. On first use, a modal offers **Browse current stories** and **Start from today** before any implicit reading. Browse is the initially focused non-destructive choice. Tab cycles the two choices; Enter activates the focused choice. At large text sizes, the explanation scrolls and the choices remain reachable. The displayed count and membership digest come from the same locked projection. Start from today marks exactly those retained IDs read, preserves saves, preferences, and explicit unread overrides, and leaves later arrivals unread regardless of occurrence time. A changed membership requires a fresh displayed choice. Valid existing v1–v11 states migrate with onboarding already complete and no read changes.

After onboarding, a fresh panel open into a source reader treats its first visibly presented selected story as read once after a brief stable dwell. Home, My setup, and insight details never read a hidden story. The one-shot waits for the first non-empty projection, captures that event ID and panel-open generation, and uses the same per-story mutation only if the same generation remains visible with that exact story still selected. Automatic opening reprojections update the candidate and restart the dwell rather than losing or duplicating the action. A pointer click, `j`/`k`, `Home`/`End`, or source/plugin-page activation likewise marks only the selected event ID read and cancels any pending automatic action. Pointer hover, re-summoning an already open panel, refresh, section/filter reprojection, and later arrivals do not repeat the initial action. Opening Tune or Settings before the dwell completes cancels it because the story is no longer the active surface. The inspector action and `u` key toggle the selected story in either direction; **Mark group read**, **Mark briefing read**, and the other sections' **Mark all as read** actions each state their distinct batch scope.

Closing, refreshing, or merely rendering a feed never marks unrelated stories read. On a fresh open after onboarding, an initially empty projection keeps the one-shot armed so the first story actually presented by that open receives the same behavior; closing cancels it. The first-use choice also cancels the one-shot, so browsing leaves the backlog unread. State v12 retains the migrated `readThrough` baseline, bounded canonical `readOverrides`, saved records, and preferences; it adds the local onboarding choice and exact briefing snapshot. Overrides outside the current bounded edition are pruned on the next reading-state mutation. Saved state is independent from read state. Events no longer present in the live bounded feed may remain in local saved metadata with their original source fields.

If a queued per-story write becomes stale because refresh atomically replaced the edition first, the helper leaves current state unchanged and the panel quietly reprojects. That normal race never presents as a feed or storage failure.

## State model

| State | Visible behavior | Recovery |
| --- | --- | --- |
| First use | Loads a valid cache or checks the feed, then offers Browse current stories / Start from today | Choose explicitly; neither rendering nor waiting marks news read |
| Briefing complete | Says that this briefing is caught up; its rows remain available | Explicit New briefing when another eligible selection exists |
| Cached | Shows last-known-good news immediately without an edition-status banner | Background refresh |
| Checking | Keeps cached content readable and shows a restrained animated indicator on **Check for updates** | Wait or cancel by closing |
| Updated | Adopts the newer edition atomically without adding persistent status copy | Read normally |
| No newer edition | Leaves the current news unchanged | Read normally |
| Publisher stale | Keeps validated cached news readable; operational monitoring carries publication-age detail | Wait for publication |
| Offline | Keeps validated cached news readable without replacing it with network diagnostics | Retry later |
| Source partial | Keeps valid events and names unavailable source adapters | Retry later |
| Empty | Valid feed contains no events in the selected section | Change section or filters |
| Filtered empty | Current filters match nothing | Clear filters |
| Invalid feed | Rejects candidate, preserves cache, explains validation failure | Retry or inspect diagnostics |
| No cache and failed | Gives a concise failure and direct retry action | Retry when online |
| Local live edition | Shows the owner-built news normally; edition-origin detail remains internal | Rerun `make local-latest` when desired |

## Source opening

Titles, summaries, tags, image alternatives, credits, and URLs are untrusted data. Display text is plain text except for the article reading pane, which may turn collector-preserved HTTPS link markers into accent-colored `<a href>` labels built from escaped text. Those links open only through the same `open-source` helper as **Original source**; javascript, http, and other unsafe hrefs are dropped at collect time and ignored in the pane. The UI never renders remote HTML, Markdown, SVG, scripts, or embedded media from the feed. It loads images only from direct `image.sourceUrl` values on the exact allowlisted marketplace/YouTube HTTPS families or validated legacy content-addressed `image.path` values from older caches. The publisher has already inspected marketplace raster bytes; YouTube URLs must match the fixed thumbnail shape. Missing or failed imagery leaves the complete text story intact.

The image preference always reports whether the current edition actually contains validated images. Turning it on when an edition has no images must not imply that an image is loading or available.

## Top-bar newspaper

The main manifest declares both `panel` and `bar-widget`; normal enablement places one newspaper in the right section. The widget shows the deduplicated number of unread stories reachable through at least one current persistent section projection plus distinct publisher/source health. A story hidden by every section's Settings cannot keep the badge active, and one story appearing in multiple sections counts once. Left click summons or raises the same panel, middle click checks the published edition, and right click hides the widget after writing the local preference. Its hidden root is invisible, so Omarchy's module slot computes exact zero width and height rather than reserving a phantom gap.

Tune Your Radar in the panel exposes “Top-bar newspaper”, story images, and Core/Plugins/YouTube visibility as On/Off controls, so a hidden widget or rail can be restored through the global shortcut or documented IPC. While visible, it checks from the last real attempt at most every five minutes after either success or failure, and watches the validated feed cache so unread and health change without opening the panel. Hiding stops its due-checked network timer. It emits no desktop pop-up notification and keeps no separate companion lifecycle.

## Visual language

- Use current Omarchy `Color`, `Style`, and `Border` contracts rather than hard-coded theme colors or sizes.
- Use one Omarchy-and-radar visual identity rather than stacking two complete symbols. The official full-strength green Omarchy logo remains primary; two compact amber radar rings, one sweep, and one blip live inside its central negative space and must remain distinct at 24 pixels. Launcher-like surfaces use an opaque dark badge so recognition never depends on the compositing surface. Inside the panel, use transparent dark/light contrast variants on the theme-native header plate so light themes never receive a pasted-on black box.
- Use the system monospace family and Omarchy type scale; distinguish masthead, section, headline, summary, metadata, and source through hierarchy rather than excessive color.
- Accent marks focus, selection, and one lead rule. Urgent color is reserved for actual source or compatibility warnings.
- A selected row must pair its fill with explicit primary and secondary foregrounds. It must never keep an ambient muted token that can blend into the selected fill; this is visually accepted in maintained dark and light themes.
- Dense metadata remains secondary inside collapsed Details; the main reading path prioritizes headline, `date · source`, full article body, and intentional actions.
- Motion is limited to active refresh, brief viewport adjustments, and normal compositor window transitions. There is no perpetual radar sweep or persistent pipeline-status copy.

## Accessibility boundary

The panel must expose meaningful roles, names, focus order, selected state, section counts, refresh status, source health, and actionable labels. Visual columns must not create a different reading order from keyboard or assistive technology.

Release acceptance includes keyboard-only traversal, visible focus in light and dark themes, long titles, repaired control characters, narrow layout, 200% text scaling, reduced motion, and exact text alternatives for icons and trust markers. Full screen-reader claims require explicit assistive-technology evidence and must not be inferred from QML metadata alone.

## Expanded home, setup and relevance (0.5.0)

Front Page opens a scrollable home overview. The retained brief is one section alongside setup changes, recent marketplace additions and dated version changes. A finished brief remains finished and those other sections remain useful. No hidden reader selection is implicitly read; opening a briefing card deliberately enters the reader. Source-section read behavior remains unchanged.

For You opens directly into personal news on every section activation. My setup remains an explicit secondary tab. A setup card leads with the enabled version, documented version and a precise comparison label. Unknown or incomparable versions say so. Details provide plain-text source notes and original links; they never install or update software. Workflow details explain the idea, its review basis and the related projects. A project can be opened from a workflow and Back returns to that workflow before leaving details.

Context & follows exposes project, source and stable creator targets. Project and creator Follow controls, source/project/creator Mute future news controls, and clear controls operate on local state. Legacy source-wide follows stay clearable but no longer contribute personal news or future briefing candidates. Following & muted exposes the complete saved choices even when their source story is no longer visible. Muting changes future selection and source browsing; it cannot rewrite the current briefing or hide Saved. Every control must remain keyboard-reachable and visible at large text sizes.

The window lifecycle prepares an exact pre-map float/placement rule before revealing the normal window. Cached local projection has priority over network freshness, with a bounded recovery deadline. Saved geometry is clamped to usable connected-monitor space, and repeated summon keeps the active control. Final runtime evidence determines the precise compositor-close persistence boundary; do not claim unsupported older compositor behavior.

## Empty selections and truthful status

The wide source-reader inspector and its separator appear only when a story is selected; compact readers show that selected body inline. Per-story actions are absent without a selection. An empty source section or search uses the available reading width for a concise explanation and one useful recovery action. A completed briefing keeps Home and its discoveries reachable through Front Page; it does not require a new briefing to explore them. Home and My setup reset their scrolling when changing routes, and keyboard actions cannot mark, save or open a nonexistent story.

Project and workflow details traverse original source links in their rendered order before the share action. Opening a different detail starts at its heading; changing Follow/Mute within the same project preserves its scroll and focused control.

Local development candidates that already contain every upstream commit do not display an update warning. Divergent history is described as unavailable automatic updating without claiming that the public branch is a newer release.

The public Home presents at most seven selected headlines with short readable teasers before its workflow ideas. A weekly edition and RSS remain available for broader browsing. Article links retain usable source destinations; card teasers show their labels without raw link syntax. Marketplace metadata appears only where applicable.

## Unread navigation and filter feedback

The rail heading is SECTIONS · UNREAD and every badge is the section unread count. All/Unread only changes the visible story total, not the unread badge. Other saved filters still scope that section. The toolbar places its heading above wrapping actions so Settings remains visible; the summary explains how many read stories Unread only hides. Reading state is shared across sections and is never reset to make a counter larger.

## Automatic discovery candidate

Discovery headings are **New in the marketplace** and **Latest changes**. Every card shows the event date and a factual selection label. Enter opens original source text with provenance and optional matching notes; all actions retain arrow/Tab navigation. These sections update with the feed even after the finite briefing is finished. They ignore inbox unread/time filters, but respect search, mutes and hidden source sections. Quiet-period retention is explicitly labelled with the original activity date. Opening a discovery detail does not implicitly mark a briefing item read.
