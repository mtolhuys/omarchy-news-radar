# Data model

## Principles

The feed is a versioned public contract, not an internal dump of source responses. It must be compact, deterministic, bounded, forward-migratable, and sufficient for every version 1 client view without requiring clients to understand marketplace or GitHub payloads.

Unknown required schema versions fail closed. Unknown optional fields are ignored. Missing required fields, invalid enum values, impossible timestamps, duplicate IDs, unsafe URLs, or exceeded bounds invalidate the candidate feed.

## Feed envelope

Version 1 has this conceptual shape:

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-08-31T14:00:00Z",
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
- Events are sorted descending by `occurredAt`, then stable descending discovery order, then ascending ID.
- Source IDs are unique and come from a closed enum in version 1.

Source `status` values are `current`, `not-modified`, `stale`, or `failed`. A failed source records one bounded public-safe reason code, never tokens, response bodies, stack traces, or internal runner paths.

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

Version 1 event types:

- `omarchy-released`
- `plugin-added`
- `plugin-released`
- `plugin-retired`
- `plugin-verification-changed`
- `community-link`

Sections are `core`, `plugins`, or `community`. “front-page”, “for-you”, and “saved” are client projections, not stored source sections.

Significance is `routine`, `notable`, or `critical`. Only explicit reviewed curation may set `notable`. `critical` is reserved for an authoritative upstream security or breaking-compatibility statement and requires a decision record or reviewed curation entry; it is never derived from popularity or prose sentiment.

Marketplace trust values are `verified`, `reviewed`, `unverified`, `unknown`, or `not-applicable`. `securityAudit` remains false unless an authoritative source explicitly establishes a real audit; marketplace automated checks must never set it true.

Compatibility basis is `declared`, `inferred-from-source`, or `unknown`. Version 1 should prefer `unknown` over inference.

## Bounds and normalization

- Event ID: ASCII, maximum 32 characters, `evt_` plus 24 lowercase hexadecimal characters.
- Title: plain text, 1–160 Unicode scalar values after normalization.
- Summary: plain text, 1–400 Unicode scalar values.
- Source label: 1–60 characters.
- URL: HTTPS, maximum 2,048 characters, no credentials, control characters, fragments containing secrets, or non-public host literals.
- Entity ID: 1–160 characters from a conservative plugin-ID/release-ID grammar.
- Entity name: 1–120 characters.
- Tags: at most 12 unique normalized lowercase tags, each 1–32 characters.
- Channels: at most 8 values from a closed vocabulary.
- All timestamps: canonical UTC RFC 3339 with `Z`.
- Public image paths: optional relative `assets/images/<sha256>.(jpg|png|webp)` only, with 1–4,096 pixel dimensions, at most 12 million pixels, bounded plain-text alt/credit, and no upstream URL in the public feed.

### Optional observed metrics

An event may carry at most one canonical record for each closed metric ID: `marketplace-views`, `marketplace-hearts`, `marketplace-copies`, `repository-stars`, and `release-asset-downloads`. Each record contains a non-negative JavaScript-safe integer `value`, canonical UTC `observedAt`, and validated public HTTPS `sourceUrl`. Records sort by ID.

These are observed source facts, not occurrences. Counter changes never create an event or change its ID, timestamps, significance, curation, ordering, or Front Page position. Marketplace aggregates specifically mean anonymous detail views, hearts, and command copies; they do not mean installs, downloads, unique people, votes, rankings, or security.

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

Stars, views, hearts, copy counts, release-asset downloads, repository update timestamps, observed commits, preview paths, and source fingerprints are not news identities. Valid counters may enrich an event created by another supported fact; valid preview metadata is retained only so the publisher can mirror its optional image.

## Local state

```json
{
  "schemaVersion": 4,
  "seenThrough": "2026-08-31T14:00:00Z",
  "saved": {
    "evt_8cb067f9ef7da216bcab4781": {
      "savedAt": "2026-08-31T14:05:00Z",
      "title": "Omarchy Disk Lens 0.4.1",
      "sourceUrl": "https://github.com/mtolhuys/omarchy-disk-lens/releases/tag/v0.4.1",
      "occurredAt": "2026-08-31T09:00:00Z",
      "type": "plugin-released"
    }
  },
  "preferences": {
    "barVisible": true,
    "imagesVisible": true,
    "interests": ["security", "quickshell"],
    "sectionFilters": {
      "front-page": {"period":"all","significance":"all","unreadOnly":false,"imagesOnly":false,"types":[]},
      "for-you": {"period":"all","significance":"all","unreadOnly":false,"imagesOnly":false,"types":[]},
      "core": {"period":"all","significance":"all","unreadOnly":false,"imagesOnly":false,"types":[]},
      "plugins": {"period":"7d","significance":"notable","unreadOnly":false,"imagesOnly":true,"types":["plugin-released"]},
      "community": {"period":"all","significance":"all","unreadOnly":false,"imagesOnly":false,"types":[]},
      "saved": {"period":"all","significance":"all","unreadOnly":false,"imagesOnly":false,"types":[]}
    },
    "sectionProfiles": {
      "front-page": {"name":"Front Page","icon":"newspaper","tone":"clear"},
      "for-you": {"name":"For You","icon":"spark","tone":"clear"},
      "core": {"name":"Core","icon":"core","tone":"clear"},
      "plugins": {"name":"My Extensions","icon":"spark","tone":"accent"},
      "community": {"name":"Community","icon":"community","tone":"clear"},
      "saved": {"name":"Saved","icon":"saved","tone":"clear"}
    }
  }
}
```

Saved records intentionally duplicate a small bounded subset so a bookmark survives the rolling feed window. Cap saved items at 250 with explicit UI before refusing another; never silently discard a saved item.

`seenThrough` is monotonic. It advances only to the greatest event timestamp captured in a successfully rendered session and never to wall-clock “now.” Corrupt state is quarantined and replaced by defaults without modifying feed cache.

State v4 retains v3 filters and adds one strict presentation profile for each client section. A profile contains a normalized 1–32-character plain-text name, an icon from `newspaper`, `spark`, `core`, `plugins`, `community`, or `saved`, and a tone from `clear`, `soft`, `accent`, or `ink`. Tone IDs map to current Omarchy tokens in QML; no arbitrary color or markup enters state. Valid v1, v2, and v3 states migrate atomically with saved, seen, existing v2 preferences, and v3 filters preserved; profiles receive defaults and no migration data is sent over the network.

Source membership is not part of the profile. Stable section IDs continue to own the fixed projection and are always shown in settings; changing a name, icon, or tone has no effect on collection, ranking, filtering semantics, or network requests.

## Schema evolution

Additive optional fields may appear within schema version 1. A semantic change to required fields, enums, ID calculation, read-state meaning, or validation bounds requires a new schema version plus explicit migration and compatibility tests. The publisher may offer multiple feed versions during a documented transition; the client never guesses across versions.
