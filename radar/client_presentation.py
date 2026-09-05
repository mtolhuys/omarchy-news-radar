"""Inert source-linked story presentation shared by client projections."""

from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import urlencode, urljoin

from .constants import MARKETPLACE_IMAGE_ORIGIN, YOUTUBE_IMAGE_ORIGIN
from .filters import has_reader_image
from .local_edition import local_image_url
from .reading import article_segments, list_summary
from .state import event_is_read
from .validation import validate_https_url

MARKETPLACE_PLUGIN_PAGE = "https://plugins.omarchy.org/plugin.html"


def decorate_events(events: list[dict[str, Any]], state: Mapping[str, Any], *, local: Any, image_base: str, env: Mapping[str, str]) -> list[dict[str, Any]]:
    saved_ids = set(state["saved"])
    decorated: list[dict[str, Any]] = []
    metric_labels = {
        "marketplace-views": "Views",
        "marketplace-hearts": "Hearts",
        "marketplace-copies": "Command copies",
        "repository-stars": "Repository stars",
        "release-asset-downloads": "Release asset downloads",
        "youtube-views": "Views",
        "youtube-likes": "Likes",
    }
    metric_order = tuple(metric_labels)
    for event in events:
        item = dict(event)
        item["isUnread"] = not event_is_read(state, item)
        item["isSaved"] = item["id"] in saved_ids
        # Cards stay scannable. The inspector keeps the full 0.4.14 body.
        item["listSummary"] = list_summary(item.get("summary"), item.get("title", ""))
        item["summarySegments"] = article_segments(item.get("summary"))
        image = item.get("image") if has_reader_image(item) else None
        if state["preferences"]["imagesVisible"] and isinstance(image, dict):
            source_url = image.get("sourceUrl")
            if isinstance(source_url, str) and (
                source_url.startswith(MARKETPLACE_IMAGE_ORIGIN + "/")
                or source_url.startswith(YOUTUBE_IMAGE_ORIGIN + "/")
            ):
                item["imageUrl"] = source_url
            elif "path" in image:
                # Legacy mirrored editions / local private caches.
                if local is not None:
                    cached_url = local_image_url(str(image["path"]), env)
                    if cached_url:
                        item["imageUrl"] = cached_url
                else:
                    item["imageUrl"] = urljoin(image_base, image["path"])
        entity = item.get("entity")
        if isinstance(entity, dict) and entity.get("kind") == "plugin":
            item["marketplaceUrl"] = validate_https_url(
                f"{MARKETPLACE_PLUGIN_PAGE}?{urlencode({'id': entity['id']})}",
                "plugin marketplace URL",
            )
        metrics = item.get("metrics", [])
        if isinstance(metrics, list) and metrics:
            by_id = {
                metric["id"]: metric
                for metric in metrics
                if isinstance(metric, dict) and metric.get("id") in metric_labels
            }
            ordered = [by_id[metric_id] for metric_id in metric_order if metric_id in by_id]
            item["metricItems"] = [
                {
                    "id": metric["id"],
                    "label": metric_labels[metric["id"]],
                    "valueText": f"{metric['value']:,}",
                }
                for metric in ordered
            ]
            item["metricsObservedAt"] = max(metric["observedAt"] for metric in ordered)
            if any(metric["id"].startswith("marketplace-") for metric in ordered):
                item["metricsCaveat"] = (
                    "Marketplace views, hearts, and command copies are anonymous aggregate "
                    "interactions—not installs, downloads, unique people, rankings, votes, "
                    "or security signals."
                )
        # The feed retains metric provenance for audits. The presentation model
        # intentionally exposes only inert display facts, never raw aggregate
        # endpoint links that are not useful reading destinations.
        item.pop("metrics", None)
        decorated.append(item)
    return decorated
