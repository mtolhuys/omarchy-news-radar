#!/usr/bin/python3
"""Capture bounded compositor observations and animation frames in a lab guest."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

TITLE = "📰 Omarchy News Radar"
NEIGHBORS = {"Radar Opening Neighbor", "Radar Opening Neighbor 2", "Radar Opening Neighbor 3"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    next_frame = 0.0
    frames = 0
    samples = []
    first_map = False
    while time.monotonic() - started < 5:
        clients = json.loads(subprocess.run(["hyprctl", "clients", "-j"], capture_output=True,
                                            text=True, check=True, timeout=1).stdout)
        elapsed = time.monotonic() - started
        radar = [c for c in clients if c.get("title") == TITLE]
        neighbor = [c for c in clients if c.get("title") in NEIGHBORS]
        samples.append({"elapsed": elapsed, "radar": radar, "neighbor": neighbor})
        if radar and not first_map:
            first_map = True
            result = subprocess.run(["omarchy-shell", "shell", "call", "io.github.mtolhuys.news-radar", "debugState", ""],
                                    capture_output=True, text=True, check=True, timeout=2)
            (args.directory / "first-map-state.json").write_text(result.stdout)
        if elapsed >= next_frame:
            subprocess.run(["grim", str(args.directory / f"frame-{frames:03d}.png")], check=True, timeout=2)
            frames += 1
            next_frame = elapsed + 0.1
        time.sleep(0.01)
    (args.directory / "samples.json").write_text(json.dumps(samples))
    (args.directory / "done").write_text(str(frames))


if __name__ == "__main__":
    main()
