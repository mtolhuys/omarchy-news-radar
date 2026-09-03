"""Deterministic reading-surface helpers.

The feed may carry a long official article (0.4.14). The list is a skimmable
index, so cards receive a short cleaned teaser while the inspector keeps the
full bounded body. Nothing here rewrites, translates, or invents facts: it
selects leading prose after stripping locators and promotional sentences.
"""

from __future__ import annotations

from .sources.youtube_text import (
    NEUTRAL_SUMMARY,
    SENTENCE_SPLIT_RE,
    _is_promotional,
    _strip_locators,
    count_letters,
)

LIST_SUMMARY_MAX = 220
MIN_TEASER_LETTERS = 12


def list_summary(value: object, fallback: object = "") -> str:
    """Return a compact card teaser from one untrusted body or summary."""

    raw = value if isinstance(value, str) else ""
    if raw.strip() == NEUTRAL_SUMMARY:
        raw = ""
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
