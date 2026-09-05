#!/usr/bin/python3
"""Build small source-linked briefing fixtures for the disposable guest."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from radar.io import atomic_write_json
from radar.model import event_sort_key
from radar.validation import validate_feed


def timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--now", help="An explicit UTC clock for deterministic fixture checks")
    args = parser.parse_args()
    clock = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    clock = clock.replace(microsecond=0)
    feed = json.loads(args.source.read_text(encoding="utf-8"))
    generated = clock - timedelta(minutes=5)
    core = next(event for event in feed["events"] if event["type"] == "omarchy-released")
    plugin = next(event for event in feed["events"] if event["type"] == "plugin-released")

    def event(template: dict, identity: int, title: str, age: timedelta) -> dict:
        result = copy.deepcopy(template)
        result.pop("metrics", None)
        result.pop("image", None)
        result["id"] = f"evt_{identity:024x}"
        result["title"] = title
        result["summary"] = "Synthetic Plugin Lab story. Its original source remains available; no compatibility or impact claim is inferred."
        result["occurredAt"] = timestamp(clock - age)
        result["discoveredAt"] = timestamp(generated)
        result["source"] = {"label": "Synthetic source", "url": f"https://github.com/example/radar-fixture/releases/tag/{identity}"}
        return result

    events = [
        event(core, 0xC01, "Synthetic core update: a calmer desktop", timedelta(days=1)),
        event(core, 0xC02, "Synthetic core update: more predictable workspaces", timedelta(days=1, hours=1)),
    ]
    events[1]["type"] = "omarchy-news"
    events[1]["entity"] = {"kind": "omarchy", "id": "synthetic-workspaces", "name": "Synthetic Omarchy News"}
    events[1]["source"] = {"label": "Synthetic Omarchy News", "url": "https://omarchy.org/news/2026/09/synthetic-workspaces"}
    feed["schemaVersion"] = 2
    for index in range(3):
        item = event(plugin, 0xB01 + index, f"Synthetic Radar release {3 - index}", timedelta(days=1, hours=2, minutes=index))
        item["entity"] = {
            "kind": "plugin", "id": "io.github.mtolhuys.news-radar", "name": "Omarchy News Radar",
            "repository": "https://github.com/mtolhuys/omarchy-news-radar", "version": f"0.0.{3 - index}",
        }
        events.append(item)
    for index in range(3):
        item = event(plugin, 0xD01 + index, f"Synthetic discovery {index + 1}: a useful everyday workflow", timedelta(days=2, hours=index))
        item["type"] = "plugin-added"
        item["entity"] = {
            "kind": "plugin", "id": f"org.example.radar-discovery-{index}", "name": f"Synthetic discovery {index + 1}",
        }
        events.append(item)
    feed["generatedAt"] = timestamp(generated)
    feed["publishedAt"] = timestamp(generated)
    feed["window"] = {"from": timestamp(clock - timedelta(days=30)), "through": timestamp(generated)}
    for health in feed["sources"]:
        health["checkedAt"] = timestamp(generated)
    feed["events"] = sorted(events, key=event_sort_key)
    args.output.mkdir(parents=True, exist_ok=True)
    atomic_write_json(args.output / "initial.json", validate_feed(feed, now=clock, public_only=True))

    later = copy.deepcopy(feed)
    later["generatedAt"] = timestamp(clock - timedelta(minutes=4))
    later["publishedAt"] = later["generatedAt"]
    later["window"]["through"] = later["generatedAt"]
    late = event(events[-1], 0x1A7E, "Synthetic late arrival with an older occurrence date", timedelta(days=5))
    late["discoveredAt"] = later["generatedAt"]
    late["entity"] = {"kind": "plugin", "id": "org.example.radar-late-arrival", "name": "Synthetic late arrival"}
    later["events"] = sorted(later["events"] + [late], key=event_sort_key)
    atomic_write_json(args.output / "later.json", validate_feed(later, now=clock, public_only=True))
    atomic_write_json(args.output / "expected.json", {
        "initialIds": [item["id"] for item in feed["events"]],
        "lateId": late["id"],
        "groupIds": [f"evt_{index:024x}" for index in range(0xB01, 0xB04)],
        "initialGeneratedAt": feed["generatedAt"],
        "laterGeneratedAt": later["generatedAt"],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
