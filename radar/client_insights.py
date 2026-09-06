"""Optional insight cache, fixed generic retrieval, and private setup projection."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Mapping
from pathlib import Path

from .constants import BUILD_ID, FEED_ORIGIN, INSIGHTS_URL
from .discovery import automatic_discoveries, discovery_edition
from .errors import RadarError, ValidationError
from .http import FetchPolicy, decode_json, fetch_bytes
from .insights import INSIGHTS_MAX_BYTES, project_version, validate_insights
from .io import atomic_write_json, read_json_bounded, refuse_symlink
from .relevance import default_relevance, relevance_controls, target_status, validate_target, KINDS
from .client_setup import parse_installed_facts
from .state import _OwnedFileLock, StateLock, cache_root, load_feed, load_state, save_state
from .validation import format_timestamp, parse_timestamp


def load_insights(environment: Mapping[str, str] | None = None, *, now: datetime | None = None) -> dict[str, Any] | None:
    """Missing or invalid optional content never disables the validated news."""
    try:
        refuse_symlink(cache_root(environment))
        return validate_insights(read_json_bounded(cache_root(environment) / "insights.json", INSIGHTS_MAX_BYTES), now=now)
    except (OSError, RadarError):
        return None


def _validators(environment: Mapping[str, str]) -> dict[str, Any] | None:
    try:
        value = read_json_bounded(cache_root(environment) / "insights-http.json", 4096)
        if not isinstance(value, dict) or set(value) != {"url", "etag", "lastModified"} or value["url"] != INSIGHTS_URL:
            return None
        for key in ("etag", "lastModified"):
            item = value[key]
            if item is not None and (not isinstance(item, str) or not 1 <= len(item) <= 512 or any(ord(c) < 32 or ord(c) == 127 for c in item)):
                return None
        return value
    except (OSError, RadarError):
        return None


def refresh_insights(environment: Mapping[str, str] | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    env = dict(environment or os.environ)
    clock = now or datetime.now(timezone.utc)
    cached = load_insights(env, now=clock)
    base = cache_root(env)
    status = "cached" if cached else "missing"
    try:
        with _OwnedFileLock(base / "insights-refresh.lock", label="insights refresh", contention_message="insights refresh is already running", nonblocking=True):
            try:
                check = read_json_bounded(base / "insights-check.json", 512)
                if not isinstance(check, dict) or set(check) != {"checkedAt"}:
                    raise ValidationError("invalid insights check")
                age = (clock - parse_timestamp(check["checkedAt"])).total_seconds()
                if 0 <= age < 300:
                    return {"protocolVersion": 1, "status": status, "insights": cached, "attempted": False}
            except (OSError, RadarError):
                pass
            atomic_write_json(base / "insights-check.json", {"checkedAt": format_timestamp(clock)})
            validators = _validators(env) if cached else None
            if env.get("OMARCHY_NEWS_RADAR_TEST_MODE") == "1":
                path = env.get("OMARCHY_NEWS_RADAR_TEST_INSIGHTS")
                if not path:
                    return {"protocolVersion": 1, "status": status, "insights": cached, "attempted": False}
                raw = read_json_bounded(Path(path), INSIGHTS_MAX_BYTES)
                headers = {}
                response_code = 200
            else:
                headers = {"Accept": "application/json", "Accept-Encoding": "gzip", "User-Agent": f"omarchy-news-radar-client/{BUILD_ID.removeprefix('news-radar-')}"}
                if validators:
                    if validators["etag"]:
                        headers["If-None-Match"] = validators["etag"]
                    if validators["lastModified"]:
                        headers["If-Modified-Since"] = validators["lastModified"]
                data, headers, response_code = fetch_bytes(INSIGHTS_URL, policy=FetchPolicy(INSIGHTS_MAX_BYTES, 8.0, frozenset({FEED_ORIGIN})), headers=headers, allow_not_modified=validators is not None)
                raw = cached if response_code == 304 else decode_json(data, label="insights")
            candidate = validate_insights(raw, now=clock)
            if cached and candidate["publishedAt"] < cached["publishedAt"]:
                return {"protocolVersion": 1, "status": "cached", "insights": cached, "attempted": True}
            with StateLock(env):
                atomic_write_json(base / "insights.json", candidate)
                lowered = {key.lower(): value for key, value in headers.items()}
                metadata = {"url": INSIGHTS_URL, "etag": lowered.get("etag"), "lastModified": lowered.get("last-modified")}
                if response_code == 304 and validators:
                    metadata = {key: value or validators[key] for key, value in metadata.items()}
                # Reuse validation before future request headers can contain
                # remote bytes; malformed metadata is simply not persisted.
                safe = all(value is None or (isinstance(value, str) and len(value) <= 512 and all(ord(c) >= 32 and ord(c) != 127 for c in value)) for key, value in metadata.items() if key != "url")
                if not safe:
                    metadata = {"url": INSIGHTS_URL, "etag": None, "lastModified": None}
                atomic_write_json(base / "insights-http.json", metadata)
            return {"protocolVersion": 1, "status": "cached", "insights": candidate, "attempted": True}
    except (OSError, RadarError) as exc:
        return {"protocolVersion": 1, "status": status, "insights": cached, "attempted": True,
                "message": "Additional project coverage is unavailable; existing news remains readable.", "reason": str(exc)}


def set_relevance(kind: str, identity: str, mode: str, environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    validate_target(kind, identity)
    if mode not in {"follow", "mute", "clear"}:
        raise ValidationError("relevance mode is invalid")
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        suffix = KINDS[kind]
        for prefix in ("followed", "muted"):
            state["relevance"][prefix + suffix] = [item for item in state["relevance"][prefix + suffix] if item != identity]
        if mode != "clear":
            state["relevance"][("followed" if mode == "follow" else "muted") + suffix].append(identity)
        state = save_state(state, environment)
    return {"protocolVersion": 1, "status": "ok", "state": state, "relevanceControls": relevance_controls(state),
            "message": "Preferences updated. Your current briefing and saved stories remain available; new briefings use these choices."}


def compact_project(project: Mapping[str, Any]) -> dict[str, Any]:
    """Do not duplicate a project's full release history in every news row."""
    omitted = {"releases", "newerReleases", "image"}
    result = {key: value for key, value in project.items() if key not in omitted}
    result["newerReleaseCount"] = len(project.get("newerReleases", []))
    return result


def insight_projection(insights: Mapping[str, Any] | None, state: Mapping[str, Any], installed_ids: list[str], installed_facts: list[dict[str, Any]], *, query: str = "", installed_facts_available: bool = True, known_names: Mapping[str, str] | None = None) -> dict[str, Any]:
    if not isinstance(installed_facts_available, bool):
        raise ValidationError("installed facts availability must be a boolean")
    relevance = state.get("relevance", default_relevance())
    versions = {item["id"]: item["version"] for item in installed_facts}
    local_names = {item["id"]: item["name"] for item in installed_facts if "name" in item}
    local_descriptions = {item["id"]: item["description"] for item in installed_facts if "description" in item}
    first_party = {item["id"] for item in installed_facts if item.get("firstParty") is True}
    installed = set(installed_ids) | versions.keys()
    projects = []
    by_id = {}
    for project in (insights or {}).get("projects", []):
        item = project_version(project, versions.get(project["id"]),
                               installed=project["kind"] == "omarchy" or project["id"] in installed)
        targets = []
        if item["kind"] == "plugin":
            targets.append(target_status(relevance, "plugin", item["id"], item["name"]))
        targets.append(target_status(relevance, "source", "marketplace" if item["kind"] == "plugin" else "omarchy-releases"))
        if item.get("creatorId"):
            targets.append(target_status(relevance, "creator", item["creatorId"]))
        item["relevanceTargets"] = targets
        item["followed"] = any(target["followed"] for target in targets)
        item["muted"] = any(target["muted"] for target in targets)
        item["imageUrl"] = item.get("image", {}).get("sourceUrl", "") if state["preferences"]["imagesVisible"] else ""
        item["coverageAvailable"] = True
        by_id[item["id"]] = item
        projects.append(item)
    my_setup = []
    for identity in sorted(installed):
        if identity in by_id:
            my_setup.append(by_id[identity])
        elif identity not in first_party:
            name = local_names.get(identity) or (known_names or {}).get(identity) or identity
            version = versions.get(identity)
            target = target_status(relevance, "plugin", identity, name)
            my_setup.append({"id": identity, "name": name, "kind": "plugin", "installed": True,
                             "installedVersion": version, "publishedVersion": None,
                             "comparisonState": "unknown",
                             "comparisonLabel": f"Enabled · {version}" if version else "Enabled locally",
                             "coverageLabel": "Release notes are not published in Radar for this project yet",
                             "coverageAvailable": False, "releaseCoverageAvailable": False,
                             "description": local_descriptions.get(identity, ""), "releases": [], "newerReleases": [], "source": None,
                             "imageUrl": "", "followed": target["followed"], "muted": target["muted"], "relevanceTargets": [target]})
    setup_order = {"behind": 0, "current": 1, "ahead": 1}
    my_setup.sort(key=lambda item: (
        setup_order.get(item["comparisonState"], 2 if item.get("description") else 3),
        item["name"].casefold(), item["id"],
    ))
    needle = " ".join(query.lower().split())
    def matches(item: Mapping[str, Any]) -> bool:
        return not needle or needle in " ".join(str(item.get(key, "")) for key in ("name", "title", "summary", "description", "body")).lower()
    visible = [item for item in projects if not item["muted"] and matches(item)]
    updates = [item for item in visible if item["comparisonState"] == "behind"]
    return {"insights": {"status": "cached" if insights else "missing", "publishedAt": insights["publishedAt"] if insights else "",
                         "coverageAvailable": insights is not None, "installedFactsAvailable": installed_facts_available,
                         # Detail resolution must survive search and mute: a
                         # saved/current briefing row can remain reachable even
                         # when its project card is outside the visible scope.
                         "projectDetails": projects,
                         "projects": visible, "collections": []},
            "home": {"featuredCollections": [], "discoveries": [], "setupUpdates": updates[:6],
                     "featuredCollectionCount": 0, "discoveryCount": 0, "setupUpdateCount": len(updates)},
            "mySetup": [item for item in my_setup if matches(item)], "relevanceControls": relevance_controls(state)}


def insights_model(installed_facts_json: str = "[]", environment: Mapping[str, str] | None = None, *, now: datetime | None = None, query: str = "", installed_facts_available: bool = True) -> dict[str, Any]:
    if len(query) > 100:
        raise ValidationError("insight query exceeds its bound")
    facts = parse_installed_facts(installed_facts_json)
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        insights = load_insights(environment, now=now)
        feed = load_feed(environment, now=now)
        edition, retained, warning = discovery_edition(feed, environment, now=now)
    result = insight_projection(insights, state, [], facts, query=query, installed_facts_available=installed_facts_available)
    result["home"].update(automatic_discoveries(edition, feed, state, result["insights"]["projectDetails"], query=query, retained=retained, warning=warning))
    return {"protocolVersion": 1, "status": "ok", "state": state, **result}
