"""Escaped JSON, RSS and static HTML publication."""

from __future__ import annotations

import hashlib
import html
import os
import shutil
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from xml.etree import ElementTree as ET

from .io import canonical_json_bytes
from .errors import FetchError, ValidationError
from .http import FetchPolicy, fetch_bytes
from .images import MAX_IMAGE_BYTES, inspect_raster
from .model import front_page
from .validation import format_timestamp, parse_timestamp, validate_feed

CSP = "default-src 'none'; style-src 'self'; img-src 'self' https://plugins.omarchy.org; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


def render_rss(feed: Mapping[str, Any]) -> bytes:
    validated = validate_feed(dict(feed), now=parse_timestamp(feed["generatedAt"]))
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Omarchy News Radar"
    ET.SubElement(channel, "link").text = "https://mtolhuijs.nl/news-radar/"
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


def _story(event: Mapping[str, Any], *, lead: bool = False) -> str:
    title = html.escape(str(event["title"]))
    summary = html.escape(str(event["summary"]))
    source_label = html.escape(str(event["source"]["label"]))
    source_url = html.escape(str(event["source"]["url"]), quote=True)
    occurred = html.escape(str(event["occurredAt"]))
    section = html.escape(str(event["classification"]["section"]))
    trust = html.escape(str(event["trust"]["marketplace"]))
    class_name = "story lead" if lead else "story"
    image = event.get("image")
    image_html = ""
    if isinstance(image, dict):
        src = image.get("sourceUrl") if isinstance(image.get("sourceUrl"), str) else image.get("path")
        if isinstance(src, str):
            image_html = (
                f'<img src="{html.escape(src, quote=True)}" '
                f'alt="{html.escape(str(image["alt"]), quote=True)}" '
                f'width="{int(image["width"])}" height="{int(image["height"])}" loading="lazy">\n  '
            )
    return f'''<article class="{class_name}">
  {image_html}<div class="copy">
  <p class="kicker">{section} · {occurred}</p>
  <h2>{title}</h2>
  <p>{summary}</p>
  <p class="meta">Trust: {trust}</p>
  <a href="{source_url}" rel="noopener noreferrer external">{source_label} →</a></div>
</article>'''


def render_html(feed: Mapping[str, Any]) -> bytes:
    validated = validate_feed(dict(feed), now=parse_timestamp(feed["generatedAt"]))
    edition = front_page(validated["events"])
    stories = "\n".join(_story(event, lead=index == 0) for index, event in enumerate(edition))
    health = ", ".join(f"{html.escape(source['id'])}: {html.escape(source['status'])}" for source in validated["sources"])
    generated = html.escape(validated["generatedAt"])
    published = html.escape(str(validated.get("publishedAt", validated["generatedAt"])))
    page = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{html.escape(CSP, quote=True)}">
  <meta name="referrer" content="no-referrer">
  <title>Omarchy News Radar</title>
  <link rel="stylesheet" href="assets/site.css">
  <link rel="alternate" type="application/rss+xml" title="Omarchy News Radar" href="feed.xml">
</head>
<body>
  <header>
    <p class="eyebrow">Independent community project</p>
    <h1>Omarchy News Radar</h1>
    <p class="deck">A calm, source-linked edition of meaningful Omarchy activity.</p>
    <p class="health">Sources collected {generated} · artifact published {published} · {health}</p>
  </header>
  <main>{stories if stories else '<p class="empty">This edition contains no events.</p>'}</main>
  <footer><a href="events.json">JSON feed</a> · <a href="feed.xml">RSS</a></footer>
</body>
</html>
'''
    return page.encode("utf-8")


SITE_CSS = b'''*{box-sizing:border-box}body{margin:0 auto;max-width:1120px;padding:3rem 1.25rem;background:#101315;color:#e7e7e2;font:16px/1.6 ui-monospace,monospace}header{border-bottom:2px solid #e7e7e2;margin-bottom:2rem;padding-bottom:2rem}h1{font-size:clamp(2.5rem,8vw,5.5rem);letter-spacing:-.08em;line-height:.88;margin:.3rem 0 1rem}.eyebrow,.kicker,.meta,.health{font-size:.76rem;letter-spacing:.08em;text-transform:uppercase;color:#9aa0a3}.deck{font-size:1.25rem;max-width:46rem}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:#4a5053}.story{background:#101315;padding:1.5rem}.story.lead{grid-column:1/-1;padding:2.5rem}.story img{display:block;width:100%;height:auto;max-height:18rem;object-fit:cover;margin:0 0 1rem}.story h2{font-size:1.55rem;line-height:1.1}.lead h2{font-size:clamp(2rem,5vw,3.8rem)}a{color:#e7e7e2;text-underline-offset:.2em}footer{padding:2rem 0}.empty{background:#101315;padding:2rem}@media(min-width:701px){.story.lead{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:2rem}.story.lead img{margin:0;max-height:26rem}}@media(max-width:700px){body{padding:2rem 1rem}main{display:block}.story{border-bottom:1px solid #4a5053}.story.lead{padding:1.5rem}}@media(prefers-color-scheme:light){body,.story,.empty{background:#f2f0e9;color:#181a1b}main{background:#aaa}.eyebrow,.kicker,.meta,.health{color:#596064}a{color:#181a1b}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}\n'''


ImageFetcher = Callable[[str], tuple[bytes, str]]


def _fetch_image(url: str) -> tuple[bytes, str]:
    data, headers, _ = fetch_bytes(
        url,
        policy=FetchPolicy(MAX_IMAGE_BYTES, 20.0, frozenset({"https://plugins.omarchy.org"})),
        headers={"Accept": "image/webp,image/png,image/jpeg", "User-Agent": "omarchy-news-radar-publisher/0.1"},
    )
    return data, str(headers.get("Content-Type", ""))


def materialize_images(
    feed: Mapping[str, Any], asset_directory: Path, *, image_fetcher: ImageFetcher = _fetch_image
) -> tuple[dict[str, Any], list[str]]:
    """Validate allowlisted marketplace previews and publish their HTTPS URLs.

    Rasters are not mirrored onto the feed host. ``asset_directory`` is retained
    for call-site compatibility; only ``assets/site.css`` is written by publish().
    """

    del asset_directory  # no longer used for hosted rasters
    candidate = validate_feed(dict(feed), now=parse_timestamp(feed["generatedAt"]))
    public_feed = deepcopy(candidate)
    failures: list[str] = []
    for event in public_feed["events"]:
        image = event.get("image")
        if not isinstance(image, dict) or "sourceUrl" not in image:
            continue
        try:
            data, content_type = image_fetcher(str(image["sourceUrl"]))
            info = inspect_raster(data, content_type)
            if (info.width, info.height) != (image["width"], image["height"]):
                raise ValidationError("image dimensions differ from marketplace metadata")
            event["image"] = {
                "sourceUrl": image["sourceUrl"],
                "alt": image["alt"],
                "credit": image["credit"],
                "width": info.width,
                "height": info.height,
            }
        except (FetchError, ValidationError, OSError) as exc:
            failures.append(f"{event['id']}: {exc}")
            del event["image"]
    return validate_feed(public_feed, now=parse_timestamp(public_feed["generatedAt"]), public_only=True), failures


def publish(
    feed: Mapping[str, Any],
    destination: Path,
    *,
    source_revision: str = "unknown",
    image_fetcher: ImageFetcher = _fetch_image,
    published_at: datetime | None = None,
) -> dict[str, Any]:
    validated = validate_feed(dict(feed), now=parse_timestamp(feed["generatedAt"]))
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
        html_bytes = render_html(validated)
        (temporary / "events.json").write_bytes(events_bytes)
        (temporary / "feed.xml").write_bytes(rss_bytes)
        (temporary / "index.html").write_bytes(html_bytes)
        (temporary / "assets" / "site.css").write_bytes(SITE_CSS)
        month = validated["generatedAt"][:7]
        (temporary / "archive" / f"{month}.json").write_bytes(events_bytes)
        digest = hashlib.sha256(events_bytes).hexdigest()
        (temporary / "BUILD-INFO.txt").write_text(
            f"sourceRevision={source_revision}\neventsSha256={digest}\npublishedAt={validated['publishedAt']}\n",
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
        }
    finally:
        if temporary and temporary.exists() and temporary != Path("."):
            shutil.rmtree(temporary)
