from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.errors import ValidationError
from radar.sources.community import community_events
from radar.sources.marketplace import diff_marketplace, parse_marketplace
from radar.sources.omarchy_releases import diff_releases, parse_releases

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class SourceTests(unittest.TestCase):
    def payload(self, name: str):
        return json.loads((ROOT / f"tests/fixtures/{name}").read_text(encoding="utf-8"))

    def test_release_adapter_ignores_drafts_and_strips_markup(self) -> None:
        baseline = parse_releases(self.payload("releases-baseline.json"))
        self.assertEqual(["379400001"], list(baseline))
        self.assertNotIn("#", baseline["379400001"]["summary"])
        current = parse_releases(self.payload("releases-next.json"))
        self.assertNotIn("unsafe-example", current["379486590"]["summary"])

    def test_release_diff_labels_prereleases_and_ignores_unchanged_removed_and_old(self) -> None:
        baseline = parse_releases(self.payload("releases-baseline.json"))
        payload = self.payload("releases-next.json")
        prerelease = copy.deepcopy(payload[0])
        prerelease.update(
            {
                "id": 379486591,
                "tag_name": "v4.1.0-rc1",
                "name": "Omarchy 4.1.0 RC1",
                "html_url": "https://github.com/omacom/omarchy/releases/tag/v4.1.0-rc1",
                "published_at": "2026-08-31T12:00:00Z",
                "prerelease": True,
            }
        )
        old = copy.deepcopy(payload[0])
        old.update(
            {
                "id": 1,
                "tag_name": "v1.0.0",
                "html_url": "https://github.com/omacom/omarchy/releases/tag/v1.0.0",
                "published_at": "2020-01-01T00:00:00Z",
            }
        )
        current = parse_releases([payload[0], prerelease, old])
        events = diff_releases(
            baseline,
            current,
            discovered_at=CLOCK,
            window_from=datetime(2026, 6, 2, 14, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(["Omarchy v4.0.2", "Omarchy v4.1.0-rc1 (prerelease)"], [event["title"] for event in events])
        prior_with_removed = dict(current)
        prior_with_removed.update(baseline)
        self.assertEqual([], diff_releases(prior_with_removed, current, discovered_at=CLOCK, window_from=datetime(2026, 6, 2, 14, 0, tzinfo=timezone.utc)))

    def test_release_adapter_rejects_malformed_duplicate_and_unbounded_pages(self) -> None:
        with self.assertRaises(ValidationError):
            parse_releases({})
        duplicate = self.payload("releases-next.json")
        duplicate.append(copy.deepcopy(duplicate[0]))
        with self.assertRaises(ValidationError):
            parse_releases(duplicate)
        template = self.payload("releases-next.json")[0]
        paginated = []
        for index in range(301):
            item = copy.deepcopy(template)
            item["id"] = 400000000 + index
            paginated.append(item)
        with self.assertRaises(ValidationError):
            parse_releases(paginated)

    def test_marketplace_bootstrap_is_explicit_and_silent(self) -> None:
        current = parse_marketplace(self.payload("catalog-baseline.json"))
        with self.assertRaises(ValidationError):
            diff_marketplace(None, current, discovered_at=CLOCK)
        events, snapshot = diff_marketplace(None, current, discovered_at=CLOCK, bootstrap=True)
        self.assertEqual([], events)
        self.assertEqual(2, len(snapshot["plugins"]))

    def test_supported_marketplace_diffs_and_metadata_noise(self) -> None:
        baseline = parse_marketplace(self.payload("catalog-baseline.json"))
        _, previous = diff_marketplace(None, baseline, discovered_at=CLOCK, bootstrap=True)
        current = parse_marketplace(self.payload("catalog-next.json"))
        events, _ = diff_marketplace(previous, current, discovered_at=CLOCK)
        self.assertEqual(
            ["plugin-added", "plugin-released", "plugin-verification-changed"],
            sorted(item["type"] for item in events),
        )
        noise_payload = self.payload("catalog-baseline.json")
        noise_payload["plugins"][0]["stars"] = 5000
        noise_payload["plugins"][0]["description"] = "Changed wording only."
        noise = parse_marketplace(noise_payload)
        noise_events, _ = diff_marketplace(previous, noise, discovered_at=CLOCK)
        self.assertEqual([], noise_events)

    def test_marketplace_explicit_retirement_multi_plugin_repo_and_schema_checks(self) -> None:
        baseline_payload = self.payload("catalog-baseline.json")
        second = copy.deepcopy(baseline_payload[0] if isinstance(baseline_payload, list) else baseline_payload["plugins"][0])
        second["id"] = "org.example.second"
        second["name"] = "Second"
        baseline_payload["plugins"].append(second)
        baseline = parse_marketplace(baseline_payload)
        _, previous = diff_marketplace(None, baseline, discovered_at=CLOCK, bootstrap=True)
        retired_payload = copy.deepcopy(baseline_payload)
        retired_payload["plugins"][0]["retired"] = True
        retired = parse_marketplace(retired_payload)
        events, _ = diff_marketplace(previous, retired, discovered_at=CLOCK)
        self.assertEqual(["plugin-retired"], [event["type"] for event in events])
        self.assertEqual(3, len(retired["plugins"]))
        invalid = self.payload("catalog-baseline.json")
        invalid["stateSchemaVersion"] = 99
        invalid["warnings"] = ["untrusted warning"]
        with self.assertRaises(ValidationError):
            parse_marketplace(invalid)

    def test_retirement_requires_two_complete_absences_and_reappearance_recovers(self) -> None:
        baseline = parse_marketplace(self.payload("catalog-baseline.json"))
        _, previous = diff_marketplace(None, baseline, discovered_at=CLOCK, bootstrap=True)
        missing_payload = self.payload("catalog-baseline.json")
        missing_payload["plugins"] = missing_payload["plugins"][:1]
        missing = parse_marketplace(missing_payload)
        first_events, first = diff_marketplace(previous, missing, discovered_at=CLOCK)
        self.assertEqual([], first_events)
        second_events, second = diff_marketplace(first, missing, discovered_at=CLOCK)
        self.assertEqual(["plugin-retired"], [item["type"] for item in second_events])
        restored_events, restored = diff_marketplace(second, baseline, discovered_at=CLOCK)
        self.assertFalse(restored["plugins"]["org.example.focus"]["retired"])
        self.assertEqual([], restored_events)

    def test_community_records_are_reviewed_bounded_json(self) -> None:
        events = community_events(ROOT / "content/community", discovered_at=CLOCK)
        self.assertEqual(["community-link"], [event["type"] for event in events])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "future.json"
            record = {
                "id": "future",
                "publishedAt": "2027-01-01T00:00:00Z",
                "title": "Future",
                "summary": "Future record.",
                "sourceUrl": "https://example.com/future",
                "author": "Example",
                "tags": ["guide"],
            }
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(ValidationError):
                community_events(Path(temporary), discovered_at=CLOCK)

    def test_community_rejects_invalid_records_and_strips_copied_markup(self) -> None:
        base = {
            "id": "reviewed",
            "publishedAt": "2026-08-30T10:00:00Z",
            "title": "**A reviewed guide**",
            "summary": "<b>Original</b> [workflow](https://example.com/copy) with `commands`.",
            "sourceUrl": "https://example.com/original",
            "author": "Example",
            "tags": ["guide"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / "record.json"
            path.write_text(json.dumps(base), encoding="utf-8")
            event = community_events(directory, discovered_at=CLOCK)[0]
            self.assertEqual("A reviewed guide", event["title"])
            self.assertEqual("Original workflow with commands.", event["summary"])

            invalid_records = {
                "unsafe-url": {**base, "sourceUrl": "http://example.com/source"},
                "overlong": {**base, "title": "x" * 161},
                "unknown-tag": {**base, "tags": ["unknown tag"]},
                "significance": {**base, "significance": "viral"},
            }
            for name, record in invalid_records.items():
                with self.subTest(name=name):
                    path.write_text(json.dumps(record), encoding="utf-8")
                    with self.assertRaises(ValidationError):
                        community_events(directory, discovered_at=CLOCK)

            path.write_text(json.dumps(base), encoding="utf-8")
            duplicate = dict(base)
            (directory / "second.json").write_text(json.dumps(duplicate), encoding="utf-8")
            with self.assertRaises(ValidationError):
                community_events(directory, discovered_at=CLOCK)


if __name__ == "__main__":
    unittest.main()
