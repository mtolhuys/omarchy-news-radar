from __future__ import annotations

import json
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from radar.collector import FixtureInputs, collect_from_fixtures, collect_production, empty_snapshot, load_snapshot
from radar.io import canonical_json_bytes
from radar.sources.marketplace import CATALOG_URL
from radar.sources.omarchy_releases import API_URL

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class CollectorIntegrationTests(unittest.TestCase):
    def inputs(self, generation: str) -> FixtureInputs:
        return FixtureInputs(
            ROOT / f"tests/fixtures/releases-{generation}.json",
            ROOT / f"tests/fixtures/catalog-{generation}.json",
            ROOT / "content/community",
            ROOT / "content/curation",
        )

    def test_bootstrap_is_silent_for_marketplace_and_second_generation_is_stable(self) -> None:
        baseline_feed, baseline_snapshot = collect_from_fixtures(
            self.inputs("baseline"),
            previous_snapshot=None,
            now=CLOCK,
            bootstrap_marketplace=True,
        )
        self.assertFalse(any(event["type"].startswith("plugin-") for event in baseline_feed["events"]))
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

    def test_production_adapter_paginates_with_bounded_headers(self) -> None:
        release = json.loads((ROOT / "tests/fixtures/releases-next.json").read_text(encoding="utf-8"))[0]
        first_page = []
        for index in range(100):
            item = deepcopy(release)
            item["id"] = 500000000 + index
            item["draft"] = True
            first_page.append(item)
        catalog = (ROOT / "tests/fixtures/catalog-baseline.json").read_bytes()
        calls: list[tuple[str, dict[str, str]]] = []

        def fixture_fetch(url, *, policy, headers=None):  # type: ignore[no-untyped-def]
            calls.append((url, dict(headers or {})))
            if url == API_URL + "?per_page=100&page=1":
                return canonical_json_bytes(first_page), {}, 200
            if url == API_URL + "?per_page=100&page=2":
                return b"[]", {}, 200
            if url == CATALOG_URL:
                return catalog, {}, 200
            raise AssertionError(f"unexpected URL: {url}")

        with mock.patch("radar.collector.fetch_bytes", side_effect=fixture_fetch):
            feed, snapshot = collect_production(
                previous_snapshot=empty_snapshot(),
                community_directory=ROOT / "content/community",
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
            ],
            [url for url, _ in calls],
        )
        self.assertEqual("Bearer fixture-token", calls[0][1]["Authorization"])
        self.assertEqual("2022-11-28", calls[0][1]["X-GitHub-Api-Version"])
        self.assertEqual({}, snapshot["sources"]["omarchy-releases"]["releases"])
        self.assertEqual(["community-link"], [event["type"] for event in feed["events"]])


if __name__ == "__main__":
    unittest.main()
