"""Deterministic topic clustering for bounded Front Page diversity.

Core keeps every official Omarchy News item. The Front Page is finite, so a
single-cycle story that ships as three articles (a Foundation announcement plus
its patronage and sponsorship follow-ups) used to consume the whole news quota
and push the rest of the edition below the fold.

Clustering answers one narrow question: do two items look like the same story?
It is derived from the published title and the leading summary sentence with a
closed stoplist, never from rewriting, summarizing, translating, sentiment, or
popularity. Selection keeps the newest item of each cluster first and then
backfills in the original freshness order, so nothing is reordered and no item
is edited.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

# Topic tokens are Unicode letter runs of at least four characters. Digits and
# version numbers are deliberately excluded: "0.4.15" is not a topic.
TOKEN_RE = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
LEADING_SENTENCE_RE = re.compile(r"(?<=[.!?…。！？])\s")
MAX_SENTENCE_CHARS = 200
MAX_TOKENS_PER_EVENT = 24

# Generic structural words plus feed-wide vocabulary that would otherwise link
# unrelated stories through one shared token.
STOP_TOKENS = frozenset(
    {
        "about",
        "after",
        "again",
        "against",
        "already",
        "also",
        "another",
        "because",
        "been",
        "before",
        "being",
        "between",
        "both",
        "cannot",
        "come",
        "coming",
        "could",
        "does",
        "doing",
        "done",
        "down",
        "during",
        "each",
        "from",
        "gets",
        "have",
        "having",
        "here",
        "into",
        "just",
        "know",
        "like",
        "made",
        "make",
        "makes",
        "many",
        "more",
        "most",
        "much",
        "must",
        "need",
        "needs",
        "next",
        "only",
        "other",
        "over",
        "same",
        "should",
        "some",
        "still",
        "such",
        "than",
        "that",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "under",
        "until",
        "very",
        "want",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "will",
        "with",
        "without",
        "would",
        "your",
        "yours",
        # Feed vocabulary: present in most items, so useless as a topic.
        "announced",
        "announcement",
        "announcing",
        "available",
        "blog",
        "desktop",
        "introduces",
        "introducing",
        "linux",
        "news",
        "omarchy",
        "plugin",
        "plugins",
        "post",
        "radar",
        "release",
        "released",
        "releases",
        "today",
        "update",
        "updated",
        "updates",
        "version",
        "week",
        "year",
    }
)


def _leading_sentence(value: Any) -> str:
    text = " ".join(str(value or "").split())[:MAX_SENTENCE_CHARS]
    return LEADING_SENTENCE_RE.split(text, maxsplit=1)[0] if text else ""


def topic_tokens(event: Mapping[str, Any]) -> frozenset[str]:
    """Return the bounded topic vocabulary published with one event."""

    text = unicodedata.normalize(
        "NFC", f"{event.get('title', '')} {_leading_sentence(event.get('summary'))}"
    ).casefold()
    tokens: list[str] = []
    for token in TOKEN_RE.findall(text):
        if token in STOP_TOKENS or token in tokens:
            continue
        tokens.append(token)
        if len(tokens) >= MAX_TOKENS_PER_EVENT:
            break
    return frozenset(tokens)


def cluster_events(events: Sequence[Mapping[str, Any]]) -> list[int]:
    """Assign each event a cluster index by greedy shared-token linkage.

    Items arrive in canonical freshness order, so the assignment is stable: two
    items share a cluster only when they share at least one topic token,
    directly or through an already-linked item.
    """

    clusters: list[set[str]] = []
    assignment: list[int] = []
    for event in events:
        tokens = topic_tokens(event)
        index = -1
        if tokens:
            index = next(
                (
                    position
                    for position, cluster in enumerate(clusters)
                    if cluster & tokens
                ),
                -1,
            )
        if index < 0:
            clusters.append(set(tokens))
            index = len(clusters) - 1
        else:
            clusters[index] |= tokens
        assignment.append(index)
    return assignment


def diversify_by_topic(
    events: Sequence[Mapping[str, Any]], maximum: int
) -> list[Mapping[str, Any]]:
    """Take at most `maximum` items, one per cluster first, then backfill.

    The result stays in the incoming freshness order. With one topic in the
    window the behavior is identical to a plain quota.
    """

    if maximum <= 0 or not events:
        return []
    assignment = cluster_events(events)
    chosen: set[int] = set()
    seen_clusters: set[int] = set()
    for position, cluster in enumerate(assignment):
        if len(chosen) >= maximum:
            break
        if cluster in seen_clusters:
            continue
        seen_clusters.add(cluster)
        chosen.add(position)
    for position in range(len(events)):
        if len(chosen) >= maximum:
            break
        chosen.add(position)
    return [event for position, event in enumerate(events) if position in chosen]


def cluster_titles(events: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Diagnostic helper: event ID to cluster index for tests and review."""

    ordered = list(events)
    return {
        str(event.get("id", position)): cluster
        for position, (event, cluster) in enumerate(zip(ordered, cluster_events(ordered)))
    }
