"""Repository, collector, publisher and QML-helper command entry points."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .client import (
    installed_plugins,
    indicator_model,
    mark_section_read_state,
    open_source,
    projection_model,
    purge_state,
    read_model,
    refresh,
    refresh_if_due,
    require_unprivileged,
    set_event_read_state,
    toggle_saved_state,
    set_preferences,
    set_section_filter,
)
from .collector import FixtureInputs, collect_from_fixtures, collect_production, load_snapshot, save_snapshot
from .errors import RadarError
from .io import atomic_write_json
from .local_edition import import_local_edition
from .local_collection import commit_local_source_snapshot, prepare_local_source_snapshot
from .publisher import publish
from .publication_state import (
    audit_marketplace_additions,
    migrate_legacy_source_snapshot,
    restore_publication_source_snapshot,
)
from .validation import parse_timestamp, validate_feed
from .window import activate_window

ROOT = Path(__file__).resolve().parent.parent


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def client_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="news-radar-client")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("read")
    commands.add_parser("refresh")
    due = commands.add_parser("refresh-if-due")
    due.add_argument("--minimum-age", required=True, type=int)
    commands.add_parser("indicator")
    commands.add_parser("installed")
    commands.add_parser("purge")
    commands.add_parser("activate-window")
    reading = commands.add_parser("set-read")
    reading.add_argument("--event-id", required=True)
    reading.add_argument("--read", required=True, choices=("true", "false"))
    section_reading = commands.add_parser("mark-section-read")
    section_reading.add_argument("--section", required=True)
    section_reading.add_argument("--installed-json", default="[]")
    saved = commands.add_parser("toggle-saved")
    saved.add_argument("--event-id", required=True)
    preferences = commands.add_parser("set-preferences")
    preferences.add_argument("--bar-visible", choices=("true", "false"))
    preferences.add_argument("--images-visible", choices=("true", "false"))
    opening = commands.add_parser("open-source")
    opening.add_argument("--url", required=True)
    projection = commands.add_parser("project")
    projection.add_argument("--section", required=True)
    projection.add_argument("--installed-json", default="[]")
    projection.add_argument("--query", default="")
    projection.add_argument("--limit", type=int, default=12)
    projection.add_argument("--retained-read-ids-json", default="[]")
    section_filter = commands.add_parser("set-section-filter")
    section_filter.add_argument("--section", required=True)
    section_filter.add_argument("--filter-json", required=True)
    args = parser.parse_args(argv)
    try:
        require_unprivileged()
        if args.command == "read":
            result = read_model()
        elif args.command == "refresh":
            result = refresh()
        elif args.command == "refresh-if-due":
            result = refresh_if_due(args.minimum_age)
        elif args.command == "indicator":
            result = indicator_model()
        elif args.command == "installed":
            result = installed_plugins()
        elif args.command == "activate-window":
            result = activate_window()
        elif args.command == "set-read":
            result = set_event_read_state(args.event_id, args.read == "true")
        elif args.command == "mark-section-read":
            result = mark_section_read_state(args.section, args.installed_json)
        elif args.command == "toggle-saved":
            result = toggle_saved_state(args.event_id)
        elif args.command == "set-preferences":
            result = set_preferences(
                bar_visible=None if args.bar_visible is None else args.bar_visible == "true",
                images_visible=None if args.images_visible is None else args.images_visible == "true",
            )
        elif args.command == "open-source":
            result = open_source(args.url)
        elif args.command == "set-section-filter":
            if len(args.filter_json) > 8192:
                raise RadarError("section filter exceeds its bound")
            try:
                filter_value = json.loads(args.filter_json)
            except json.JSONDecodeError as exc:
                raise RadarError("section filter must be a JSON object") from exc
            if not isinstance(filter_value, dict):
                raise RadarError("section filter must be a JSON object")
            result = set_section_filter(args.section, filter_value)
        elif args.command == "project":
            result = projection_model(
                args.section,
                args.installed_json,
                args.query,
                limit=args.limit,
                retained_read_ids_json=args.retained_read_ids_json,
            )
        else:
            result = purge_state()
        _print(result)
        return 0 if result.get("status") not in {"offline", "invalid-feed"} else 2
    except (RadarError, OSError, subprocess.SubprocessError) as exc:
        _print({"protocolVersion": 1, "status": "failed", "message": str(exc)})
        return 2


def build_fixture(*, second_generation: bool, output: Path, snapshot_output: Path | None = None) -> dict[str, Any]:
    previous_path = ROOT / "tests/fixtures/source-snapshot-baseline.json"
    previous = load_snapshot(previous_path) if second_generation else None
    suffix = "next" if second_generation else "baseline"
    inputs = FixtureInputs(
        releases=ROOT / f"tests/fixtures/releases-{suffix}.json",
        marketplace=ROOT / f"tests/fixtures/catalog-{suffix}.json",
        community=ROOT / "tests/fixtures/community",
        curation=ROOT / "content/curation",
        engagement=ROOT / f"tests/fixtures/engagement-{suffix}.json",
    )
    clock = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)
    feed, snapshot = collect_from_fixtures(
        inputs,
        previous_snapshot=previous,
        now=clock,
        bootstrap_marketplace=not second_generation,
    )
    atomic_write_json(output, feed)
    if snapshot_output:
        save_snapshot(snapshot_output, snapshot)
    return feed


def repository_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m radar")
    commands = parser.add_subparsers(dest="command", required=True)
    fixture = commands.add_parser("feed-fixture")
    fixture.add_argument("--baseline", action="store_true")
    fixture.add_argument("--output", type=Path, default=ROOT / "dist/events.json")
    fixture.add_argument("--snapshot-output", type=Path)
    site = commands.add_parser("site")
    site.add_argument("--feed", type=Path, default=ROOT / "tests/fixtures/feed-valid.json")
    site.add_argument("--output", type=Path, default=ROOT / "dist")
    commands.add_parser("validate-feed").add_argument("path", type=Path)
    local_import = commands.add_parser("import-local-edition")
    local_import.add_argument("--edition", type=Path, required=True)
    local_prepare = commands.add_parser("prepare-local-source-snapshot")
    local_prepare.add_argument("--tracked", type=Path, required=True)
    local_prepare.add_argument("--output", type=Path, required=True)
    local_commit = commands.add_parser("commit-local-source-snapshot")
    local_commit.add_argument("--snapshot", type=Path, required=True)
    publication_restore = commands.add_parser("restore-publication-source-snapshot")
    publication_restore.add_argument("--previous", type=Path, required=True)
    publication_restore.add_argument("--tracked", type=Path, required=True)
    publication_restore.add_argument("--output", type=Path, required=True)
    publication_migrate = commands.add_parser("migrate-source-snapshot-v2")
    publication_migrate.add_argument("--source", type=Path, required=True)
    publication_migrate.add_argument("--output", type=Path, required=True)
    publication_audit = commands.add_parser("audit-marketplace-additions")
    publication_audit.add_argument("--previous", type=Path, required=True)
    publication_audit.add_argument("--current", type=Path, required=True)
    collect = commands.add_parser("collect")
    collect.add_argument("--snapshot", type=Path, default=ROOT / "state/source-snapshot.json")
    collect.add_argument("--output", type=Path, default=ROOT / "dist")
    collect.add_argument("--bootstrap-marketplace", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "feed-fixture":
            feed = build_fixture(second_generation=not args.baseline, output=args.output, snapshot_output=args.snapshot_output)
            _print({"status": "ok", "events": len(feed["events"]), "output": str(args.output)})
        elif args.command == "site":
            value = json.loads(args.feed.read_text(encoding="utf-8"))
            feed = validate_feed(value, now=parse_timestamp(value["generatedAt"]))
            revision = os.environ.get("SOURCE_REVISION", "working-tree")
            _print({"status": "ok", **publish(feed, args.output, source_revision=revision)})
        elif args.command == "collect":
            previous = load_snapshot(args.snapshot)
            clock = datetime.now(timezone.utc).replace(microsecond=0)
            feed, snapshot = collect_production(
                previous_snapshot=previous,
                community_directory=ROOT / "content/community",
                curation_directory=ROOT / "content/curation",
                now=clock,
                bootstrap_marketplace=args.bootstrap_marketplace,
                github_token=os.environ.get("GITHUB_TOKEN"),
            )
            revision = os.environ.get("GITHUB_SHA", os.environ.get("SOURCE_REVISION", "working-tree"))
            result = publish(
                feed,
                args.output,
                source_revision=revision,
                published_at=datetime.now(timezone.utc).replace(microsecond=0),
            )
            save_snapshot(args.snapshot, snapshot)
            _print({"status": "ok", "events": len(feed["events"]), **result})
        elif args.command == "validate-feed":
            value = json.loads(args.path.read_text(encoding="utf-8"))
            validate_feed(value, now=parse_timestamp(value["generatedAt"]), public_only=True)
            _print({"status": "ok"})
        elif args.command == "import-local-edition":
            require_unprivileged()
            imported = import_local_edition(args.edition)
            _print({"status": "ok", **{key: value for key, value in imported.items() if key != "feed"}})
        elif args.command == "prepare-local-source-snapshot":
            require_unprivileged()
            prepared = prepare_local_source_snapshot(args.tracked, args.output)
            _print({"status": "ok", **prepared})
        elif args.command == "commit-local-source-snapshot":
            require_unprivileged()
            committed = commit_local_source_snapshot(args.snapshot)
            _print({"status": "ok", **committed})
        elif args.command == "restore-publication-source-snapshot":
            restored = restore_publication_source_snapshot(
                args.previous, args.tracked, args.output
            )
            _print({"status": "ok", **restored})
        elif args.command == "migrate-source-snapshot-v2":
            migrated = migrate_legacy_source_snapshot(args.source, args.output)
            _print({"status": "ok", **migrated})
        else:
            audited = audit_marketplace_additions(args.previous, args.current)
            _print({"status": "ok", **audited})
        return 0
    except (RadarError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
