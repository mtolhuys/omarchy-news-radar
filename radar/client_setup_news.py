"""Optional generic setup-news cache and fixed-origin refresh."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .constants import BUILD_ID, FEED_ORIGIN, SETUP_NEWS_URL
from .errors import RadarError, ValidationError
from .http import FetchPolicy, decode_json, fetch_bytes
from .io import atomic_write_json, read_json_bounded, refuse_symlink
from .setup_news import SETUP_NEWS_MAX_BYTES, setup_news_events, validate_setup_news
from .state import StateLock, _OwnedFileLock, cache_root
from .validation import format_timestamp, parse_timestamp


def load_setup_news(
    environment: Mapping[str, str] | None = None, *, now: datetime | None = None
) -> dict[str, Any] | None:
    try:
        refuse_symlink(cache_root(environment))
        return validate_setup_news(
            read_json_bounded(cache_root(environment) / "setup-news.json", SETUP_NEWS_MAX_BYTES),
            now=now,
        )
    except (OSError, RadarError):
        return None


def _validators(environment: Mapping[str, str]) -> dict[str, Any] | None:
    try:
        value = read_json_bounded(cache_root(environment) / "setup-news-http.json", 4096)
        if (
            not isinstance(value, dict)
            or set(value) != {"url", "etag", "lastModified"}
            or value["url"] != SETUP_NEWS_URL
        ):
            return None
        for key in ("etag", "lastModified"):
            item = value[key]
            if item is not None and (
                not isinstance(item, str)
                or not 1 <= len(item) <= 512
                or any(ord(character) < 32 or ord(character) == 127 for character in item)
            ):
                return None
        return value
    except (OSError, RadarError):
        return None


def refresh_setup_news(
    environment: Mapping[str, str] | None = None, *, now: datetime | None = None
) -> dict[str, Any]:
    env = dict(environment or os.environ)
    clock = now or datetime.now(timezone.utc)
    cached = load_setup_news(env, now=clock)
    base = cache_root(env)
    status = "cached" if cached else "missing"
    try:
        with _OwnedFileLock(
            base / "setup-news-refresh.lock",
            label="setup news refresh",
            contention_message="setup news refresh is already running",
            nonblocking=True,
        ):
            try:
                check = read_json_bounded(base / "setup-news-check.json", 512)
                if not isinstance(check, dict) or set(check) != {"checkedAt"}:
                    raise ValidationError("invalid setup news check")
                age = (clock - parse_timestamp(check["checkedAt"])).total_seconds()
                if 0 <= age < 300:
                    return {
                        "protocolVersion": 1,
                        "status": status,
                        "stories": len(setup_news_events(cached)) if cached else 0,
                        "attempted": False,
                        "changed": False,
                    }
            except (OSError, RadarError):
                pass
            atomic_write_json(base / "setup-news-check.json", {"checkedAt": format_timestamp(clock)})
            validators = _validators(env) if cached else None
            if env.get("OMARCHY_NEWS_RADAR_TEST_MODE") == "1":
                path = env.get("OMARCHY_NEWS_RADAR_TEST_SETUP_NEWS")
                if not path:
                    return {
                        "protocolVersion": 1,
                        "status": status,
                        "stories": len(setup_news_events(cached)) if cached else 0,
                        "attempted": False,
                        "changed": False,
                    }
                raw = read_json_bounded(Path(path), SETUP_NEWS_MAX_BYTES)
                headers: Mapping[str, str] = {}
                response_code = 200
            else:
                request_headers = {
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "User-Agent": f"omarchy-news-radar-client/{BUILD_ID.removeprefix('news-radar-')}",
                }
                if validators:
                    if validators["etag"]:
                        request_headers["If-None-Match"] = validators["etag"]
                    if validators["lastModified"]:
                        request_headers["If-Modified-Since"] = validators["lastModified"]
                data, headers, response_code = fetch_bytes(
                    SETUP_NEWS_URL,
                    policy=FetchPolicy(SETUP_NEWS_MAX_BYTES, 8.0, frozenset({FEED_ORIGIN})),
                    headers=request_headers,
                    allow_not_modified=validators is not None,
                )
                raw = cached if response_code == 304 else decode_json(data, label="setup news")
            candidate = validate_setup_news(raw, now=clock)
            if cached and candidate["publishedAt"] < cached["publishedAt"]:
                candidate = cached
            changed = candidate != cached
            with StateLock(env):
                atomic_write_json(base / "setup-news.json", candidate)
                lowered = {key.lower(): value for key, value in headers.items()}
                metadata = {
                    "url": SETUP_NEWS_URL,
                    "etag": lowered.get("etag"),
                    "lastModified": lowered.get("last-modified"),
                }
                if response_code == 304 and validators:
                    metadata = {
                        key: value or validators[key] for key, value in metadata.items()
                    }
                safe = all(
                    value is None
                    or (
                        isinstance(value, str)
                        and len(value) <= 512
                        and all(ord(character) >= 32 and ord(character) != 127 for character in value)
                    )
                    for key, value in metadata.items()
                    if key != "url"
                )
                atomic_write_json(
                    base / "setup-news-http.json",
                    metadata if safe else {"url": SETUP_NEWS_URL, "etag": None, "lastModified": None},
                )
            return {
                "protocolVersion": 1,
                "status": "cached",
                "stories": len(setup_news_events(candidate)),
                "attempted": True,
                "changed": changed,
            }
    except (OSError, RadarError) as exc:
        return {
            "protocolVersion": 1,
            "status": status,
            "stories": len(setup_news_events(cached)) if cached else 0,
            "attempted": True,
            "changed": False,
            "message": "Setup news is unavailable; the regular edition remains readable.",
            "reason": str(exc),
        }


def merge_setup_news(
    feed: Mapping[str, Any],
    setup_news: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if setup_news is None:
        return dict(feed)
    feed_semantic_keys = {
        (item["type"], item["entity"]["kind"], item["entity"]["id"], item["occurredAt"])
        for item in feed["events"]
    }
    merged = {
        item["id"]: item
        for item in setup_news_events(setup_news)
        if (item["type"], item["entity"]["kind"], item["entity"]["id"], item["occurredAt"])
        not in feed_semantic_keys
    }
    # The rolling edition wins when it carries the same story because it may
    # contain fresher metrics or editorial enrichment.
    merged.update({item["id"]: dict(item) for item in feed["events"]})
    return {**feed, "events": sorted(merged.values(), key=lambda item: (
        -parse_timestamp(item["occurredAt"]).timestamp(),
        -parse_timestamp(item["discoveredAt"]).timestamp(),
        item["id"],
    ))}


def load_reading_feed(
    environment: Mapping[str, str] | None = None, *, now: datetime | None = None
) -> dict[str, Any] | None:
    """Load the complete validated story universe used by reader actions."""

    from .state import load_feed

    feed = load_feed(environment, now=now)
    return merge_setup_news(feed, load_setup_news(environment, now=now)) if feed else None
