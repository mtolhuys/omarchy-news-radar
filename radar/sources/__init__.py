"""Allowlisted source adapters."""

from .community import community_events
from .marketplace import diff_marketplace, enrich_plugin_descriptions, parse_marketplace
from .marketplace_engagement import parse_engagement
from .omarchy_news import diff_news, enrich_omarchy_news, parse_news_rss
from .omarchy_releases import diff_releases, parse_releases
from .youtube import (
    parse_search_video_ids,
    parse_videos,
    rank_youtube_events,
    should_refresh_youtube,
    youtube_events,
)

__all__ = [
    "community_events",
    "diff_marketplace",
    "enrich_plugin_descriptions",
    "diff_news",
    "enrich_omarchy_news",
    "diff_releases",
    "parse_marketplace",
    "parse_engagement",
    "parse_news_rss",
    "parse_releases",
    "parse_search_video_ids",
    "parse_videos",
    "rank_youtube_events",
    "should_refresh_youtube",
    "youtube_events",
]
