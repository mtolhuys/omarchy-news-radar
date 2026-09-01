#!/usr/bin/python3
"""Loopback-only Plugin Lab feed server with an opt-in bounded delay."""

from __future__ import annotations

import argparse
import os
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        if self.path.split("?", 1)[0] == "/current.json":
            delay_path = Path(self.directory) / "delay-seconds"
            try:
                delay = float(delay_path.read_text(encoding="ascii").strip())
            except (FileNotFoundError, OSError, UnicodeError, ValueError):
                delay = 0.0
            if 0.0 < delay <= 5.0:
                time.sleep(delay)
        super().do_GET()

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()
    os.chdir(args.directory)
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        lambda *values, **options: Handler(*values, directory=str(args.directory), **options),
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
