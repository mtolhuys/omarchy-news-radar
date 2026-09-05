"""Shared escaped document structure and fixed public destinations."""

import html
from pathlib import Path
from ..constants import FEED_URL, PLUGIN_ID
from ..reading import article_segments
from ..validation import parse_timestamp

CSP = "default-src 'none'; style-src 'self'; img-src 'self' https://plugins.omarchy.org https://i.ytimg.com; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
SITE_URL = FEED_URL.rsplit("/", 1)[0] + "/"
MARKETPLACE_URL = f"https://plugins.omarchy.org/plugin.html?id={PLUGIN_ID}"
WALKTHROUGH_URL = "https://github.com/mtolhuys/omarchy-news-radar#readme"
PAGE_TITLE = "Omarchy News Radar — catch up with what changed"
PAGE_DESCRIPTION = "Omarchy releases, official news and plugin activity, linked to their original sources. Read the web edition or bring Radar to your Omarchy desktop."
MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


SITE_CSS = Path(__file__).with_name("site.css").read_bytes()


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def date_label(timestamp: str) -> str:
    date = parse_timestamp(timestamp)
    return f"{date.day} {MONTH_NAMES[date.month - 1]} {date.year}"


def external(url: str, label: str) -> str:
    return f'<a href="{escape(url)}" rel="noopener noreferrer external">{escape(label)} →</a>'


def paragraphs(value: str) -> str:
    blocks = []
    for part in value.split("\n\n"):
        if not part.strip():
            continue
        content = "".join(
            f'<a href="{escape(segment["url"])}" rel="noopener noreferrer external">{escape(segment["text"])}</a>'
            if segment["kind"] == "link" else escape(segment["text"])
            for segment in article_segments(part)
        )
        blocks.append(f"<p>{content}</p>")
    return "\n".join(blocks)


def document(*, title: str, description: str, path: str, body: str, footer: str = "") -> bytes:
    base = "../" * path.count("/")
    canonical = SITE_URL + path.removesuffix("index.html")
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{escape(CSP)}">
  <meta name="referrer" content="no-referrer">
  <meta name="description" content="{escape(description)}">
  <meta property="og:type" content="{'website' if path == 'index.html' else 'article'}">
  <meta property="og:site_name" content="Omarchy News Radar">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{escape(title)}">
  <meta name="twitter:description" content="{escape(description)}">
  <title>{escape(title)}</title>
  <link rel="canonical" href="{escape(canonical)}">
  <link rel="stylesheet" href="{base}assets/site.css">
  <link rel="alternate" type="application/rss+xml" title="Omarchy News Radar" href="{base}feed.xml">
</head>
<body>
  <a class="skip-link" href="#news">Skip to the news</a>
  <div class="masthead"><a class="wordmark" href="{base or './'}">OMARCHY / NEWS RADAR</a><a href="{base}feed.xml">Follow via RSS</a></div>
  {body}
  <aside class="desktop" aria-labelledby="desktop-title">
    <div><p class="eyebrow">A calmer way to keep up</p><h2 id="desktop-title">Bring Radar to your desktop</h2>
    <p>A finite briefing, useful discoveries and source-linked changes for your setup. Your follows, saves and reading history stay on your device.</p></div>
    <nav class="desktop-actions" aria-label="Get the desktop plugin">
      <a class="install" href="{escape(MARKETPLACE_URL)}" rel="noopener noreferrer external">Install from the marketplace →</a>
      {external(WALKTHROUGH_URL, 'See the desktop walkthrough')}
    </nav>
  </aside>
  <footer><nav aria-label="Edition feeds"><a href="{base}feed.xml">Follow via RSS</a> · <a href="{base}events.json">JSON feed</a></nav>
    <p>Independent community project. Original sources remain the authority.</p>{footer}
  </footer>
</body>
</html>
'''.encode("utf-8")
