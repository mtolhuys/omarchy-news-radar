from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from radar.provenance import project_matches_event_source, release_matches_event_source
from radar.site.pages import render_collection, render_story
from tests.unit.test_publisher import PageElements

ROOT = Path(__file__).resolve().parents[2]


class SiteProvenanceTests(unittest.TestCase):
    def setUp(self):
        feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text())
        self.insights = json.loads((ROOT / "tests/fixtures/insights-valid.json").read_text())
        self.event = next(event for event in feed["events"] if event["entity"]["id"] == "io.github.mtolhuys.disk-lens"
                          and event["entity"].get("version") == "0.4.1")
        self.collection = copy.deepcopy(self.insights["collections"][0])
        self.primary = {"label": "Original workflow documentation", "url": "https://example.com/original-workflow"}
        self.collection["source"] = self.primary

    def links(self, page):
        return [link.get("href") for link in PageElements(page).attributes("a")]

    def test_primary_source_remains_visible_without_additional_sources(self):
        for additional in (None, []):
            with self.subTest(additional=additional):
                self.collection.pop("sourceLinks", None)
                if additional is not None:
                    self.collection["sourceLinks"] = additional
                page = render_collection(self.collection, self.insights)
                self.assertEqual(1, self.links(page).count(self.primary["url"]))
                self.assertIn(self.primary["label"].encode(), page)

    def test_additional_links_preserve_primary_label_and_deduplicate_urls(self):
        extra = {"label": "Additional documentation", "url": "https://example.com/additional-workflow"}
        self.collection["sourceLinks"] = [extra, {**self.primary, "label": "A duplicate label"}, extra]
        page = render_collection(self.collection, self.insights)
        links = self.links(page)
        self.assertEqual(1, links.count(self.primary["url"]))
        self.assertEqual(1, links.count(extra["url"]))
        self.assertIn(self.primary["label"].encode(), page)
        self.assertNotIn(b"A duplicate label", page)

    def test_matching_repository_version_still_includes_source_explanation(self):
        page = render_story(self.event, self.insights)
        self.assertIn(b"From the release notes", page)
        self.assertIn(b"Source release notes for 0.4.1", page)

    def test_old_or_missing_repository_does_not_inherit_current_project_notes(self):
        for repository in (None, "https://github.com/previous-owner/disk-lens", "https://github.com/mtolhuys/omarchy-disk-lens-other"):
            with self.subTest(repository=repository):
                event = copy.deepcopy(self.event)
                event["entity"].pop("repository", None)
                if repository:
                    event["entity"]["repository"] = repository
                    event["source"]["url"] = repository + "/releases/tag/0.4.1"
                page = render_story(event, self.insights)
                self.assertNotIn(b"From the release notes", page)
                self.assertIn(event["source"]["url"], self.links(page))

    def test_foreign_release_url_is_not_rendered_as_this_storys_explanation(self):
        self.insights["projects"][0]["releases"][0]["sourceUrl"] = "https://github.com/another-owner/another-project/releases/tag/0.4.1"
        page = render_story(self.event, self.insights)
        self.assertNotIn(b"From the release notes", page)

    def test_provenance_requires_matching_identity_kind_and_public_repository(self):
        project = self.insights["projects"][0]
        release = project["releases"][0]
        self.assertTrue(project_matches_event_source(self.event, project))
        self.assertTrue(release_matches_event_source(self.event, project, release))
        for replacement in ({"id": "another-project"}, {"kind": "omarchy"},
                            {"source": None}, {"source": {}},
                            {"source": {"url": "https://github.com/other/repository"}}):
            with self.subTest(replacement=replacement):
                self.assertFalse(project_matches_event_source(self.event, {**project, **replacement}))
        for repository in ("https://gitlab.com/mtolhuys/omarchy-disk-lens", "https://github.com/mtolhuys",
                           "https://github.com/mtolhuys/../omarchy-disk-lens", "https://github.com/mtolhuys%2fother/omarchy-disk-lens",
                           "https://github.com/mtolhuys/omarchy-disk-lens/../../other/project",
                           "https://github.com/mtolhuys/omarchy-disk-lens/%2e%2e/%2e%2e/other/project",
                           "https://github.com/mtolhuys/omarchy-disk-lens/releases%2Ftag/0.4.1"):
            with self.subTest(repository=repository):
                event = copy.deepcopy(self.event)
                event["entity"]["repository"] = repository
                self.assertFalse(project_matches_event_source(event, project))


if __name__ == "__main__":
    unittest.main()
