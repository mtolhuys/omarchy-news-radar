"""Compose the front page, durable stories, reviewed workflows and weekly editions."""

from typing import Any, Mapping
from ..insights import matching_release, validate_insights
from ..model import front_page
from ..provenance import release_matches_event_source
from ..validation import parse_timestamp, validate_feed
from .cards import collection_card, preview, project_card, story
from .common import PAGE_DESCRIPTION, PAGE_TITLE, date_label, document, escape, external, paragraphs


def edition_week(feed: Mapping[str, Any]) -> str:
    year, week, _ = parse_timestamp(feed["generatedAt"]).isocalendar()
    return f"{year}-W{week:02d}"


def render_html(feed: Mapping[str, Any], insights: Mapping[str, Any] | None = None) -> bytes:
    validated = validate_feed(dict(feed), now=parse_timestamp(feed.get("publishedAt", feed["generatedAt"])))
    insight = validate_insights(dict(insights), now=parse_timestamp(insights["publishedAt"])) if insights else None
    selection = front_page(validated["events"])
    if insight:
        selection = selection[:7]
    stories = "\n".join(story(event, lead=index == 0, link=insight is not None) for index, event in enumerate(selection))
    if not stories:
        stories = '<p class="empty">No stories in this edition yet. You can check back later or follow via RSS.</p>'
    discoveries = ""
    if insight and insight["collections"]:
        cards = "\n".join(collection_card(item) for item in insight["collections"][:6])
        discoveries = f'''<section class="discoveries" aria-labelledby="discover-title">
          <div class="section-heading"><div><p class="eyebrow">Make your desktop yours</p><h2 id="discover-title">Something useful to try</h2></div><p>Reviewed ideas. Original sources.</p></div>
          <div class="discovery-grid">{cards}</div></section>'''
    week = edition_week(validated)
    weekly = f'<a href="editions/{week}/">Read this week’s edition →</a>' if insight else ""
    body = f'''<header><p class="eyebrow">Independent community project · {date_label(validated['generatedAt'])}</p>
      <h1>Omarchy News Radar</h1><p class="deck">Know what changed.<br><span>Find your next useful discovery.</span></p>
      <div class="header-actions"><a href="#headlines">Read the latest ↓</a>{weekly}</div>
    </header>
    <main id="news" tabindex="-1" aria-label="Front page">
      <section id="headlines" aria-labelledby="headlines-title"><div class="section-heading"><h2 id="headlines-title">On the radar</h2><p>Every story leads to its source.</p></div><div class="story-grid">{stories}</div></section>
      {discoveries}
    </main>'''
    health = ", ".join(f"{escape(item['id'])}: {escape(item['status'])}" for item in validated["sources"])
    details = f'<details class="health"><summary>Publication details</summary><p>Sources collected {escape(validated["generatedAt"])} · artifact published {escape(validated.get("publishedAt", validated["generatedAt"]))} · {health}</p></details>'
    return document(title=PAGE_TITLE, description=PAGE_DESCRIPTION, path="index.html", body=body, footer=details)


def render_story(event: Mapping[str, Any], insights: Mapping[str, Any]) -> bytes:
    project = next((item for item in insights["projects"] if item["id"] == event["entity"]["id"]), None)
    version = event["entity"].get("version")
    release = matching_release(project["releases"], version) if project and version else None
    if release and not release_matches_event_source(event, project, release):
        release = None
    explanation = ""
    if release:
        explanation = f'<section class="notes"><h2>From the release notes</h2>{paragraphs(release["summary"])}{external(release["sourceUrl"], "Read the complete original notes")}</section>'
    related = [item for item in insights["collections"] if event["entity"]["id"] in item["projectIds"]]
    if related:
        explanation += '<section><h2>Put it to use</h2><div class="discovery-grid">' + "".join(collection_card(item, base="../../") for item in related[:3]) + '</div></section>'
    trust = event["trust"]["marketplace"]
    marketplace = f'<p class="meta">Marketplace: {escape(trust)}. Verification records compatibility, not a security audit.</p>' if trust != "not-applicable" else ""
    body = f'''<header class="detail-heading"><p class="eyebrow">{escape(event['classification']['section'])} · {date_label(event['occurredAt'])}</p>
      <h1>{escape(event['title'])}</h1>{external(event['source']['url'], event['source']['label'])}</header>
      <main id="news" class="detail" tabindex="-1">{preview(event)}{paragraphs(event['summary'])}
      {marketplace}{explanation}</main>'''
    return document(title=event["title"] + " · Omarchy News Radar", description=event["summary"][:300],
                    path=f"stories/{event['id']}/index.html", body=body)


def render_collection(item: Mapping[str, Any], insights: Mapping[str, Any]) -> bytes:
    projects = {project["id"]: project for project in insights["projects"]}
    cards = "\n".join(project_card(projects[identity]) for identity in item["projectIds"])
    source_links = {}
    for source in [item["source"], *item.get("sourceLinks", [])]:
        source_links.setdefault(source["url"], source)
    sources = "\n".join(f"<li>{external(source['url'], source['label'])}</li>" for source in source_links.values())
    body = f'''<header class="detail-heading"><p class="eyebrow">A workflow worth exploring</p><h1>{escape(item['title'])}</h1><p class="deck">{escape(item['summary'])}</p></header>
      <main id="news" class="detail" tabindex="-1">{preview(item)}{paragraphs(item['body'])}
      <section><h2>The projects</h2>{cards}</section><section class="notes"><h2>Go to the source</h2>
      <ul>{sources}</ul><p class="meta">Documentation reviewed {date_label(item['reviewedAt'])}. A reviewed suggestion is not a security audit.</p></section></main>'''
    return document(title=item["title"] + " · Omarchy News Radar", description=item["summary"],
                    path=f"discover/{item['id']}/index.html", body=body)


def render_week(feed: Mapping[str, Any]) -> bytes:
    week = edition_week(feed)
    events = [event for event in feed["events"] if edition_week({"generatedAt": event["occurredAt"]}) == week]
    cards = "\n".join(story(event, base="../../") for event in events[:40])
    if not cards:
        cards = '<p class="empty">No stories were collected for this week yet.</p>'
    title = f"Omarchy this week · {week}"
    body = f'''<header class="detail-heading"><p class="eyebrow">The weekly edition</p><h1>Omarchy this week</h1><p class="deck">{week} · {len(events)} source-linked stories</p><p>Collected through {date_label(feed['generatedAt'])}. This page updates during the week.</p></header>
      <main id="news" tabindex="-1"><div class="story-grid">{cards}</div><p>Showing up to 40 stories. The RSS feed includes the full rolling edition.</p></main>'''
    return document(title=title, description=f"Source-linked Omarchy activity collected for {week}.", path=f"editions/{week}/index.html", body=body)
