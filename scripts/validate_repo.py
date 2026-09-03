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
from typing import NoReturn

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from radar.collector import FixtureInputs, collect_from_fixtures, load_snapshot  # noqa: E402
from radar.io import canonical_json_bytes  # noqa: E402
from radar.validation import validate_feed  # noqa: E402


def fail(message: str) -> NoReturn:
    raise SystemExit(f"error: {message}")


def tracked_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    return [ROOT / item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]


def validate_tracked_text() -> None:
    text_suffixes = {
        ".md", ".py", ".qml", ".js", ".json", ".xml", ".svg", ".css", ".yml", ".yaml", ".sh", ".lua", ".toml", ""
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
        if path.exists() and path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")


def validate_generated_fixture() -> None:
    previous = load_snapshot(ROOT / "tests/fixtures/source-snapshot-baseline.json")
    inputs = FixtureInputs(
        ROOT / "tests/fixtures/releases-next.json",
        ROOT / "tests/fixtures/catalog-next.json",
        ROOT / "tests/fixtures/community",
        ROOT / "content/curation",
        ROOT / "tests/fixtures/engagement-next.json",
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
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        fail("manifest version is invalid")
    package_version = re.search(
        r'^__version__ = "([^"]+)"$',
        (ROOT / "radar" / "__init__.py").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    build_version = re.search(
        r'^BUILD_ID = "news-radar-([^"]+)"$',
        (ROOT / "radar" / "constants.py").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if package_version is None or build_version is None:
        fail("runtime version identity is missing")
    if version != package_version.group(1) or version != build_version.group(1):
        fail("manifest, package, and helper versions disagree")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if f"## Install the published v{version}" not in readme:
        fail("README installation heading does not match the manifest version")
    if f"Version `{version}` is the current release." not in readme:
        fail("README release status does not match the manifest version")
    if not (ROOT / "docs" / "release-notes" / f"{version}.md").is_file():
        fail("release notes do not match the manifest version")
    if manifest["kinds"] != ["panel", "bar-widget"] or set(manifest["entryPoints"]) != {"panel", "barWidget"}:
        fail("manifest must pair its panel with the optional bar widget")
    if manifest.get("keepLoaded") is not None or manifest.get("barWidget", {}).get("defaultSection") != "right":
        fail("manifest bar widget lifecycle or default placement is invalid")
    entries = {name: ROOT / value for name, value in manifest["entryPoints"].items()}
    if not all(entry.is_file() for entry in entries.values()):
        fail("manifest entry point does not exist")
    icon_value = manifest.get("icon")
    if icon_value != "assets/io.github.mtolhuys.news-radar.svg":
        fail("manifest icon identity is invalid")
    icon_path = ROOT / icon_value
    if not icon_path.is_file():
        fail("manifest icon does not exist")
    try:
        icon_bytes = icon_path.read_bytes()
        if len(icon_bytes) > 64 * 1024:
            fail("manifest icon exceeds its 64 KiB bound")
        icon_text = icon_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        fail(f"manifest icon is invalid UTF-8 SVG: {exc}")
    lowered_icon = icon_text.casefold()
    forbidden_icon_tokens = (
        "<!",
        "<script",
        "<style",
        "<image",
        "<foreignobject",
        "href=",
        "url(",
    )
    if any(token in lowered_icon for token in forbidden_icon_tokens):
        fail("manifest icon must be inert self-contained SVG geometry")
    root_match = re.match(r"\s*<svg\s+([^>]*)>", icon_text)
    if root_match is None or not icon_text.rstrip().endswith("</svg>"):
        fail("manifest icon has an invalid SVG root")
    attribute_pairs = [
        (match.group(1), match.group(3))
        for match in re.finditer(r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(['\"])(.*?)\2", root_match.group(1))
    ]
    if len(attribute_pairs) != len({name for name, _ in attribute_pairs}):
        fail("manifest icon root attributes must be unique")
    attributes = dict(attribute_pairs)
    if attributes.get("xmlns") != "http://www.w3.org/2000/svg" or attributes.get("viewBox") != "0 0 128 128":
        fail("manifest icon must be a bounded 128-unit SVG")
    required_brand_geometry = (
        '#111418',
        '#9ece6a',
        '#ffad24',
        'translate(64 64) scale(.075) translate(-600 -600)',
        'm1200 1200h-480v-80h400v-1040',
        '<circle cx="64" cy="64" r="19"',
    )
    if any(token not in icon_text for token in required_brand_geometry):
        fail("manifest icon does not match the reviewed Omarchy-and-radar brand geometry")
    if (ROOT / "assets" / "io.github.mtolhuys.news-radar-light.svg").exists():
        fail("retired light-theme icon must not be shipped")
    brand_logo_path = ROOT / "assets" / "omarchy-logo.svg"
    if not brand_logo_path.is_file():
        fail("official Omarchy title logo is missing")
    brand_logo_text = brand_logo_path.read_text(encoding="utf-8")
    lowered_brand_logo = brand_logo_text.casefold()
    if any(token in lowered_brand_logo for token in forbidden_icon_tokens):
        fail("Omarchy title logo must be inert self-contained SVG geometry")
    for token in ('viewBox="0 0 1200 1200"', '#9ece6a', 'm1200 1200h-480v-80h400v-1040'):
        if token not in brand_logo_text:
            fail("Omarchy title logo does not match the reviewed official geometry")
    panel_mark_paths = (
        ROOT / "assets" / "io.github.mtolhuys.news-radar-panel.svg",
        ROOT / "assets" / "io.github.mtolhuys.news-radar-panel-light.svg",
    )
    for panel_mark_path in panel_mark_paths:
        if not panel_mark_path.is_file():
            fail(f"panel mark is missing: {panel_mark_path.name}")
        panel_mark_text = panel_mark_path.read_text(encoding="utf-8")
        lowered_panel_mark = panel_mark_text.casefold()
        if any(token in lowered_panel_mark for token in forbidden_icon_tokens):
            fail(f"panel mark must be inert self-contained SVG geometry: {panel_mark_path.name}")
        if '#111418' in panel_mark_text or '<rect' in lowered_panel_mark:
            fail(f"panel mark must remain transparent: {panel_mark_path.name}")
        for token in ('viewBox="0 0 128 128"', 'm1200 1200h-480v-80h400v-1040', '<circle cx="64" cy="64" r="19"'):
            if token not in panel_mark_text:
                fail(f"panel mark lacks reviewed geometry: {panel_mark_path.name}")
    banner_source = ROOT / "assets" / "readme-banner.svg"
    marketplace_preview = ROOT / "preview.png"
    readme_walkthrough = ROOT / "preview.gif"
    if not banner_source.is_file() or not marketplace_preview.is_file() or not readme_walkthrough.is_file():
        fail("README and marketplace preview assets are missing")
    marketplace_preview_bytes = marketplace_preview.read_bytes()
    if marketplace_preview_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        fail("marketplace preview must remain a root preview.png")
    marketplace_preview_size = (
        int.from_bytes(marketplace_preview_bytes[16:20], "big"),
        int.from_bytes(marketplace_preview_bytes[20:24], "big"),
    )
    if marketplace_preview_size != (1200, 675):
        fail("marketplace preview must remain a 1200x675 16:9 hero image")
    banner_text = banner_source.read_text(encoding="utf-8")
    for token in ("COMMUNITY PLUGIN", "OMARCHY", "NEWS RADAR", "#9ece6a", "#ffad24"):
        if token not in banner_text:
            fail(f"README banner lacks reviewed brand token: {token}")
    walkthrough_bytes = readme_walkthrough.read_bytes()
    if walkthrough_bytes[:6] not in (b"GIF87a", b"GIF89a"):
        fail("README walkthrough is not a GIF")
    walkthrough_size = (
        int.from_bytes(walkthrough_bytes[6:8], "little"),
        int.from_bytes(walkthrough_bytes[8:10], "little"),
    )
    if walkthrough_size != (960, 573):
        fail("README walkthrough must remain 960x573")
    if len(walkthrough_bytes) > 6 * 1024 * 1024:
        fail("README walkthrough exceeds the 6 MiB repository budget")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    if "(assets/readme-banner.svg)" not in readme_text:
        fail("README does not embed the reviewed brand banner")
    if "(preview.gif)" not in readme_text:
        fail("README does not embed the product walkthrough")
    qml = entries["panel"].read_text(encoding="utf-8")
    for required_text in ("function open(", "function close(", "property string runtimeBuildIdentity"):
        if required_text not in qml:
            fail(f"panel entry point lacks {required_text}")
    if f'news-radar-{version}+identity-1' not in qml:
        fail("panel runtime identity does not match the manifest version")
    if 'String(manifest.__sourceDir) + "/assets/omarchy-logo.svg"' not in qml:
        fail("panel title does not load the bundled Omarchy logo")
    if 'text: "NEWS RADAR"' not in qml or 'text: "OMARCHY NEWS RADAR"' in qml:
        fail("panel title must pair the Omarchy logo with the News Radar product name")
    forbidden = ("Qt.openUrlExternally", "shell -c", "bash -c")
    for value in forbidden:
        if value in qml:
            fail(f"panel contains forbidden runtime path: {value}")
    if qml.count("Text.RichText") != 1:
        fail("panel may use Text.RichText only once, for the article reading pane")
    if "textFormat: root.inspectorArticleMode ? Text.RichText : Text.PlainText" not in qml:
        fail("article body RichText must be constrained to inspectorArticleMode")
    if "function openArticleLink(url)" not in qml or "linkColor: Color.accent" not in qml:
        fail("article links must use accent styling and openArticleLink")
    if "RadarModel.articleBodyHtml" not in qml or "RadarModel.acceptedHttpsUrl" not in qml:
        fail("article links must be built from escaped segments, not raw feed HTML")
    for helper_name in ("news-radar-client", "news-radar-shortcut", "news-radar-launcher"):
        helper = (ROOT / "bin" / helper_name).read_text(encoding="utf-8")
        if "exec python3 -B -m " not in helper:
            fail(f"{helper_name} must disable bytecode writes in the watched plugin directory")

    update_source = (ROOT / "radar" / "plugin_update.py").read_text(encoding="utf-8")
    if "omarchy-plugin-update" not in update_source:
        fail("plugin update helper must call omarchy-plugin-update")
    for forbidden_update in ("merge --ff-only", "git pull", "git reset"):
        if forbidden_update in update_source:
            fail(f"plugin update helper must not implement its own git mutation: {forbidden_update}")
    panel_source = (ROOT / "src" / "Panel.qml").read_text(encoding="utf-8")
    for required_update_ui in ("pluginUpdateNotice", "Update plugin", '"update-status"', '"update-apply"'):
        if required_update_ui not in panel_source:
            fail(f"panel lacks plugin update UI contract: {required_update_ui}")
    makefile_text = (ROOT / "Makefile").read_text(encoding="utf-8")
    if "local-downgrade" not in makefile_text or "local-behind" not in makefile_text:
        fail("Makefile must expose local-downgrade and local-behind test helpers")
    if not (ROOT / "scripts" / "downgrade_local_plugin.sh").is_file():
        fail("local-downgrade script is missing")
    if not (ROOT / "scripts" / "mark_local_plugin_behind.sh").is_file():
        fail("local-behind script is missing")

    shortcut_source = (ROOT / "radar" / "shortcut.py").read_text(encoding="utf-8")
    shortcut_cli = (ROOT / "radar" / "shortcut_cli.py").read_text(encoding="utf-8")
    if 'CHORD = "SUPER + ALT + N"' not in shortcut_source or "MODMASK = 72" not in shortcut_source:
        fail("shortcut helper must own the audited Super+Alt+N chord")
    for forbidden_shortcut_path in ("replace-default-editor", 'hl.unbind("{CHORD}")'):
        if forbidden_shortcut_path in shortcut_source or forbidden_shortcut_path in shortcut_cli:
            fail(f"shortcut helper contains a forbidden action-replacement path: {forbidden_shortcut_path}")

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    local_sync = (ROOT / "scripts" / "sync_local_plugin.sh").read_text(encoding="utf-8")
    if "local-latest: validate" not in makefile or "scripts/sync_local_plugin.sh" not in makefile:
        fail("Makefile must expose the validated local-latest sync target")
    for required_text in (
        "status --porcelain --untracked-files=normal",
        "installed plugin tracks a non-local origin",
        'omarchy-plugin-update "$PLUGIN_ID" --yes',
        '"$TARGET/bin/news-radar-launcher" install',
        "import-local-edition",
        "Migrated the panel-only preview",
    ):
        if required_text not in local_sync:
            fail(f"local-latest sync lacks required safety contract: {required_text}")
    for forbidden_text in ("git pull", "git reset", "news-radar-shortcut install"):
        if forbidden_text in local_sync:
            fail(f"local-latest sync contains forbidden mutation: {forbidden_text}")

    desktop_entry = ROOT / "share/applications/io.github.mtolhuys.news-radar.desktop"
    desktop_text = desktop_entry.read_text(encoding="utf-8")
    for required_text in (
        "Name=Omarchy News Radar",
        "Exec=omarchy-shell shell summon io.github.mtolhuys.news-radar",
        "Icon=io.github.mtolhuys.news-radar",
        "X-Omarchy-News-Radar-Managed=true",
    ):
        if required_text not in desktop_text:
            fail(f"application launcher lacks required contract: {required_text}")

    local_edition = (ROOT / "radar" / "local_edition.py").read_text(encoding="utf-8")
    for required_text in (
        "BUILD_INFO_PATTERN",
        "inspect_raster",
        "hashlib.sha256(data).hexdigest() != source.stem",
        "atomic_write_json(marker_path(environment), marker)",
    ):
        if required_text not in local_edition:
            fail(f"local edition import lacks required validation contract: {required_text}")


def validate_workflows() -> None:
    workflows_dir = ROOT / ".github" / "workflows"
    workflows = list(workflows_dir.glob("*.yml"))
    if not workflows:
        fail("GitHub Actions workflows are missing")
    if (workflows_dir / "publication.yml").exists():
        fail("publication.yml must remain removed; Forge Laravel owns live publication")
    test_workflow = workflows_dir / "test.yml"
    if not test_workflow.is_file():
        fail("test.yml workflow is missing")
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        for reference in re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", text):
            if not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", reference):
                fail(f"workflow action is not pinned to an immutable SHA: {reference}")
        if "contents: write" in text:
            fail(f"workflow requests repository write permission: {workflow.name}")


def optional_tools() -> list[str]:
    results: list[str] = []
    shellcheck = shutil.which("shellcheck")
    if shellcheck:
        scripts = [path for path in tracked_files() if path.suffix == ".sh" or path.parent.name == "bin"]
        if scripts:
            subprocess.run([shellcheck, *map(str, scripts)], cwd=ROOT, check=True)
            results.append(f"ok - ShellCheck validated {len(scripts)} scripts")
    else:
        results.append("skip - ShellCheck is not installed")
    desktop_validator = shutil.which("desktop-file-validate")
    if desktop_validator:
        subprocess.run(
            [desktop_validator, str(ROOT / "share/applications/io.github.mtolhuys.news-radar.desktop")],
            cwd=ROOT,
            check=True,
        )
        results.append("ok - desktop-file-validate checked the launcher")
    else:
        results.append("skip - desktop-file-validate is not installed")
    omarchy_source = os.environ.get("OMARCHY_SOURCE")
    qmllint = shutil.which("qmllint")
    fallback_qmllint = Path("/usr/lib/qt6/bin/qmllint")
    if qmllint is None and fallback_qmllint.is_file() and os.access(fallback_qmllint, os.X_OK):
        qmllint = str(fallback_qmllint)
    if qmllint and omarchy_source:
        source = Path(omarchy_source)
        if not (source / "shell/services/PluginRegistry.qml").is_file():
            fail("OMARCHY_SOURCE is not a selected Omarchy checkout")
        qmllint_help = subprocess.run(
            [qmllint, "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        warning_controls = [
            "-W",
            "0",
            "--missing-property",
            "disable",
            "--unqualified",
            "disable",
            "--signal-handler-parameters",
            "disable",
        ]
        if not all(
            option in qmllint_help
            for option in ("--missing-property", "--unqualified", "--signal-handler-parameters")
        ):
            warning_controls = []
        with tempfile.TemporaryDirectory(prefix="omarchy-news-radar-qml-") as temporary:
            import_root = Path(temporary)
            namespace = import_root / "qs"
            namespace.mkdir()
            for module in ("Commons", "Ui"):
                (namespace / module).symlink_to(source / "shell" / module, target_is_directory=True)
            qml_files = sorted((ROOT / "src").rglob("*.qml"))
            subprocess.run(
                [
                    qmllint,
                    *warning_controls,
                    "-I",
                    str(import_root),
                    *map(str, qml_files),
                ],
                cwd=ROOT,
                check=True,
            )
        results.append(
            "ok - qmllint checked all QML against OMARCHY_SOURCE "
            "(Omarchy singleton/context-only diagnostics excluded)"
        )
    elif not qmllint:
        results.append("skip - qmllint is not available on PATH or at the Qt 6 system path")
    else:
        results.append("skip - qmllint needs OMARCHY_SOURCE")
    return results


def main() -> int:
    if not compileall.compile_dir(ROOT / "radar", quiet=1):
        fail("Python compilation failed")
    validate_tracked_text()
    validate_json_files()
    validate_generated_fixture()
    validate_manifest()
    validate_workflows()
    optional_results = optional_tools()
    print("ok - Python source compiles")
    print("ok - tracked text is UTF-8 English-ready and free of placeholders")
    print("ok - JSON, schemas, generated feed, paired panel/bar manifest, and pinned workflows validate")
    for result in optional_results:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
