from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urljoin, urlsplit

from radar.errors import FetchError, ValidationError
from radar.insights_builder import build_insights, load_collections
from radar.io import canonical_json_bytes
from radar.publication_images import materialize_insight_images
from radar.publisher import publish
from radar.site.common import paragraphs
from radar.sources.release_notes import parse_release_notes
from tests.unit.test_publisher import PageElements

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


class InsightsPublicationTests(unittest.TestCase):
    def setUp(self):
        self.feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text())
        self.insights = json.loads((ROOT / "tests/fixtures/insights-valid.json").read_text())
        self.snapshot = {"schemaVersion": 2, "events": [], "sources": {"marketplace": {"plugins": {
            "io.github.mtolhuys.news-radar": {"name": "Radar", "description": "Source-linked news",
                "repository": "https://github.com/mtolhuys/omarchy-news-radar", "retired": False}
        }}}}

    def build(self, **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            return build_insights(self.snapshot, published_at=CLOCK, content_directory=Path(directory), **kwargs)

    def test_release_explanations_strip_active_markup_without_following_links(self):
        payload = [{"tag_name": "v1.2.3", "published_at": "2026-09-01T00:00:00Z", "name": "Release",
                    "html_url": "https://github.com/example/plugin/releases/tag/v1.2.3",
                    "body": "# Changes\n\n- Added [search](https://example.com).\n- Faster startup.\n\n```sh\necho injected\n```\n<img src=x onerror=alert(1)>"}]
        result = parse_release_notes(payload, "example/plugin")
        self.assertEqual(["Added search.", "Faster startup."], [change["text"] for change in result[0]["changes"]])
        self.assertNotIn("echo injected", result[0]["summary"])
        self.assertNotIn("<img", result[0]["summary"])
        self.assertTrue(all(item["sourceUrl"] == payload[0]["html_url"] for item in result[0]["changes"]))
        for foreign in ["https://github.com/other/plugin/releases/tag/v1.2.3", "https://github.com/example/plugin/releases/tag/v8.0.0"]:
            with self.assertRaises(ValidationError):
                parse_release_notes([{**payload[0], "html_url": foreign}], "example/plugin")

    def test_drafts_and_prereleases_do_not_masquerade_as_stable_updates(self):
        self.assertEqual([], parse_release_notes([{"draft": True}, {"prerelease": True}], "example/plugin"))
        with self.assertRaises(ValidationError):
            parse_release_notes([{}] * 31, "example/plugin")
        with self.assertRaises(ValidationError):
            parse_release_notes([{"draft": "false"}], "example/plugin")

    def test_code_examples_never_become_release_changes(self):
        examples = [
            "~~~yaml\n- EXAMPLE_ONLY\n~~~\n- After the example.",
            "````yaml\n```\n- EXAMPLE_ONLY\n````\n- After the example.",
            "    - EXAMPLE_ONLY\n\n- After the example.",
            "\t- EXAMPLE_ONLY\n\n- After the example.",
            "   ~~~yaml\n- EXAMPLE_ONLY\n   ~~~~\n- After the example.",
            "~~~yaml\n- EXAMPLE_ONLY",
            "```yaml\n- EXAMPLE_ONLY",
        ]
        for example in examples:
            with self.subTest(example=example):
                raw = {"tag_name": "v1.0.0", "published_at": "2026-09-01T00:00:00Z", "name": "Release",
                       "html_url": "https://github.com/example/plugin/releases/tag/v1.0.0",
                       "body": "- A real documented change.\n\n" + example}
                result = parse_release_notes([raw], "example/plugin")[0]
                expected = ["A real documented change."]
                if "After the example." in example:
                    expected.append("After the example.")
                self.assertEqual(expected, [item["text"] for item in result["changes"]])
                self.assertNotIn("EXAMPLE_ONLY", result["summary"])

    def test_offline_build_is_deterministic_and_does_not_invent_catalog_release_dates(self):
        with patch("radar.insights_builder.fetch_release_notes") as fetch:
            first, second = self.build(), self.build()
        fetch.assert_not_called()
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        radar = next(item for item in first["projects"] if item["id"] == "io.github.mtolhuys.news-radar")
        self.assertEqual([], radar["releases"])
        self.assertEqual("github:mtolhuys", radar["creatorId"])

    def test_fetch_failure_retains_known_notes_and_successful_empty_index_replaces_them(self):
        previous = self.build()
        radar = next(item for item in previous["projects"] if item["id"] == "io.github.mtolhuys.news-radar")
        radar["releases"] = [{"version": "0.4.16", "publishedAt": "2026-09-01T00:00:00Z", "title": "Radar 0.4.16",
                              "summary": "An original source explanation", "changes": [],
                              "sourceUrl": "https://github.com/mtolhuys/omarchy-news-radar/releases/tag/v0.4.16"}]
        with patch("radar.insights_builder.fetch_release_notes", side_effect=FetchError("timeout", "timeout")):
            failed = self.build(fetch_releases=True, previous_insights=previous)
        self.assertEqual(radar["releases"], failed["projects"][1]["releases"])
        with patch("radar.insights_builder.fetch_release_notes", return_value=[]):
            success = self.build(fetch_releases=True, previous_insights=previous)
        self.assertEqual([], success["projects"][1]["releases"])

    def test_changed_repository_never_inherits_or_fetches_old_owners_notes(self):
        self.snapshot["sources"]["marketplace"]["plugins"]["io.github.mtolhuys.news-radar"]["repository"] = "https://github.com/unreviewed/replacement"
        with patch("radar.insights_builder.fetch_release_notes", return_value=[]) as fetch:
            self.build(fetch_releases=True)
        self.assertEqual(["omacom/omarchy"], [call.args[0] for call in fetch.call_args_list])

    def test_fresh_core_release_survives_optional_notes_failure_with_older_sidecar(self):
        old = self.build()
        old["projects"][0]["releases"] = [{"version": "4.0.0", "publishedAt": "2026-09-01T00:00:00Z", "title": "Old release",
            "summary": "Known prior fact", "changes": [], "sourceUrl": "https://github.com/omacom/omarchy/releases/tag/4.0.0"}]
        self.snapshot["sources"]["omarchy-releases"] = {"releases": {"1": {"tag": "4.0.1", "title": "New release",
            "publishedAt": "2026-09-04T00:00:00Z", "summary": "Fresh collected fact",
            "url": "https://github.com/omacom/omarchy/releases/tag/4.0.1", "prerelease": False}}}
        with patch("radar.insights_builder.fetch_release_notes", side_effect=FetchError("timeout", "timeout")):
            current = self.build(fetch_releases=True, previous_insights=old)
        self.assertEqual(["4.0.1", "4.0.0"], [item["version"] for item in current["projects"][0]["releases"]])
        self.assertEqual("Fresh collected fact", current["projects"][0]["releases"][0]["summary"])

    def test_same_release_keeps_rich_notes_when_optional_fetch_fails_but_uses_fresh_metadata(self):
        old = self.build()
        source = "https://github.com/omacom/omarchy/releases/tag/4.0.0"
        previous = {"version": "4.0.0", "publishedAt": "2026-09-01T00:00:00Z", "title": "Original title",
                    "summary": "Previously fetched complete release explanation, including source context.",
                    "changes": [{"text": "A documented improvement.", "sourceUrl": source}], "sourceUrl": source}
        old["projects"][0]["releases"] = [previous]
        fresh = {"tag": "4.0.0", "title": "Corrected source title", "publishedAt": "2026-09-02T00:00:00Z",
                 "summary": "Brief collected summary.", "url": source, "prerelease": False}
        self.snapshot["sources"]["omarchy-releases"] = {"releases": {"1": fresh}}
        with patch("radar.insights_builder.fetch_release_notes", side_effect=FetchError("timeout", "timeout")):
            current = self.build(fetch_releases=True, previous_insights=old)
        release = current["projects"][0]["releases"][0]
        self.assertEqual(previous["summary"], release["summary"])
        self.assertEqual(previous["changes"], release["changes"])
        self.assertEqual(fresh["title"], release["title"])
        self.assertEqual(fresh["publishedAt"], release["publishedAt"])
        self.assertEqual(source, release["sourceUrl"])
        # Matching version text cannot transfer facts across a different source.
        fresh["url"] = "https://github.com/omacom/omarchy/releases/tag/v4.0.0"
        with patch("radar.insights_builder.fetch_release_notes", side_effect=FetchError("timeout", "timeout")):
            changed_source = self.build(fetch_releases=True, previous_insights=old)
        release = changed_source["projects"][0]["releases"][0]
        self.assertEqual(fresh["summary"], release["summary"])
        self.assertEqual([], release["changes"])
        self.assertEqual(fresh["url"], release["sourceUrl"])

    def test_invalid_record_fails_even_when_its_projects_are_unavailable(self):
        record = copy.deepcopy(self.insights["collections"][0])
        record["arbitrary"] = "unknown field"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            (path / "discovery.json").write_text(json.dumps(record))
            with self.assertRaises(ValidationError):
                build_insights(self.snapshot, published_at=CLOCK, content_directory=path)

    def test_production_uses_current_event_projects_without_authored_collections(self):
        catalog = self.snapshot["sources"]["marketplace"]["plugins"]
        template = copy.deepcopy(next(iter(catalog.values())))
        for number in range(110):
            catalog[f"org.example.project{number}"] = {**template, "name": f"Project {number}"}
        event = copy.deepcopy(self.feed["events"][0])
        event["entity"]["id"] = "org.example.project109"
        self.snapshot["events"] = [event]
        insights = build_insights(self.snapshot, published_at=CLOCK)
        self.assertEqual(100, len(insights["projects"]))
        self.assertEqual("org.example.project109", insights["projects"][1]["id"])
        self.assertEqual([], insights["collections"])

    def test_bad_discovery_image_is_omitted_without_losing_explanations(self):
        insight = copy.deepcopy(self.insights)
        insight["projects"][0]["image"] = {"sourceUrl": "https://plugins.omarchy.org/assets/img/plugins/test.png",
            "width": 1, "height": 1, "alt": "Preview", "credit": "Marketplace"}
        output, failures = materialize_insight_images(insight, image_fetcher=lambda url: (b"<svg/>", "image/svg+xml"))
        self.assertNotIn("image", output["projects"][0])
        self.assertEqual(insight["projects"][0]["releases"], output["projects"][0]["releases"])
        self.assertEqual(1, len(failures))

    def test_static_page_ids_are_stable_escaped_and_all_internal_links_resolve(self):
        insight = copy.deepcopy(self.insights)
        insight["collections"][0]["title"] = '<script>alert("remote")</script>'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "site"
            result = publish(self.feed, root, insights=insight, published_at=CLOCK)
            for event in self.feed["events"]:
                self.assertTrue((root / "stories" / event["id"] / "index.html").is_file())
            self.assertTrue((root / "editions/2026-W36/index.html").is_file())
            self.assertTrue((root / "discover/inspect-disk-space/index.html").is_file())
            for file in root.rglob("*.html"):
                page = PageElements(file.read_bytes())
                self.assertNotIn("script", [tag for tag, _ in page.elements])
                for attrs in page.attributes("a") + page.attributes("link"):
                    href = attrs.get("href") or ""
                    if href.startswith("https:"):
                        continue
                    parsed = urlsplit(urljoin("https://preview/" + file.relative_to(root).as_posix(), href))
                    target = root / parsed.path.lstrip("/")
                    if parsed.path.endswith("/"):
                        target /= "index.html"
                    self.assertTrue(target.is_file(), str(target))
            repeated = publish(self.feed, root, insights=insight, published_at=CLOCK)
            self.assertEqual(result, repeated)

    def test_failed_sidecar_cannot_replace_the_previous_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "site"
            publish(self.feed, root, insights=self.insights, published_at=CLOCK)
            before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            with self.assertRaises(ValidationError):
                publish(self.feed, root, insights={**self.insights, "schemaVersion": 42}, published_at=CLOCK)
            after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            self.assertEqual(before, after)

    def test_article_links_are_usable_without_rendering_remote_markup(self):
        rendered = paragraphs('Read [A <guide>](https://example.com/guide?a=1&b=2).\n\n<script>bad()</script> [run](javascript:bad())')
        page = PageElements(rendered.encode())
        self.assertEqual(["https://example.com/guide?a=1&b=2"], [item["href"] for item in page.attributes("a")])
        self.assertIn("A &lt;guide&gt;", rendered)
        self.assertNotIn("script", [tag for tag, _ in page.elements])
        self.assertIn("[run](javascript:bad())", rendered)
