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

from .constants import FEED_URL, PLUGIN_ID
from .io import canonical_json_bytes
from .errors import FetchError, ValidationError
from .http import FetchPolicy, fetch_bytes
from .images import MAX_IMAGE_BYTES, inspect_raster
from .model import front_page
from .validation import format_timestamp, parse_timestamp, validate_feed

CSP = "default-src 'none'; style-src 'self'; img-src 'self' https://plugins.omarchy.org https://i.ytimg.com; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
SITE_URL = FEED_URL.rsplit("/", 1)[0] + "/"
MARKETPLACE_URL = f"https://plugins.omarchy.org/plugin.html?id={PLUGIN_ID}"
WALKTHROUGH_URL = "https://github.com/mtolhuys/omarchy-news-radar#readme"
PAGE_TITLE = "Omarchy News Radar — catch up with what changed"
PAGE_DESCRIPTION = "Omarchy releases, official news and plugin activity, linked to their original sources. Read the web edition or bring Radar to your Omarchy desktop."
MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def render_rss(feed: Mapping[str, Any]) -> bytes:
    validated = validate_feed(dict(feed), now=parse_timestamp(feed["generatedAt"]))
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


def _story(event: Mapping[str, Any], *, lead: bool = False) -> str:
    title = html.escape(str(event["title"]))
    summary = html.escape(str(event["summary"]))
    source_label = html.escape(str(event["source"]["label"]))
    source_url = html.escape(str(event["source"]["url"]), quote=True)
    occurred = html.escape(str(event["occurredAt"]))
    occurred_at = parse_timestamp(str(event["occurredAt"]))
    occurred_label = f"{occurred_at.day} {MONTH_NAMES[occurred_at.month - 1]} {occurred_at.year}"
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
    if image_html:
        class_name += " has-image"
    return f'''<article class="{class_name}">
  {image_html}<div class="copy">
  <p class="kicker">{section} · <time datetime="{occurred}">{occurred_label}</time></p>
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
  <meta name="description" content="{html.escape(PAGE_DESCRIPTION, quote=True)}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Omarchy News Radar">
  <meta property="og:title" content="{html.escape(PAGE_TITLE, quote=True)}">
  <meta property="og:description" content="{html.escape(PAGE_DESCRIPTION, quote=True)}">
  <meta property="og:url" content="{html.escape(SITE_URL, quote=True)}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{html.escape(PAGE_TITLE, quote=True)}">
  <meta name="twitter:description" content="{html.escape(PAGE_DESCRIPTION, quote=True)}">
  <title>{html.escape(PAGE_TITLE)}</title>
  <link rel="canonical" href="{html.escape(SITE_URL, quote=True)}">
  <link rel="stylesheet" href="assets/site.css">
  <link rel="alternate" type="application/rss+xml" title="Omarchy News Radar" href="feed.xml">
</head>
<body>
  <a class="skip-link" href="#news">Skip to the news</a>
  <header>
    <div class="masthead">
      <p class="eyebrow">Independent community project</p>
      <a href="feed.xml">Follow via RSS</a>
    </div>
    <h1>Omarchy News Radar</h1>
    <p class="deck">Catch up on Omarchy releases, official news and plugin activity. Every story leads to its original source.</p>
    <aside class="desktop" aria-labelledby="desktop-title">
      <div>
        <h2 id="desktop-title">Keep Radar on your desktop</h2>
        <p>Find stories about your enabled plugins, save useful discoveries and pick up where you left off. Your reading state and plugin matching stay on your device.</p>
      </div>
      <nav class="desktop-actions" aria-label="Get the desktop plugin">
        <a class="install" href="{html.escape(MARKETPLACE_URL, quote=True)}" rel="noopener noreferrer external">Install from the marketplace →</a>
        <a href="{html.escape(WALKTHROUGH_URL, quote=True)}" rel="noopener noreferrer external">See the desktop walkthrough</a>
      </nav>
    </aside>
  </header>
  <main id="news" tabindex="-1" aria-label="Front page">{stories if stories else '<p class="empty">No stories in this edition yet. You can check back later or follow via RSS.</p>'}</main>
  <footer>
    <nav aria-label="Edition feeds"><a href="feed.xml">Follow via RSS</a> · <a href="events.json">JSON feed</a></nav>
    <p>Independent community project. Original sources remain the authority.</p>
    <details class="health"><summary>Publication details</summary><p>Sources collected {generated} · artifact published {published} · {health}</p></details>
  </footer>
</body>
</html>
'''
    return page.encode("utf-8")


SITE_CSS = b'''*{box-sizing:border-box}
:root{color-scheme:dark light;--paper:#101315;--ink:#e7e7e2;--secondary:#aeb5b8;--rule:#4a5053;--accent:#9ece6a}
body{margin:0 auto;max-width:1120px;padding:2rem 1.25rem;background:var(--paper);color:var(--ink);font:1rem/1.6 ui-monospace,monospace;overflow-wrap:anywhere}
header{border-bottom:2px solid var(--ink);margin-bottom:1.5rem;padding-bottom:1.5rem}
.masthead{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.5rem 1rem;margin-bottom:1.5rem}
.masthead p{margin:0}.masthead a,.desktop-actions{font-size:.875rem}
h1{font-size:clamp(2.5rem,7vw,4.5rem);letter-spacing:-.065em;line-height:1.05;margin:.3rem 0 1rem}
.eyebrow,.kicker,.meta{font-size:.8125rem;letter-spacing:.06em;text-transform:uppercase;color:var(--secondary)}
.deck{font-size:1.125rem;max-width:48rem;margin-bottom:1.5rem}
.desktop{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:1rem 2rem;border-top:1px solid var(--rule);padding-top:1.25rem}
.desktop h2{font-size:1rem;margin:0 0 .5rem}.desktop p{max-width:43rem;font-size:.9375rem;margin:0;color:var(--secondary)}
.desktop-actions{display:flex;flex-direction:column;justify-content:center;align-items:flex-start;gap:.75rem;max-width:20rem}
.install{background:var(--accent);color:var(--paper);font-weight:700;padding:.65rem .85rem;text-decoration:none;border:1px solid var(--accent)}
.install:hover{text-decoration:underline}
main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--rule)}
.story{background:var(--paper);padding:1.5rem;min-width:0}.story.lead{grid-column:1/-1;padding:2rem}.copy{min-width:0}
.story img{display:block;width:100%;height:auto;max-height:18rem;object-fit:cover;margin:0 0 1rem}
.story h2{font-size:1.55rem;line-height:1.2}.lead h2{font-size:clamp(2rem,5vw,3.25rem)}
a{color:var(--ink);text-underline-offset:.2em}a:hover{text-decoration-thickness:2px}
a:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:4px}
.skip-link{position:fixed;left:1rem;top:0;transform:translateY(-200%);background:var(--paper);padding:.75rem;z-index:1}.skip-link:focus{transform:translateY(0)}
footer{padding:2rem 0;font-size:.875rem}footer p,.health{color:var(--secondary)}.health summary{cursor:pointer}.health p{max-width:60rem}
.empty{grid-column:1/-1;background:var(--paper);padding:2rem;margin:0}
@media(min-width:701px){.story.lead.has-image{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:2rem}.story.lead img{margin:0;max-height:26rem}}
@media(max-width:800px){.desktop{grid-template-columns:minmax(0,1fr)}.desktop-actions{max-width:none}}
@media(max-width:700px){body{padding:1.5rem 1rem}main{display:block}.story{border-bottom:1px solid var(--rule)}.story.lead{padding:1.5rem}}
@media(prefers-color-scheme:light){:root{--paper:#f2f0e9;--ink:#181a1b;--secondary:#50575a;--rule:#aaa;--accent:#355b17}}
@media(forced-colors:active){.install{border-color:ButtonText}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
'''


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
        source_url = str(image["sourceUrl"])
        # YouTube hqdefault URLs are allowlisted by shape; no scrape/mirror.
        if source_url.startswith("https://i.ytimg.com/vi/") and source_url.endswith("/hqdefault.jpg"):
            event["image"] = {
                "sourceUrl": source_url,
                "alt": image["alt"],
                "credit": image["credit"],
                "width": image["width"],
                "height": image["height"],
            }
            continue
        try:
            data, content_type = image_fetcher(source_url)
            info = inspect_raster(data, content_type)
            if (info.width, info.height) != (image["width"], image["height"]):
                raise ValidationError("image dimensions differ from marketplace metadata")
            event["image"] = {
                "sourceUrl": source_url,
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
