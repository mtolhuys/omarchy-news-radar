#!/usr/bin/python3
"""Offline repository contract validation without optional downloads."""

from __future__ import annotations

import compileall
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from radar.collector import FixtureInputs, collect_from_fixtures, load_snapshot  # noqa: E402
from radar.io import canonical_json_bytes  # noqa: E402
from radar.validation import validate_feed  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def tracked_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    return [ROOT / item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]


def validate_tracked_text() -> None:
    text_suffixes = {
        ".md", ".py", ".qml", ".js", ".json", ".xml", ".css", ".yml", ".yaml", ".sh", ".lua", ".toml", ""
    }
    forbidden_paths = ("/home/", "file://", ".qcow2", ".iso")
    for path in tracked_files():
        if not path.exists() or path.suffix.lower() not in text_suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            fail(f"tracked text is not UTF-8: {path.relative_to(ROOT)}")
        if "[" + "TODO:" in text:
            fail(f"tracked placeholder remains: {path.relative_to(ROOT)}")
        if path.relative_to(ROOT).as_posix().startswith("docs/evidence/"):
            for forbidden in forbidden_paths:
                if forbidden in text:
                    fail(f"evidence contains a machine-local path: {path.relative_to(ROOT)}")


def validate_json_files() -> None:
    for path in tracked_files():
        if path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")


def validate_generated_fixture() -> None:
    previous = load_snapshot(ROOT / "tests/fixtures/source-snapshot-baseline.json")
    inputs = FixtureInputs(
        ROOT / "tests/fixtures/releases-next.json",
        ROOT / "tests/fixtures/catalog-next.json",
        ROOT / "content/community",
        ROOT / "content/curation",
    )
    feed, _ = collect_from_fixtures(
        inputs,
        previous_snapshot=previous,
        now=datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc),
        bootstrap_marketplace=False,
    )
    expected = (ROOT / "tests/fixtures/feed-valid.json").read_bytes()
    actual = canonical_json_bytes(feed)
    if actual != expected:
        fail("tests/fixtures/feed-valid.json has generated-file drift")
    validate_feed(json.loads(expected), now=datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc))


def validate_manifest() -> None:
    path = ROOT / "manifest.json"
    if not path.exists():
        fail("manifest.json is missing")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required = {"schemaVersion", "id", "name", "version", "author", "description", "kinds", "entryPoints"}
    if not required.issubset(manifest):
        fail("manifest is missing required fields")
    if manifest["schemaVersion"] != 1 or manifest["id"] != "io.github.mtolhuys.news-radar":
        fail("manifest identity is invalid")
    if manifest["kinds"] != ["panel"] or set(manifest["entryPoints"]) != {"panel"}:
        fail("version 1 manifest must remain panel-only")
    if manifest.get("keepLoaded") is not None or "barWidget" in manifest:
        fail("version 1 manifest must not stay loaded or declare a bar widget")
    entry = ROOT / manifest["entryPoints"]["panel"]
    if not entry.is_file():
        fail("manifest panel entry point does not exist")
    qml = entry.read_text(encoding="utf-8")
    for required_text in ("function open(", "function close(", "property string runtimeBuildIdentity"):
        if required_text not in qml:
            fail(f"panel entry point lacks {required_text}")
    forbidden = ("Text.RichText", "Qt.openUrlExternally", '"bar-widget"', "shell -c", "bash -c")
    for value in forbidden:
        if value in qml:
            fail(f"panel contains forbidden runtime path: {value}")
    for helper_name in ("news-radar-client", "news-radar-shortcut"):
        helper = (ROOT / "bin" / helper_name).read_text(encoding="utf-8")
        if "exec python3 -B -m " not in helper:
            fail(f"{helper_name} must disable bytecode writes in the watched plugin directory")


def validate_workflows() -> None:
    workflows = list((ROOT / ".github" / "workflows").glob("*.yml"))
    if not workflows:
        fail("GitHub Actions workflows are missing")
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        for reference in re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", text):
            if not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", reference):
                fail(f"workflow action is not pinned to an immutable SHA: {reference}")
        if "contents: write" in text:
            fail(f"workflow requests repository write permission: {workflow.name}")
    publish = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    for required in ("contents: read", "pages: write", "id-token: write", "state/source-snapshot.json"):
        if required not in publish:
            fail(f"publish workflow lacks required least-privilege/state contract: {required}")


def optional_tools() -> None:
    shellcheck = shutil.which("shellcheck")
    if shellcheck:
        scripts = [path for path in tracked_files() if path.suffix == ".sh" or path.parent.name == "bin"]
        if scripts:
            subprocess.run([shellcheck, *map(str, scripts)], cwd=ROOT, check=True)
    omarchy_source = os.environ.get("OMARCHY_SOURCE")
    qmllint = shutil.which("qmllint")
    if qmllint and omarchy_source:
        source = Path(omarchy_source)
        if not (source / "shell/services/PluginRegistry.qml").is_file():
            fail("OMARCHY_SOURCE is not a selected Omarchy checkout")
        subprocess.run([qmllint, "-I", str(source / "shell"), str(ROOT / "src/Panel.qml")], cwd=ROOT, check=True)


def main() -> int:
    if not compileall.compile_dir(ROOT / "radar", quiet=1):
        fail("Python compilation failed")
    validate_tracked_text()
    validate_json_files()
    validate_generated_fixture()
    validate_manifest()
    validate_workflows()
    optional_tools()
    print("ok - Python source compiles")
    print("ok - tracked text is UTF-8 English-ready and free of placeholders")
    print("ok - JSON, schema fixtures, generated feed, panel-only manifest, and pinned workflows validate")
    print("ok - optional shell/QML validators passed when available and configured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
