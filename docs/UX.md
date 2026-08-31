# UX contract

## Character

Radar should feel like unfolding a compact morning paper inside Omarchy: editorial hierarchy, generous rhythm, sharp typography, and a finite edition. It must not resemble a notification drawer, package manager, analytics dashboard, or dense GitHub activity log.

The newspaper metaphor is visual and organizational, not nostalgic decoration. Avoid fake paper textures, ornamental ink noise, novelty page turns, and inaccessible multi-column reading order.

## Primary invocation

The recommended global shortcut is `Super+Alt+N` for “news.” Audited Omarchy Quattro defaults and the disposable live binding set leave that chord free, while `Super+Shift+N` remains the Editor launcher. Radar never displaces Editor or any other action.

Shortcut installation is a separate, explicit setup action after plugin enablement. `status` performs a read-only inspection. `install` may add one managed Radar binding only when the live binding table and personal override file both show that `Super+Alt+N` is free. The setup tool refuses every conflict, writes only its owned managed block, validates a Hyprland reload, and supports exact removal. Removing the block releases `Super+Alt+N`; the Editor binding is unchanged throughout.

The plugin must remain openable through documented shell IPC even without the shortcut:

```bash
omarchy-shell shell toggle io.github.mtolhuys.news-radar
```

## Surface

Version 1 is an on-demand normal desktop window paired with a default-on, optional top-bar newspaper. The panel entry point creates a compositor-managed `FloatingWindow` with a bounded minimum size. It is movable, resizable, maximizable, and participates in ordinary `Alt+Tab`; closing it through window management follows the same state/process teardown as `Escape`. Radar does not expose a minimize button because that action is unreliable in the supported hosted-window lifecycle.

The panel has four stable visual zones:

1. **Masthead:** Omarchy News Radar, local date, edition freshness, source health, and close action.
2. **Section rail:** Front Page, For You, Core, Plugins, Community, and Saved with bounded counts.
3. **Edition:** one lead item followed by compact secondary stories in a responsive reading grid.
4. **Story inspector:** optional preview image and credit, source, event type, occurrence time, tags, compatibility, verification boundary, summary, compact icon metrics and caveat, save action, human-facing marketplace page when applicable, and original-source action.

Wide layouts may use two visual columns, but the semantic and keyboard order remains one canonical sequence. Narrow layouts collapse to one column and wrap story actions without changing content or controls. Preferred and minimum window geometry clamp to the active screen so large text cannot make the surface exceed the monitor.

## Front page composition

The front page is finite. The initial viewport should communicate the most important changes without requiring search or scrolling through routine events.

- One lead item may receive the largest treatment.
- Up to six secondary items may appear above the fold.
- Remaining activity is grouped by section and date.
- The interface states exactly what “since last read” means.
- No autoplay, carousel, ticker, infinite scroll, or continuously moving decoration is allowed. A visible Load more control may reveal the next twelve matches from the already downloaded edition, up to the feed bound.

## Keyboard model

All behavior must remain reachable without a pointer:

| Key | Action |
| --- | --- |
| `Super+Alt+N` | Toggle Radar globally after explicit conflict-free setup |
| `Escape` or `q` | Close Radar |
| `j` / `Down` | Select next story |
| `k` / `Up` | Select previous story |
| `Enter` or `o` | Open selected original source |
| `s` | Save or unsave selected story locally |
| `/` | Focus search/filter input |
| `r` | Refresh the feed |
| `Tab` / `Shift+Tab` | Cycle to the next / previous primary section |
| `1`–`6` | Switch between the six primary sections |
| `Home` / `End` | Select first or last story in the current section |

Shortcuts must not fire while a text field is actively editing, except `Escape` to leave or close in the documented order. Every pointer action must have an equivalent keyboard route and visible focus treatment.

## Section settings, filters, and pagination

Each section exposes a cogwheel named **Settings**. Its options screen permits a bounded plain-text display name, one large semantic icon from a closed six-item palette, and one background from a closed four-tone palette derived from current Omarchy colors. Appearance applies only to that section, persists privately, and has an exact per-section reset.

The same screen visibly lists source membership as read-only. Source membership remains dictated by the edition contract: customization cannot silently turn Core into marketplace news or Community into an arbitrary feed. The screen then shows the immutable built-in section rule and local refinements for time window, significance, unread-only, images-only, and relevant event types. Filters apply only to that section, persist in private state, never alter the public feed, and can be reset exactly. Counts reflect each section's active filter; search further narrows only the current visible projection.

The initial projection contains at most twelve stories. Load more increases that local limit by twelve, never performs a network request, and states when all matching stories are loaded.

## Seen and saved semantics

“New” means an event occurred after the locally stored `seenThrough` timestamp. When a populated panel opens, it captures the greatest event timestamp in that exact edition as `sessionThrough`. Closing normally advances `seenThrough` to at most `sessionThrough`; a newer event fetched after the session cutoff must remain new on the next open.

Opening an original source is not required to mark the edition seen. Saved state is independent from seen state. Events no longer present in the live bounded feed may remain in local saved metadata with their original source fields.

## State model

| State | Visible behavior | Recovery |
| --- | --- | --- |
| First use | Explains the empty cache and starts one refresh | Wait or retry |
| Cached | Shows last-known-good edition immediately with age | Background refresh |
| Refreshing | Keeps cached content readable and shows restrained progress | Wait or cancel by closing |
| Current | Shows successful generation time and complete available sources | Read normally |
| Offline | Keeps cache, labels failed refresh and cache age | Retry |
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

The main manifest declares both `panel` and `bar-widget`; normal enablement places one newspaper in the right section. The widget shows a bounded unread count and a source-health dot. Left click opens the same panel, middle click refreshes, and right click hides the widget after writing the local preference. Its hidden root is invisible, so Omarchy's module slot computes exact zero width and height rather than reserving a phantom gap.

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
