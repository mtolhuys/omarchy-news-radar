"""Conservative ownership checks before joining historical stories to current notes."""

import re
from typing import Any, Mapping
from urllib.parse import unquote, urlsplit

_REPOSITORY_PART = re.compile(r"[A-Za-z0-9_.-]+")


def _github_repository(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        return None
    decoded_path = unquote(parsed.path)
    if (
        "\\" in decoded_path or re.search(r"%2f|%5c", parsed.path, re.IGNORECASE)
        or any(part in {".", ".."} for part in decoded_path.split("/")) or parsed.path.startswith("//")
    ):
        return None
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2 or any(part in {".", ".."} or not _REPOSITORY_PART.fullmatch(part) for part in parts[:2]):
        return None
    return parts[0].lower(), parts[1].lower()


def project_matches_event_source(event: Mapping[str, Any], project: Mapping[str, Any]) -> bool:
    """Require the historical event and current project to establish one repository.

    Repository-owned enrichment currently covers GitHub only. Missing provenance
    stays unknown; entity ID or a familiar version alone never proves ownership.
    Source links may point below the repository, such as its releases index.
    """
    entity = event.get("entity")
    source = project.get("source")
    if not isinstance(entity, Mapping) or not isinstance(source, Mapping):
        return False
    if entity.get("id") != project.get("id") or entity.get("kind") != project.get("kind"):
        return False
    repository = _github_repository(entity.get("repository"))
    return repository is not None and repository == _github_repository(source.get("url"))


def release_matches_event_source(
    event: Mapping[str, Any], project: Mapping[str, Any], release: Mapping[str, Any],
) -> bool:
    """Additionally require the selected release to belong to that repository."""
    return (
        project_matches_event_source(event, project)
        and _github_repository(event["entity"]["repository"]) == _github_repository(release.get("sourceUrl"))
    )
