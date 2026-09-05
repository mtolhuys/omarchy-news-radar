"""Bounded public source explanations, independent of the rolling news feed."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from functools import cmp_to_key
from typing import Any, Mapping

from .constants import FEED_ORIGIN, FUTURE_SKEW_SECONDS
from .errors import ValidationError
from .io import canonical_json_bytes
from .validation import (
    ENTITY_ID_RE, normalize_article_summary, normalize_text, parse_timestamp,
    require_exact_keys, require_list, require_mapping, require_string,
    validate_https_url, validate_image,
)

INSIGHTS_SCHEMA_VERSION = 1
INSIGHTS_MAX_BYTES = 2 * 1024 * 1024
MAX_PROJECTS = 100
MAX_COLLECTIONS = 30
MAX_RELEASES = 30
MAX_CHANGES = 12
COLLECTION_ID_RE = re.compile(r"^(?=.{1,80}$)[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def _shape(value: Any, required: set[str], optional: set[str], label: str) -> Mapping[str, Any]:
    item = require_mapping(value, label)
    if not required <= set(item) or set(item) - required - optional:
        raise ValidationError(f"{label} has an unknown or incomplete shape")
    return item


def _identifier(value: Any, label: str) -> str:
    value = require_string(value, label, 1, 160)
    if not ENTITY_ID_RE.fullmatch(value):
        raise ValidationError(f"{label} is invalid")
    return value


def _source(value: Any) -> dict[str, str]:
    item = require_mapping(value, "insight source")
    require_exact_keys(item, {"label", "url"}, "insight source")
    return {"label": normalize_text(item["label"], 120), "url": validate_https_url(item["url"])}


def _time(value: Any, clock: datetime) -> str:
    if parse_timestamp(value) > clock + timedelta(seconds=FUTURE_SKEW_SECONDS):
        raise ValidationError("insight timestamp is in the future")
    return value


def _array(value: Any, limit: int, label: str) -> list[Any]:
    items = require_list(value, label)
    if len(items) > limit:
        raise ValidationError(f"{label} exceeds its item bound")
    return items


def validate_insights(value: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """Validate generic insight facts; never couple availability to feed clocks."""

    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    value = _shape(value, {"schemaVersion", "publishedAt", "projects", "collections"}, set(), "insights")
    if type(value["schemaVersion"]) is not int or value["schemaVersion"] != INSIGHTS_SCHEMA_VERSION:
        raise ValidationError("unsupported insights schemaVersion")
    projects = []
    project_ids: set[str] = set()
    for raw in _array(value["projects"], MAX_PROJECTS, "insight projects"):
        raw = _shape(raw, {"id", "kind", "name", "description", "source", "releases"}, {"creatorId", "image"}, "insight project")
        identity = _identifier(raw["id"], "project ID")
        if identity in project_ids or not isinstance(raw["kind"], str) or raw["kind"] not in {"plugin", "omarchy"}:
            raise ValidationError("insight project identity or kind is invalid")
        project_ids.add(identity)
        project = {"id": identity, "kind": raw["kind"], "name": normalize_text(raw["name"], 120),
                   "description": normalize_article_summary(raw["description"], 2000), "source": _source(raw["source"])}
        if "creatorId" in raw:
            project["creatorId"] = _identifier(raw["creatorId"], "creator ID")
        if "image" in raw:
            project["image"] = validate_image(raw["image"], public_only=True)
            if "sourceUrl" not in project["image"]:
                raise ValidationError("insight image requires an allowlisted source URL")
        versions: set[str] = set()
        releases = []
        for item in _array(raw["releases"], MAX_RELEASES, "project releases"):
            item = _shape(item, {"version", "publishedAt", "title", "summary", "changes", "sourceUrl"}, set(), "insight release")
            version = normalize_text(item["version"], 80)
            if version != item["version"]:
                raise ValidationError("release version must be exact plain text")
            if version in versions:
                raise ValidationError("insight release versions must be unique")
            versions.add(version)
            changes = []
            for change in _array(item["changes"], MAX_CHANGES, "release changes"):
                change = _shape(change, {"text", "sourceUrl"}, set(), "release change")
                changes.append({"text": normalize_text(change["text"], 1000), "sourceUrl": validate_https_url(change["sourceUrl"])})
            releases.append({"version": version, "publishedAt": _time(item["publishedAt"], clock),
                             "title": normalize_text(item["title"], 200), "summary": normalize_article_summary(item["summary"], 8000, minimum=0),
                             "changes": changes, "sourceUrl": validate_https_url(item["sourceUrl"])})
        project["releases"] = sorted(releases, key=lambda item: (item["publishedAt"], item["version"]), reverse=True)
        projects.append(project)
    collections = []
    collection_ids: set[str] = set()
    for raw in _array(value["collections"], MAX_COLLECTIONS, "insight collections"):
        raw = _shape(raw, {"id", "title", "summary", "body", "projectIds", "source", "shareUrl", "reviewedAt"}, {"image", "sourceLinks"}, "insight collection")
        identity = require_string(raw["id"], "collection ID", 1, 80)
        if not COLLECTION_ID_RE.fullmatch(identity) or identity in collection_ids:
            raise ValidationError("collection ID is invalid or duplicated")
        collection_ids.add(identity)
        members = _array(raw["projectIds"], 20, "collection project IDs")
        if any(not isinstance(item, str) or item not in project_ids for item in members) or len(members) != len(set(members)):
            raise ValidationError("collection project IDs must reference unique known projects")
        share = validate_https_url(raw["shareUrl"])
        if share != FEED_ORIGIN + "/news-radar/discover/" + identity + "/":
            raise ValidationError("collection share URL must be its fixed public page")
        collection = {"id": identity, "title": normalize_text(raw["title"], 160),
                      "summary": normalize_text(raw["summary"], 600), "body": normalize_article_summary(raw["body"], 12000),
                      "projectIds": list(members), "source": _source(raw["source"]), "shareUrl": share,
                      "reviewedAt": _time(raw["reviewedAt"], clock)}
        if "sourceLinks" in raw:
            collection["sourceLinks"] = [_source(item) for item in _array(raw["sourceLinks"], 20, "collection sources")]
        if "image" in raw:
            collection["image"] = validate_image(raw["image"], public_only=True)
            if "sourceUrl" not in collection["image"]:
                raise ValidationError("insight image requires an allowlisted source URL")
        collections.append(collection)
    result = {"schemaVersion": INSIGHTS_SCHEMA_VERSION, "publishedAt": _time(value["publishedAt"], clock),
              "projects": projects, "collections": collections}
    if len(canonical_json_bytes(result)) > INSIGHTS_MAX_BYTES:
        raise ValidationError("insights exceed the byte bound")
    return result


def _semver(value: str) -> tuple[tuple[int, int, int], tuple[str, ...]] | None:
    match = SEMVER_RE.fullmatch(value)
    if not match:
        return None
    prerelease = tuple((match.group(4) or "").split(".")) if match.group(4) else ()
    if any(part.isdigit() and len(part) > 1 and part.startswith("0") for part in prerelease):
        return None
    return (tuple(int(match.group(index)) for index in (1, 2, 3)), prerelease)


def compare_versions(left: str | None, right: str | None) -> int | None:
    """SemVer precedence, optional conventional v prefix; never lexical guesses."""

    if not left or not right:
        return None
    if left == right:
        return 0
    a, b = _semver(left), _semver(right)
    if a is None or b is None:
        return None
    if a[0] != b[0]:
        return 1 if a[0] > b[0] else -1
    if not a[1] or not b[1]:
        return 0 if a[1] == b[1] else (1 if not a[1] else -1)
    for x, y in zip(a[1], b[1]):
        if x == y:
            continue
        if x.isdigit() and y.isdigit():
            return 1 if int(x) > int(y) else -1
        if x.isdigit() != y.isdigit():
            return -1 if x.isdigit() else 1
        return 1 if x > y else -1
    return (len(a[1]) > len(b[1])) - (len(a[1]) < len(b[1]))


def matching_release(releases: list[Mapping[str, Any]], version: str | None) -> Mapping[str, Any] | None:
    """Match an explanation's identity, not merely equivalent precedence.

    A conventional v prefix can differ between a manifest and its Git tag.
    Build metadata remains exact; multiple matching tags are ambiguous.
    """
    if not version:
        return None
    matches = [release for release in releases if release["version"] == version or (
        _semver(version) is not None and _semver(release["version"]) is not None
        and version.removeprefix("v") == release["version"].removeprefix("v")
    )]
    return matches[0] if len(matches) == 1 else None


def project_version(project: Mapping[str, Any], installed_version: str | None, *, installed: bool) -> dict[str, Any]:
    releases = project["releases"]
    # If every version shares a defined precedence, find the highest. Mixed
    # schemes stay unknown; publication time is never used as version order.
    known = bool(releases) and all(_semver(item["version"]) is not None for item in releases)
    ordered = sorted(releases, key=cmp_to_key(lambda a, b: -(compare_versions(a["version"], b["version"]) or 0))) if known else list(releases)
    latest = ordered[0]["version"] if ordered else None
    comparable = compare_versions(installed_version, latest) if known or len(ordered) == 1 else None
    state = "not-installed" if not installed else {None: "unknown", 0: "current", -1: "behind", 1: "ahead"}[comparable]
    newer = [dict(item) for item in ordered if installed and compare_versions(installed_version, item["version"]) == -1]
    labels = {"not-installed": "Not enabled on this desktop", "unknown": "Version comparison unavailable",
              "current": "No newer documented release version", "behind": "Newer documented releases available",
              "ahead": "Installed version is newer than this coverage"}
    return {**project, "installed": installed, "installedVersion": installed_version, "publishedVersion": latest,
            "comparisonState": state, "comparisonLabel": labels[state], "releases": ordered,
            "newerReleases": newer, "coverageLabel": "Documented releases; coverage may be incomplete"}
