from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from radar.curation import apply_curation, load_curation
from radar.errors import ValidationError

ROOT = Path(__file__).resolve().parents[2]


class CurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))["events"]

    @staticmethod
    def record(event_id: str, **values: object) -> dict[str, object]:
        return {
            "eventId": event_id,
            "significance": "notable",
            "reviewer": "Fixture reviewer",
            "reviewedAt": "2026-08-31T14:00:00Z",
            **values,
        }

    def test_overlay_changes_only_reviewed_presentation_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "lead.json"
            path.write_text(
                json.dumps(
                    self.record(
                        self.events[0]["id"],
                        lead=True,
                        summary="A reviewed factual summary.",
                        tags=["featured", "system"],
                    )
                ),
                encoding="utf-8",
            )
            overlays = load_curation(Path(temporary))
            curated, lead = apply_curation(self.events, overlays)
        self.assertEqual(self.events[0]["id"], lead)
        self.assertEqual("notable", curated[0]["classification"]["significance"])
        self.assertTrue(curated[0]["classification"]["curated"])
        self.assertEqual("A reviewed factual summary.", curated[0]["summary"])
        self.assertEqual(["featured", "system"], curated[0]["classification"]["tags"])
        self.assertEqual(self.events[0]["source"], curated[0]["source"])
        self.assertEqual(self.events[0]["entity"], curated[0]["entity"])

    def test_unknown_fields_significance_missing_events_and_multiple_leads_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            invalid = self.record(self.events[0]["id"], sourceUrl="https://example.com/replacement")
            (directory / "invalid.json").write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_curation(directory)

        with self.assertRaises(ValidationError):
            apply_curation(self.events, {"evt_000000000000000000000000": self.record("evt_000000000000000000000000")})

        overlays = {
            self.events[0]["id"]: self.record(self.events[0]["id"], lead=True),
            self.events[1]["id"]: self.record(self.events[1]["id"], lead=True),
        }
        with self.assertRaises(ValidationError):
            apply_curation(self.events, overlays)

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "invalid.json").write_text(
                json.dumps(self.record(self.events[0]["id"], significance="routine")),
                encoding="utf-8",
            )
            with self.assertRaises(ValidationError):
                load_curation(directory)


if __name__ == "__main__":
    unittest.main()
