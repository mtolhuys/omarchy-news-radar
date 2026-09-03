"""Allowlisted official Omarchy News RSS 2.0 adapter."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from ..errors import ValidationError
from ..model import event_id
from ..validation import format_timestamp, normalize_text, parse_timestamp, validate_https_url

# Canonical self link from the live feed. Both /news/rss and /news/rss.xml
# currently serve the same document; collection allowlists only this URL.
RSS_URL = "https://omarchy.org/news/rss.xml"
PUBLIC_URL = "https://omarchy.org/news"
RSS_ORIGIN = "https://omarchy.org"
MAX_ITEMS = 100
MAX_RSS_BYTES = 512 * 1024
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
DC_NS = "http://purl.org/dc/elements/1.1/"
ATOM_NS = "http://www.w3.org/2005/Atom"

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
SLUG_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._:+-]{0,159})$")
NEWS_PATH_RE = re.compile(r"^/news/[0-9]{4}/[0-9]{2}/[A-Za-z0-9][A-Za-z0-9._-]{0,158}$")


def _child_text(element: ET.Element, name: str, namespace: str | None = None) -> str:
    if namespace:
        node = element.find(f"{{{namespace}}}{name}")
    else:
        node = element.find(name)
    if node is None or node.text is None:
        return ""
    return str(node.text)


def _plain_summary(value: str, fallback: str) -> str:
    text = TAG_RE.sub(" ", value)
    text = WHITESPACE_RE.sub(" ", html.unescape(text)).strip()
    if not text:
        text = fallback
    if len(text) > 400:
        text = text[:397].rstrip() + "…"
    return normalize_text(text, 400)


def _allowlisted_news_url(value: str, label: str) -> str:
    url = validate_https_url(value, label)
    parsed = urlsplit(url)
    if parsed.netloc != "omarchy.org" or not NEWS_PATH_RE.fullmatch(parsed.path):
        raise ValidationError("Omarchy News item URL is outside the allowlisted path family")
    return url


def _news_identity(guid: str, link: str) -> tuple[str, str, str]:
    """Return (entity_id, occurrence_key, source_url) from guid with link fallback."""

    source = _allowlisted_news_url(guid.strip() or link.strip(), "omarchy-news.guid")
    link_url = _allowlisted_news_url(link.strip() or source, "omarchy-news.link")
    slug = urlsplit(source).path.rsplit("/", 1)[-1]
    if not SLUG_RE.fullmatch(slug):
        raise ValidationError("Omarchy News item slug is invalid")
    return slug, source, link_url


def _parse_pub_date(value: str) -> str:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError) as exc:
        raise ValidationError("Omarchy News pubDate is invalid") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return format_timestamp(parsed.astimezone(timezone.utc).replace(microsecond=0))


def parse_news_rss(payload: bytes | str) -> dict[str, dict[str, Any]]:
    """Parse and normalize the official Omarchy News RSS 2.0 document."""

    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = payload
    if not isinstance(raw, (bytes, bytearray)) or len(raw) == 0 or len(raw) > MAX_RSS_BYTES:
        raise ValidationError("Omarchy News RSS payload size is invalid")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValidationError("Omarchy News RSS is not well-formed XML") from exc
    if root.tag != "rss" or root.attrib.get("version") != "2.0":
        raise ValidationError("Omarchy News payload must be RSS 2.0")
    channel = root.find("channel")
    if channel is None:
        raise ValidationError("Omarchy News RSS channel is missing")
    self_link = channel.find(f"{{{ATOM_NS}}}link")
    if self_link is not None:
        href = self_link.attrib.get("href", "")
        if href and href not in {RSS_URL, "https://omarchy.org/news/rss"}:
            raise ValidationError("Omarchy News RSS self link is not allowlisted")
    items = channel.findall("item")
    if len(items) > MAX_ITEMS:
        raise ValidationError("Omarchy News RSS item bound exceeded")
    news: dict[str, dict[str, Any]] = {}
    for item in items:
        title = normalize_text(_child_text(item, "title") or "Omarchy News", 160)
        link_raw = _child_text(item, "link")
        guid_raw = _child_text(item, "guid").strip() or link_raw
        entity_id, occurrence_key, link_url = _news_identity(guid_raw, link_raw)
        if entity_id in news:
            raise ValidationError("Omarchy News item ids must be unique")
        published_at = _parse_pub_date(_child_text(item, "pubDate"))
        parse_timestamp(published_at, "omarchy-news.pubDate")
        creator = _child_text(item, "creator", DC_NS).strip() or "Omarchy News"
        description = _child_text(item, "description")
        encoded = _child_text(item, "encoded", CONTENT_NS)
        summary = _plain_summary(description or encoded, title)
        news[entity_id] = {
            "id": entity_id,
            "guid": occurrence_key,
            "title": title,
            "url": occurrence_key if occurrence_key.startswith("https://omarchy.org/news/") else link_url,
            "publishedAt": published_at,
            "summary": summary,
            "creator": normalize_text(creator, 120),
        }
    return dict(sorted(news.items(), key=lambda pair: pair[0]))


def diff_news(
    previous: Mapping[str, Mapping[str, Any]],
    current: Mapping[str, Mapping[str, Any]],
    *,
    discovered_at: datetime,
    window_from: datetime,
) -> list[dict[str, Any]]:
    """Emit new Omarchy News events inside the rolling window."""

    events: list[dict[str, Any]] = []
    for item_id, item in current.items():
        if item_id in previous or parse_timestamp(item["publishedAt"]) < window_from:
            continue
        source_url = str(item["url"])
        events.append(
            {
                "id": event_id("omarchy-news", "omarchy", item_id, item["guid"], source_url),
                "type": "omarchy-news",
                "occurredAt": item["publishedAt"],
                "discoveredAt": format_timestamp(discovered_at),
                "title": item["title"],
                "summary": item["summary"],
                "source": {"label": "Omarchy News", "url": source_url},
                "entity": {
                    "kind": "omarchy",
                    "id": item_id,
                    "name": item["creator"],
                },
                "classification": {
                    "section": "core",
                    "significance": "routine",
                    "curated": False,
                    "tags": ["news"],
                },
                "trust": {"marketplace": "not-applicable", "securityAudit": False},
                "compatibility": {"channels": ["quattro"], "basis": "declared"},
            }
        )
    return events
