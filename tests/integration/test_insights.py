from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from radar.client import ensure_briefing, indicator_model, projection_model, set_event_read_state, toggle_saved_state
from radar.client_insights import insights_model, load_insights, refresh_insights, set_relevance
from radar.client_setup import installed_plugins, parse_installed_facts
from radar.constants import INSIGHTS_URL, STATE_SCHEMA_VERSION
from radar.errors import FetchError, ValidationError
from radar.insights import compare_versions, matching_release, project_version, validate_insights
from radar.io import atomic_write_json
from radar.relevance import default_relevance
from radar.state import cache_root, default_state, load_state, save_feed, save_state, user_state_path

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)
PLUGIN = "io.github.mtolhuys.disk-lens"


class InsightsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.environment = {"HOME": str(base / "home"), "XDG_CACHE_HOME": str(base / "cache"), "XDG_STATE_HOME": str(base / "state")}
        self.insights = json.loads((ROOT / "tests/fixtures/insights-valid.json").read_text())
        self.feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text())
        save_feed(self.feed, self.environment, now=CLOCK)
        self.facts = json.dumps([{"id": PLUGIN, "version": "0.3.0"}])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def store_insights(self) -> None:
        atomic_write_json(cache_root(self.environment) / "insights.json", self.insights)

    def project(self, section: str = "front-page") -> dict:
        return projection_model(section, json.dumps([PLUGIN]), "", self.environment, now=CLOCK, installed_facts_json=self.facts)

    def test_semver_precedence_is_strict_and_build_metadata_is_not_an_update(self) -> None:
        for a, b, expected in [("1.9.0", "1.10.0", -1), ("v1.0.0", "1.0.0", 0),
                               ("1.0.0-alpha.9", "1.0.0-alpha.10", -1), ("1.0.0-rc.1", "1.0.0", -1),
                               ("1.0.0+abc", "1.0.0+def", 0), ("dev", "dev", 0),
                               ("1.0", "1.1", None), ("01.0.0", "1.0.0", None),
                               ("1.0.0-alpha.01", "1.0.0", None), (None, "1.0.0", None)]:
            with self.subTest(a=a, b=b):
                self.assertEqual(expected, compare_versions(a, b))

    def test_release_identity_accepts_v_prefix_but_not_build_metadata_or_ambiguous_tags(self) -> None:
        release = {"version": "v1.0.0+one"}
        self.assertIs(release, matching_release([release], "1.0.0+one"))
        self.assertIsNone(matching_release([release], "1.0.0+two"))
        self.assertIsNone(matching_release([release, {"version": "1.0.0+one"}], "1.0.0+one"))
        self.assertIsNone(matching_release([{"version": "vrolling"}], "rolling"))

    def test_version_journey_contains_only_provably_newer_documented_releases(self) -> None:
        project = self.insights["projects"][0]
        row = project_version(project, "0.4.0", installed=True)
        self.assertEqual("behind", row["comparisonState"])
        self.assertEqual(["0.4.1"], [item["version"] for item in row["newerReleases"]])
        project["releases"][0]["version"] = "rolling"
        row = project_version(project, "rolling", installed=True)
        self.assertEqual("unknown", row["comparisonState"])
        self.assertEqual([], row["newerReleases"])

    def test_validation_rejects_malformed_references_urls_counts_and_future_time(self) -> None:
        cases = []
        bad = copy.deepcopy(self.insights); bad["collections"][0]["projectIds"] = ["unknown"]; cases.append(bad)
        bad = copy.deepcopy(self.insights); bad["collections"][0]["shareUrl"] = "https://example.com/share"; cases.append(bad)
        bad = copy.deepcopy(self.insights); bad["projects"][0]["releases"][0]["changes"][0]["sourceUrl"] = "file:///etc/passwd"; cases.append(bad)
        bad = copy.deepcopy(self.insights); bad["projects"] *= 60; cases.append(bad)
        bad = copy.deepcopy(self.insights); bad["publishedAt"] = "2027-08-31T14:00:00Z"; cases.append(bad)
        bad = copy.deepcopy(self.insights); bad["collections"][0]["tracking"] = "bad"; cases.append(bad)
        bad = copy.deepcopy(self.insights); bad["projects"][0]["kind"] = []; cases.append(bad)
        bad = copy.deepcopy(self.insights); bad["projects"][0]["source"]["url"] = "https://example.com:invalid/"; cases.append(bad)
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_insights(value, now=CLOCK)

    def test_collection_slugs_match_the_public_single_hyphen_route_and_length_bound(self) -> None:
        schema = json.loads((ROOT / "schemas/insights-v1.schema.json").read_text())
        properties = schema["$defs"]["collection"]["properties"]
        for identity, valid in [("a", True), ("one-two-3", True), ("a" * 80, True),
                                ("trailing-", False), ("two--parts", False), ("-leading", False),
                                ("Upper", False), ("a" * 81, False)]:
            with self.subTest(identity=identity):
                value = copy.deepcopy(self.insights)
                collection = value["collections"][0]
                collection["id"] = identity
                collection["shareUrl"] = f"https://mtolhuijs.nl/news-radar/discover/{identity}/"
                for field in ("id", "shareUrl"):
                    self.assertEqual(valid, re.fullmatch(properties[field]["pattern"], collection[field]) is not None)
                if valid:
                    self.assertEqual(identity, validate_insights(value, now=CLOCK)["collections"][0]["id"])
                else:
                    with self.assertRaises(ValidationError):
                        validate_insights(value, now=CLOCK)

    def test_insights_survive_feed_clock_and_membership_churn_and_completed_brief(self) -> None:
        self.store_insights()
        state = default_state(); state["briefing"] = {"generatedAt": self.feed["generatedAt"], "groups": []}
        save_state(state, self.environment)
        before = self.project()
        self.assertTrue(before["briefing"]["complete"])
        self.assertEqual(1, len(before["home"]["featuredCollections"]))
        newer = copy.deepcopy(self.feed); newer["events"] = []; newer["generatedAt"] = "2026-08-31T14:01:00Z"; newer["window"]["through"] = newer["generatedAt"]
        save_feed(newer, self.environment, now=CLOCK + timedelta(minutes=1))
        after = self.project()
        self.assertEqual(before["home"], after["home"])
        self.assertEqual("behind", after["mySetup"][0]["comparisonState"])

    def test_missing_or_corrupt_insights_keep_news_and_explicit_unknown_setup(self) -> None:
        for raw in (None, {"schemaVersion": 900}):
            if raw:
                atomic_write_json(cache_root(self.environment) / "insights.json", raw)
            result = self.project("plugins")
            self.assertTrue(result["events"])
            self.assertEqual("missing", result["insights"]["status"])
            self.assertEqual("unknown", result["mySetup"][0]["comparisonState"])
            self.assertFalse(result["mySetup"][0]["coverageAvailable"])

    def test_event_release_explanation_is_bound_to_its_exact_version(self) -> None:
        self.store_insights()
        item = next(event for event in self.project("plugins")["events"] if event["entity"]["id"] == PLUGIN)
        self.assertEqual("0.4.1", item["releaseInsight"]["version"])
        self.assertEqual("0.3.0", item["projectInsight"]["installedVersion"])
        self.feed["events"][0]["entity"]["version"] = "uncovered"
        save_feed(self.feed, self.environment, now=CLOCK)
        item = next(event for event in self.project("plugins")["events"] if event["id"] == self.feed["events"][0]["id"])
        self.assertIsNone(item["releaseInsight"])

    def test_story_only_search_retains_source_explanations_and_full_project_detail(self) -> None:
        self.store_insights()
        result = projection_model("plugins", json.dumps([PLUGIN]), "treemap", self.environment,
                                  now=CLOCK, installed_facts_json=self.facts)
        self.assertEqual([], result["insights"]["projects"])
        self.assertEqual([], result["mySetup"])
        event = next(item for item in result["events"] if item["entity"].get("version") == "0.4.1")
        self.assertEqual(PLUGIN, event["projectInsight"]["id"])
        self.assertEqual("0.4.1", event["releaseInsight"]["version"])
        detail = next(item for item in result["insights"]["projectDetails"] if item["id"] == PLUGIN)
        self.assertEqual(self.insights["projects"][0]["releases"], detail["releases"])
        self.assertEqual("0.3.0", detail["installedVersion"])

    def test_collection_only_search_retains_full_member_details(self) -> None:
        self.store_insights()
        result = insights_model(self.facts, self.environment, now=CLOCK, query="useful")
        self.assertEqual([], result["insights"]["projects"])
        self.assertEqual(1, len(result["home"]["featuredCollections"]))
        member = result["home"]["featuredCollections"][0]["projects"][0]
        self.assertNotIn("releases", member)
        detail = next(item for item in result["insights"]["projectDetails"] if item["id"] == member["id"])
        self.assertEqual(self.insights["projects"][0]["releases"], detail["releases"])

    def test_historical_story_never_inherits_new_repository_notes_or_creator_targets(self) -> None:
        project = self.insights["projects"][0]
        project["source"]["url"] = "https://github.com/new-owner/new-project"
        project["creatorId"] = "github:new-owner"
        for release in project["releases"]:
            release["sourceUrl"] = f"https://github.com/new-owner/new-project/releases/tag/{release['version']}"
            for change in release["changes"]:
                change["sourceUrl"] = release["sourceUrl"]
        self.store_insights()
        result = self.project("plugins")
        row = next(item for item in result["events"] if item["entity"]["id"] == PLUGIN)
        self.assertIsNone(row["projectInsight"])
        self.assertIsNone(row["releaseInsight"])
        self.assertEqual(["github:mtolhuys"], [target["id"] for target in row["relevanceTargets"] if target["kind"] == "creator"])
        # The current project remains available separately as current coverage.
        detail = next(item for item in result["insights"]["projectDetails"] if item["id"] == PLUGIN)
        self.assertEqual(project["source"], detail["source"])

    def test_matching_project_does_not_attach_a_foreign_repository_release(self) -> None:
        release = self.insights["projects"][0]["releases"][0]
        release["sourceUrl"] = "https://github.com/unrelated/project/releases/tag/0.4.1"
        for change in release["changes"]:
            change["sourceUrl"] = release["sourceUrl"]
        self.store_insights()
        result = self.project("plugins")
        row = next(item for item in result["events"] if item["entity"].get("version") == "0.4.1")
        self.assertIsNotNone(row["projectInsight"])
        self.assertIsNone(row["releaseInsight"])

    def test_muted_saved_and_briefing_details_keep_sources_and_respect_image_preferences(self) -> None:
        self.insights["projects"][0]["image"] = {"sourceUrl": "https://plugins.omarchy.org/assets/img/plugins/example.png",
            "alt": "Project preview", "credit": "Marketplace", "width": 100, "height": 100}
        self.store_insights()
        ensure_briefing(json.dumps([PLUGIN]), self.environment, now=CLOCK)
        event = next(item for item in self.feed["events"] if item["entity"].get("version") == "0.4.1")
        toggle_saved_state(event["id"], self.environment, now=CLOCK)
        set_relevance("plugin", PLUGIN, "mute", self.environment)
        state = load_state(self.environment)[0]
        state["preferences"]["imagesVisible"] = False
        save_state(state, self.environment)
        for section in ("saved", "front-page"):
            with self.subTest(section=section):
                result = self.project(section)
                detail = next(item for item in result["insights"]["projectDetails"] if item["id"] == PLUGIN)
                self.assertTrue(detail["muted"])
                self.assertEqual("", detail["imageUrl"])
                self.assertEqual(self.insights["projects"][0]["source"], detail["source"])
                self.assertEqual(self.insights["projects"][0]["releases"], detail["releases"])
                row = next(item for item in result["events"] if item["entity"]["id"] == PLUGIN)
                self.assertEqual(PLUGIN, row["projectInsight"]["id"])
                self.assertTrue(all(item["id"] != PLUGIN for item in result["insights"]["projects"]))

    def test_mute_preserves_current_snapshot_saved_and_all_reading_facts(self) -> None:
        self.store_insights()
        ensure_briefing(json.dumps([PLUGIN]), self.environment, now=CLOCK)
        event = next(item for item in self.feed["events"] if item["entity"]["id"] == PLUGIN)
        toggle_saved_state(event["id"], self.environment, now=CLOCK)
        before = load_state(self.environment)[0]
        set_relevance("plugin", PLUGIN, "mute", self.environment)
        after = load_state(self.environment)[0]
        for field in ("briefing", "saved", "readOverrides", "readThrough"):
            self.assertEqual(before[field], after[field])
        self.assertFalse(any(item["entity"]["id"] == PLUGIN for item in self.project("plugins")["events"]))
        self.assertTrue(any(item["entity"]["id"] == PLUGIN for item in self.project()["events"]))
        self.assertTrue(any(item["id"] == event["id"] for item in self.project("saved")["events"]))
        self.assertEqual([], self.project()["home"]["featuredCollections"])
        ensure_briefing(json.dumps([PLUGIN]), self.environment, now=CLOCK, replace=True)
        self.assertFalse(any(item["entity"]["id"] == PLUGIN for item in self.project()["events"]))

    def test_follow_creator_and_source_relevance_can_be_cleared_without_reads(self) -> None:
        before = load_state(self.environment)[0]["readOverrides"]
        set_relevance("creator", "github:example", "follow", self.environment)
        result = projection_model("for-you", "[]", "", self.environment, now=CLOCK)
        self.assertTrue(any(item["entity"]["id"] == "org.example.notes" for item in result["events"]))
        self.assertEqual("github:example", result["relevanceControls"][0]["id"])
        set_relevance("creator", "github:example", "clear", self.environment)
        set_relevance("source", "omarchy-news", "follow", self.environment)
        result = projection_model("for-you", "[]", "", self.environment, now=CLOCK)
        self.assertEqual([], result["events"])
        self.assertEqual(["omarchy-news"], result["state"]["relevance"]["followedSources"])
        self.assertEqual(before, result["state"]["readOverrides"])

    def test_legacy_marketplace_follow_does_not_duplicate_plugins_in_personal_news(self) -> None:
        set_relevance("source", "marketplace", "follow", self.environment)
        before = load_state(self.environment)[0]
        empty = projection_model("for-you", "[]", "", self.environment, now=CLOCK)
        self.assertEqual([], empty["events"])
        personal = self.project("for-you")
        self.assertTrue(personal["events"])
        self.assertTrue(all(event["entity"]["id"] == PLUGIN for event in personal["events"]))
        self.assertGreater(self.project("plugins")["totalEvents"], personal["totalEvents"])
        self.assertEqual(before, load_state(self.environment)[0])
        set_relevance("plugin", "org.example.notes", "follow", self.environment)
        self.assertTrue(any(event["entity"]["id"] == "org.example.notes"
                            for event in self.project("for-you")["events"]))
        set_relevance("source", "marketplace", "mute", self.environment)
        self.assertEqual([], self.project("for-you")["events"])

    def test_unread_badge_and_hidden_read_feedback_survive_filter_toggle(self) -> None:
        rows = self.project("plugins")["events"]
        self.assertGreater(len(rows), 1)
        set_event_read_state(rows[0]["id"], True, self.environment, now=CLOCK)
        all_rows = self.project("plugins")
        self.assertEqual(0, all_rows["hiddenReadCount"])
        state = load_state(self.environment)[0]
        state["preferences"]["sectionFilters"]["plugins"]["unreadOnly"] = True
        save_state(state, self.environment)
        unread = self.project("plugins")
        self.assertEqual(all_rows["unreadCounts"], unread["unreadCounts"])
        self.assertEqual(1, unread["hiddenReadCount"])
        self.assertEqual(all_rows["totalEvents"] - 1, unread["totalEvents"])
        retained = projection_model("plugins", json.dumps([PLUGIN]), "", self.environment,
                                    now=CLOCK, retained_read_ids_json=json.dumps([rows[0]["id"]]))
        self.assertEqual(0, retained["hiddenReadCount"])
        self.assertEqual(1, retained["retainedReadCount"])
        self.assertEqual(all_rows["unreadCounts"], retained["unreadCounts"])

    def test_mute_indicator_and_projection_share_same_unread_scope(self) -> None:
        set_relevance("source", "marketplace", "mute", self.environment)
        union = set()
        for section in ("front-page", "for-you", "core", "plugins", "youtube", "saved"):
            union.update(item["id"] for item in self.project(section)["events"] if item["isUnread"])
        result = indicator_model(self.environment, now=CLOCK, installed_json=json.dumps([PLUGIN]))
        self.assertEqual(len(union), result["unread"])

    def test_relevance_mutation_and_reading_preserve_each_others_state(self) -> None:
        set_relevance("plugin", PLUGIN, "follow", self.environment)
        event = self.feed["events"][0]
        set_event_read_state(event["id"], True, self.environment, now=CLOCK)
        set_relevance("plugin", PLUGIN, "mute", self.environment)
        state = load_state(self.environment)[0]
        self.assertEqual([], state["relevance"]["followedPlugins"])
        self.assertEqual([PLUGIN], state["relevance"]["mutedPlugins"])
        self.assertIs(True, state["readOverrides"][event["id"]])
        with self.assertRaises(ValidationError):
            set_relevance("source", "arbitrary.example", "follow", self.environment)

    def test_v12_migration_retains_snapshot_onboarding_and_every_supported_fact(self) -> None:
        ensure_briefing(json.dumps([PLUGIN]), self.environment, now=CLOCK)
        original = load_state(self.environment)[0]
        legacy = copy.deepcopy(original); legacy.pop("relevance"); legacy["schemaVersion"] = 12
        atomic_write_json(user_state_path(self.environment), legacy)
        migrated, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertEqual(STATE_SCHEMA_VERSION, migrated["schemaVersion"])
        self.assertEqual(default_relevance(), migrated["relevance"])
        for key in legacy.keys() - {"schemaVersion"}:
            self.assertEqual(legacy[key], migrated[key])

    def test_manifest_facts_are_data_only_matching_owned_regular_files(self) -> None:
        directory = Path(self.environment["HOME"]) / ".config/omarchy/plugins" / PLUGIN
        directory.mkdir(parents=True)
        manifest = directory / "manifest.json"
        manifest.write_text(json.dumps({"id": PLUGIN, "name": "My Disk Lens", "version": "0.3.0",
                                        "description": "See what is using your disk.", "hook": "never executed"}))
        result = mock.Mock(returncode=0, stdout=json.dumps([{"id": PLUGIN, "name": "Disk Lens", "enabled": True}]))
        with mock.patch("radar.client_setup.subprocess.run", return_value=result) as run:
            facts = installed_plugins(self.environment)
            self.assertEqual([{"id": PLUGIN, "name": "My Disk Lens", "version": "0.3.0",
                               "description": "See what is using your disk."}], facts["plugins"])
            self.assertEqual(1, run.call_count)
            target = directory / "other.json"; manifest.rename(target); manifest.symlink_to(target)
            fallback = installed_plugins(self.environment)["plugins"][0]
            self.assertIsNone(fallback["version"])
            self.assertEqual("Disk Lens", fallback["name"])
        with self.assertRaises(ValidationError):
            parse_installed_facts('[{"id":"../../escape","version":"1.0.0"}]')

    def test_optional_local_names_are_bounded_and_old_facts_remain_valid(self) -> None:
        self.assertEqual([{"id": PLUGIN, "version": "0.3.0"}], parse_installed_facts(self.facts))
        for field in ({"name": "x" * 121}, {"name": "Two\nLines"}, {"name": None},
                      {"description": "x" * 601}, {"description": "Two\nLines"}, {"description": None},
                      {"firstParty": "true"}, {"path": "/private/plugin"}):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                parse_installed_facts(json.dumps([{"id": PLUGIN, "version": None, **field}]))
        named = json.dumps([{"id": PLUGIN, "version": "0.3.0", "name": "My Disk Lens"}])
        result = projection_model("for-you", json.dumps([PLUGIN]), "", self.environment,
                                  now=CLOCK, installed_facts_json=named)
        self.assertEqual("My Disk Lens", result["mySetup"][0]["name"])
        described = json.dumps([{"id": PLUGIN, "version": "0.3.0", "name": "My Disk Lens",
                                 "description": "See what is using your disk."}])
        result = projection_model("for-you", json.dumps([PLUGIN]), "", self.environment,
                                  now=CLOCK, installed_facts_json=described)
        self.assertEqual("See what is using your disk.", result["mySetup"][0]["description"])
        self.assertEqual("Enabled · 0.3.0", result["mySetup"][0]["comparisonLabel"])
        fallback = self.project("for-you")["mySetup"][0]
        expected = next(event["entity"]["name"] for event in self.feed["events"] if event["entity"]["id"] == PLUGIN)
        self.assertEqual(expected, fallback["name"])

    def test_setup_excludes_only_explicit_first_party_shell_components(self) -> None:
        values = [{"id": "org.example.infrastructure", "name": "Shell infrastructure", "enabled": True, "firstParty": True},
                  {"id": "omarchy.custom-example", "name": "A local plugin", "enabled": True, "firstParty": False},
                  {"id": PLUGIN, "name": "Disk Lens", "enabled": True, "firstParty": True}]
        with mock.patch("radar.client_setup.subprocess.run", return_value=mock.Mock(returncode=0, stdout=json.dumps(values))):
            installed = installed_plugins(self.environment)
        self.assertEqual(sorted(item["id"] for item in values), installed["pluginIds"])
        result = projection_model("for-you", json.dumps(installed["pluginIds"]), "", self.environment,
                                  now=CLOCK, installed_facts_json=json.dumps(installed["plugins"]))
        self.assertEqual(["omarchy.custom-example"], [item["id"] for item in result["mySetup"]])
        self.assertTrue(any(item["entity"]["id"] == PLUGIN for item in result["events"]))
        self.store_insights()
        result = insights_model(json.dumps(installed["plugins"]), self.environment, now=CLOCK)
        self.assertEqual({PLUGIN, "omarchy.custom-example"}, {item["id"] for item in result["mySetup"]})

    def test_successful_empty_setup_is_distinct_from_unavailable_discovery(self) -> None:
        with mock.patch("radar.client_setup.subprocess.run", return_value=mock.Mock(returncode=0, stdout="[]")):
            self.assertTrue(installed_plugins(self.environment)["factsAvailable"])
        result = insights_model("[]", self.environment, now=CLOCK)
        self.assertTrue(result["insights"]["installedFactsAvailable"])
        self.assertEqual([], result["mySetup"])
        result = insights_model("[]", self.environment, now=CLOCK, installed_facts_available=False)
        self.assertFalse(result["insights"]["installedFactsAvailable"])
        self.assertEqual([], result["mySetup"])

    def test_refresh_sends_only_generic_request_and_preserves_good_cache_on_failure(self) -> None:
        self.store_insights()
        set_relevance("plugin", PLUGIN, "follow", self.environment)
        with mock.patch("radar.client_insights.fetch_bytes", return_value=(json.dumps(self.insights).encode(), {"ETag": '"known"'}, 200)) as fetch:
            result = refresh_insights(self.environment, now=CLOCK)
            self.assertEqual("cached", result["status"])
            args, kwargs = fetch.call_args
            self.assertEqual((INSIGHTS_URL,), args)
            self.assertEqual({"Accept", "Accept-Encoding", "User-Agent"}, set(kwargs["headers"]))
            self.assertNotIn(PLUGIN, json.dumps(kwargs["headers"]))
        metadata = (cache_root(self.environment) / "insights-http.json").read_bytes()
        with mock.patch("radar.client_insights.fetch_bytes", side_effect=FetchError("network-error", "offline")):
            result = refresh_insights(self.environment, now=CLOCK + timedelta(minutes=6))
            self.assertEqual("cached", result["status"])
            self.assertEqual(self.insights, load_insights(self.environment, now=CLOCK))
            self.assertEqual(metadata, (cache_root(self.environment) / "insights-http.json").read_bytes())

    def test_not_modified_and_due_checks_do_not_replace_valid_cache(self) -> None:
        self.store_insights()
        atomic_write_json(cache_root(self.environment) / "insights-http.json", {"url": INSIGHTS_URL, "etag": '"known"', "lastModified": None})
        with mock.patch("radar.client_insights.fetch_bytes", return_value=(b"", {}, 304)) as fetch:
            result = refresh_insights(self.environment, now=CLOCK)
            self.assertEqual("cached", result["status"])
            self.assertTrue(fetch.call_args.kwargs["allow_not_modified"])
            self.assertEqual('"known"', fetch.call_args.kwargs["headers"]["If-None-Match"])
            result = refresh_insights(self.environment, now=CLOCK + timedelta(seconds=1))
            self.assertFalse(result["attempted"])
            self.assertEqual(1, fetch.call_count)

    def test_invalid_sidecar_response_never_replaces_cache_or_validators(self) -> None:
        self.store_insights()
        atomic_write_json(cache_root(self.environment) / "insights-http.json", {"url": INSIGHTS_URL, "etag": '"old"', "lastModified": None})
        with mock.patch("radar.client_insights.fetch_bytes", return_value=(b'{"schemaVersion":42}', {"ETag": '"bad"'}, 200)):
            result = refresh_insights(self.environment, now=CLOCK)
        self.assertEqual("cached", result["status"])
        self.assertEqual('"old"', json.loads((cache_root(self.environment) / "insights-http.json").read_text())["etag"])
        self.assertEqual(self.insights, load_insights(self.environment, now=CLOCK))

    def test_home_is_finite_and_event_metadata_does_not_duplicate_release_histories(self) -> None:
        template = self.insights["projects"][1]
        for number in range(15):
            self.insights["projects"].append({**template, "id": f"org.example.discovery{number}"})
        self.store_insights()
        result = self.project("plugins")
        self.assertEqual(8, len(result["home"]["discoveries"]))
        self.assertEqual(16, result["home"]["discoveryCount"])
        project = next(item["projectInsight"] for item in result["events"] if item["entity"]["id"] == PLUGIN)
        self.assertNotIn("releases", project)
        self.assertNotIn("newerReleases", project)
        self.assertEqual(2, project["newerReleaseCount"])

    def test_omarchy_platform_is_not_a_plugin_discovery_and_core_notes_remain_available(self) -> None:
        core = copy.deepcopy(self.insights["projects"][0])
        core.update({"id": "omarchy", "kind": "omarchy", "name": "Omarchy", "creatorId": "github:omacom",
                     "source": {"label": "Omarchy source", "url": "https://github.com/omacom/omarchy"}})
        release = core["releases"][0]
        release["version"] = "v4.0.2"
        release["sourceUrl"] = "https://github.com/omacom/omarchy/releases/tag/v4.0.2"
        for change in release["changes"]:
            change["sourceUrl"] = release["sourceUrl"]
        core["releases"] = [release]
        self.insights["projects"].insert(0, core)
        self.store_insights()
        result = self.project("core")
        self.assertTrue(all(item["kind"] == "plugin" for item in result["home"]["discoveries"]))
        detail = next(item for item in result["insights"]["projectDetails"] if item["id"] == "omarchy")
        self.assertTrue(detail["installed"])
        self.assertIsNone(detail["installedVersion"])
        self.assertEqual("unknown", detail["comparisonState"])
        event = next(item for item in result["events"] if item["entity"]["id"] == "omarchy")
        self.assertEqual(release, event["releaseInsight"])
        self.assertEqual("unknown", event["projectInsight"]["comparisonState"])

    def test_followed_uninstalled_project_never_claims_an_enabled_plugin_match(self) -> None:
        # Routine release activity outside enabled plugins becomes meaningful
        # through the explicit follow, without inventing local installation.
        self.feed["events"] = [event for event in self.feed["events"] if event["entity"]["id"] == PLUGIN]
        for event in self.feed["events"]:
            event["classification"]["significance"] = "routine"
        save_feed(self.feed, self.environment, now=CLOCK)
        set_relevance("plugin", PLUGIN, "follow", self.environment)
        ensure_briefing("[]", self.environment, now=CLOCK)
        result = projection_model("front-page", "[]", "", self.environment, now=CLOCK)
        self.assertEqual("followed", result["events"][0]["briefingReason"])
        self.assertEqual("Followed on this desktop", result["events"][0]["briefingReasonLabel"])

    def test_clearing_all_relevance_controls_leaves_no_hidden_preference(self) -> None:
        for kind, identity in (("plugin", PLUGIN), ("source", "marketplace"), ("creator", "github:example")):
            set_relevance(kind, identity, "mute", self.environment)
        model = insights_model(self.facts, self.environment, now=CLOCK)
        for target in model["relevanceControls"]:
            set_relevance(target["kind"], target["id"], "clear", self.environment)
        self.assertEqual(default_relevance(), load_state(self.environment)[0]["relevance"])

    def test_oversized_combined_preferences_are_refused_before_replacing_state(self) -> None:
        before = load_state(self.environment)[0]
        oversized = copy.deepcopy(before)
        oversized["relevance"]["followedPlugins"] = [f"org.example.p{n}" for n in range(500)]
        oversized["relevance"]["mutedCreators"] = ["github:example"]
        with self.assertRaises(ValidationError):
            save_state(oversized, self.environment)
        self.assertEqual(before, load_state(self.environment)[0])


if __name__ == "__main__":
    unittest.main()
