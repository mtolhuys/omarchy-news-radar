#!/usr/bin/python3
"""Create synthetic visual/runtime states inside a disposable guest."""

from __future__ import annotations

import copy
import hashlib
import json
import struct
import sys
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def fixture_png(width: int = 720, height: int = 405) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            paper = 238 if 34 < x < width - 34 and 28 < y < height - 28 else 24
            if paper == 238 and (48 < y < 70 or (90 < y < 340 and (x // 32) % 3 == 0)):
                color = (40, 50, 54)
            elif paper == 238 and x < width // 2 and 92 < y < 238:
                color = (63, 146, 166)
            else:
                color = (paper, paper, paper - 4 if paper > 40 else paper)
            row.extend(color)
        rows.append(bytes(row))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b"")


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
    feed["publishedAt"] = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    image_bytes = fixture_png()
    image_digest = hashlib.sha256(image_bytes).hexdigest()
    image_path = f"assets/images/{image_digest}.png"
    (output / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (output / image_path).write_bytes(image_bytes)
    # Front Page deterministically promotes the newest Omarchy release ahead
    # of routine plugin events. Put the visual on that actual lead rather than
    # relying on raw source-array order.
    pictured = next(event for event in feed["events"] if event["type"] == "omarchy-released")
    pictured["image"] = {
        "path": image_path,
        "alt": "Synthetic newspaper preview for Plugin Lab acceptance",
        "credit": "News Radar test fixture",
        "width": 720,
        "height": 405,
    }
    plugin_release = next(event for event in feed["events"] if event["type"] == "plugin-released")
    plugin_release["image"] = copy.deepcopy(pictured["image"])
    # Reproduce the historical feed shape that made With images look broken:
    # the reader hides this unrelated marketing art on verification changes.
    verification = next(
        event for event in feed["events"] if event["type"] == "plugin-verification-changed"
    )
    verification["image"] = copy.deepcopy(pictured["image"])
    write(output / "valid.json", feed)

    background = copy.deepcopy(feed)
    background["generatedAt"] = "2026-08-31T14:01:00Z"
    background["window"]["through"] = "2026-08-31T14:01:00Z"
    background_event = event_clone(
        feed["events"][0],
        0xBEE,
        datetime(2026, 8, 31, 14, 1, tzinfo=timezone.utc),
    )
    background_event["discoveredAt"] = "2026-08-31T14:01:00Z"
    background_event["title"] = "A background-only unread arrival"
    background["events"].insert(0, background_event)
    write(output / "background.json", background)

    stale = copy.deepcopy(feed)
    stale["generatedAt"] = "2026-08-31T14:01:00Z"
    stale["window"]["through"] = "2026-08-31T14:01:00Z"
    stale["publishedAt"] = "2026-08-31T14:01:00Z"
    write(output / "stale.json", stale)

    recovered = copy.deepcopy(feed)
    recovered["generatedAt"] = "2026-08-31T14:02:00Z"
    recovered["window"]["through"] = "2026-08-31T14:02:00Z"
    write(output / "recovered.json", recovered)

    later = copy.deepcopy(feed)
    later["generatedAt"] = "2026-08-31T14:03:00Z"
    later["window"]["through"] = "2026-08-31T14:03:00Z"
    newest = event_clone(feed["events"][0], 0xABC, datetime(2026, 8, 31, 14, 1, tzinfo=timezone.utc))
    newest["discoveredAt"] = "2026-08-31T14:02:00Z"
    newest["title"] = "An event that arrived during the open session"
    newest["entity"] = {"kind": "plugin", "id": "io.github.mtolhuys.disk-lens", "name": "Omarchy Disk Lens", "version": "0.4.2", "repository": "https://github.com/mtolhuys/omarchy-disk-lens"}
    newest["source"] = {"label": "Synthetic release", "url": "https://github.com/mtolhuys/omarchy-disk-lens/releases/tag/v0.4.2"}
    newest["summary"] = "This synthetic event proves that refresh and close cannot mark an unselected story as read."
    later["events"].insert(0, newest)
    write(output / "later.json", later)

    partial = copy.deepcopy(later)
    partial["generatedAt"] = "2026-08-31T14:04:00Z"
    partial["window"]["through"] = "2026-08-31T14:04:00Z"
    for source_health in partial["sources"]:
        if source_health["id"] == "marketplace":
            source_health["status"] = "failed"
            source_health["reason"] = "timeout"
    write(output / "partial.json", partial)

    empty = copy.deepcopy(later)
    empty["generatedAt"] = "2026-08-31T14:05:00Z"
    empty["window"]["through"] = "2026-08-31T14:05:00Z"
    empty["events"] = []
    write(output / "empty.json", empty)

    long_text = copy.deepcopy(later)
    long_text["generatedAt"] = "2026-08-31T14:07:00Z"
    long_text["window"]["through"] = "2026-08-31T14:07:00Z"
    long_text["events"][0]["title"] = "長い見出し — " + "Keyboard-first Omarchy panel text " * 4
    long_text["events"][0]["summary"] = "Unicode remains inert plain text. " + "This deliberately long summary checks wrapping, clipping, and inspector scrolling. " * 4
    write(output / "long.json", long_text)

    dense = copy.deepcopy(feed)
    dense["generatedAt"] = "2026-08-31T14:06:00Z"
    dense["window"]["through"] = "2026-08-31T14:06:00Z"
    start = datetime(2026, 8, 31, 14, 3, tzinfo=timezone.utc)
    dense["events"] = [event_clone(feed["events"][0], 1000 + index, start - timedelta(minutes=index)) for index in range(120)]
    write(output / "dense.json", dense)

    (output / "malformed.json").write_text("{not-json", encoding="utf-8")
    (output / "oversized.json").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
