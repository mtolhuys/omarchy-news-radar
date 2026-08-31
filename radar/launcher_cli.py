"""Command-line boundary for explicit application-launcher management."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .errors import RadarError
from .launcher import inspect, install, remove


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="news-radar-launcher")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("install")
    commands.add_parser("remove")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = inspect()
        elif args.command == "install":
            result = install()
        else:
            result = remove()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except RadarError as exc:
        print(
            json.dumps({"status": "refused", "message": str(exc)}, sort_keys=True, indent=2),
            file=sys.stderr,
        )
        print(
            "No launcher file was overwritten. Resolve the reported target explicitly and retry.",
            file=sys.stderr,
        )
        return 2


raise SystemExit(main())
