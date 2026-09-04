from __future__ import annotations

import copy
import json
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from radar.client import refresh
from radar.constants import FEED_MAX_BYTES

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class FixtureServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:  # type: ignore[no-untyped-def]
        return


class FeedHandler(BaseHTTPRequestHandler):
    feed = (ROOT / "tests/fixtures/feed-valid.json").read_bytes()
    etag = '"fixture-v1"'
    last_modified = "Mon, 31 Aug 2026 14:00:00 GMT"
    requests: list[dict[str, str]] = []

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, body: bytes, *, status: int = 200, declared: int | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body) if declared is None else declared))
        self.send_header("ETag", type(self).etag)
        self.send_header("Last-Modified", type(self).last_modified)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self) -> None:
        type(self).requests.append(
            {
                "method": self.command,
                "path": self.path,
                "accept": self.headers.get("Accept", ""),
                "userAgent": self.headers.get("User-Agent", ""),
                "ifNoneMatch": self.headers.get("If-None-Match", ""),
                "ifModifiedSince": self.headers.get("If-Modified-Since", ""),
            }
        )
        if self.path == "/feed":
            if (
                self.headers.get("If-None-Match") == type(self).etag
                or self.headers.get("If-Modified-Since") == type(self).last_modified
            ):
                self.send_response(304)
                self.send_header("ETag", type(self).etag)
                self.send_header("Last-Modified", type(self).last_modified)
                self.end_headers()
            else:
                self._send(self.feed)
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/feed")
            self.end_headers()
        elif self.path == "/redirect-away":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/feed")
            self.end_headers()
        elif self.path == "/truncated":
            self._send(b"{")
        elif self.path == "/oversized":
            self._send(b"", declared=FEED_MAX_BYTES + 1)
        elif self.path == "/bad-length":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "not-a-number")
            self.end_headers()
        elif self.path == "/unsupported":
            value = json.loads(self.feed)
            value["schemaVersion"] = 99
            self._send(json.dumps(value).encode("utf-8"))
        elif self.path == "/future":
            value = json.loads(self.feed)
            value["generatedAt"] = "2027-01-01T00:00:00Z"
            self._send(json.dumps(value).encode("utf-8"))
        elif self.path == "/slow":
            time.sleep(0.2)
            self._send(self.feed)
        elif self.path == "/rate":
            self.send_response(429)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self._send(b"{}", status=404)


class ClientNetworkIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        FeedHandler.requests = []
        FeedHandler.etag = '"fixture-v1"'
        FeedHandler.last_modified = "Mon, 31 Aug 2026 14:00:00 GMT"
        self.server = FixtureServer(("127.0.0.1", 0), FeedHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.environment = {
            "HOME": str(root / "home"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_STATE_HOME": str(root / "state"),
            "OMARCHY_NEWS_RADAR_TEST_MODE": "1",
            "OMARCHY_NEWS_RADAR_TEST_FEED_URL": self.origin + "/feed",
        }

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def test_success_and_same_origin_redirect_use_bounded_get_contract(self) -> None:
        result = refresh(self.environment, now=CLOCK)
        self.assertEqual("updated", result["status"])
        self.environment["OMARCHY_NEWS_RADAR_TEST_FEED_URL"] = self.origin + "/redirect"
        self.assertEqual("no-change", refresh(self.environment, now=CLOCK)["status"])
        self.assertEqual(["/feed", "/redirect", "/feed"], [item["path"] for item in FeedHandler.requests])
        for request in FeedHandler.requests:
            self.assertEqual("GET", request["method"])
            self.assertEqual("application/json", request["accept"])
            self.assertEqual("omarchy-news-radar-client/0.4.16", request["userAgent"])

    def test_repeated_refresh_uses_conditional_get_and_keeps_valid_cache_on_304(self) -> None:
        first = refresh(self.environment, now=CLOCK)
        self.assertEqual("updated", first["status"])

        second = refresh(self.environment, now=CLOCK)
        self.assertEqual("no-change", second["status"])
        self.assertTrue(second["cachePreserved"])
        self.assertEqual(2, len(FeedHandler.requests))
        self.assertEqual('"fixture-v1"', FeedHandler.requests[1]["ifNoneMatch"])
        self.assertEqual(
            "Mon, 31 Aug 2026 14:00:00 GMT",
            FeedHandler.requests[1]["ifModifiedSince"],
        )

    def test_network_and_candidate_failures_preserve_last_known_good(self) -> None:
        self.assertEqual("updated", refresh(self.environment, now=CLOCK)["status"])
        expectations = {
            "/redirect-away": "offline",
            "/truncated": "invalid-feed",
            "/oversized": "invalid-feed",
            "/bad-length": "offline",
            "/unsupported": "invalid-feed",
            "/future": "invalid-feed",
            "/rate": "offline",
        }
        for path, expected in expectations.items():
            with self.subTest(path=path):
                self.environment["OMARCHY_NEWS_RADAR_TEST_FEED_URL"] = self.origin + path
                result = refresh(self.environment, now=CLOCK)
                self.assertEqual(expected, result["status"])
                self.assertTrue(result["cachePreserved"])
                self.assertIsNotNone(result["feed"])
                if path == "/rate":
                    self.assertEqual("rate-limited", result["reason"])
                if path == "/bad-length":
                    self.assertEqual("http-error", result["reason"])

    def test_total_timeout_is_bounded_and_preserves_cache(self) -> None:
        self.assertEqual("updated", refresh(self.environment, now=CLOCK)["status"])
        self.environment["OMARCHY_NEWS_RADAR_TEST_FEED_URL"] = self.origin + "/slow"
        self.environment["OMARCHY_NEWS_RADAR_TEST_TIMEOUT_SECONDS"] = "0.05"
        started = time.monotonic()
        result = refresh(self.environment, now=CLOCK)
        self.assertEqual("offline", result["status"])
        self.assertEqual("timeout", result["reason"])
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertTrue(result["cachePreserved"])

    def test_test_url_boundary_cannot_redirect_or_target_non_loopback_http(self) -> None:
        self.environment["OMARCHY_NEWS_RADAR_TEST_FEED_URL"] = "http://example.com/feed"
        result = refresh(self.environment, now=CLOCK)
        self.assertEqual("offline", result["status"])
        self.assertEqual("validation-failed", result["reason"])
        self.assertEqual([], FeedHandler.requests)

    def test_test_variables_are_ignored_without_the_explicit_mode(self) -> None:
        environment = dict(self.environment)
        del environment["OMARCHY_NEWS_RADAR_TEST_MODE"]
        production = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))
        with mock.patch("radar.client._fetch_feed", return_value=copy.deepcopy(production)) as fetch:
            result = refresh(environment, now=CLOCK)
        self.assertEqual("updated", result["status"])
        fetch.assert_called_once_with()
        self.assertEqual([], FeedHandler.requests)


if __name__ == "__main__":
    unittest.main()
