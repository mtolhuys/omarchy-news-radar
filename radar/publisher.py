"""Escaped JSON, RSS and static HTML publication."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree as ET

from .io import canonical_json_bytes
from .errors import ValidationError
from .validation import format_timestamp, parse_timestamp, validate_feed
from .insights import INSIGHTS_MAX_BYTES, validate_insights
from .setup_news import SETUP_NEWS_MAX_BYTES, validate_setup_news
from .publication_images import ImageFetcher, _fetch_image, materialize_images, materialize_insight_images
from .site.common import CSP, SITE_URL, SITE_CSS
from .site.pages import render_html, render_story, render_collection, render_week, edition_week


def render_rss(feed: Mapping[str, Any]) -> bytes:
    validated = validate_feed(dict(feed), now=parse_timestamp(feed.get("publishedAt", feed["generatedAt"])))
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Omarchy News Radar"
    ET.SubElement(channel, "link").text = SITE_URL
    ET.SubElement(channel, "description").text = "Source-linked Omarchy ecosystem activity. Independent community project."
    last_build = str(validated.get("publishedAt", validated["generatedAt"]))
    ET.SubElement(channel, "lastBuildDate").text = datetime.strptime(last_build, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    for event in validated["events"]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = event["id"]
        ET.SubElement(item, "title").text = event["title"]
        ET.SubElement(item, "link").text = event["source"]["url"]
        ET.SubElement(item, "description").text = event["summary"]
        ET.SubElement(item, "pubDate").text = datetime.strptime(event["occurredAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    ET.indent(rss, space="  ")
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="utf-8") + b"\n"




def publish(
    feed: Mapping[str, Any],
    destination: Path,
    *,
    source_revision: str = "unknown",
    image_fetcher: ImageFetcher = _fetch_image,
    published_at: datetime | None = None,
    insights: Mapping[str, Any] | None = None,
    setup_news: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validated = validate_feed(dict(feed), now=parse_timestamp(feed.get("publishedAt", feed["generatedAt"])))
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=parent))
    try:
        (temporary / "assets").mkdir()
        (temporary / "archive").mkdir()
        validated, image_failures = materialize_images(validated, temporary / "assets", image_fetcher=image_fetcher)
        publication_clock = (published_at or parse_timestamp(validated["generatedAt"])).astimezone(timezone.utc).replace(microsecond=0)
        validated = validate_feed(
            {**validated, "publishedAt": format_timestamp(publication_clock)},
            now=publication_clock,
            public_only=True,
        )
        events_bytes = canonical_json_bytes(validated)
        rss_bytes = render_rss(validated)
        public_insights = validate_insights(dict(insights), now=publication_clock) if insights is not None else None
        public_setup_news = (
            validate_setup_news(dict(setup_news), now=publication_clock)
            if setup_news is not None
            else None
        )
        if public_insights is not None:
            public_insights, insight_image_failures = materialize_insight_images(public_insights, image_fetcher=image_fetcher)
            image_failures.extend(insight_image_failures)
        html_bytes = render_html(validated, public_insights)
        (temporary / "events.json").write_bytes(events_bytes)
        (temporary / "feed.xml").write_bytes(rss_bytes)
        (temporary / "index.html").write_bytes(html_bytes)
        (temporary / "assets" / "site.css").write_bytes(SITE_CSS)
        if public_insights is not None:
            insight_bytes = canonical_json_bytes(public_insights)
            if len(insight_bytes) > INSIGHTS_MAX_BYTES:
                raise ValidationError("insights publication exceeds its byte bound")
            (temporary / "insights.json").write_bytes(insight_bytes)
            pages = {}
            for event in validated["events"]:
                pages[f"stories/{event['id']}/index.html"] = render_story(event, public_insights)
            for collection in public_insights["collections"]:
                pages[f"discover/{collection['id']}/index.html"] = render_collection(collection, public_insights)
            pages[f"editions/{edition_week(validated)}/index.html"] = render_week(validated)
            for relative, page in pages.items():
                if len(page) > 256 * 1024:
                    raise ValidationError("public page exceeds its byte bound")
                target = temporary / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(page)
        if public_setup_news is not None:
            setup_news_bytes = canonical_json_bytes(public_setup_news)
            if len(setup_news_bytes) > SETUP_NEWS_MAX_BYTES:
                raise ValidationError("setup news publication exceeds its byte bound")
            (temporary / "setup-news.json").write_bytes(setup_news_bytes)
        month = validated["generatedAt"][:7]
        (temporary / "archive" / f"{month}.json").write_bytes(events_bytes)
        digest = hashlib.sha256(events_bytes).hexdigest()
        setup_news_digest = (
            hashlib.sha256(canonical_json_bytes(public_setup_news)).hexdigest()
            if public_setup_news is not None
            else None
        )
        (temporary / "BUILD-INFO.txt").write_text(
            f"sourceRevision={source_revision}\neventsSha256={digest}\n"
            + (f"setupNewsSha256={setup_news_digest}\n" if setup_news_digest else "")
            + f"publishedAt={validated['publishedAt']}\n",
            encoding="utf-8",
        )
        if destination.exists():
            backup = destination.with_name(f".{destination.name}.previous")
            if backup.exists():
                shutil.rmtree(backup)
            os.replace(destination, backup)
            try:
                os.replace(temporary, destination)
                temporary = Path()
            except OSError:
                os.replace(backup, destination)
                raise
            shutil.rmtree(backup)
        else:
            os.replace(temporary, destination)
            temporary = Path()
        return {
            "eventsSha256": digest,
            "sourceRevision": source_revision,
            "publishedAt": validated["publishedAt"],
            "images": sum("image" in event for event in validated["events"]),
            "imageFailures": image_failures,
            "setupNews": len(public_setup_news["plugins"]) if public_setup_news else 0,
        }
    finally:
        if temporary and temporary.exists() and temporary != Path("."):
            shutil.rmtree(temporary)
