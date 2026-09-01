"""Command-line boundary for explicit shortcut management."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .errors import ShortcutError
from .shortcut import inspect, install, remove


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="news-radar-shortcut")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("install")
    commands.add_parser("remove")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = {"protocolVersion": 1, "status": "ok", **inspect().public()}
        elif args.command == "install":
            result = {"protocolVersion": 1, **install()}
        else:
            result = {"protocolVersion": 1, **remove()}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except ShortcutError as exc:
        print(
            json.dumps({"protocolVersion": 1, "status": "refused", "message": str(exc)}, sort_keys=True, indent=2),
            file=sys.stderr,
        )
        print("Manual fallback: choose a free key in ~/.config/hypr/bindings.lua; Radar remains openable through shell IPC.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
