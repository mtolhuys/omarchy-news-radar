"""Attach optional source facts without affecting event identity or ordering."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from .sources.marketplace_engagement import ENGAGEMENT_URL
from .validation import validate_event

MARKETPLACE_METRICS = {"repository-stars"}
ENGAGEMENT_METRICS = {
    "marketplace-views",
    "marketplace-hearts",
    "marketplace-copies",
}
RELEASE_METRICS = {"release-asset-downloads"}


def _metric(metric_id: str, value: int, observed_at: str, source_url: str) -> dict[str, Any]:
    return {
        "id": metric_id,
        "value": value,
        "observedAt": observed_at,
        "sourceUrl": source_url,
    }


def enrich_event_metrics(
    events: Iterable[Mapping[str, Any]],
    *,
    observed_at: str,
    marketplace: Mapping[str, Any] | None,
    engagement: Mapping[str, Mapping[str, int]] | None,
    releases: Mapping[str, Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Refresh only metrics whose source succeeded; retain prior facts on failure."""

    release_by_url = {
        str(release.get("url")): release
        for release in (releases or {}).values()
        if isinstance(release, Mapping)
    }
    marketplace_plugins = marketplace.get("plugins", {}) if marketplace is not None else {}
    enriched: list[dict[str, Any]] = []

    for raw_event in events:
        event = deepcopy(dict(raw_event))
        current = {
            str(item.get("id")): dict(item)
            for item in event.get("metrics", [])
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        }
        entity = event.get("entity", {})
        entity_id = str(entity.get("id", "")) if isinstance(entity, Mapping) else ""

        if marketplace is not None and entity.get("kind") == "plugin":
            for metric_id in MARKETPLACE_METRICS:
                current.pop(metric_id, None)
            plugin = marketplace_plugins.get(entity_id) if isinstance(marketplace_plugins, Mapping) else None
            if isinstance(plugin, Mapping) and isinstance(plugin.get("stars"), int):
                current["repository-stars"] = _metric(
                    "repository-stars",
                    int(plugin["stars"]),
                    observed_at,
                    str(plugin["repository"]),
                )

        if engagement is not None and entity.get("kind") == "plugin":
            for metric_id in ENGAGEMENT_METRICS:
                current.pop(metric_id, None)
            aggregate = engagement.get(entity_id)
            if isinstance(aggregate, Mapping):
                for key, metric_id in (
                    ("views", "marketplace-views"),
                    ("hearts", "marketplace-hearts"),
                    ("copies", "marketplace-copies"),
                ):
                    current[metric_id] = _metric(
                        metric_id,
                        int(aggregate[key]),
                        observed_at,
                        ENGAGEMENT_URL,
                    )

        if releases is not None and event.get("type") == "omarchy-released":
            for metric_id in RELEASE_METRICS:
                current.pop(metric_id, None)
            source = event.get("source", {})
            source_url = str(source.get("url", "")) if isinstance(source, Mapping) else ""
            release = release_by_url.get(source_url)
            if isinstance(release, Mapping) and int(release.get("assetCount", 0)) > 0:
                current["release-asset-downloads"] = _metric(
                    "release-asset-downloads",
                    int(release["assetDownloads"]),
                    observed_at,
                    str(release["url"]),
                )

        if current:
            event["metrics"] = [current[key] for key in sorted(current)]
        else:
            event.pop("metrics", None)
        enriched.append(validate_event(event))
    return enriched
