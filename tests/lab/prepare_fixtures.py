#!/usr/bin/python3
"""Create synthetic visual/runtime states inside a disposable guest."""

from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def event_clone(base: dict, index: int, when: datetime) -> dict:
    item = copy.deepcopy(base)
    item["id"] = f"evt_{index:024x}"
    item["occurredAt"] = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    item["discoveredAt"] = "2026-08-31T14:03:00Z"
    item["title"] = f"Synthetic bounded story {index:03d}"
    item["summary"] = "A deterministic synthetic story exercises dense keyboard navigation and ListView virtualization."
    item["source"] = {"label": "Synthetic source", "url": f"https://github.com/example/synthetic-{index}"}
    item["entity"] = {"kind": "plugin", "id": f"org.example.synthetic-{index}", "name": f"Synthetic {index}"}
    item["classification"] = {"section": "plugins", "significance": "routine", "curated": False, "tags": ["synthetic"]}
    item["trust"] = {"marketplace": "unverified", "securityAudit": False}
    item["compatibility"] = {"channels": [], "basis": "unknown"}
    item["type"] = "plugin-added"
    return item


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: prepare_fixtures.py <feed-valid.json> <output-directory>")
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)
    feed = json.loads(source.read_text(encoding="utf-8"))
    write(output / "valid.json", feed)

    later = copy.deepcopy(feed)
    later["generatedAt"] = "2026-08-31T14:02:00Z"
    later["window"]["through"] = "2026-08-31T14:02:00Z"
    newest = event_clone(feed["events"][0], 0xABC, datetime(2026, 8, 31, 14, 1, tzinfo=timezone.utc))
    newest["discoveredAt"] = "2026-08-31T14:02:00Z"
    newest["title"] = "An event that arrived during the open session"
    newest["entity"] = {"kind": "plugin", "id": "io.github.mtolhuys.disk-lens", "name": "Omarchy Disk Lens", "version": "0.4.2", "repository": "https://github.com/mtolhuys/omarchy-disk-lens"}
    newest["source"] = {"label": "Synthetic release", "url": "https://github.com/mtolhuys/omarchy-disk-lens/releases/tag/v0.4.2"}
    newest["summary"] = "This synthetic event proves that a refresh cannot move the open session's seen-through cutoff."
    later["events"].insert(0, newest)
    write(output / "later.json", later)

    partial = copy.deepcopy(later)
    for source_health in partial["sources"]:
        if source_health["id"] == "marketplace":
            source_health["status"] = "failed"
            source_health["reason"] = "timeout"
    write(output / "partial.json", partial)

    empty = copy.deepcopy(later)
    empty["events"] = []
    write(output / "empty.json", empty)

    long_text = copy.deepcopy(later)
    long_text["events"][0]["title"] = "長い見出し — " + "Keyboard-first Omarchy panel text " * 4
    long_text["events"][0]["summary"] = "Unicode remains inert plain text. " + "This deliberately long summary checks wrapping, clipping, and inspector scrolling. " * 4
    write(output / "long.json", long_text)

    dense = copy.deepcopy(feed)
    dense["generatedAt"] = "2026-08-31T14:03:00Z"
    dense["window"]["through"] = "2026-08-31T14:03:00Z"
    start = datetime(2026, 8, 31, 14, 3, tzinfo=timezone.utc)
    dense["events"] = [event_clone(feed["events"][0], 1000 + index, start - timedelta(minutes=index)) for index in range(120)]
    write(output / "dense.json", dense)

    (output / "malformed.json").write_text("{not-json", encoding="utf-8")
    (output / "oversized.json").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
