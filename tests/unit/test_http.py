from __future__ import annotations

import gzip
import http.client
import io
import random
import unittest
import urllib.error
from email.message import Message
from unittest import mock

from radar.errors import FetchError
from radar.http import FetchPolicy, fetch_bytes


class BodyResponse(io.BytesIO):
    def __init__(self, body: bytes, headers: list[tuple[str, str]]) -> None:
        super().__init__(body)
        self.headers = Message()
        for name, value in headers:
            self.headers[name] = value
        self.status = 200
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        result = super().read(size)
        self.bytes_read += len(result)
        return result


class HttpBodyTests(unittest.TestCase):
    def fetch(
        self,
        body: bytes,
        *,
        encoding: str | None = "gzip",
        maximum_bytes: int = 1024,
        extra_headers: list[tuple[str, str]] | None = None,
    ) -> tuple[bytes, BodyResponse]:
        headers = [] if encoding is None else [("Content-Encoding", encoding)]
        response = BodyResponse(body, headers + (extra_headers or []))
        self.last_response = response
        with mock.patch("radar.http.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = response
            data, _, status = fetch_bytes(
                "https://feed.example/events.json",
                policy=FetchPolicy(maximum_bytes, 5.0, frozenset({"https://feed.example"})),
            )
        self.assertEqual(200, status)
        return data, response

    def assert_fetch_error(self, reason: str, body: bytes, **kwargs: object) -> None:
        with self.assertRaises(FetchError) as raised:
            self.fetch(body, **kwargs)  # type: ignore[arg-type]
        self.assertEqual(reason, raised.exception.reason)

    def test_gzip_returns_decoded_bytes_and_accepts_exact_decoded_bound(self) -> None:
        original = bytes(range(256)) * 256
        encoded = gzip.compress(original, mtime=0)
        data, response = self.fetch(encoded, maximum_bytes=len(original), encoding=" GZip ")
        self.assertEqual(original, data)
        self.assertEqual(len(encoded), response.bytes_read)

    def test_gzip_expansion_stops_at_the_decoded_bound(self) -> None:
        encoded = gzip.compress(b"x" * (2 * 1024 * 1024), mtime=0)
        self.assert_fetch_error("too-large", encoded, maximum_bytes=4096)

    def test_gzip_decodes_across_network_chunk_boundaries(self) -> None:
        original = random.Random(0).randbytes(128 * 1024)
        encoded = gzip.compress(original, mtime=0)
        self.assertEqual(original, self.fetch(encoded, maximum_bytes=len(encoded))[0])

    def test_gzip_members_share_the_same_decoded_bound(self) -> None:
        encoded = gzip.compress(b"x" * 512, mtime=0) + gzip.compress(b"y" * 512, mtime=0)
        self.assertEqual(b"x" * 512 + b"y" * 512, self.fetch(encoded)[0])
        self.assert_fetch_error("too-large", encoded, maximum_bytes=1023)

    def test_gzip_members_cannot_bypass_the_total_timeout(self) -> None:
        encoded = gzip.compress(b"x", mtime=0) + gzip.compress(b"y", mtime=0)
        with mock.patch("radar.http.time.monotonic", side_effect=[0, 0, 0, 6]):
            self.assert_fetch_error("timeout", encoded)

    def test_gzip_encoded_body_is_bounded_even_when_it_expands_to_two_bytes(self) -> None:
        encoded = bytearray(gzip.compress(b"{}", mtime=0))
        encoded[3] = 8  # A long original filename occupies wire bytes without decoded output.
        body = bytes(encoded[:10]) + b"x" * 2048 + b"\0" + bytes(encoded[10:])
        self.assert_fetch_error("too-large", body, maximum_bytes=1024)
        self.assertEqual(1025, self.last_response.bytes_read)

    def test_oversized_declared_length_rejects_before_reading(self) -> None:
        self.assert_fetch_error("too-large", b"", extra_headers=[("Content-Length", "1025")])
        self.assertEqual(0, self.last_response.bytes_read)

    def test_identity_fallback_and_wire_limit_remain_supported(self) -> None:
        for encoding in (None, "identity"):
            with self.subTest(encoding=encoding):
                self.assertEqual(b"x" * 1024, self.fetch(b"x" * 1024, encoding=encoding)[0])
                self.assert_fetch_error("too-large", b"x" * 1025, encoding=encoding)

    def test_rejects_corrupt_truncated_and_trailing_gzip_data(self) -> None:
        encoded = gzip.compress(b'{"valid": true}', mtime=0)
        corrupt_crc = encoded[:-8] + bytes([encoded[-8] ^ 1]) + encoded[-7:]
        for body in (
            b"",
            b"not gzip",
            encoded[:5],
            encoded[:-8],
            encoded[:-1],
            corrupt_crc,
            encoded + b"trailing data",
            encoded + gzip.compress(b"", mtime=0)[:-1],
        ):
            with self.subTest(body=body):
                self.assert_fetch_error("http-error", body)

    def test_only_one_supported_content_encoding_is_accepted(self) -> None:
        for encoding in ("", "br", "deflate", "gzip, gzip", "gzip, identity"):
            with self.subTest(encoding=encoding):
                self.assert_fetch_error("http-error", b"{}", encoding=encoding)
                self.assertEqual(0, self.last_response.bytes_read)
        self.assert_fetch_error("http-error", b"{}", extra_headers=[("Content-Encoding", "identity")])

    def test_short_http_body_cannot_pass_as_complete_json_or_gzip(self) -> None:
        for encoding, body in ((None, b"{}"), ("gzip", gzip.compress(b"{}", mtime=0))):
            with self.subTest(encoding=encoding):
                self.assert_fetch_error(
                    "http-error", body, encoding=encoding,
                    extra_headers=[("Content-Length", str(len(body) + 1))],
                )

    def test_truncated_chunked_http_returns_a_typed_error(self) -> None:
        with mock.patch.object(BodyResponse, "read", side_effect=http.client.IncompleteRead(b"{")):
            self.assert_fetch_error("http-error", b"{}", encoding=None)

    def test_304_remains_bodyless_even_when_it_describes_a_gzip_representation(self) -> None:
        headers = Message()
        headers["Content-Encoding"] = "gzip"
        headers["Content-Length"] = "5000"
        headers["ETag"] = '"edition"'
        not_modified = urllib.error.HTTPError("https://feed.example/events.json", 304, "Not Modified", headers, None)
        with mock.patch("radar.http.urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = not_modified
            data, response_headers, status = fetch_bytes(
                "https://feed.example/events.json",
                policy=FetchPolicy(1024, 5.0, frozenset({"https://feed.example"})),
                allow_not_modified=True,
            )
        self.assertEqual(304, status)
        self.assertEqual(b"", data)
        self.assertEqual('"edition"', response_headers["ETag"])


if __name__ == "__main__":
    unittest.main()
