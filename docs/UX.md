# UX contract

## Character

Radar should feel like unfolding a compact morning paper inside Omarchy: editorial hierarchy, generous rhythm, sharp typography, and a finite edition. It must not resemble a notification drawer, package manager, analytics dashboard, or dense GitHub activity log.

The newspaper metaphor is visual and organizational, not nostalgic decoration. Avoid fake paper textures, ornamental ink noise, novelty page turns, and inaccessible multi-column reading order.

## Primary invocation

The recommended global shortcut is `Super+Alt+N` for “news.” Audited Omarchy Quattro defaults and the disposable live binding set leave that chord free, while `Super+Shift+N` remains the Editor launcher. Radar never displaces Editor or any other action.

Shortcut installation is a separate, explicit setup action after plugin enablement. `status` performs a read-only inspection. `install` may add one managed Radar binding only when the live binding table and personal override file both show that `Super+Alt+N` is free. The setup tool refuses every conflict, writes only its owned managed block, validates a Hyprland reload, and supports exact removal. Removing the block releases `Super+Alt+N`; the Editor binding is unchanged throughout.

The plugin must remain openable through documented shell IPC even without the shortcut:

```bash
omarchy-shell shell summon io.github.mtolhuys.news-radar
```

An optional XDG application entry exposes **Omarchy News Radar** with its bundled newspaper mark in Omarchy's normal Apps menu. Its action summons the same panel through shell IPC. The shortcut, Apps row, and newspaper all share one state model: closed opens and focuses; open but obscured raises and focuses; already foreground stays open and focused. Repeated activation is never a close gesture. `Escape`, `q`, the close control, and window-manager close are the consistent close routes. Installation and removal are explicit because the current third-party plugin lifecycle runs no hooks; the helper may mutate only its receipt-backed desktop entry and icon.

## Surface

Version 1 is an on-demand normal desktop window paired with a default-on, optional top-bar newspaper. The panel entry point creates a compositor-managed `FloatingWindow` with a bounded minimum size. It is movable, resizable, maximizable, and participates in ordinary `Alt+Tab`; closing it through window management follows the same state/process teardown as `Escape`. Radar does not expose a minimize button because that action is unreliable in the supported hosted-window lifecycle.

The panel has four stable visual zones:

1. **Masthead:** Omarchy News Radar, local date, edition freshness, source health, and close action.
2. **Section rail:** Front Page, For You, Core, Plugins, and Saved with bounded counts.
3. **Edition:** one lead item followed by compact secondary stories in a responsive reading grid.
4. **Story inspector:** optional preview image and credit, source, event type, occurrence time, tags, compatibility, verification boundary, summary, compact icon metrics and caveat, save action, human-facing marketplace page when applicable, and original-source action.

Wide layouts may use two visual columns, but the semantic and keyboard order remains one canonical sequence. Narrow and large-text layouts collapse to one column, place masthead/window controls on a reachable second row, and wrap story actions without changing content or controls. Preferred and minimum window geometry clamp to the active screen so large text cannot make the surface exceed the monitor.

A compact keyboard guide sits directly below search instead of at the bottom of the section rail. It includes section, story, source, save, read-state, pagination, and update-check keys. The **Check for updates** control also repeats `R` on hover. Meaningful secondary text uses a contrast-preserving tier derived from the panel foreground in both light and dark themes; the ambient muted token is not used for reader content.

## Front page composition

The front page is finite. The initial viewport should communicate the most important changes without requiring search or scrolling through routine events.

- One lead item may receive the largest treatment.
- Up to six secondary items may appear above the fold.
- Remaining activity is grouped by section and date.
- Every story row states `UNREAD` or `READ`, section badges expose unread counts, and the inspector exposes the exact selected-story toggle.
- No autoplay, carousel, ticker, infinite scroll, or continuously moving decoration is allowed. A visible Load more control may reveal the next twelve matches from the already downloaded edition, up to the feed bound.

## Keyboard model

All behavior must remain reachable without a pointer:

| Key | Action |
| --- | --- |
| `Super+Alt+N` | Summon or raise Radar after explicit conflict-free setup |
| `Escape` or `q` | Close Radar |
| `j` / `Down` | Select next story |
| `k` / `Up` | Select previous story |
| `Enter` or `o` | Open selected original source |
| `s` | Save or unsave selected story locally |
| `u` | Mark the selected story read or unread locally |
| `/` | Focus search/filter input |
| `r` | Check the published edition; **Check for updates** repeats this shortcut on hover |
| `Tab` / `Shift+Tab` | Cycle to the next / previous primary section |
| `1`–`5` | Switch between the five primary sections |
| `Home` / `End` | Select first or last story in the current section |

Shortcuts must not fire while a text field is actively editing, except `Escape` to leave or close in the documented order. Every pointer action must have an equivalent keyboard route and visible focus treatment.

## Section settings, filters, and pagination

Each section exposes a cogwheel named **Settings**. Names, icons, order, background, and source scope remain canonical so two sections cannot look interchangeable or imply that their editorial scope moved. The screen visibly lists that fixed source membership, then offers only actionable local refinements for time window, significance, unread-only, images-only, and relevant event types. There is no renaming control or explanatory filler.

Filters apply only to that section, persist in private state, never alter the public feed, and can be reset exactly. Counts reflect each section's active filter; search further narrows only the current visible projection.

Each section header exposes **Mark all as read** while that filtered section has unread stories. It marks every unread story matching the section's persistent Settings filters, including stories beyond the loaded page, through one atomic local-state update. Temporary search does not change the batch scope. The control is disabled while another reading/state mutation is pending and reports completion before the projection reloads.

The initial projection contains at most twelve stories. Load more increases that local limit by twelve, never performs a network request, and states when all matching stories are loaded. Down from the final visible story focuses the control and changes its label to the explicit Enter action, Up returns to the story list, and Enter expands the page while preserving the prior selection; the next Down reaches the first newly revealed story.

## Read and saved semantics

Every projected story has one explicit local `isUnread` fact. A pointer click, `j`/`k`, `Home`/`End`, or source/plugin-page activation deliberately selects that story and marks only its event ID read. Pointer hover and the default selection on open do not count as reading. The inspector action and `u` key toggle the selected story in either direction; **Mark all as read** is the one explicit batch action.

Closing, refreshing, or merely rendering a feed never marks unrelated stories read. State v9 retains state v7's migrated `readThrough` baseline and bounded canonical `readOverrides` map for exact per-event decisions while removing the obsolete interests and section-profile fields. Overrides outside the current bounded edition are pruned on the next reading-state mutation. Saved state is independent from read state. Events no longer present in the live bounded feed may remain in local saved metadata with their original source fields.

If a queued per-story write becomes stale because refresh atomically replaced the edition first, the helper leaves current state unchanged and the panel quietly reprojects. That normal race never presents as a feed or storage failure.

## State model

| State | Visible behavior | Recovery |
| --- | --- | --- |
| First use | Explains the empty cache and starts one refresh | Wait or retry |
| Cached | Shows last-known-good edition immediately with age | Background refresh |
| Checking | Keeps cached content readable and shows a restrained animated indicator on **Check for updates** | Wait or cancel by closing |
| Updated | Adopts the newer edition atomically and reports its exact new-story count | Read normally |
| No newer edition | Reports the artifact publication age without implying a source crawl | Read normally |
| Publisher stale | Shows publisher lag when artifact publication exceeds 90 minutes, even if old source checks succeeded | Wait for publication or use an intentional local edition |
| Offline | Keeps cache and labels the failed check, artifact age, and local cache age | Retry |
| Source partial | Keeps valid events and names unavailable source adapters | Retry later |
| Empty | Valid feed contains no events in the selected section | Change section or filters |
| Filtered empty | Current filters match nothing | Clear filters |
| Invalid feed | Rejects candidate, preserves cache, explains validation failure | Retry or inspect diagnostics |
| No cache and failed | Gives a concise failure and direct retry action | Retry when online |
| Local live edition | Shows an owner-built edition collected from live allowlisted sources, including the number of validated images available | Rerun `make local-latest` |

## Source opening

Titles, summaries, tags, image alternatives, credits, and URLs are untrusted data. Display text is plain text. Source URLs appear as labels but open only through a dedicated button or keyboard action. The UI never renders remote HTML, Markdown, SVG, scripts, or embedded media. It loads images only from content-addressed paths in the validated feed, resolved against that feed's fixed origin; the publisher has already mirrored and inspected those raster bytes. Missing or failed imagery leaves the complete text story intact.

The image preference always reports whether the current edition actually contains validated images. Turning it on when an edition has no images must not imply that an image is loading or available.

## Top-bar newspaper

The main manifest declares both `panel` and `bar-widget`; normal enablement places one newspaper in the right section. The widget shows a bounded unread count plus distinct publisher/source health. Left click summons or raises the same panel, middle click checks the published edition, and right click hides the widget after writing the local preference. Its hidden root is invisible, so Omarchy's module slot computes exact zero width and height rather than reserving a phantom gap.

Tune Your Radar in the panel exposes “Top-bar newspaper” as an On/Off control, so a hidden widget can be restored through the global shortcut or documented IPC. Hiding stops its due-checked network timer. It emits no desktop notification and keeps no separate companion lifecycle.

## Visual language

- Use current Omarchy `Color`, `Style`, and `Border` contracts rather than hard-coded theme colors or sizes.
- Use the system monospace family and Omarchy type scale; distinguish masthead, section, headline, summary, metadata, and source through hierarchy rather than excessive color.
- Accent marks focus, selection, and one lead rule. Urgent color is reserved for actual source or compatibility warnings.
- A selected row must pair its fill with explicit primary and secondary foregrounds. It must never keep an ambient muted token that can blend into the selected fill; this is visually accepted in maintained dark and light themes.
- Dense metadata remains secondary and collapsible; the main reading path prioritizes headline and summary.
- Any motion is bounded to active refresh and has equivalent literal status text. There is no perpetual radar sweep.

## Accessibility boundary

The panel must expose meaningful roles, names, focus order, selected state, section counts, refresh status, source health, and actionable labels. Visual columns must not create a different reading order from keyboard or assistive technology.

Release acceptance includes keyboard-only traversal, visible focus in light and dark themes, long titles, repaired control characters, narrow layout, 200% text scaling, reduced motion, and exact text alternatives for icons and trust markers. Full screen-reader claims require explicit assistive-technology evidence and must not be inferred from QML metadata alone.
