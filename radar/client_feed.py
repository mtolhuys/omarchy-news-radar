"""Cached news retrieval and conditional fixed-origin refresh scheduling."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .client_common import response
from .constants import BUILD_ID, FEED_MAX_BYTES, FEED_ORIGIN, FEED_URL
from .errors import FetchError, RadarError, StorageError, ValidationError
from .freshness import edition_timing, update_message
from .http import FetchPolicy, decode_json, fetch_bytes
from .io import read_json_bounded
from .local_edition import local_edition_metadata
from .state import (RefreshLock, feed_cached_at, load_feed_http, load_feed, load_state,
                    load_update_check, save_feed, save_feed_http, save_update_check)
from .validation import parse_timestamp, validate_feed

CLIENT_USER_AGENT = f"omarchy-news-radar-client/{BUILD_ID.removeprefix('news-radar-')}"

@dataclass(frozen=True)
class FeedFetch:
    candidate: dict[str, Any] | None
    status: int
    url: str | None = None
    etag: str | None = None
    last_modified: str | None = None


def read_model(environment: Mapping[str, str] | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    clock = now or datetime.now(timezone.utc)
    feed = load_feed(environment, now=clock)
    state, quarantined = load_state(environment)
    if feed is None:
        return response("first-use", feed=None, state=state, quarantine=quarantined)
    local = local_edition_metadata(feed, environment)
    return response(
        "cached",
        feed=feed,
        state=state,
        quarantine=quarantined,
        editionMode="local" if local else "published",
        localEdition=local,
        timing=edition_timing(feed, now=clock, cached_at=feed_cached_at(environment)),
    )


def _test_feed(
    environment: Mapping[str, str],
    validators: Mapping[str, Any] | None = None,
) -> dict[str, Any] | FeedFetch | None:
    if environment.get("OMARCHY_NEWS_RADAR_TEST_MODE") != "1":
        return None
    path = environment.get("OMARCHY_NEWS_RADAR_TEST_FEED")
    url = environment.get("OMARCHY_NEWS_RADAR_TEST_FEED_URL")
    if path and url:
        raise ValidationError("test feed path and URL are mutually exclusive")
    if path:
        return read_json_bounded(Path(path), FEED_MAX_BYTES)
    if url:
        try:
            timeout = float(environment.get("OMARCHY_NEWS_RADAR_TEST_TIMEOUT_SECONDS", "1"))
        except ValueError as exc:
            raise ValidationError("test timeout is invalid") from exc
        if not 0.05 <= timeout <= 5.0:
            raise ValidationError("test timeout is outside its bound")
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return _fetch_feed_url(
            url,
            policy=FetchPolicy(
                FEED_MAX_BYTES, timeout, frozenset({origin}), allow_loopback_http=True
            ),
            validators=validators,
        )
    raise ValidationError("test mode requires an explicit fixture path or loopback URL")


def _header(headers: Mapping[str, str], name: str) -> str | None:
    lowered = name.lower()
    return next((value for key, value in headers.items() if key.lower() == lowered), None)


def _fetch_feed_url(
    url: str,
    *,
    policy: FetchPolicy,
    validators: Mapping[str, Any] | None = None,
) -> FeedFetch:
    request_headers = {"Accept": "application/json", "Accept-Encoding": "gzip", "User-Agent": CLIENT_USER_AGENT}
    applicable = validators if validators and validators.get("url") == url else None
    if applicable:
        if isinstance(applicable.get("etag"), str):
            request_headers["If-None-Match"] = applicable["etag"]
        if isinstance(applicable.get("lastModified"), str):
            request_headers["If-Modified-Since"] = applicable["lastModified"]
    data, response_headers, status = fetch_bytes(
        url,
        policy=policy,
        headers=request_headers,
        allow_not_modified=applicable is not None,
    )
    etag = _header(response_headers, "ETag")
    last_modified = _header(response_headers, "Last-Modified")
    if status == 304:
        return FeedFetch(
            None,
            status,
            url=url,
            etag=etag or applicable.get("etag"),
            last_modified=last_modified or applicable.get("lastModified"),
        )
    return FeedFetch(
        decode_json(data, label="feed"),
        status,
        url=url,
        etag=etag,
        last_modified=last_modified,
    )


def _fetch_feed(
    *, timeout: float = 12.0, validators: Mapping[str, Any] | None = None
) -> FeedFetch:
    """Fetch production feed with a fixed URL and closed redirect origin."""

    return _fetch_feed_url(
        FEED_URL,
        policy=FetchPolicy(FEED_MAX_BYTES, timeout, frozenset({FEED_ORIGIN})),
        validators=validators,
    )


def _youtube_event_count(feed: Mapping[str, Any] | None) -> int:
    if not isinstance(feed, Mapping):
        return 0
    events = feed.get("events")
    if not isinstance(events, list):
        return 0
    return sum(1 for event in events if isinstance(event, Mapping) and event.get("type") == "youtube-video")


def _should_adopt_published_for_youtube(
    cached: Mapping[str, Any] | None,
    validated: Mapping[str, Any],
    *,
    local_edition: bool,
) -> bool:
    """Adopt an older published edition when a local live edition lacks YouTube.

    D029 still refuses ordinary published downgrades. This narrow exception only
    applies while a digest-matched local edition has zero youtube-video events
    and the validated published candidate has at least one, so Check for updates
    can fill the YouTube section from Forge without waiting for generatedAt.
    """
    if not local_edition or cached is None:
        return False
    return _youtube_event_count(cached) == 0 and _youtube_event_count(validated) > 0


def refresh(environment: Mapping[str, str] | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    env = dict(environment or os.environ)
    clock = now or datetime.now(timezone.utc)
    cached = load_feed(env, now=clock)
    local = local_edition_metadata(cached, env)
    try:
        with RefreshLock(env):
            try:
                save_update_check("failed", env, now=clock)
            except (RadarError, OSError):
                pass
            validators = load_feed_http(env) if cached is not None else None
            fetched = _test_feed(env, validators)
            if fetched is None:
                fetched = (
                    _fetch_feed(validators=validators)
                    if validators and validators.get("url") == FEED_URL
                    else _fetch_feed()
                )
            if isinstance(fetched, Mapping):
                fetched = FeedFetch(dict(fetched), 200)
            if fetched.status == 304:
                if cached is None:
                    raise FetchError("http-error", "server returned 304 without a valid cached feed")
                validated = cached
                not_modified = True
            else:
                if fetched.candidate is None:
                    raise FetchError("http-error", "server returned an empty feed response")
                validated = validate_feed(fetched.candidate, now=clock, public_only=True)
                not_modified = False
            published_timing = edition_timing(validated, now=clock)
            candidate_is_newer = not not_modified and (cached is None or (
                parse_timestamp(validated["generatedAt"])
                > parse_timestamp(cached["generatedAt"])
            ))
            adopt_for_youtube = _should_adopt_published_for_youtube(
                cached,
                validated,
                local_edition=local is not None,
            ) if not not_modified else False
            if candidate_is_newer or adopt_for_youtube:
                previous_ids = {event["id"] for event in cached["events"]} if cached else set()
                new_stories = sum(event["id"] not in previous_ids for event in validated["events"])
                selected = save_feed(validated, env, now=clock)
                edition_mode = "published"
                local = None
                edition_changed = True
                cache_preserved = False
            else:
                selected = cached or validated
                edition_mode = "local" if local is not None else "published"
                new_stories = 0
                edition_changed = False
                cache_preserved = cached is not None

            if fetched.url is not None:
                try:
                    save_feed_http(
                        fetched.url,
                        fetched.etag,
                        fetched.last_modified,
                        env,
                    )
                except (RadarError, OSError):
                    pass

            if published_timing["publisherStale"]:
                status = "stale-publication"
            elif edition_changed:
                status = "updated"
            elif local is not None:
                status = "local-current"
            else:
                status = "no-change"
            selected_timing = edition_timing(
                selected,
                now=clock,
                cached_at=feed_cached_at(env),
            )
            try:
                save_update_check("success", env, now=clock)
            except (RadarError, OSError):
                pass
        return response(
            status,
            feed=selected,
            cachePreserved=cache_preserved,
            editionMode=edition_mode,
            localEdition=local,
            publishedGeneratedAt=validated["generatedAt"],
            newStories=new_stories,
            editionChanged=edition_changed,
            timing=selected_timing,
            publishedTiming=published_timing,
            message=update_message(
                status,
                timing=published_timing,
                new_stories=new_stories,
                local_edition=edition_mode == "local",
            ),
        )
    except (RadarError, OSError) as exc:
        reason = exc.reason if isinstance(exc, FetchError) else "validation-failed" if isinstance(exc, ValidationError) else "local-error"
        invalid_candidate = isinstance(exc, ValidationError) or (
            isinstance(exc, FetchError) and exc.reason in {"invalid-json", "too-large"}
        )
        status = "invalid-feed" if invalid_candidate else "offline"
        cache_timing = (
            edition_timing(cached, now=clock, cached_at=feed_cached_at(env))
            if cached is not None
            else None
        )
        return response(
            status,
            reason=reason,
            detail=str(exc),
            feed=cached,
            cachePreserved=cached is not None,
            editionMode="local" if local is not None else "published",
            localEdition=local,
            newStories=0,
            editionChanged=False,
            timing=cache_timing,
            message=update_message(status, timing=cache_timing, local_edition=local is not None),
        )


def refresh_if_due(
    minimum_age: int,
    environment: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not 300 <= minimum_age <= 86400:
        raise ValidationError("minimum refresh age is outside its bound")
    clock = now or datetime.now(timezone.utc)
    cached = load_feed(environment, now=clock)
    update_check = load_update_check(environment, now=clock)
    checked_at = (
        parse_timestamp(update_check["checkedAt"])
        if update_check
        else feed_cached_at(environment)
    )
    due_after = (
        min(minimum_age, 300)
        if update_check and update_check["outcome"] == "failed"
        else minimum_age
    )
    if checked_at is not None:
        age = max(0.0, (clock - checked_at).total_seconds())
        if age < due_after:
            return response(
                "not-due",
                feed=cached,
                cachePreserved=cached is not None,
                timing=edition_timing(cached, now=clock, cached_at=feed_cached_at(environment))
                if cached is not None else None,
                nextCheckInSeconds=max(1, math.ceil(due_after - age)),
                lastUpdateCheck=update_check,
            )
    result = refresh(environment, now=clock)
    result["nextCheckInSeconds"] = (
        min(minimum_age, 300)
        if result["status"] in {"offline", "invalid-feed"}
        else minimum_age
    )
    return result
