# Curation contract

## Activity and significance

Radar separates two questions:

1. **Did this happen?** Source adapters and deterministic diffs answer this.
2. **Is this especially worth attention?** A reviewed curation record answers this.

An automated event may be useful without being notable. A curated item must still have a provable source event or reviewed community record. Curation never invents facts, changes source timestamps, or hides trust metadata.

## Front Page

The front page is composed deterministically from the live window:

1. Explicit `critical` items ordered by occurrence time.
2. Explicit `notable` items ordered by occurrence time.
3. The newest official Omarchy release when not already included.
4. Installed-plugin events for the local “For You” projection.
5. A bounded mix of routine plugin and community activity, preventing one category from consuming the entire edition.

Server output may nominate a lead item, but the client verifies that the referenced event exists. Without an explicit lead, the first highest-significance event becomes the visual lead. Popularity counters never decide the lead.

## Notable criteria

An item may be marked notable when at least one reviewed statement is true:

- It materially changes the default Omarchy experience.
- It introduces or changes a plugin API, lifecycle, compatibility boundary, or security posture.
- It provides a genuinely distinct capability rather than a near-duplicate.
- It consolidates fragmented community work or removes a common maintenance burden.
- It teaches a reusable workflow with clear original evidence.
- It affects a large class of existing installations.

Stars, social reach, author identity, DHH amplification, novelty alone, visual polish alone, or marketplace verification alone are insufficient.

## Summary style

Summaries are concise, neutral, and factual:

- State what changed and why a user might care.
- Prefer specific verbs and concrete scope.
- Distinguish declared compatibility, observed metadata, and editorial inference.
- Avoid “amazing,” “game-changing,” “must-have,” “best,” “safe,” and unsupported superlatives.
- Do not reproduce release notes or article passages. Paraphrase within 400 characters and link the original.
- Never call automated marketplace validation a security audit.
- Never include installation commands in the summary; source pages own installation guidance.

## Curation records

A curation record references an existing deterministic event ID and may add only:

- significance;
- a reviewed summary override within the same factual boundary;
- a lead nomination;
- bounded editorial tags;
- reviewer identity and review timestamp for repository audit history.

The generated public feed does not expose private reviewer metadata beyond what the project intentionally publishes. Removing curation returns the event to routine presentation; it does not delete the underlying activity.

## Corrections

Corrections are new repository changes with a clear commit history. If a published summary is materially wrong, fix the source record, regenerate the same event ID, add a public `correctedAt` optional field under the same schema contract, and explain the correction in the project changelog when user impact warrants it.

Never silently redirect an event to a different source or reuse an event ID for a different occurrence.

## Independence and conflicts

Maintainers may curate their own work, but notable status for their own project requires a second reviewer once the project accepts outside contributions. Sponsored placement, paid ranking, affiliate links, and undisclosed conflicts are outside version 1.
