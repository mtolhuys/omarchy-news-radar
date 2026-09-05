"""Bounded inspection of optional public image references; no raster hosting."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import monotonic
from typing import Any, Callable, Mapping
from .errors import FetchError, ValidationError
from .http import FetchPolicy, fetch_bytes
from .images import MAX_IMAGE_BYTES, inspect_raster
from .validation import parse_timestamp, validate_feed
from .insights import validate_insights

ImageFetcher = Callable[[str], tuple[bytes, str]]
IMAGE_INSPECTION_SECONDS = 60.0


def _fetch_image(url: str) -> tuple[bytes, str]:
    data, headers, _ = fetch_bytes(
        url,
        policy=FetchPolicy(MAX_IMAGE_BYTES, 20.0, frozenset({"https://plugins.omarchy.org"})),
        headers={"Accept": "image/webp,image/png,image/jpeg", "User-Agent": "omarchy-news-radar-publisher/0.1"},
    )
    return data, str(headers.get("Content-Type", ""))


def _inspect_sources(items: list[dict[str, Any]], image_fetcher: ImageFetcher) -> dict[str, tuple[Any, str]]:
    """Deduplicate URLs and stop starting optional work after one bounded budget.

    Four requests can be in flight. Their ordinary twenty-second request timeout
    still applies at the deadline; queued work then becomes a harmless omission.
    Only small dimension records survive each fetch, never a catalog of rasters.
    """
    sources = list(dict.fromkeys(item["image"]["sourceUrl"] for item in items
                                if not item["image"]["sourceUrl"].startswith("https://i.ytimg.com/vi/")))
    deadline = monotonic() + IMAGE_INSPECTION_SECONDS

    def inspect(source: str) -> tuple[Any, str]:
        if monotonic() >= deadline:
            return None, "optional image inspection budget reached"
        try:
            data, content_type = image_fetcher(source)
            return inspect_raster(data, content_type), ""
        except (FetchError, ValidationError, OSError) as exc:
            return None, str(exc)

    with ThreadPoolExecutor(max_workers=4) as executor:
        return dict(zip(sources, executor.map(inspect, sources)))


def _apply_inspections(items: list[dict[str, Any]], image_fetcher: ImageFetcher) -> list[str]:
    inspected = _inspect_sources(items, image_fetcher)
    failures = []
    for item in items:
        image = item["image"]
        source = image["sourceUrl"]
        if source.startswith("https://i.ytimg.com/vi/"):
            continue
        info, error = inspected[source]
        if not error and (info.width, info.height) != (image["width"], image["height"]):
            error = "image dimensions differ from marketplace metadata"
        if error:
            failures.append(f"{item['id']}: {error}")
            del item["image"]
    return failures


def materialize_images(
    feed: Mapping[str, Any], asset_directory: Path, *, image_fetcher: ImageFetcher = _fetch_image
) -> tuple[dict[str, Any], list[str]]:
    """Validate allowlisted marketplace previews and publish their HTTPS URLs.

    Rasters are not mirrored onto the feed host. ``asset_directory`` is retained
    for call-site compatibility; only ``assets/site.css`` is written by publish().
    """

    del asset_directory  # no longer used for hosted rasters
    candidate = validate_feed(dict(feed), now=parse_timestamp(feed.get("publishedAt", feed["generatedAt"])))
    public_feed = deepcopy(candidate)
    items = [event for event in public_feed["events"]
             if isinstance(event.get("image"), dict) and "sourceUrl" in event["image"]]
    failures = _apply_inspections(items, image_fetcher)
    return validate_feed(public_feed, now=parse_timestamp(public_feed.get("publishedAt", public_feed["generatedAt"])), public_only=True), failures


def materialize_insight_images(
    insights: Mapping[str, Any], *, image_fetcher: ImageFetcher = _fetch_image,
) -> tuple[dict[str, Any], list[str]]:
    """Inspect at most twelve discovery thumbnails, four at a time, independently of news."""
    result = deepcopy(validate_insights(dict(insights), now=parse_timestamp(insights["publishedAt"])))
    candidates = [item for item in result["collections"] + result["projects"] if "image" in item]
    failures = []
    for item in candidates[12:]:
        del item["image"]
        failures.append(f"{item['id']}: optional discovery image budget reached")

    failures.extend(_apply_inspections(candidates[:12], image_fetcher))
    return result, failures
