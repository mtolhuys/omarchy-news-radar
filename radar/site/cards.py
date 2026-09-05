"""Small source-linked cards shared by public editions and detail pages."""

from typing import Any, Mapping
from ..reading import collapse_article_links
from .common import date_label, escape, external


def preview(item: Mapping[str, Any]) -> str:
    image = item.get("image")
    if not isinstance(image, dict):
        return ""
    url = image.get("sourceUrl", image.get("path"))
    return f'<img src="{escape(url)}" alt="{escape(image["alt"])}" width="{int(image["width"])}" height="{int(image["height"])}" loading="lazy">'


def story(event: Mapping[str, Any], *, lead: bool = False, base: str = "", link: bool = True) -> str:
    image = preview(event)
    classes = "story" + (" lead" if lead else "") + (" has-image" if image else "")
    title = escape(event["title"])
    if link:
        title = f'<a href="{base}stories/{escape(event["id"])}/">{title}</a>'
    summary = collapse_article_links(str(event["summary"]))
    if len(summary) > 300:
        summary = summary[:299].rsplit(" ", 1)[0].rstrip() + "…"
    trust = event["trust"]["marketplace"]
    marketplace = f'<p class="meta">Marketplace: {escape(trust)}</p>' if trust != "not-applicable" else ""
    return f'''<article class="{classes}">{image}<div class="copy">
  <p class="kicker">{escape(event['classification']['section'])} · <time datetime="{escape(event['occurredAt'])}">{date_label(event['occurredAt'])}</time></p>
  <h2>{title}</h2><p>{escape(summary)}</p>
  {marketplace}
  {external(event['source']['url'], event['source']['label'])}
</div></article>'''


def collection_card(item: Mapping[str, Any], *, base: str = "") -> str:
    return f'''<article class="discovery-card">
      <p class="kicker">Workflow idea · {len(item['projectIds'])} projects</p>
      <h3><a href="{base}discover/{escape(item['id'])}/">{escape(item['title'])}</a></h3>
      <p>{escape(item['summary'])}</p>
      <a class="text-action" href="{base}discover/{escape(item['id'])}/">Explore the workflow →</a>
    </article>'''


def project_card(project: Mapping[str, Any]) -> str:
    latest = project["releases"][0] if project["releases"] else None
    coverage = f"Most recently published notes: {escape(latest['version'])}" if latest else "See the source for version and compatibility details."
    return f'''<article class="project-card">{preview(project)}<div>
      <h3>{escape(project['name'])}</h3><p>{escape(project['description'])}</p>
      <p class="meta">{coverage}</p>{external(project['source']['url'], project['source']['label'])}
    </div></article>'''
