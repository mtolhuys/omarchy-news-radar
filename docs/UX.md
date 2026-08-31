# UX contract

## Character

Radar should feel like unfolding a compact morning paper inside Omarchy: editorial hierarchy, generous rhythm, sharp typography, and a finite edition. It must not resemble a notification drawer, package manager, analytics dashboard, or dense GitHub activity log.

The newspaper metaphor is visual and organizational, not nostalgic decoration. Avoid fake paper textures, ornamental ink noise, novelty page turns, and inaccessible multi-column reading order.

## Primary invocation

The recommended global shortcut is `Super+N` for “news.” It is currently unused in the audited Quattro defaults and live binding set, while `Super+Shift+N` launches the editor and `Super+Ctrl+N` toggles nightlight.

Shortcut installation is a separate, explicit setup action after plugin enablement. The setup tool must inspect the live binding table, refuse any conflict, write only its owned managed block, validate a Hyprland reload, and support status and removal.

The plugin must remain openable through documented shell IPC even without the shortcut:

```bash
omarchy-shell shell toggle io.github.mtolhuys.news-radar
```

## Surface

Version 1 is an on-demand panel with no required top-bar icon. It opens centered on the active monitor, fits within current outer gaps, never exceeds the usable monitor rectangle, and becomes scrollable before content clips.

The panel has four stable visual zones:

1. **Masthead:** Omarchy News Radar, local date, edition freshness, source health, and close action.
2. **Section rail:** Front Page, For You, Core, Plugins, Community, and Saved with bounded counts.
3. **Edition:** one lead item followed by compact secondary stories in a responsive reading grid.
4. **Story inspector:** source, event type, occurrence time, tags, compatibility, verification boundary, summary, save action, and open-source action.

Wide layouts may use two visual columns, but the semantic and keyboard order remains one canonical sequence. Narrow layouts collapse to one column without changing content or controls.

## Front page composition

The front page is finite. The initial viewport should communicate the most important changes without requiring search or scrolling through routine events.

- One lead item may receive the largest treatment.
- Up to six secondary items may appear above the fold.
- Remaining activity is grouped by section and date.
- The interface states exactly what “since last read” means.
- No autoplay, carousel, ticker, infinite scroll, or continuously moving decoration is allowed.

## Keyboard model

All behavior must remain reachable without a pointer:

| Key | Action |
| --- | --- |
| `Super+N` | Toggle Radar globally after explicit setup |
| `Escape` or `q` | Close Radar |
| `j` / `Down` | Select next story |
| `k` / `Up` | Select previous story |
| `Enter` or `o` | Open selected original source |
| `s` | Save or unsave selected story locally |
| `/` | Focus search/filter input |
| `r` | Refresh the feed |
| `1`–`6` | Switch between the six primary sections |
| `Home` / `End` | Select first or last story in the current section |

Shortcuts must not fire while a text field is actively editing, except `Escape` to leave or close in the documented order. Every pointer action must have an equivalent keyboard route and visible focus treatment.

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

## Source opening

Titles, summaries, tags, and URLs are untrusted data. Display text is plain text. Source URLs appear as labels but open only through a dedicated button or keyboard action. The UI never renders remote HTML, Markdown, images, SVG, scripts, or embedded media.

## Top-bar policy

No bar widget ships in version 1. The current Omarchy plugin lifecycle places an enabled `bar-widget` in the bar, which makes “installed but hidden by default” an awkward hidden state. If usage proves an indicator valuable, build a separate optional companion plugin with its own manifest and lifecycle rather than coupling the core reader to a phantom bar slot.

The future indicator may show only a restrained unread dot/count and open the same panel. It must default to no notifications, respect bar orientation and cross-axis sizing, and receive separate pointer and lifecycle acceptance.

## Visual language

- Use current Omarchy `Color`, `Style`, and `Border` contracts rather than hard-coded theme colors or sizes.
- Use the system monospace family and Omarchy type scale; distinguish masthead, section, headline, summary, metadata, and source through hierarchy rather than excessive color.
- Accent marks focus, selection, and one lead rule. Urgent color is reserved for actual source or compatibility warnings.
- Dense metadata remains secondary and collapsible; the main reading path prioritizes headline and summary.
- Any motion is bounded to active refresh and has equivalent literal status text. There is no perpetual radar sweep.

## Accessibility boundary

The panel must expose meaningful roles, names, focus order, selected state, section counts, refresh status, source health, and actionable labels. Visual columns must not create a different reading order from keyboard or assistive technology.

Release acceptance includes keyboard-only traversal, visible focus in light and dark themes, long titles, repaired control characters, narrow layout, 200% text scaling, reduced motion, and exact text alternatives for icons and trust markers. Full screen-reader claims require explicit assistive-technology evidence and must not be inferred from QML metadata alone.
