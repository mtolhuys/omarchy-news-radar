from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest import mock

from radar.collector import (
    FixtureInputs,
    collect_from_fixtures,
    collect_production,
    empty_snapshot,
    load_snapshot,
    validate_snapshot,
)
from radar.constants import MAX_EVENTS
from radar.errors import ValidationError
from radar.io import canonical_json_bytes
from radar.model import event_sort_key
from radar.sources.marketplace import CATALOG_URL
from radar.sources.marketplace_engagement import ENGAGEMENT_URL
from radar.sources.omarchy_news import RSS_URL
from radar.sources.omarchy_releases import API_URL

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


def snapshot_event(*, index: int, occurred_at: datetime) -> dict[str, Any]:
    event = deepcopy(
        json.loads(
            (ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8")
        )["events"][0]
    )
    event["id"] = f"evt_{index:024x}"
    timestamp = occurred_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    event["occurredAt"] = timestamp
    event["discoveredAt"] = timestamp
    return event


class CollectorIntegrationTests(unittest.TestCase):
    def inputs(self, generation: str) -> FixtureInputs:
        return FixtureInputs(
            ROOT / f"tests/fixtures/releases-{generation}.json",
            ROOT / f"tests/fixtures/catalog-{generation}.json",
            ROOT / "tests/fixtures/community",
            ROOT / "content/curation",
            ROOT / f"tests/fixtures/engagement-{generation}.json",
        )

    def test_bootstrap_backfill_is_bounded_and_second_generation_is_stable(self) -> None:
        baseline_feed, baseline_snapshot = collect_from_fixtures(
            self.inputs("baseline"),
            previous_snapshot=None,
            now=CLOCK,
            bootstrap_marketplace=True,
        )
        self.assertLessEqual(
            len([event for event in baseline_feed["events"] if event["type"] == "plugin-added"]),
            12,
        )
        next_feed, next_snapshot = collect_from_fixtures(
            self.inputs("next"),
            previous_snapshot=baseline_snapshot,
            now=CLOCK,
            bootstrap_marketplace=False,
        )
        repeated, repeated_snapshot = collect_from_fixtures(
            self.inputs("next"),
            previous_snapshot=baseline_snapshot,
            now=CLOCK,
            bootstrap_marketplace=False,
        )
        self.assertEqual(canonical_json_bytes(next_feed), canonical_json_bytes(repeated))
        self.assertEqual(next_snapshot, repeated_snapshot)
        self.assertEqual((ROOT / "tests/fixtures/feed-valid.json").read_bytes(), canonical_json_bytes(next_feed))
        retained, retained_snapshot = collect_from_fixtures(
            self.inputs("next"),
            previous_snapshot=next_snapshot,
            now=CLOCK,
            bootstrap_marketplace=False,
        )
        self.assertEqual(canonical_json_bytes(next_feed), canonical_json_bytes(retained))
        self.assertEqual(6, len(retained_snapshot["events"]))

    def test_aged_canonical_snapshot_loads_without_using_the_host_clock(self) -> None:
        event = snapshot_event(
            index=1,
            occurred_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        snapshot = {"schemaVersion": 2, "events": [event], "sources": {}}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source-snapshot.json"
            path.write_bytes(canonical_json_bytes(snapshot))
            self.assertEqual(snapshot, load_snapshot(path))

    def test_snapshot_rejects_events_outside_exact_canonical_order(self) -> None:
        first = snapshot_event(index=1, occurred_at=CLOCK)
        second = snapshot_event(index=2, occurred_at=CLOCK)
        self.assertEqual([first, second], sorted([second, first], key=event_sort_key))

        with self.assertRaisesRegex(ValidationError, "canonical order"):
            validate_snapshot(
                {"schemaVersion": 2, "events": [second, first], "sources": {}}
            )

    def test_snapshot_rejects_duplicate_event_ids(self) -> None:
        event = snapshot_event(index=1, occurred_at=CLOCK)
        with self.assertRaisesRegex(ValidationError, "duplicate event IDs"):
            validate_snapshot(
                {"schemaVersion": 2, "events": [event, deepcopy(event)], "sources": {}}
            )

    def test_snapshot_rejects_an_over_bound_event_ledger(self) -> None:
        over_bound = [
            snapshot_event(index=index, occurred_at=CLOCK)
            for index in range(MAX_EVENTS + 1)
        ]
        with self.assertRaisesRegex(ValidationError, "event bound"):
            validate_snapshot({"schemaVersion": 2, "events": over_bound, "sources": {}})

    def test_successor_retention_uses_the_explicit_collection_clock(self) -> None:
        expired = snapshot_event(index=1, occurred_at=CLOCK - timedelta(days=31))
        previous = {"schemaVersion": 2, "events": [expired], "sources": {}}

        with mock.patch("radar.model.datetime") as host_datetime:
            host_datetime.now.return_value = datetime(2000, 1, 1, tzinfo=timezone.utc)
            _, successor = collect_from_fixtures(
                self.inputs("baseline"),
                previous_snapshot=previous,
                now=CLOCK,
                bootstrap_marketplace=True,
            )

        self.assertNotIn(expired["id"], {event["id"] for event in successor["events"]})

    def test_fixed_clock_collection_is_independent_of_the_host_date(self) -> None:
        retained = snapshot_event(index=1, occurred_at=CLOCK - timedelta(days=1))
        previous = {"schemaVersion": 2, "events": [retained], "sources": {}}

        def collect_with_host_date(
            host_date: datetime,
        ) -> tuple[dict[str, Any], dict[str, Any]]:
            with mock.patch("radar.model.datetime") as host_datetime:
                host_datetime.now.return_value = host_date
                return collect_from_fixtures(
                    self.inputs("baseline"),
                    previous_snapshot=previous,
                    now=CLOCK,
                    bootstrap_marketplace=True,
                )

        past_feed, past_snapshot = collect_with_host_date(
            datetime(2000, 1, 1, tzinfo=timezone.utc)
        )
        future_feed, future_snapshot = collect_with_host_date(
            datetime(2100, 1, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(canonical_json_bytes(past_feed), canonical_json_bytes(future_feed))
        self.assertEqual(
            canonical_json_bytes(past_snapshot),
            canonical_json_bytes(future_snapshot),
        )

    def test_failed_source_preserves_snapshot_and_emits_no_mass_change(self) -> None:
        previous = load_snapshot(ROOT / "tests/fixtures/source-snapshot-baseline.json")
        feed, snapshot = collect_from_fixtures(
            self.inputs("next"),
            previous_snapshot=previous,
            now=CLOCK,
            bootstrap_marketplace=False,
            failed_sources={"marketplace": "timeout"},
        )
        self.assertEqual(previous["sources"]["marketplace"], snapshot["sources"]["marketplace"])
        self.assertFalse(any(event["type"].startswith("plugin-") for event in feed["events"]))
        health = next(item for item in feed["sources"] if item["id"] == "marketplace")
        self.assertEqual(("failed", "timeout"), (health["status"], health["reason"]))

    def test_rediscovered_event_keeps_its_first_observed_timestamps(self) -> None:
        previous = load_snapshot(ROOT / "tests/fixtures/source-snapshot-baseline.json")
        first_feed, first_snapshot = collect_from_fixtures(
            self.inputs("next"),
            previous_snapshot=previous,
            now=CLOCK,
            bootstrap_marketplace=False,
        )
        # Model a lagging source baseline paired with the already published
        # event history. Recollection must not make that same event look new.
        lagging = deepcopy(first_snapshot)
        lagging["sources"] = deepcopy(previous["sources"])
        repeated_feed, _ = collect_from_fixtures(
            self.inputs("next"),
            previous_snapshot=lagging,
            now=CLOCK + timedelta(minutes=15),
            bootstrap_marketplace=False,
        )
        first_events = {event["id"]: event for event in first_feed["events"]}
        repeated_events = {event["id"]: event for event in repeated_feed["events"]}
        common_new_ids = set(first_events) - {event["id"] for event in previous["events"]}
        self.assertTrue(common_new_ids)
        for event_id in common_new_ids:
            self.assertEqual(
                (first_events[event_id]["occurredAt"], first_events[event_id]["discoveredAt"]),
                (repeated_events[event_id]["occurredAt"], repeated_events[event_id]["discoveredAt"]),
            )

    def test_production_adapter_paginates_with_bounded_headers(self) -> None:
        release = json.loads((ROOT / "tests/fixtures/releases-next.json").read_text(encoding="utf-8"))[0]
        first_page = []
        for index in range(100):
            item = deepcopy(release)
            item["id"] = 500000000 + index
            item["draft"] = True
            first_page.append(item)
        catalog = (ROOT / "tests/fixtures/catalog-baseline.json").read_bytes()
        engagement = (ROOT / "tests/fixtures/engagement-baseline.json").read_bytes()
        calls: list[tuple[str, dict[str, str]]] = []

        def fixture_fetch(url, *, policy, headers=None):  # type: ignore[no-untyped-def]
            calls.append((url, dict(headers or {})))
            if url == API_URL + "?per_page=100&page=1":
                return canonical_json_bytes(first_page), {}, 200
            if url == API_URL + "?per_page=100&page=2":
                return b"[]", {}, 200
            if url == CATALOG_URL:
                return catalog, {}, 200
            if url == ENGAGEMENT_URL:
                return engagement, {}, 200
            if url == RSS_URL:
                return (ROOT / "tests/fixtures/omarchy-news-baseline.xml").read_bytes(), {}, 200
            raise AssertionError(f"unexpected URL: {url}")

        with mock.patch("radar.collector.fetch_bytes", side_effect=fixture_fetch):
            feed, snapshot = collect_production(
                previous_snapshot=empty_snapshot(),
                community_directory=ROOT / "tests/fixtures/community",
                curation_directory=ROOT / "content/curation",
                now=CLOCK,
                bootstrap_marketplace=True,
                github_token="fixture-token",
            )
        self.assertEqual(
            [
                API_URL + "?per_page=100&page=1",
                API_URL + "?per_page=100&page=2",
                CATALOG_URL,
                ENGAGEMENT_URL,
                RSS_URL,
            ],
            [url for url, _ in calls],
        )
        self.assertEqual("Bearer fixture-token", calls[0][1]["Authorization"])
        self.assertEqual("2022-11-28", calls[0][1]["X-GitHub-Api-Version"])
        self.assertEqual({}, snapshot["sources"]["omarchy-releases"]["releases"])
        self.assertEqual(
            {"community-link", "omarchy-news"},
            {event["type"] for event in feed["events"]},
        )


if __name__ == "__main__":
    unittest.main()
