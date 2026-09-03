"""Allowlisted YouTube Data API v3 adapter for Omarchy-related videos.

Collection is deliberately conservative. Sponsor blocks, course funnels, and
link walls are removed from descriptions, only substantive Omarchy activity
enters the lane, and one channel can hold at most two slots so a prolific
uploader cannot become the section. All of it is deterministic text and
position work: metrics never create, remove, or reorder an event outside the
documented YouTube-only interleave.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import urlencode

from ..errors import ValidationError
from ..model import event_id
from ..validation import format_timestamp, normalize_text, parse_timestamp, validate_event
from .youtube_text import (
    KEYWORD_RE,
    NEUTRAL_SUMMARY,
    SUMMARY_MAX_CHARS,
    evaluate_eligibility,
    sanitize_description,
)

API_ORIGIN = "https://www.googleapis.com"
API_BASE = f"{API_ORIGIN}/youtube/v3"
PUBLIC_URL = "https://www.youtube.com"
THUMB_ORIGIN = "https://i.ytimg.com"
SEARCH_QUERIES = ("Omarchy", "Omarchy Linux", "Omarchy Quattro")
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
REFRESH_CADENCE = timedelta(hours=2)
MAX_SEARCH_RESULTS = 25
MAX_VIDEOS_LOOKUP = 50
TOP_N = 8
MAX_SECTION_EVENTS = 24
# One channel may hold at most this many lane slots after ranking.
MAX_EVENTS_PER_CHANNEL = 2
HQDEFAULT_WIDTH = 480
HQDEFAULT_HEIGHT = 360
MAX_METRIC_VALUE = 9_007_199_254_740_991


def watch_url(video_id: str) -> str:
    return f"{PUBLIC_URL}/watch?v={video_id}"


def thumbnail_url(video_id: str) -> str:
    return f"{THUMB_ORIGIN}/vi/{video_id}/hqdefault.jpg"


def search_url(*, query: str, api_key: str) -> str:
    return (
        f"{API_BASE}/search?"
        + urlencode(
            {
                "part": "snippet",
                "type": "video",
                "q": query,
                "maxResults": str(MAX_SEARCH_RESULTS),
                "key": api_key,
            }
        )
    )


def videos_url(*, video_ids: Sequence[str], api_key: str) -> str:
    if not video_ids or len(video_ids) > MAX_VIDEOS_LOOKUP:
        raise ValidationError("YouTube videos lookup size is invalid")
    return (
        f"{API_BASE}/videos?"
        + urlencode(
            {
                "part": "snippet,statistics",
                "id": ",".join(video_ids),
                "key": api_key,
            }
        )
    )


def _non_negative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_METRIC_VALUE:
        if isinstance(value, str) and value.isdigit():
            parsed = int(value)
            if 0 <= parsed <= MAX_METRIC_VALUE:
                return parsed
        raise ValidationError(f"YouTube {name} is invalid")
    return value


def _snippet_text(snippet: Mapping[str, Any]) -> str:
    title = snippet.get("title") if isinstance(snippet.get("title"), str) else ""
    description = snippet.get("description") if isinstance(snippet.get("description"), str) else ""
    return f"{title}\n{description}"


def parse_search_video_ids(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        raise ValidationError("YouTube search payload must be an object")
    items = payload.get("items")
    if not isinstance(items, list) or len(items) > MAX_SEARCH_RESULTS:
        raise ValidationError("YouTube search items are invalid")
    video_ids: list[str] = []
    seen: set[str] = set()
    for raw in items:
        if not isinstance(raw, dict):
            raise ValidationError("YouTube search item is invalid")
        if raw.get("kind") not in {None, "youtube#searchResult"}:
            continue
        identity = raw.get("id")
        if not isinstance(identity, dict):
            raise ValidationError("YouTube search id is invalid")
        if identity.get("kind") not in {None, "youtube#video"}:
            continue
        video_id = identity.get("videoId")
        if not isinstance(video_id, str) or not VIDEO_ID_RE.fullmatch(video_id):
            raise ValidationError("YouTube video id is invalid")
        snippet = raw.get("snippet")
        if not isinstance(snippet, dict):
            raise ValidationError("YouTube search snippet is invalid")
        if not KEYWORD_RE.search(_snippet_text(snippet)):
            continue
        if video_id not in seen:
            seen.add(video_id)
            video_ids.append(video_id)
    return video_ids


def _summary_text(prose: str) -> str:
    """Publish sanitized prose, or one neutral sentence when none survived."""

    return normalize_text(prose or NEUTRAL_SUMMARY, SUMMARY_MAX_CHARS)


def _channel_key(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _reupload_key(video: Mapping[str, Any]) -> tuple[str, str]:
    """Group byte-different re-uploads of one title from one channel."""

    title = "".join(
        character
        for character in " ".join(str(video.get("title", "")).split()).casefold()
        if character.isalnum() or character.isspace()
    )
    return (_channel_key(video.get("channelTitle")), " ".join(title.split()))


def parse_videos(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValidationError("YouTube videos payload must be an object")
    items = payload.get("items")
    if not isinstance(items, list) or len(items) > MAX_VIDEOS_LOOKUP:
        raise ValidationError("YouTube videos items are invalid")
    videos: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in items:
        if not isinstance(raw, dict):
            raise ValidationError("YouTube video item is invalid")
        video_id = raw.get("id")
        if not isinstance(video_id, str) or not VIDEO_ID_RE.fullmatch(video_id):
            raise ValidationError("YouTube video id is invalid")
        if video_id in seen:
            raise ValidationError("YouTube video id is duplicated")
        snippet = raw.get("snippet")
        statistics = raw.get("statistics")
        if not isinstance(snippet, dict) or not isinstance(statistics, dict):
            raise ValidationError("YouTube video snippet or statistics are invalid")
        title = normalize_text(snippet.get("title"), 160)
        sanitized = sanitize_description(snippet.get("description"))
        if not evaluate_eligibility(title=title, prose=sanitized.prose).eligible:
            # Promotional, link-only, incidental, or amplified items never enter
            # the lane. The closed reason codes stay internal to collection.
            continue
        published_raw = snippet.get("publishedAt")
        if not isinstance(published_raw, str):
            raise ValidationError("YouTube publishedAt is invalid")
        # API may include fractional seconds; normalize to canonical UTC Z.
        published = published_raw.replace("Z", "+00:00")
        try:
            published_dt = datetime.fromisoformat(published).astimezone(timezone.utc).replace(microsecond=0)
        except ValueError as exc:
            raise ValidationError("YouTube publishedAt is invalid") from exc
        channel = snippet.get("channelTitle")
        if not isinstance(channel, str) or not channel.strip():
            channel = "YouTube"
        summary = _summary_text(sanitized.prose)
        videos.append(
            {
                "id": video_id,
                "title": title,
                "summary": summary,
                "channelTitle": normalize_text(channel, 120),
                "publishedAt": format_timestamp(published_dt),
                "views": _non_negative_int(statistics.get("viewCount", 0), "viewCount"),
                "likes": _non_negative_int(statistics.get("likeCount", 0), "likeCount"),
            }
        )
        seen.add(video_id)
    return videos


def _dedupe_reuploads(videos: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Keep one record per channel/title group, preferring the observed leader."""

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in videos:
        video = dict(raw)
        key = _reupload_key(video)
        if not key[1]:
            grouped[(key[0], str(video["id"]))] = video
            continue
        current = grouped.get(key)
        if current is None:
            grouped[key] = video
            continue
        challenger = (
            -int(video.get("views", 0)),
            parse_timestamp(str(video["publishedAt"])).timestamp(),
            str(video["id"]),
        )
        incumbent = (
            -int(current.get("views", 0)),
            parse_timestamp(str(current["publishedAt"])).timestamp(),
            str(current["id"]),
        )
        if challenger < incumbent:
            grouped[key] = video
    return list(grouped.values())


def _cap_per_channel(
    ordered: Sequence[Mapping[str, Any]], *, maximum: int = MAX_EVENTS_PER_CHANNEL
) -> list[dict[str, Any]]:
    """Apply the per-channel cap after ranking so order stays rank order."""

    counts: dict[str, int] = {}
    capped: list[dict[str, Any]] = []
    for video in ordered:
        channel = _channel_key(video.get("channelTitle"))
        if channel and counts.get(channel, 0) >= maximum:
            continue
        counts[channel] = counts.get(channel, 0) + 1
        capped.append(dict(video))
    return capped


def rank_youtube_videos(videos: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Interleave top views, likes, and recent selections into a bounded lane."""

    unique = {str(video["id"]): dict(video) for video in _dedupe_reuploads(videos)}
    by_views = sorted(unique.values(), key=lambda item: (-int(item["views"]), str(item["id"])))[:TOP_N]
    by_likes = sorted(unique.values(), key=lambda item: (-int(item["likes"]), str(item["id"])))[:TOP_N]
    by_recent = sorted(
        unique.values(),
        key=lambda item: (-parse_timestamp(str(item["publishedAt"])).timestamp(), str(item["id"])),
    )[:TOP_N]
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in zip(by_views, by_likes, by_recent):
        for item in group:
            video_id = str(item["id"])
            if video_id in seen:
                continue
            ordered.append(item)
            seen.add(video_id)
    # zip stops at the shortest list; append any remainder from longer tops.
    for bucket in (by_views, by_likes, by_recent):
        for item in bucket:
            video_id = str(item["id"])
            if video_id in seen:
                continue
            ordered.append(item)
            seen.add(video_id)
    return _cap_per_channel(ordered)[:MAX_SECTION_EVENTS]


def rank_youtube_events(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Reorder youtube-video events using section-local ranking only."""

    videos: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for raw in events:
        event = dict(raw)
        if event.get("type") != "youtube-video":
            continue
        entity = event.get("entity")
        metrics = {
            str(item.get("id")): item
            for item in event.get("metrics", [])
            if isinstance(item, Mapping)
        }
        if not isinstance(entity, Mapping):
            continue
        video_id = str(entity.get("id", ""))
        views = int(metrics.get("youtube-views", {}).get("value", 0)) if isinstance(metrics.get("youtube-views"), Mapping) else 0
        likes = int(metrics.get("youtube-likes", {}).get("value", 0)) if isinstance(metrics.get("youtube-likes"), Mapping) else 0
        videos.append(
            {
                "id": video_id,
                "title": str(event.get("title", "")),
                "channelTitle": str(entity.get("name", "")),
                "publishedAt": event["occurredAt"],
                "views": views,
                "likes": likes,
            }
        )
        by_id[video_id] = event
    return [by_id[item["id"]] for item in rank_youtube_videos(videos) if item["id"] in by_id]


def youtube_events(
    videos: Sequence[Mapping[str, Any]],
    *,
    discovered_at: datetime,
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    clock = discovered_at.astimezone(timezone.utc).replace(microsecond=0)
    observed = observed_at or format_timestamp(clock)
    events: list[dict[str, Any]] = []
    eligible = [
        video
        for video in videos
        if evaluate_eligibility(
            title=str(video.get("title", "")), prose=str(video.get("summary", ""))
        ).eligible
    ]
    for video in rank_youtube_videos(eligible):
        video_id = str(video["id"])
        # ENTITY_ID_RE requires an alphanumeric first character; YouTube IDs may start with _/-.
        entity_id = f"yt:{video_id}"
        source = watch_url(video_id)
        event = {
            "id": event_id("youtube-video", "youtube", entity_id, video_id, source),
            "type": "youtube-video",
            "occurredAt": str(video["publishedAt"]),
            "discoveredAt": format_timestamp(clock),
            "title": str(video["title"]),
            "summary": str(video["summary"]),
            "source": {"label": "YouTube", "url": source},
            "entity": {
                "kind": "youtube",
                "id": entity_id,
                "name": str(video["channelTitle"]),
            },
            "classification": {
                "section": "youtube",
                "significance": "routine",
                "curated": False,
                "tags": ["youtube"],
            },
            "trust": {"marketplace": "not-applicable", "securityAudit": False},
            "compatibility": {"channels": [], "basis": "unknown"},
            "image": {
                "sourceUrl": thumbnail_url(video_id),
                "alt": f"YouTube thumbnail for {video['title']}"[:180],
                "credit": "YouTube",
                "width": HQDEFAULT_WIDTH,
                "height": HQDEFAULT_HEIGHT,
            },
            "metrics": [
                {
                    "id": "youtube-likes",
                    "value": int(video["likes"]),
                    "observedAt": observed,
                    "sourceUrl": source,
                },
                {
                    "id": "youtube-views",
                    "value": int(video["views"]),
                    "observedAt": observed,
                    "sourceUrl": source,
                },
            ],
        }
        events.append(validate_event(event))
    return events


def should_refresh_youtube(
    previous_source: Mapping[str, Any] | None,
    *,
    now: datetime,
) -> bool:
    """Return True when YouTube should be fetched again.

    The two-hour cadence conserves quota only after a successful non-empty
    snapshot. Missing, malformed, or empty ``videoIds`` always refresh so the
    first populate (and empty→filled) is never delayed by the gate.
    """
    if not isinstance(previous_source, Mapping):
        return True
    video_ids = previous_source.get("videoIds")
    if not isinstance(video_ids, list) or len(video_ids) == 0:
        return True
    checked_at = previous_source.get("checkedAt")
    if not isinstance(checked_at, str):
        return True
    try:
        previous = parse_timestamp(checked_at, "youtube checkedAt")
    except ValidationError:
        return True
    return now.astimezone(timezone.utc) - previous >= REFRESH_CADENCE
