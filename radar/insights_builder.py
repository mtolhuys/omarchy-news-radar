"""Produce one generic, source-backed companion feed without changing news continuity."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .errors import FetchError, ValidationError
from .insights import INSIGHTS_MAX_BYTES, MAX_COLLECTIONS, MAX_PROJECTS, MAX_RELEASES, validate_insights
from .io import canonical_json_bytes, read_json_bounded
from .sources.release_notes import fetch_release_notes
from .validation import format_timestamp, parse_timestamp

# Repository-owned opt-in coverage. Catalog URLs never choose new network destinations.
# Changing this set requires source review; an empty GitHub releases index is valid.
RELEASE_REPOSITORIES = {
    "omarchy": "omacom/omarchy",
    "io.github.mtolhuys.news-radar": "mtolhuys/omarchy-news-radar",
    "io.github.mtolhuys.theme-manager": "mtolhuys/omarchy-theme-manager",
    "sridhar.layout-presets": "srikat/omarchy-layout-presets",
    "sridhar.shelf": "srikat/omarchy-shelf",
    "io.github.nejcm.pomodoro": "nejcm/omarchy-pomodoro",
    "bottelet.focus-modes": "Bottelet/omarchy-focus-modes",
}
CONTENT_DIRECTORY = Path(__file__).resolve().parents[1] / "content/discoveries"


def load_collections(directory: Path) -> list[dict[str, Any]]:
    paths = sorted(directory.glob("*.json")) if directory.exists() else []
    if len(paths) > MAX_COLLECTIONS:
        raise ValidationError("too many reviewed discoveries")
    records = [read_json_bounded(path, 32 * 1024) for path in paths]
    if any(not isinstance(item, dict) for item in records):
        raise ValidationError("reviewed discovery must be an object")
    identities = []
    for item in records:
        members = item.get("projectIds")
        if not isinstance(members, list) or any(not isinstance(identity, str) for identity in members):
            raise ValidationError("reviewed discovery project IDs must be an array of strings")
        identities.extend(members)
    # Validate every repository-owned record before availability/date filtering.
    # Placeholder projects satisfy referential checks without trusting catalog data.
    placeholders = [{"id": identity, "kind": "plugin", "name": identity[:120], "description": identity,
                     "source": {"label": "Project", "url": "https://github.com/omacom/omarchy"}, "releases": []}
                    for identity in sorted(set(identities))]
    clock = datetime(9998, 1, 1, tzinfo=timezone.utc)
    return validate_insights({"schemaVersion": 1, "publishedAt": "2026-01-01T00:00:00Z",
                              "projects": placeholders, "collections": records}, now=clock)["collections"]


def _core_project(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    releases = snapshot.get("sources", {}).get("omarchy-releases", {}).get("releases", {})
    selected = sorted(releases.values(), key=lambda item: (item["publishedAt"], item["tag"]), reverse=True)
    versions = set()
    summaries = []
    for item in selected:
        if item.get("prerelease") or item["tag"] in versions:
            continue
        versions.add(item["tag"])
        summaries.append({"version": item["tag"], "publishedAt": item["publishedAt"], "title": item["title"],
                          "summary": item["summary"], "changes": [], "sourceUrl": item["url"]})
        if len(summaries) == MAX_RELEASES:
            break
    return {"id": "omarchy", "kind": "omarchy", "name": "Omarchy",
            "description": "The Omarchy desktop. Release explanations link to the maintainers' published notes.",
            "source": {"label": "Omarchy source", "url": "https://github.com/omacom/omarchy"},
            "creatorId": "github:omacom", "releases": summaries}


def _plugin_project(identity: str, entry: Mapping[str, Any]) -> dict[str, Any]:
    repository = entry["repository"]
    project = {"id": identity, "kind": "plugin", "name": entry["name"],
               "description": entry["description"] or entry["name"],
               "source": {"label": "Project source", "url": repository}, "releases": []}
    parsed = urlsplit(repository)
    path = parsed.path.strip("/").split("/")
    if parsed.netloc == "github.com" and len(path) == 2:
        project["creatorId"] = "github:" + path[0].lower()
    if entry.get("preview"):
        project["image"] = {**entry["preview"], "alt": f"{entry['name']} preview", "credit": "Omarchy Plugin Marketplace"}
    return project


def _merge_collected_releases(previous: list[dict[str, Any]], collected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {item["version"]: deepcopy(item) for item in previous}
    for fresh in collected:
        item = deepcopy(fresh)
        old = merged.get(item["version"])
        if old and old["sourceUrl"] == item["sourceUrl"]:
            # The normal collector supplies a shorter news summary and no
            # extracted changes. Keep richer source-bound coverage until a
            # successful expanded-notes fetch supplies its replacement.
            if not item["changes"] and old["changes"]:
                item["changes"] = old["changes"]
            if len(old["summary"]) > len(item["summary"]):
                item["summary"] = old["summary"]
        merged[item["version"]] = item
    return sorted(merged.values(), key=lambda item: (item["publishedAt"], item["version"]), reverse=True)[:MAX_RELEASES]


def build_insights(
    snapshot: Mapping[str, Any], *, published_at: datetime,
    content_directory: Path = CONTENT_DIRECTORY, fetch_releases: bool = False,
    github_token: str | None = None, previous_insights: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select reviewed projects and recent activity, with honest bounded release coverage.

    Optional upstream failure retains previously validated source facts. An explicit
    successful empty index removes stale coverage; dates always belong to upstream.
    """
    collections = load_collections(content_directory)
    # Fixed-clock historical builds omit discoveries that had not been reviewed yet.
    collections = [item for item in collections if parse_timestamp(item.get("reviewedAt")) <= published_at]
    catalog = snapshot.get("sources", {}).get("marketplace", {}).get("plugins", {})
    available = {identity: entry for identity, entry in catalog.items() if not entry.get("retired")}
    collections = [item for item in collections if all(identity == "omarchy" or identity in available for identity in item.get("projectIds", []))]
    priority = [identity for item in collections for identity in item.get("projectIds", [])]
    priority += list(RELEASE_REPOSITORIES)
    priority += [event["entity"]["id"] for event in sorted(snapshot.get("events", []), key=lambda event: (event["occurredAt"], event["id"]), reverse=True)]
    priority += sorted(available)
    selected: list[str] = []
    for identity in priority:
        if identity in available and identity not in selected and len(selected) < MAX_PROJECTS - 1:
            selected.append(identity)
    projects = [_core_project(snapshot)] + [_plugin_project(identity, available[identity]) for identity in selected]
    illustrated = {identity for item in collections for identity in item["projectIds"]}
    for project in projects:
        if project["id"] not in illustrated:
            project.pop("image", None)
    previous = validate_insights(dict(previous_insights), now=published_at) if previous_insights else None
    prior = {item["id"]: item for item in previous["projects"]} if previous else {}
    for project in projects:
        old = prior.get(project["id"])
        if old and old["source"]["url"] == project["source"]["url"] and old["releases"]:
            # The normal collector may already know a new core release even if
            # the optional expanded-notes request is currently unavailable.
            project["releases"] = _merge_collected_releases(old["releases"], project["releases"])
    if fetch_releases:
        candidates = [project for project in projects if project["id"] in RELEASE_REPOSITORIES]

        def enrich(project: dict[str, Any]) -> None:
            repository = RELEASE_REPOSITORIES[project["id"]]
            # A changed catalog ownership/repository never inherits another project's notes.
            if project["source"]["url"].rstrip("/") != f"https://github.com/{repository}":
                return
            try:
                releases = fetch_release_notes(repository, github_token=github_token)
                checked = validate_insights({"schemaVersion": 1, "publishedAt": format_timestamp(published_at),
                                            "projects": [{**project, "releases": releases}], "collections": []}, now=published_at)
                project["releases"] = checked["projects"][0]["releases"]
            except (FetchError, ValidationError, OSError):
                # Optional coverage cannot suppress a valid news edition.
                pass

        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(enrich, candidates))
    result = validate_insights({"schemaVersion": 1, "publishedAt": format_timestamp(published_at),
                               "projects": projects, "collections": collections}, now=published_at)
    if len(canonical_json_bytes(result)) > INSIGHTS_MAX_BYTES:
        raise ValidationError("insights publication exceeds its byte bound")
    return result
