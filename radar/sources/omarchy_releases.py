"""GitHub published-release normalization."""

from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any, Iterable, Mapping

from ..errors import ValidationError
from ..model import event_id
from ..validation import format_timestamp, normalize_text, parse_timestamp, validate_https_url

API_URL = "https://api.github.com/repos/basecamp/omarchy/releases"
PUBLIC_URL = "https://github.com/basecamp/omarchy/releases"
MAX_RELEASES = 300
MAX_RELEASE_ASSETS = 1000
MAX_METRIC_VALUE = 9_007_199_254_740_991

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
TAG_RE = re.compile(r"<[^>]+>")
MARKUP_RE = re.compile(r"(?m)^\s{0,3}[#>*+-]+\s*|[`*_~]")
HEADING_RE = re.compile(r"(?m)^\s{0,3}#{1,6}\s+.*$")


def release_summary(body: Any, fallback: str) -> str:
    text = body if isinstance(body, str) else ""
    text = FENCE_RE.sub(" ", text)
    text = IMAGE_RE.sub(" ", text)
    text = LINK_RE.sub(r"\1", text)
    text = TAG_RE.sub(" ", text)
    text = HEADING_RE.sub(" ", text)
    text = MARKUP_RE.sub("", text)
    paragraphs = [" ".join(part.split()) for part in re.split(r"\n\s*\n", text) if part.strip()]
    candidate = paragraphs[0] if paragraphs else fallback
    if len(candidate) > 400:
        candidate = candidate[:397].rstrip() + "…"
    return normalize_text(html.unescape(candidate), 400)


def parse_releases(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValidationError("GitHub releases payload must be an array")
    if len(payload) > MAX_RELEASES:
        raise ValidationError("GitHub releases pagination bound exceeded")
    releases: dict[str, dict[str, Any]] = {}
    for item in payload:
        if not isinstance(item, dict):
            raise ValidationError("GitHub release must be an object")
        if item.get("draft") is True:
            continue
        raw_id = item.get("id")
        if not isinstance(raw_id, int) or raw_id <= 0:
            raise ValidationError("GitHub release id is invalid")
        key = str(raw_id)
        if key in releases:
            raise ValidationError("GitHub release ids must be unique")
        published = item.get("published_at")
        parse_timestamp(published, "release.published_at")
        url = validate_https_url(item.get("html_url"), "release.html_url")
        tag = normalize_text(item.get("tag_name"), 80)
        title_source = item.get("name") if isinstance(item.get("name"), str) and item["name"].strip() else tag
        title = normalize_text(title_source, 120)
        prerelease = item.get("prerelease") is True
        assets_raw = item.get("assets")
        if assets_raw is None:
            assets_raw = []
        if not isinstance(assets_raw, list) or len(assets_raw) > MAX_RELEASE_ASSETS:
            raise ValidationError("GitHub release assets are invalid")
        asset_downloads = 0
        for asset in assets_raw:
            if not isinstance(asset, dict):
                raise ValidationError("GitHub release asset is invalid")
            count = asset.get("download_count")
            if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= MAX_METRIC_VALUE:
                raise ValidationError("GitHub release asset download count is invalid")
            asset_downloads += count
            if asset_downloads > MAX_METRIC_VALUE:
                raise ValidationError("GitHub release asset downloads exceed their bound")
        releases[key] = {
            "id": key,
            "tag": tag,
            "title": title,
            "publishedAt": published,
            "url": url,
            "prerelease": prerelease,
            "summary": release_summary(item.get("body"), f"Omarchy {tag} was published."),
            "assetCount": len(assets_raw),
            "assetDownloads": asset_downloads,
        }
    return dict(sorted(releases.items(), key=lambda pair: int(pair[0])))


def diff_releases(
    previous: Mapping[str, Mapping[str, Any]],
    current: Mapping[str, Mapping[str, Any]],
    *,
    discovered_at: datetime,
    window_from: datetime,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for release_id, release in current.items():
        if release_id in previous or parse_timestamp(release["publishedAt"]) < window_from:
            continue
        suffix = " (prerelease)" if release["prerelease"] else ""
        source_url = str(release["url"])
        events.append(
            {
                "id": event_id("omarchy-released", "omarchy", "omarchy", release_id, source_url),
                "type": "omarchy-released",
                "occurredAt": release["publishedAt"],
                "discoveredAt": format_timestamp(discovered_at),
                "title": f"Omarchy {release['tag']}{suffix}",
                "summary": release["summary"],
                "source": {"label": "GitHub release", "url": source_url},
                "entity": {
                    "kind": "omarchy",
                    "id": "omarchy",
                    "name": "Omarchy",
                    "version": release["tag"],
                    "repository": "https://github.com/omacom/omarchy",
                },
                "classification": {
                    "section": "core",
                    "significance": "routine",
                    "curated": False,
                    "tags": ["release"],
                },
                "trust": {"marketplace": "not-applicable", "securityAudit": False},
                "compatibility": {"channels": ["quattro"], "basis": "declared"},
            }
        )
    return events
