"""Private follows and mutes, with stable identities and explicit reset paths."""

from __future__ import annotations

import re
from typing import Any, Mapping
from urllib.parse import urlsplit

from .constants import SOURCE_IDS
from .errors import ValidationError

KINDS = {"plugin": "Plugins", "source": "Sources", "creator": "Creators"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+-]{0,159}$")
MAX_RELEVANCE_IDS = 500


def default_relevance() -> dict[str, list[str]]:
    return {prefix + suffix: [] for prefix in ("followed", "muted") for suffix in KINDS.values()}


def validate_target(kind: str, identity: str) -> None:
    if kind not in KINDS or not isinstance(identity, str) or not ID_RE.fullmatch(identity):
        raise ValidationError("relevance target is invalid")
    if kind == "source" and identity not in SOURCE_IDS:
        raise ValidationError("relevance source is unknown")


def validate_relevance(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict) or set(value) != set(default_relevance()):
        raise ValidationError("relevance has an unknown or incomplete shape")
    result = {}
    for kind, suffix in KINDS.items():
        for prefix in ("followed", "muted"):
            key = prefix + suffix
            items = value[key]
            if not isinstance(items, list) or len(items) > MAX_RELEVANCE_IDS:
                raise ValidationError("relevance exceeds its item bound")
            for identity in items:
                validate_target(kind, identity)
            if len(items) != len(set(items)):
                raise ValidationError("relevance identities must be unique")
            result[key] = sorted(items)
        if set(result["followed" + suffix]) & set(result["muted" + suffix]):
            raise ValidationError("a relevance target cannot be followed and muted")
    if sum(len(items) for items in result.values()) > MAX_RELEVANCE_IDS:
        raise ValidationError("combined relevance targets exceed their item bound")
    return result


def target_status(relevance: Mapping[str, Any], kind: str, identity: str, label: str = "") -> dict[str, Any]:
    suffix = KINDS[kind]
    return {"kind": kind, "id": identity, "label": label or identity,
            "followed": identity in relevance["followed" + suffix],
            "muted": identity in relevance["muted" + suffix]}


def event_targets(event: Mapping[str, Any], projects: Mapping[str, Any] | None = None) -> list[tuple[str, str, str]]:
    entity = event["entity"]
    targets = []
    if entity["kind"] == "plugin":
        targets.append(("plugin", entity["id"], entity["name"]))
    source = {"omarchy-released": "omarchy-releases", "omarchy-news": "omarchy-news",
              "community-link": "community", "youtube-video": "youtube"}.get(event["type"], "marketplace")
    targets.append(("source", source, event["source"]["label"]))
    project = (projects or {}).get(entity["id"], {})
    creator = project.get("creatorId")
    # Repository-owner identities are reproducible from validated provenance.
    # Never treat mutable display labels as creator identifiers.
    if not creator:
        repository = urlsplit(entity.get("repository", ""))
        parts = repository.path.strip("/").split("/")
        if repository.hostname == "github.com" and len(parts) == 2 and re.fullmatch(r"[A-Za-z0-9-]{1,39}", parts[0]):
            creator = "github:" + parts[0].lower()
    if creator and ID_RE.fullmatch(creator):
        targets.append(("creator", creator, creator))
    return targets


def event_relevance(event: Mapping[str, Any], state: Mapping[str, Any], projects: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    relevance = state.get("relevance", default_relevance())
    return [target_status(relevance, *target) for target in event_targets(event, projects)]


def is_muted(event: Mapping[str, Any], state: Mapping[str, Any]) -> bool:
    return any(target["muted"] for target in event_relevance(event, state))


def is_followed(event: Mapping[str, Any], state: Mapping[str, Any]) -> bool:
    return any(target["followed"] for target in event_relevance(event, state))


def relevance_controls(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    relevance = state["relevance"]
    return [target_status(relevance, kind, identity)
            for kind, suffix in KINDS.items()
            for identity in sorted(set(relevance["followed" + suffix] + relevance["muted" + suffix]))]
