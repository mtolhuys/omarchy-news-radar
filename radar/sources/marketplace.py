"""Marketplace catalog normalization and conservative two-run diffs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from ..errors import ValidationError
from ..model import event_id
from ..validation import format_timestamp, normalize_text, parse_timestamp, validate_https_url

CATALOG_URL = "https://raw.githubusercontent.com/omacom/omarchy-plugin-marketplace/main/site/catalog.json"
MARKETPLACE_URL = "https://plugins.omarchy.org/"
VERIFICATION = {"verified", "reviewed", "unverified", "unknown"}


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
        tags_raw = raw.get("tags") if isinstance(raw.get("tags"), list) else []
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
        plugins[plugin_id] = {
            "name": normalize_text(raw.get("name"), 120),
            "description": normalize_text(raw.get("description") or f"{raw.get('name')} is listed in the Omarchy plugin marketplace.", 400),
            "version": version,
            "repository": validate_https_url(raw.get("repo"), "plugin.repo"),
            "sourceUrl": _plugin_url(raw),
            "category": normalize_text(raw.get("category") or "Uncategorized", 60),
            "tags": tags,
            "addedAt": _listing_time(raw, generated_at),
            "verification": verification,
            "retired": retired,
            "absenceCount": 0,
        }
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
    return {
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


def diff_marketplace(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    *,
    discovered_at: datetime,
    bootstrap: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return supported events and the next snapshot.

    A missing prior snapshot requires explicit bootstrap and emits no events.
    """

    if previous is None:
        if not bootstrap:
            raise ValidationError("marketplace snapshot is absent; rerun with explicit bootstrap")
        return [], {"generatedAt": current["generatedAt"], "plugins": dict(current["plugins"])}

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
                    summary=f"{plugin['name']} is now listed in the Omarchy plugin marketplace.",
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
                    summary=f"The marketplace version changed from {old_version} to {new_version}.",
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
                    summary=f"Marketplace verification changed from {old_verification} to {plugin['verification']}; this is not a security audit.",
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
                    summary="The marketplace now marks this plugin as retired.",
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
                    summary="The plugin was absent from two consecutive complete marketplace catalogs.",
                )
            )
        next_plugins[plugin_id] = retained

    return events, {"generatedAt": current["generatedAt"], "plugins": dict(sorted(next_plugins.items()))}
