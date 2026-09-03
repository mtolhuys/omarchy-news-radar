"""Deterministic reading-surface helpers.

The feed may carry a long official article (0.4.14). The list is a skimmable
index, so cards receive a short cleaned teaser while the inspector keeps the
full bounded body. Nothing here rewrites, translates, or invents facts: it
selects leading prose after stripping locators and promotional sentences.
Article bodies may keep lightweight `[label](https://...)` markers that were
copied from real RSS hrefs; those are not HTML and are never invented.
"""

from __future__ import annotations

import re

from .errors import ValidationError
from .sources.youtube_text import (
    NEUTRAL_SUMMARY,
    SENTENCE_SPLIT_RE,
    _is_promotional,
    _strip_locators,
    count_letters,
)
from .validation import validate_https_url

LIST_SUMMARY_MAX = 220
MIN_TEASER_LETTERS = 12
LINK_MARKER_RE = re.compile(r"\[([^\]\n]{1,160})\]\((https://[^)\s]{8,2048})\)")
BARE_HTTPS_RE = re.compile(
    r"https://[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251})[A-Za-z0-9]"
    r"(?::443)?(?:/[^\s<>\"']*)?"
)


def accepted_https_url(value: object) -> str:
    """Return a credential-free HTTPS URL, or empty when the candidate is unsafe."""

    if not isinstance(value, str):
        return ""
    candidate = value.strip().rstrip(".,;:)]}>")
    try:
        return validate_https_url(candidate, "article link")
    except ValidationError:
        return ""


def collapse_article_links(value: str) -> str:
    """Replace link markers with their visible labels for compact teasers."""

    return LINK_MARKER_RE.sub(lambda match: match.group(1), value)


def article_segments(value: object) -> list[dict[str, str]]:
    """Split a stored body into plain text and validated HTTPS link segments."""

    raw = value if isinstance(value, str) else ""
    events: list[tuple[int, int, dict[str, str]]] = []
    occupied: list[tuple[int, int]] = []
    for match in LINK_MARKER_RE.finditer(raw):
        href = accepted_https_url(match.group(2))
        if not href:
            continue
        label = " ".join(match.group(1).split()) or href
        events.append((match.start(), match.end(), {"kind": "link", "text": label, "url": href}))
        occupied.append((match.start(), match.end()))

    def taken(position: int) -> bool:
        return any(start <= position < end for start, end in occupied)

    for match in BARE_HTTPS_RE.finditer(raw):
        if taken(match.start()):
            continue
        raw_url = match.group(0)
        href = accepted_https_url(raw_url)
        if not href:
            continue
        trailing = len(raw_url) - len(raw_url.rstrip(".,;:)]}>"))
        end = match.end() - trailing
        if end <= match.start():
            continue
        events.append((match.start(), end, {"kind": "link", "text": href, "url": href}))
    events.sort(key=lambda item: item[0])
    segments: list[dict[str, str]] = []
    cursor = 0
    for start, end, payload in events:
        if start < cursor:
            continue
        if start > cursor:
            text = raw[cursor:start]
            if text:
                segments.append({"kind": "text", "text": text})
        segments.append(payload)
        cursor = end
    if cursor < len(raw) and raw[cursor:]:
        segments.append({"kind": "text", "text": raw[cursor:]})
    if segments:
        return segments
    return [{"kind": "text", "text": raw}] if raw else []


def list_summary(value: object, fallback: object = "") -> str:
    """Return a compact card teaser from one untrusted body or summary."""

    raw = value if isinstance(value, str) else ""
    if raw.strip() == NEUTRAL_SUMMARY:
        raw = ""
    raw = collapse_article_links(raw)
    fallback_text = " ".join(str(fallback or "").split())
    sentences = [
        sentence
        for sentence in SENTENCE_SPLIT_RE.split(" ".join(raw.replace("\r", "\n").split()))
        if sentence
    ]
    selected: list[str] = []
    length = 0
    for sentence in sentences:
        cleaned, _stripped = _strip_locators(sentence)
        if _is_promotional(cleaned) or count_letters(cleaned) < MIN_TEASER_LETTERS:
            continue
        extra = length + (1 if selected else 0) + len(cleaned)
        if extra > LIST_SUMMARY_MAX and selected:
            break
        if extra > LIST_SUMMARY_MAX:
            cleaned = cleaned[: LIST_SUMMARY_MAX - 1].rstrip() + "…"
            extra = length + (1 if selected else 0) + len(cleaned)
        selected.append(cleaned)
        length = extra
        if len(selected) == 2:
            break
    if selected:
        return " ".join(selected)[:LIST_SUMMARY_MAX]
    if fallback_text and fallback_text != NEUTRAL_SUMMARY:
        return fallback_text[:LIST_SUMMARY_MAX]
    return ""
