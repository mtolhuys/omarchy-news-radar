"""Extract bounded plain-text explanations from explicitly selected GitHub releases."""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import unquote, urlsplit

from ..errors import ValidationError
from ..http import FetchPolicy, decode_json, fetch_bytes
from ..insights import MAX_CHANGES, MAX_RELEASES
from ..validation import normalize_text, parse_timestamp, validate_https_url
from .omarchy_releases import IMAGE_RE, LINK_RE, TAG_RE

REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_NOTES_BYTES = 2 * 1024 * 1024
BULLET_RE = re.compile(r"^\s*(?:[-*+] |\d+\. )(.+)$")
FENCE_LINE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")


def _without_code_blocks(value: str) -> str:
    """Code examples are not release changes, even when they contain bullets."""
    result = []
    marker = ""
    for line in value.splitlines():
        if marker:
            if re.fullmatch(r"[ \t]*" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}[ \t]*", line):
                marker = ""
            continue
        fence = FENCE_LINE_RE.match(line)
        if fence and (fence[1][0] != "`" or "`" not in fence[2]):
            marker = fence[1]
            result.append("")
        elif line.expandtabs(4).startswith("    "):
            result.append("")
        else:
            result.append(line)
    # An unterminated fence consumes the rest of the source, as Markdown does.
    return "\n".join(result)


def _plain(value: str, maximum: int) -> str:
    text = _without_code_blocks(value)
    text = IMAGE_RE.sub("", text)
    text = LINK_RE.sub(r"\1", text)
    text = TAG_RE.sub("", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = html.unescape(text.replace("`", "").replace("**", "").replace("__", ""))
    text = "\n".join(" ".join(line.split()) for line in text.splitlines()).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text if len(text) <= maximum else text[:maximum - 1].rstrip() + "…"


def parse_release_notes(payload: Any, repository: str) -> list[dict[str, Any]]:
    """No inference, installation recipes, remote Markdown rendering, or follow-up fetches."""
    if not REPOSITORY_RE.fullmatch(repository) or not isinstance(payload, list) or len(payload) > MAX_RELEASES:
        raise ValidationError("release explanation source is invalid")
    result = []
    versions: set[str] = set()
    prefix = f"https://github.com/{repository}/releases/tag/"
    for raw in payload:
        if not isinstance(raw, dict):
            raise ValidationError("release explanation must be an object")
        if any(type(raw.get(flag, False)) is not bool for flag in ("draft", "prerelease")):
            raise ValidationError("release explanation flags must be boolean")
        if raw.get("draft") or raw.get("prerelease"):
            continue
        version = normalize_text(raw.get("tag_name"), 80)
        if version in versions:
            raise ValidationError("release explanation versions must be unique")
        versions.add(version)
        source = validate_https_url(raw.get("html_url"))
        if not source.startswith(prefix) or len(source) == len(prefix):
            raise ValidationError("release explanation URL does not match its reviewed repository")
        parsed = urlsplit(source)
        if parsed.query or parsed.fragment or unquote(source[len(prefix):]) != version:
            raise ValidationError("release explanation URL does not match its version")
        published = raw.get("published_at")
        parse_timestamp(published)
        body = raw.get("body") or ""
        if not isinstance(body, str) or len(body) > 128 * 1024:
            raise ValidationError("release explanation text exceeds its bound")
        changes = []
        for line in _without_code_blocks(body).splitlines():
            match = BULLET_RE.match(line)
            text = _plain(match.group(1), 1000) if match else ""
            if text and len(changes) < MAX_CHANGES:
                changes.append({"text": " ".join(text.split()), "sourceUrl": source})
        result.append({"version": version, "publishedAt": published,
                       "title": normalize_text(raw.get("name") or version, 200),
                       "summary": _plain(body, 8000), "changes": changes, "sourceUrl": source})
    return sorted(result, key=lambda item: (item["publishedAt"], item["version"]), reverse=True)


def fetch_release_notes(repository: str, *, github_token: str | None = None) -> list[dict[str, Any]]:
    if not REPOSITORY_RE.fullmatch(repository):
        raise ValidationError("release explanation repository is invalid")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    data, _, _ = fetch_bytes(
        f"https://api.github.com/repos/{repository}/releases?per_page={MAX_RELEASES}&page=1",
        policy=FetchPolicy(MAX_NOTES_BYTES, 15, frozenset({"https://api.github.com"}), maximum_redirects=0),
        headers=headers,
    )
    return parse_release_notes(decode_json(data, label="release explanations"), repository)
