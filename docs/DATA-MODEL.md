# Data model

## Principles

The feed is a versioned public contract, not an internal dump of source responses. It must be compact, deterministic, bounded, forward-migratable, and sufficient for every version 1 client view without requiring clients to understand marketplace or GitHub payloads.

Unsupported schema versions and unknown object fields fail closed. Only explicitly supported optional fields are accepted. Missing required fields, invalid enum values, impossible timestamps, duplicate IDs, unsafe URLs, or exceeded bounds invalidate the candidate feed.

## Feed envelope

Version 2 has this conceptual shape (version 1 remains documented historically in `schemas/feed-v1.schema.json`):

```json
{
  "schemaVersion": 2,
  "generatedAt": "2026-08-31T14:00:00Z",
  "publishedAt": "2026-08-31T14:01:00Z",
  "window": {
    "from": "2026-06-02T00:00:00Z",
    "through": "2026-08-31T14:00:00Z"
  },
  "sources": [
    {
      "id": "omarchy-releases",
      "status": "current",
      "checkedAt": "2026-08-31T13:59:55Z",
      "sourceUrl": "https://github.com/basecamp/omarchy/releases"
    }
  ],
  "events": []
}
```

### Envelope bounds

- UTF-8 JSON only.
- Maximum downloaded feed size: 2 MiB.
- Maximum live events: 500.
- `generatedAt` may not be materially in the future relative to the client clock; tolerate a documented small skew.
- `generatedAt` is the completed source-collection time. `publishedAt` is the later artifact-build time, may not predate collection, and may not be materially in the future. Legacy schema-v1 editions without `publishedAt` explicitly infer publication from `generatedAt`.
- Events are sorted descending by `occurredAt`, then stable descending discovery order, then ascending ID.
- Source IDs are unique and come from a closed enum in the active feed schema version.

Source `status` values are `current`, `not-modified`, `stale`, or `failed`. A failed source records one bounded public-safe reason code, never tokens, response bodies, stack traces, or internal runner paths.

Source health and publication freshness are separate. Successful sources at old `checkedAt` values do not make an old artifact current. The client derives publication age from `publishedAt` and local cache time from the owned cache file's UTC modification time for validation, bar health, debug state, and external monitoring. These operational facts do not become persistent reader copy while a validated edition is usable.

## Event

```json
{
  "id": "evt_8cb067f9ef7da216bcab4781",
  "type": "plugin-released",
  "occurredAt": "2026-08-31T09:00:00Z",
  "discoveredAt": "2026-08-31T14:00:00Z",
  "title": "Omarchy Disk Lens 0.4.1",
  "summary": "A maintenance release for the native disk-usage dashboard.",
  "source": {
    "label": "GitHub release",
    "url": "https://github.com/mtolhuys/omarchy-disk-lens/releases/tag/v0.4.1"
  },
  "entity": {
    "kind": "plugin",
    "id": "io.github.mtolhuys.disk-lens",
    "name": "Omarchy Disk Lens",
    "repository": "https://github.com/mtolhuys/omarchy-disk-lens",
    "version": "0.4.1"
  },
  "classification": {
    "section": "plugins",
    "significance": "routine",
    "curated": false,
    "tags": ["system", "storage"]
  },
  "trust": {
    "marketplace": "verified",
    "securityAudit": false
  },
  "compatibility": {
    "channels": ["quattro"],
    "basis": "declared"
  },
  "image": {
    "path": "assets/images/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.webp",
    "alt": "Omarchy Disk Lens plugin preview",
    "credit": "Omarchy Plugin Marketplace",
    "width": 720,
    "height": 405
  }
}
```

## Event enums

Version 2 event types:

- `omarchy-released`
- `omarchy-news`
- `plugin-added`
- `plugin-released`
- `plugin-retired`
- `plugin-verification-changed`
- `community-link`
- `youtube-video`

Sections are `core`, `plugins`, `community`, or `youtube`. “front-page”, “for-you”, and “saved” are client projections, not stored source sections. YouTube events must never appear under feed schema version 1.

Significance is `routine`, `notable`, or `critical`. Only explicit reviewed curation may set `notable`. `critical` is reserved for an authoritative upstream security or breaking-compatibility statement and requires a decision record or reviewed curation entry; it is never derived from popularity or prose sentiment.

Marketplace trust values are `verified`, `reviewed`, `unverified`, `unknown`, or `not-applicable`. `securityAudit` remains false unless an authoritative source explicitly establishes a real audit; marketplace automated checks must never set it true.

Compatibility basis is `declared`, `inferred-from-source`, or `unknown`. Version 1 should prefer `unknown` over inference.

## Bounds and normalization

- Event ID: ASCII, maximum 32 characters, `evt_` plus 24 lowercase hexadecimal characters.
- Title: plain text, 1–160 Unicode scalar values after normalization.
- Summary: plain text, 1–8,000 Unicode scalar values (official Omarchy News may carry the RSS article body; other adapters still write short factual copy). Omarchy News may include lightweight `[label](https://...)` markers copied from real RSS hrefs. List cards display a client-derived teaser of at most 220 characters and never replace this field.
- Source label: 1–60 characters.
- URL: HTTPS, maximum 2,048 characters, no credentials, control characters, fragments containing secrets, or non-public host literals.
- Entity ID: 1–160 characters from a conservative plugin-ID/release-ID grammar.
- Entity name: 1–120 characters.
- Tags: at most 12 unique normalized lowercase tags, each 1–32 characters.
- Channels: at most 8 values from a closed vocabulary.
- All timestamps: canonical UTC RFC 3339 with `Z`.
- Public images: optional legacy relative `assets/images/<sha256>.(jpg|png|webp)`, allowlisted marketplace `https://plugins.omarchy.org/assets/img/plugins/…`, or allowlisted YouTube `https://i.ytimg.com/vi/<id>/hqdefault.jpg`, each with 1–4,096 pixel dimensions, at most 12 million pixels, and bounded plain-text alt/credit.

### Optional observed metrics

An event may carry at most one canonical record for each closed metric ID: `marketplace-views`, `marketplace-hearts`, `marketplace-copies`, `repository-stars`, `release-asset-downloads`, `youtube-views`, and `youtube-likes`. Each record contains a non-negative JavaScript-safe integer `value`, canonical UTC `observedAt`, and validated public HTTPS `sourceUrl`. Records sort by ID.

These are observed source facts, not occurrences. Counter changes never create an event or change its ID, timestamps, significance, curation, or Front Page position. YouTube views/likes may reorder only the YouTube section projection. Marketplace aggregates specifically mean anonymous detail views, hearts, and command copies; they do not mean installs, downloads, unique people, votes, rankings, or security.

Replace C0/DEL control characters in display strings, normalize line breaks and repeated whitespace, and preserve Unicode without converting user content into markup. Do not silently repair structural IDs or URLs; reject them.

## Deterministic IDs

An event ID is the first 24 hexadecimal characters of SHA-256 over a canonical UTF-8 tuple:

```text
feed-v1\n<type>\n<entity-kind>\n<entity-id>\n<occurrence-key>\n<source-url>
```

The occurrence key is source-specific and stable: release database ID or tag identity, plugin listing baseline identity, old-to-new version pair, old-to-new verification pair, retirement identity, or reviewed community record ID. Re-running a collector with identical facts produces identical IDs and byte-stable event content apart from envelope generation metadata.

## Marketplace snapshot

Normalized marketplace state is keyed by canonical plugin ID and retains only fields required to detect supported events:

```json
{
  "io.github.mtolhuys.disk-lens": {
    "name": "Omarchy Disk Lens",
    "version": "0.4.1",
    "repository": "https://github.com/mtolhuys/omarchy-disk-lens",
    "category": "System",
    "tags": ["storage"],
    "addedAt": "2026-08-31T00:00:00Z",
    "verification": "verified",
    "retired": false,
    "preview": {
      "sourceUrl": "https://plugins.omarchy.org/assets/img/plugins/example-card.webp",
      "width": 720,
      "height": 405
    }
  }
}
```

Stars, views, hearts, copy counts, release-asset downloads, repository update timestamps, observed commits, preview paths, and source fingerprints are not news identities. Valid counters may enrich an event created by another supported fact; valid preview metadata is retained only so the publisher can inspect the optional marketplace raster and emit its direct allowlisted `sourceUrl`.

## Local state

```json
{
  "schemaVersion": 13,
  "onboardingComplete": true,
  "briefing": {
    "generatedAt": "2026-08-31T14:00:00Z",
    "groups": [
      {"eventIds": ["evt_8cb067f9ef7da216bcab4781"], "reason": "installed"}
    ]
  },
  "readThrough": "1970-01-01T00:00:00Z",
  "readOverrides": {
    "evt_8cb067f9ef7da216bcab4781": true
  },
  "saved": {
    "evt_8cb067f9ef7da216bcab4781": {
      "savedAt": "2026-08-31T14:05:00Z",
      "title": "Omarchy Disk Lens 0.4.1",
      "sourceUrl": "https://github.com/mtolhuys/omarchy-disk-lens/releases/tag/v0.4.1",
      "occurredAt": "2026-08-31T09:00:00Z",
      "type": "plugin-released"
    }
  },
  "relevance": {
    "followedPlugins": [],
    "mutedPlugins": [],
    "followedSources": [],
    "mutedSources": [],
    "followedCreators": [],
    "mutedCreators": []
  },
  "preferences": {
    "barVisible": true,
    "imagesVisible": true,
    "sectionFilters": {
      "front-page": {"period":"all","significance":"all","unreadOnly":false,"imagesOnly":false,"types":[]},
      "for-you": {"period":"all","significance":"all","unreadOnly":false,"imagesOnly":false,"types":[]},
      "core": {"period":"all","significance":"all","unreadOnly":false,"imagesOnly":false,"types":[]},
      "plugins": {"period":"7d","significance":"notable","unreadOnly":false,"imagesOnly":true,"types":["plugin-released"]},
      "youtube": {"period":"all","significance":"all","unreadOnly":false,"imagesOnly":false,"types":[]},
      "saved": {"period":"all","significance":"all","unreadOnly":false,"imagesOnly":false,"types":[]}
    },
    "sectionVisibility": {
      "core": true,
      "plugins": true,
      "youtube": true
    }
  }
}
```

Saved records intentionally duplicate a small bounded subset so a bookmark survives the rolling feed window. Cap saved items at 250 with explicit UI before refusing another; never silently discard a saved item.

`readThrough` is a migration baseline, not a session cursor. An event is read when its boolean `readOverrides[eventId]` exists and is true, unread when that override exists and is false, and otherwise read only when `occurredAt <= readThrough`. New installations use the Unix epoch baseline, so every current event starts unread. The panel never advances the baseline; its one initial visibly presented story per fresh open and deliberate per-story actions create or remove the smallest necessary override. The explicit filtered-section batch action applies that same rule to a validated list of at most 500 event IDs in one locked atomic write, including unloaded matches while ignoring temporary search. Corrupt state is quarantined and replaced by defaults without modifying feed cache.

State v12 adds `onboardingComplete` and nullable `briefing`. Fresh defaults require the first-use choice; all valid v1–v11 migrations set onboarding complete, leave the briefing uninitialized, and never change existing reading decisions. The v11 `sectionVisibility` contract for the hideable Core, Plugins, and YouTube rails remains. Valid older states migrate atomically: the prior `seenThrough` value becomes `readThrough`, saved data and supported preferences survive, legacy profile shapes and the v2–v7 interests array are strictly validated before being discarded, the removed Community filter stays removed, v9 gains a default YouTube section filter, and v10 gains the default-on visibility profile. `readOverrides` is a canonical event-ID-to-boolean object capped at the feed's 500-event bound. Canonical names, icons, order, backgrounds, and source scope remain code-owned rather than hidden mutable state, and no migration or reading data is sent over the network.

The stable client sections are `front-page`, `for-you`, `core`, `plugins`, `youtube`, and `saved`; they own the fixed name, projection, icon, order, source summary, filtering semantics, and network behavior. Feed classification `community` and event type `community-link` remain valid inputs to Front Page and For You, but are not client sections. YouTube stays in its own rail and does not enter Front Page in MVP.

The top-bar unread value is not a second reading-state model. It applies the same canonical read predicate, projects the currently visible sections with the current persistent filters and exact locally enabled plugin IDs, and counts the union of matching unread event IDs. A rail hidden in Tune is not a reachable destination and cannot keep the badge active. Overlap between Front Page, For You, source sections, and Saved never double-counts a story. Temporary search and pagination do not change the badge; an unread story excluded by every persistent section projection is deliberately not advertised as actionable.

Background check cadence is disposable cache metadata, not reading state or feed metadata:

```json
{"schemaVersion":1,"checkedAt":"2026-08-31T14:05:00Z","outcome":"success"}
```

The strict bounded record distinguishes an actual client attempt from source `checkedAt`, collection `generatedAt`, artifact `publishedAt`, and feed-cache modification time. `outcome` is only `success` or `failed`; malformed or materially future records are treated as absent so they cannot postpone a check. It contains no event IDs, preferences, installation facts, or user identifiers.

HTTP revalidation is a separate disposable `feed-http.json` record with exact keys `schemaVersion`, `url`, `etag`, and `lastModified`. The URL must exactly equal the request's already allowlisted feed URL before either optional validator is sent. A valid `304` reuses only an already validated `feed.json`; malformed metadata or a missing feed cache falls back to an unconditional request. The record contains public response metadata only and is removed by explicit purge.

## Schema evolution

The active feed schema has closed object shapes, including its supported optional fields. Adding fields requires an explicitly compatible versioned contract; older strict v2 clients must continue receiving an unchanged v2 shape. The 0.5.0 candidate therefore places richer public data in the independent insights-v1 companion. Changes to required fields, enums, ID calculation, read-state meaning, or validation bounds require a new schema version plus explicit migration and compatibility tests. The client never guesses across versions.

## Local briefing snapshot (introduced in state v12)

`briefing` is null before explicit panel initialization, or exactly `{generatedAt, groups}`. Each of at most five groups stores a non-empty list of canonical unique event IDs and one closed reason: `critical`, `notable`, `core`, `installed`, `discovery`, or `followed` (added in v13). Across groups, membership is unique and capped at the live feed's 500-event bound. Original facts remain in the feed; the state does not copy article text or synthesize impact claims.

The helper exposes a SHA-256 briefing identity, group identity, current retained members with original sources, remaining groups, unread member count, expired member count, and whether another eligible unread selection exists. Filtering and search can hide rows but cannot edit snapshot membership. An expired representative can be presented through a retained member while the original group ID remains stable. Missing members are disclosed and do not count as read completion.

First-use Start from today uses a SHA-256 digest of sorted current feed IDs, accompanied by `feedEventCount` from the same projection. It never uses timestamps as a reading cursor. The helper verifies membership under the shared state lock before committing; a newly adopted edition and the reading action cannot interleave their critical sections. Start from today preserves explicit false overrides. Group/briefing actions likewise verify the current briefing identity and mark only its exact retained IDs. Ordinary projection and bar-indicator queries do not initialize a briefing. Only panel ensure, explicit New briefing, and the explicit first-use action can establish or replace one.

## Insights v1 and local state v13

The companion envelope is exactly `{schemaVersion: 1, publishedAt, projects, collections}`, bounded to 2 MiB. It is independent of the rolling event timestamp and digest. Project IDs are canonical entity IDs; each project carries `kind`, `name`, `description`, `source`, optional `creatorId`/allowlisted `image`, and at most 30 releases. Each release has an exact version, upstream publication time, title, plain-text summary, up to twelve source-linked changes and original source URL. Versions are compared only under strict SemVer precedence (with a conventional optional v prefix) or an exact nonempty match. Unknown schemes do not imply an update.

A collection has an immutable lowercase alphanumeric slug with single separating hyphens, up to 80 characters, title, summary, plain-text body, up to twenty unique known project IDs, source, optional additional source links/image, fixed public `shareUrl`, and an accurate UTC review time. It creates no event and changes no news significance. Full shapes are enforced by `schemas/insights-v1.schema.json` and the runtime validator.

Local installed facts retain the backward-compatible `{id, version}` shape and may add bounded plain-text `name` and `description` fields and explicit boolean `firstParty`. They are neither stored in the public companion nor transmitted. Projection receives availability separately so an empty enabled-plugin list does not imply discovery failure. Its `insights.projectDetails` array retains all covered project details independently from filtered Home/My setup lists, preserving source context for searches, Saved and the current briefing. Version-specific story explanations additionally require matching historical repository provenance; a matching ID and version alone cannot transfer another owner's notes.

State v13 retains v12 onboarding and briefing data and adds exactly six `relevance` arrays: `followedPlugins`, `mutedPlugins`, `followedSources`, `mutedSources`, `followedCreators`, `mutedCreators`. Their combined bound is 500 targets. Each target can be followed, muted or clear; conflicting states are invalid. GitHub creator identities use `github:<lowercase-owner>`. Display-only YouTube channel names do not become creator identities. A `followed` briefing reason is added. Valid v12 states preserve their exact onboarding choice and snapshot; valid earlier states preserve supported reads, saves and preferences and skip onboarding. No schema migration constitutes a read action.

Private window geometry is separate from this reading schema. The lifecycle helper validates and clamps it against current logical monitor bounds; no local monitor or geometry fact enters either public feed.

## Personal-news correction (0.5.2 candidate)

State v13 is unchanged. `relevance.followedSources` remains valid and clearable for backward compatibility, but source-wide follows no longer match personal news or future briefing candidates. Enabled plugin IDs and explicit project/creator follows still match; all mutes retain priority. Existing briefing membership, reading overrides, saves and filters are preserved. Client projection adds `hiddenReadCount`, the number of otherwise matching read stories hidden by Unread only, excluding any retained visible rows. It is presentation data, not persisted state.
