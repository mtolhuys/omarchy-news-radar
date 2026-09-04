"""Bounded HTTPS retrieval with closed redirect origins."""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, Mapping
from urllib.parse import urljoin, urlsplit

from .errors import FetchError


@dataclass(frozen=True)
class FetchPolicy:
    maximum_bytes: int
    timeout_seconds: float
    allowed_origins: frozenset[str]
    maximum_redirects: int = 2
    allow_loopback_http: bool = False


def _allowed_url(url: str, policy: FetchPolicy) -> bool:
    parsed = urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in policy.allowed_origins or parsed.username or parsed.password:
        return False
    if parsed.scheme == "https":
        return True
    if not policy.allow_loopback_http or parsed.scheme != "http" or not parsed.hostname:
        return False
    try:
        return ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False


class ClosedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, policy: FetchPolicy) -> None:
        self.policy = policy
        self.redirects = 0

    def redirect_request(self, request: urllib.request.Request, response: Any, code: int, message: str, headers: Any, new_url: str) -> urllib.request.Request | None:
        self.redirects += 1
        resolved = urljoin(request.full_url, new_url)
        if self.redirects > self.policy.maximum_redirects or not _allowed_url(resolved, self.policy):
            raise FetchError("http-error", "redirect left the allowlisted HTTPS origin")
        return super().redirect_request(request, response, code, message, headers, resolved)


def fetch_bytes(
    url: str,
    *,
    policy: FetchPolicy,
    headers: Mapping[str, str] | None = None,
    allow_not_modified: bool = False,
) -> tuple[bytes, Mapping[str, str], int]:
    if not _allowed_url(url, policy):
        raise FetchError("validation-failed", "request URL is outside the allowlist")
    request_headers = {"User-Agent": "omarchy-news-radar/0.1 (+https://github.com/mtolhuys/omarchy-news-radar)", "Accept": "application/json"}
    request_headers.update(dict(headers or {}))
    request = urllib.request.Request(url, headers=request_headers, method="GET")
    opener = urllib.request.build_opener(ClosedRedirectHandler(policy), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    started = time.monotonic()
    try:
        with opener.open(request, timeout=policy.timeout_seconds) as response:
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    declared_length = int(content_length)
                except ValueError as exc:
                    raise FetchError("http-error", "response returned an invalid Content-Length") from exc
                if declared_length < 0:
                    raise FetchError("http-error", "response returned an invalid Content-Length")
                if declared_length > policy.maximum_bytes:
                    raise FetchError("too-large", "response exceeds the configured size bound")
            chunks: list[bytes] = []
            total = 0
            while True:
                if time.monotonic() - started > policy.timeout_seconds:
                    raise FetchError("timeout", "request exceeded its total timeout")
                chunk = response.read(min(64 * 1024, policy.maximum_bytes + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > policy.maximum_bytes:
                    raise FetchError("too-large", "response exceeds the configured size bound")
                chunks.append(chunk)
            return b"".join(chunks), dict(response.headers.items()), int(response.status)
    except FetchError:
        raise
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and allow_not_modified:
            response_headers = dict(exc.headers.items()) if exc.headers else {}
            exc.close()
            return b"", response_headers, 304
        rate_remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
        reason = "rate-limited" if exc.code == 429 or (exc.code == 403 and rate_remaining == "0") else "http-error"
        exc.close()
        raise FetchError(reason, f"server returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        detail = str(getattr(exc, "reason", exc)).lower()
        reason = "timeout" if "timed out" in detail else "network-error"
        raise FetchError(reason, "network request failed") from exc


def decode_json(data: bytes, *, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FetchError("invalid-json", f"{label} returned invalid UTF-8 JSON") from exc
