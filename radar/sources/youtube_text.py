"""Deterministic YouTube description sanitation and lane eligibility rules.

A YouTube description is untrusted channel copy. In practice it opens with a
sponsor block, a course funnel, affiliate or referral links, social handles,
chapter timecodes, and bare URLs, none of which describe the video. Radar is a
calm relevance layer, so the lane keeps only the factual prose and answers one
question: does this item describe Omarchy activity?

Every rule here is a closed marker set over the text itself. There is no
language detection, sentiment model, engagement input, popularity signal, or
channel/video allowlist, so identical text always produces an identical
decision and the same fixture always produces the same lane.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

KEYWORD_RE = re.compile(r"(?i)\bomarchy\b")

MAX_DESCRIPTION_CHARS = 10_000
MAX_DESCRIPTION_LINES = 400
SUMMARY_MAX_CHARS = 400
NEUTRAL_SUMMARY = "No factual description text was published with this video."

MIN_PROSE_LINE_LETTERS = 12
MIN_KEPT_SENTENCE_LETTERS = 8
MIN_INFORMATIVE_PROSE_LETTERS = 40
STRONG_PROSE_LETTERS = 60
SUBSTANTIVE_PROSE_LETTERS = 80
MIN_INFORMATIVE_TITLE_LETTERS = 4
MAX_HEADER_LINE_CHARS = 40

# Reason codes are a closed vocabulary so diagnostics stay bounded and stable.
REASON_WEAK_RELEVANCE = "weak-relevance"
REASON_PROMOTIONAL = "promotional-low-information"
REASON_CONTROVERSY = "controversy-amplification"
REASON_REPEATED_ALARM = "repeated-alarm"

CONTROL_KEEP_NEWLINE_RE = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")
URL_RE = re.compile(r"(?i)(?:https?://|www\.)\S+")
BARE_DOMAIN_RE = re.compile(
    r"(?i)\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*"
    r"\.(?:com|org|net|io|dev|gg|me|co|xyz|app|sh|tv|to|link|store|shop|info|live|page)"
    r"(?:/\S*)?"
)
HANDLE_RE = re.compile(r"(?<![\w/])@[A-Za-z0-9_.]{2,}")
TIMECODE_LINE_RE = re.compile(r"^\(?\d{1,2}:\d{2}(?::\d{2})?\)?\b")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…。！？])\s+")
SHOUTING_RE = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
REPEATED_PUNCTUATION_RE = re.compile(r"(?:!!|\?\?|!\?|\?!)")
ALARM_EMOJI_RE = re.compile(
    "[\U0001f6a8\u26a0\ufe0f\u203c\u2757\u2755\U0001f621\U0001f620\U0001f631"
    "\U0001f628\U0001f4a5\U0001f525\U0001f92f\U0001f480]"
)
LEADING_DECORATION_RE = re.compile(r"^[^\w(\"'\u00bf\u00a1]+", re.UNICODE)
TRAILING_SEPARATOR_RE = re.compile(r"[\s\-–—|:;,·•>»]+$")
EMPTY_BRACKET_RE = re.compile(r"[(\[{]\s*[)\]}]")

# Promotional line markers. These are removed per line, never per item, so one
# sponsor sentence cannot delete a genuinely descriptive paragraph.
PROMOTIONAL_MARKERS = (
    "sponsor",
    "sponsored",
    "sponsorship",
    "brought to you by",
    "thanks to our sponsor",
    "thanks to my sponsor",
    "promo code",
    "coupon",
    "discount code",
    "use code",
    "% off",
    "affiliate",
    "referral",
    "commission",
    "my course",
    "course:",
    "full course",
    "enroll",
    "bootcamp",
    "masterclass",
    "workshop seats",
    "patreon",
    "ko-fi",
    "kofi",
    "buy me a coffee",
    "buymeacoffee",
    "merch",
    "newsletter",
    "sign up",
    "signup",
    "subscribe",
    "like and share",
    "smash that",
    "follow me",
    "my socials",
    "socials:",
    "links:",
    "link below",
    "links below",
    "in the description",
    "join the discord",
    "discord",
    "twitter",
    "x.com",
    "instagram",
    "tiktok",
    "linkedin",
    "facebook",
    "twitch",
    "mastodon",
    "bluesky",
    "patron",
    "gear i use",
    "my gear",
    "giveaway",
    "free trial",
    "limited time",
    "dm me",
    "hire me",
    "book a call",
    "timestamps",
    "chapters",
    "music by",
    "outro music",
    "intro music",
    "utm_source",
    "utm_campaign",
    "utm_medium",
)

# Controversy terms only matter together with amplification markers below. A
# neutral mention can never remove an item on its own.
CONTROVERSY_TERMS = (
    "election",
    "president",
    "presidential",
    "politics",
    "political",
    "left-wing",
    "right-wing",
    "woke",
    "immigration",
    "abortion",
    "conspiracy",
    "drama",
    "cancel culture",
    "cancelled",
    "canceled",
    "feud",
    "boycott",
    "racist",
    "sexist",
    "nazi",
    "communist",
    "fascist",
    "genocide",
)

HYPE_PHRASES = (
    "the truth about",
    "you won't believe",
    "you wont believe",
    "must watch",
    "shocking",
    "exposed",
    "destroys",
    "destroyed",
    "insane",
    "gone wrong",
    "biggest scam",
    "is a scam",
    "stop using",
    "delete your",
    "worst ever",
    "clickbait but real",
)


@dataclass(frozen=True)
class SanitizedDescription:
    """One bounded sanitation result for a single description."""

    prose: str
    summary: str
    removed_lines: int
    stripped_urls: int
    had_text: bool

    @property
    def prose_letters(self) -> int:
        return count_letters(self.prose)


@dataclass(frozen=True)
class Eligibility:
    """Deterministic lane decision with a closed reason code."""

    eligible: bool
    reason: str = ""


def count_letters(value: str) -> int:
    """Count Unicode letters so bounds work for every script, not just Latin."""

    return sum(1 for character in value if unicodedata.category(character).startswith("L"))


def _collapse(value: str) -> str:
    return " ".join(value.split())


def _is_promotional(value: str) -> bool:
    """Match closed promo markers on word boundaries so 'patronage' survives."""

    lowered = value.casefold()
    return any(
        re.search(r"(?<!\w)" + re.escape(marker) + r"(?!\w)", lowered)
        for marker in PROMOTIONAL_MARKERS
    )


def _is_header_line(value: str) -> bool:
    """Treat short shouting or colon-terminated labels as structure, not prose."""

    if len(value) > MAX_HEADER_LINE_CHARS and not value.endswith(":"):
        return False
    if value.endswith(":") and len(value) <= MAX_HEADER_LINE_CHARS:
        return True
    letters = [character for character in value if unicodedata.category(character).startswith("L")]
    if not letters:
        return True
    return (
        len(value) <= MAX_HEADER_LINE_CHARS
        and all(not character.islower() for character in letters)
        and any(character.isupper() for character in letters)
    )


def _strip_locators(value: str) -> tuple[str, int]:
    """Remove URLs, bare domains and social handles, then tidy the remainder."""

    stripped = 0
    for pattern in (URL_RE, BARE_DOMAIN_RE, HANDLE_RE):
        value, replacements = pattern.subn(" ", value)
        stripped += replacements
    value = EMPTY_BRACKET_RE.sub(" ", value)
    value = LEADING_DECORATION_RE.sub("", value)
    value = TRAILING_SEPARATOR_RE.sub("", value)
    return _collapse(value), stripped


def sanitize_description(value: object) -> SanitizedDescription:
    """Return bounded factual prose for one untrusted description."""

    raw = value if isinstance(value, str) else ""
    raw = unicodedata.normalize("NFC", raw)[:MAX_DESCRIPTION_CHARS]
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = CONTROL_KEEP_NEWLINE_RE.sub(" ", raw)
    lines = [line.strip() for line in raw.split("\n")][:MAX_DESCRIPTION_LINES]
    had_text = any(count_letters(line) > 0 for line in lines)

    kept: list[str] = []
    removed = 0
    stripped_urls = 0
    for line in lines:
        if not line:
            continue
        if _is_promotional(line) or TIMECODE_LINE_RE.match(line) or _is_header_line(line):
            removed += 1
            continue
        cleaned, stripped = _strip_locators(line)
        stripped_urls += stripped
        if count_letters(cleaned) < MIN_PROSE_LINE_LETTERS:
            # A link-only line, a bare handle row, or a decorative fragment.
            removed += 1
            continue
        kept.append(cleaned)

    sentences = [
        sentence
        for sentence in SENTENCE_SPLIT_RE.split(_collapse(" ".join(kept)))
        if count_letters(sentence) >= MIN_KEPT_SENTENCE_LETTERS
    ]
    prose = _bound_sentences(sentences)
    return SanitizedDescription(
        prose=prose,
        summary=prose or NEUTRAL_SUMMARY,
        removed_lines=removed,
        stripped_urls=stripped_urls,
        had_text=had_text,
    )


def _bound_sentences(sentences: list[str]) -> str:
    """Keep whole factual sentences inside the summary bound; mark truncation."""

    if not sentences:
        return ""
    limit = SUMMARY_MAX_CHARS
    ellipsis_limit = limit - 3
    selected: list[str] = []
    length = 0
    for sentence in sentences:
        candidate = length + (1 if selected else 0) + len(sentence)
        if candidate > ellipsis_limit and selected:
            break
        if candidate > ellipsis_limit:
            return sentence[:ellipsis_limit].rstrip() + "…"
        selected.append(sentence)
        length = candidate
    text = " ".join(selected)
    if len(selected) < len(sentences):
        text = text[:ellipsis_limit].rstrip() + "…"
    return text[:limit]


def alarm_signals(value: str) -> int:
    """Count independent amplification markers in one bounded string."""

    lowered = value.casefold()
    signals = 0
    if len(ALARM_EMOJI_RE.findall(value)) >= 2:
        signals += 1
    if REPEATED_PUNCTUATION_RE.search(value):
        signals += 1
    shouting = [word for word in SHOUTING_RE.findall(value) if word.isupper()]
    if len(shouting) >= 3:
        signals += 1
    if any(phrase in lowered for phrase in HYPE_PHRASES):
        signals += 1
    return signals


def has_controversy_term(value: str) -> bool:
    lowered = value.casefold()
    return any(term in lowered for term in CONTROVERSY_TERMS)


def evaluate_eligibility(*, title: object, prose: object) -> Eligibility:
    """Decide whether one sanitized item belongs in the YouTube lane.

    The rules are intentionally narrow. Relevance requires the keyword in the
    title or in real cleaned prose, so a video that merely links to omarchy.org
    is not Omarchy activity. Promotional or link-only descriptions survive only
    behind an informative title. Controversy and repeated-alarm removal each
    require several independent markers together with missing substance, so a
    critical review, a negative verdict, or a non-English description is never
    removed for tone or language.
    """

    title_text = _collapse(unicodedata.normalize("NFC", title if isinstance(title, str) else ""))
    prose_text = _collapse(unicodedata.normalize("NFC", prose if isinstance(prose, str) else ""))
    if prose_text == NEUTRAL_SUMMARY:
        prose_text = ""
    prose_letters = count_letters(prose_text)
    title_has_keyword = KEYWORD_RE.search(title_text) is not None
    strong_prose = (
        KEYWORD_RE.search(prose_text) is not None and prose_letters >= STRONG_PROSE_LETTERS
    )
    if not title_has_keyword and not strong_prose:
        return Eligibility(False, REASON_WEAK_RELEVANCE)

    informative_title = (
        title_has_keyword
        and count_letters(KEYWORD_RE.sub(" ", title_text)) >= MIN_INFORMATIVE_TITLE_LETTERS
        and not _is_promotional(title_text)
    )
    if prose_letters < MIN_INFORMATIVE_PROSE_LETTERS and not informative_title:
        return Eligibility(False, REASON_PROMOTIONAL)

    combined = f"{title_text}\n{prose_text}"
    signals = alarm_signals(combined)
    if signals >= 2 and has_controversy_term(combined):
        return Eligibility(False, REASON_CONTROVERSY)
    if signals >= 3 and prose_letters < SUBSTANTIVE_PROSE_LETTERS:
        return Eligibility(False, REASON_REPEATED_ALARM)
    return Eligibility(True)
