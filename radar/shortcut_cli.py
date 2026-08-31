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
    installer = commands.add_parser("install")
    installer.add_argument("--replace-default-editor", action="store_true")
    commands.add_parser("remove")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = {"status": "ok", **inspect().public()}
        elif args.command == "install":
            result = install(replace_default_editor=args.replace_default_editor)
        else:
            result = remove()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if result.get("status") != "authorization-required" else 3
    except ShortcutError as exc:
        print(json.dumps({"status": "refused", "message": str(exc)}, sort_keys=True, indent=2), file=sys.stderr)
        print("Manual fallback: choose a different key in ~/.config/hypr/bindings.lua; Radar remains openable through shell IPC.", file=sys.stderr)
        return 2


raise SystemExit(main())
