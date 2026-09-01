"""Marketplace catalog normalization and conservative two-run diffs."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
from typing import Any, Iterable, Mapping

from ..errors import ValidationError
from ..model import event_id
from ..validation import format_timestamp, normalize_text, parse_timestamp, validate_event, validate_https_url

CATALOG_URL = "https://raw.githubusercontent.com/omacom/omarchy-plugin-marketplace/main/site/catalog.json"
MARKETPLACE_URL = "https://plugins.omarchy.org/"
VERIFICATION = {"verified", "reviewed", "unverified", "unknown"}
PREVIEW_RE = re.compile(r"^assets/img/plugins/[A-Za-z0-9._-]+\.(?:webp|png|jpg|jpeg)$")
MAX_BOOTSTRAP_EVENTS = 12
MAX_METRIC_VALUE = 9_007_199_254_740_991


def _optional_count(value: Any, name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= MAX_METRIC_VALUE:
        raise ValidationError(f"marketplace {name} is invalid")
    return value


def _bounded_description(value: Any, fallback: str) -> str:
    text = normalize_text(value or fallback, 10_000)
    if len(text) > 400:
        text = text[:397].rstrip() + "…"
    return normalize_text(text, 400)


def _plugin_url(plugin: Mapping[str, Any]) -> str:
    release = plugin.get("repositoryRelease")
    if isinstance(release, dict) and isinstance(release.get("url"), str) and release["url"]:
        return validate_https_url(release["url"], "plugin.repositoryRelease.url")
    return validate_https_url(plugin.get("repo"), "plugin.repo")


def _listing_time(plugin: Mapping[str, Any], generated_at: str) -> str:
    listed = plugin.get("listedAt")
    if isinstance(listed, str):
        try:
            parsed = datetime.fromisoformat(listed.replace("Z", "+00:00"))
            return format_timestamp(parsed)
        except (ValueError, ValidationError):
            pass
    added = plugin.get("addedAt")
    if isinstance(added, str):
        try:
            return format_timestamp(datetime.fromisoformat(added + "T00:00:00+00:00"))
        except (ValueError, ValidationError):
            pass
    return generated_at


def _has_listing_time(plugin: Mapping[str, Any]) -> bool:
    for key, suffix in (("listedAt", ""), ("addedAt", "T00:00:00+00:00")):
        value = plugin.get(key)
        if not isinstance(value, str):
            continue
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00") + suffix)
            return True
        except ValueError:
            continue
    return False


def _preview(plugin: Mapping[str, Any]) -> dict[str, Any] | None:
    path = plugin.get("previewThumbnail")
    width = plugin.get("previewThumbnailWidth")
    height = plugin.get("previewThumbnailHeight")
    if path is None and width is None and height is None:
        return None
    if not isinstance(path, str) or not PREVIEW_RE.fullmatch(path):
        raise ValidationError("marketplace preview path is invalid")
    if not isinstance(width, int) or isinstance(width, bool) or not 1 <= width <= 4096:
        raise ValidationError("marketplace preview width is invalid")
    if not isinstance(height, int) or isinstance(height, bool) or not 1 <= height <= 4096:
        raise ValidationError("marketplace preview height is invalid")
    if width * height > 12_000_000:
        raise ValidationError("marketplace preview pixel count exceeds its bound")
    return {
        "sourceUrl": "https://plugins.omarchy.org/" + path,
        "width": width,
        "height": height,
    }


def parse_marketplace(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("marketplace catalog must be an object")
    if payload.get("stateSchemaVersion") not in {1, 2}:
        raise ValidationError("marketplace stateSchemaVersion is unsupported")
    generated = payload.get("generatedAt")
    if not isinstance(generated, str):
        raise ValidationError("marketplace generatedAt is missing")
    try:
        generated_at = format_timestamp(datetime.fromisoformat(generated.replace("Z", "+00:00")))
    except ValueError as exc:
        raise ValidationError("marketplace generatedAt is invalid") from exc
    plugins_raw = payload.get("plugins")
    if not isinstance(plugins_raw, list) or len(plugins_raw) > 5000:
        raise ValidationError("marketplace plugins bound is invalid")
    plugins: dict[str, dict[str, Any]] = {}
    for raw in plugins_raw:
        if not isinstance(raw, dict):
            raise ValidationError("marketplace plugin must be an object")
        plugin_id = raw.get("id")
        if not isinstance(plugin_id, str) or not plugin_id or len(plugin_id) > 160:
            raise ValidationError("marketplace plugin id is invalid")
        if plugin_id in plugins:
            raise ValidationError("marketplace plugin ids must be unique")
        verification = str(raw.get("verificationStatus") or "unknown").lower()
        if verification not in VERIFICATION:
            verification = "unknown"
        tags_value = raw.get("tags")
        tags_raw = tags_value if isinstance(tags_value, list) else []
        tags = sorted(
            {
                str(tag).strip().lower().replace("_", "-")
                for tag in tags_raw
                if isinstance(tag, str) and 0 < len(tag.strip()) <= 32
            }
        )[:12]
        status = str(raw.get("status") or "").lower()
        retired = bool(raw.get("retired")) or status in {"retired", "removed", "deprecated"}
        version = str(raw.get("version") or "").strip()[:80]
        category = normalize_text(raw.get("category") or "Uncategorized", 60)
        category_tag = re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")[:32]
        if category_tag and category_tag not in tags:
            tags = sorted(tags + [category_tag])[:12]
        plugins[plugin_id] = {
            "name": normalize_text(raw.get("name"), 120),
            "description": _bounded_description(
                raw.get("description"),
                f"{raw.get('name')} is listed in the Omarchy plugin marketplace.",
            ),
            "version": version,
            "repository": validate_https_url(raw.get("repo"), "plugin.repo"),
            "sourceUrl": _plugin_url(raw),
            "category": category,
            "tags": tags,
            "addedAt": _listing_time(raw, generated_at),
            "listingDated": _has_listing_time(raw),
            "verification": verification,
            "retired": retired,
            "absenceCount": 0,
        }
        stars = _optional_count(raw.get("stars"), "stars")
        if stars is not None:
            plugins[plugin_id]["stars"] = stars
        preview = _preview(raw)
        if preview:
            plugins[plugin_id]["preview"] = preview
    return {"generatedAt": generated_at, "plugins": dict(sorted(plugins.items()))}


def _base_event(
    plugin_id: str,
    plugin: Mapping[str, Any],
    *,
    event_type: str,
    occurrence_key: str,
    occurred_at: str,
    discovered_at: datetime,
    title: str,
    summary: str,
) -> dict[str, Any]:
    source_url = str(plugin["sourceUrl"])
    entity: dict[str, Any] = {
        "kind": "plugin",
        "id": plugin_id,
        "name": plugin["name"],
        "repository": plugin["repository"],
    }
    if plugin.get("version"):
        entity["version"] = plugin["version"]
    event = {
        "id": event_id(event_type, "plugin", plugin_id, occurrence_key, source_url),
        "type": event_type,
        "occurredAt": occurred_at,
        "discoveredAt": format_timestamp(discovered_at),
        "title": title,
        "summary": summary,
        "source": {"label": "Plugin source", "url": source_url},
        "entity": entity,
        "classification": {
            "section": "plugins",
            "significance": "routine",
            "curated": False,
            "tags": plugin["tags"],
        },
        "trust": {"marketplace": plugin["verification"], "securityAudit": False},
        "compatibility": {"channels": [], "basis": "unknown"},
    }
    preview = plugin.get("preview")
    if isinstance(preview, dict):
        event["image"] = {
            "sourceUrl": preview["sourceUrl"],
            "alt": f"{plugin['name']} plugin preview",
            "credit": "Omarchy Plugin Marketplace",
            "width": preview["width"],
            "height": preview["height"],
        }
    return event


def enrich_plugin_descriptions(
    events: Iterable[Mapping[str, Any]], marketplace: Mapping[str, Any] | None
) -> list[dict[str, Any]]:
    """Refresh plugin explanations from the validated catalog.

    Description edits remain presentation enrichment: they update an existing
    plugin story but never create or reorder an event.
    """

    plugins = marketplace.get("plugins", {}) if marketplace is not None else {}
    enriched: list[dict[str, Any]] = []
    for raw_event in events:
        event = deepcopy(dict(raw_event))
        entity = event.get("entity")
        if event.get("type") in {
            "plugin-added",
            "plugin-released",
            "plugin-retired",
            "plugin-verification-changed",
        } and isinstance(entity, Mapping):
            plugin = plugins.get(entity.get("id"))
            if isinstance(plugin, Mapping):
                event["summary"] = plugin["description"]
        enriched.append(validate_event(event))
    return enriched


def diff_marketplace(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    *,
    discovered_at: datetime,
    bootstrap: bool = False,
    bootstrap_window_from: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return supported events and the next snapshot.

    A missing prior snapshot requires explicit bootstrap. It emits at most a
    small recent backfill so a first real edition is useful without presenting
    the whole catalog as new.
    """

    if previous is None:
        if not bootstrap:
            raise ValidationError("marketplace snapshot is absent; rerun with explicit bootstrap")
        bootstrap_events: list[dict[str, Any]] = []
        if bootstrap_window_from is not None:
            recent = [
                (plugin_id, plugin)
                for plugin_id, plugin in current["plugins"].items()
                if plugin.get("listingDated") is True
                and parse_timestamp(plugin["addedAt"]) >= bootstrap_window_from
            ]
            recent.sort(key=lambda pair: (pair[1]["addedAt"], pair[0]), reverse=True)
            for plugin_id, plugin in recent[:MAX_BOOTSTRAP_EVENTS]:
                bootstrap_events.append(
                    _base_event(
                        plugin_id,
                        plugin,
                        event_type="plugin-added",
                        occurrence_key=f"listing:{plugin['addedAt']}",
                        occurred_at=plugin["addedAt"],
                        discovered_at=discovered_at,
                        title=f"{plugin['name']} joined the marketplace",
                        summary=plugin["description"],
                    )
                )
        return bootstrap_events, {"generatedAt": current["generatedAt"], "plugins": dict(current["plugins"])}

    prior_plugins = previous.get("plugins")
    if not isinstance(prior_plugins, dict):
        raise ValidationError("previous marketplace snapshot is invalid")
    next_plugins = {plugin_id: dict(plugin) for plugin_id, plugin in current["plugins"].items()}
    events: list[dict[str, Any]] = []
    discovered_text = format_timestamp(discovered_at)

    for plugin_id, plugin in current["plugins"].items():
        old = prior_plugins.get(plugin_id)
        if not isinstance(old, dict):
            events.append(
                _base_event(
                    plugin_id,
                    plugin,
                    event_type="plugin-added",
                    occurrence_key=f"listing:{plugin['addedAt']}",
                    occurred_at=plugin["addedAt"],
                    discovered_at=discovered_at,
                    title=f"{plugin['name']} joined the marketplace",
                    summary=plugin["description"],
                )
            )
            continue
        old_version = str(old.get("version") or "")
        new_version = str(plugin.get("version") or "")
        if old_version and new_version and old_version != new_version:
            events.append(
                _base_event(
                    plugin_id,
                    plugin,
                    event_type="plugin-released",
                    occurrence_key=f"version:{old_version}->{new_version}",
                    occurred_at=discovered_text,
                    discovered_at=discovered_at,
                    title=f"{plugin['name']} {new_version}",
                    summary=plugin["description"],
                )
            )
        old_verification = str(old.get("verification") or "unknown")
        if old_verification != plugin["verification"]:
            events.append(
                _base_event(
                    plugin_id,
                    plugin,
                    event_type="plugin-verification-changed",
                    occurrence_key=f"verification:{old_verification}->{plugin['verification']}",
                    occurred_at=discovered_text,
                    discovered_at=discovered_at,
                    title=f"{plugin['name']} verification changed",
                    summary=plugin["description"],
                )
            )
        if plugin["retired"] and not bool(old.get("retired")):
            events.append(
                _base_event(
                    plugin_id,
                    plugin,
                    event_type="plugin-retired",
                    occurrence_key="explicit-retirement",
                    occurred_at=discovered_text,
                    discovered_at=discovered_at,
                    title=f"{plugin['name']} retired",
                    summary=plugin["description"],
                )
            )

    for plugin_id, old in prior_plugins.items():
        if plugin_id in current["plugins"] or not isinstance(old, dict):
            continue
        missing = int(old.get("absenceCount") or 0) + 1
        retained = dict(old)
        retained["absenceCount"] = missing
        if missing >= 2 and not bool(old.get("retired")):
            retained["retired"] = True
            events.append(
                _base_event(
                    plugin_id,
                    retained,
                    event_type="plugin-retired",
                    occurrence_key="confirmed-absence-2",
                    occurred_at=discovered_text,
                    discovered_at=discovered_at,
                    title=f"{retained['name']} left the marketplace",
                    summary=retained["description"],
                )
            )
        next_plugins[plugin_id] = retained

    return events, {"generatedAt": current["generatedAt"], "plugins": dict(sorted(next_plugins.items()))}
