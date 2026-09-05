"""Read enabled plugin facts without running plugin code or exposing setup."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .errors import RadarError, ValidationError
from .io import read_json_bounded, refuse_symlink
from .relevance import ID_RE
from .validation import normalize_text


def parse_installed_facts(raw: str) -> list[dict[str, Any]]:
    if len(raw) > 256 * 1024:
        raise ValidationError("installed facts exceed their bound")
    try:
        values = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError("installed facts are invalid JSON") from exc
    if not isinstance(values, list) or len(values) > 500:
        raise ValidationError("installed facts are invalid")
    result = []
    identities = set()
    for item in values:
        if (not isinstance(item, dict) or not {"id", "version"} <= set(item)
                or set(item) - {"id", "version", "name", "firstParty"}):
            raise ValidationError("installed fact has an unknown or incomplete shape")
        identity, version = item["id"], item["version"]
        if not isinstance(identity, str) or not ID_RE.fullmatch(identity) or identity in identities:
            raise ValidationError("installed fact identity is invalid")
        if version is not None:
            if normalize_text(version, 80) != version:
                raise ValidationError("installed version must be exact plain text")
        if "name" in item and normalize_text(item["name"], 120) != item["name"]:
            raise ValidationError("installed name must be bounded plain text")
        if "firstParty" in item and not isinstance(item["firstParty"], bool):
            raise ValidationError("installed first-party status must be a boolean")
        identities.add(identity)
        result.append(dict(item))
    return sorted(result, key=lambda item: item["id"])


def _plain_field(value: Any, maximum: int) -> str | None:
    try:
        return value if normalize_text(value, maximum) == value else None
    except ValidationError:
        return None


def _manifest_facts(identity: str, environment: Mapping[str, str]) -> dict[str, str]:
    base = Path(environment.get("XDG_CONFIG_HOME", str(Path(environment.get("HOME", str(Path.home()))) / ".config")))
    directory = base / "omarchy" / "plugins" / identity
    try:
        for path in (base, base / "omarchy", directory.parent, directory):
            refuse_symlink(path)
        path = directory / "manifest.json"
        if directory.stat().st_uid != os.getuid() or path.stat().st_uid != os.getuid():
            return {}
        manifest = read_json_bounded(path, 128 * 1024)
        if not isinstance(manifest, dict) or manifest.get("id") != identity:
            return {}
        return {key: value for key, bound in (("version", 80), ("name", 120))
                if (value := _plain_field(manifest.get(key), bound)) is not None}
    except (OSError, RadarError):
        return {}


def installed_plugins(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = dict(environment or os.environ)
    unavailable = {"protocolVersion": 1, "status": "unavailable", "pluginIds": [], "plugins": [], "factsAvailable": False}
    try:
        completed = subprocess.run(["omarchy-shell", "shell", "listPlugins"], check=False, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return unavailable
    if completed.returncode != 0 or len(completed.stdout) > 1024 * 1024:
        return unavailable
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return unavailable
    values = payload if isinstance(payload, list) else payload.get("plugins") if isinstance(payload, dict) else None
    if not isinstance(values, list) or len(values) > 5000:
        return unavailable
    ids = sorted({item["id"] for item in values if isinstance(item, dict) and item.get("enabled") is True
                  and isinstance(item.get("id"), str) and ID_RE.fullmatch(item["id"])})[:500]
    metadata = {item["id"]: item for item in values if isinstance(item, dict)
                and item.get("enabled") is True and item.get("id") in ids}
    plugins = []
    for identity in ids:
        item = {"id": identity, "version": None, **_manifest_facts(identity, env)}
        shell = metadata[identity]
        name = item.get("name") or _plain_field(shell.get("name"), 120)
        if name:
            item["name"] = name
        if isinstance(shell.get("firstParty"), bool):
            item["firstParty"] = shell["firstParty"]
        plugins.append(item)
    return {"protocolVersion": 1, "status": "ok", "pluginIds": ids,
            "plugins": plugins,
            "factsAvailable": True}
