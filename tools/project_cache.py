"""Provider-neutral structured project-cache mechanics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProjectCacheSpec:
    """Describe one provider's structured project cache."""

    path: Path
    refresh_command: str


class ProjectCacheError(RuntimeError):
    """Raised when a structured project cache cannot be loaded or updated."""


def empty_project_cache() -> dict[str, Any]:
    """Return the structured project-cache shape used by provider tooling."""
    return {"schema_version": 2, "projects": {}, "aliases": {}, "errors": {}}


def load_project_cache(spec: ProjectCacheSpec) -> dict[str, Any]:
    """Load and validate a provider project cache, or return an empty cache."""
    if not spec.path.exists():
        return empty_project_cache()

    cache = json.loads(spec.path.read_text(encoding="utf-8-sig"))
    return normalize_project_cache(cache, spec)


def normalize_project_cache(cache: Any, spec: ProjectCacheSpec) -> dict[str, Any]:
    """Validate and return the common schema-v2 project-cache shape."""
    has_supported_shape = (
        isinstance(cache, dict)
        and cache.get("schema_version") == 2
        and isinstance(cache.get("projects"), dict)
        and isinstance(cache.get("aliases"), dict)
    )
    if not has_supported_shape:
        raise ProjectCacheError(
            f"{spec.path} uses an unsupported format. "
            f"Delete it and run {spec.refresh_command} to rebuild the cache."
        )

    cache.setdefault("errors", {})
    if not isinstance(cache["errors"], dict):
        raise ProjectCacheError(
            f"{spec.path} has an invalid errors section. "
            f"Delete it and run {spec.refresh_command} to rebuild the cache."
        )
    return cache


def cache_entry_has_error(entry: Any) -> bool:
    """Return whether a cached API entry represents an unresolved fetch error."""
    return isinstance(entry, dict) and "error" in entry


def collect_cache_errors(cache: dict[str, Any], cache_name: str) -> list[str]:
    """Collect errors from a structured project cache or flat version cache."""
    structured_errors = cache.get("errors")
    entries = structured_errors if isinstance(structured_errors, dict) else cache
    return [
        f"{cache_name}:{cache_key}: {entry.get('error')}"
        for cache_key, entry in sorted(entries.items())
        if cache_entry_has_error(entry)
    ]


def get_project_cache_entry(project_ref: str, cache: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve a project id or slug against a structured project cache."""
    if not project_ref:
        return None

    projects = cache.get("projects", {})
    aliases = cache.get("aliases", {})
    if not isinstance(projects, dict) or not isinstance(aliases, dict):
        return None

    project_id = project_ref if project_ref in projects else aliases.get(project_ref)
    entry = projects.get(project_id) if project_id else None
    if not isinstance(entry, dict) or cache_entry_has_error(entry):
        return None
    return entry


def get_project_cache_error(project_ref: str, cache: dict[str, Any]) -> dict[str, Any] | None:
    """Return a stored fetch error for a project id or lookup alias."""
    errors = cache.get("errors", {})
    aliases = cache.get("aliases", {})
    if not isinstance(errors, dict) or not isinstance(aliases, dict):
        return None

    error_entry = errors.get(project_ref)
    if cache_entry_has_error(error_entry):
        return error_entry

    project_id = aliases.get(project_ref)
    error_entry = errors.get(project_id) if project_id else None
    return error_entry if cache_entry_has_error(error_entry) else None


def project_cache_has_entry(project_ref: str, cache: dict[str, Any]) -> bool:
    return get_project_cache_entry(project_ref, cache) is not None


def project_cache_project_count(cache: dict[str, Any]) -> int:
    """Return the number of unique project metadata entries in a project cache."""
    projects = cache.get("projects", {})
    return len(projects) if isinstance(projects, dict) else 0


def project_cache_alias_count(cache: dict[str, Any]) -> int:
    """Return the number of alias keys in a structured project cache."""
    aliases = cache.get("aliases", {})
    return len(aliases) if isinstance(aliases, dict) else 0


def set_project_cache_error(
    project_ref: str,
    cache: dict[str, Any],
    error: str,
    *,
    retryable: bool,
) -> None:
    """Store a project fetch error under the lookup ref that failed."""
    errors = cache.get("errors")
    if not isinstance(errors, dict):
        raise ProjectCacheError("Structured project cache has no valid errors section.")
    errors[project_ref] = {"error": error, "retryable": retryable}


def store_project_cache_entry(
    cache: dict[str, Any],
    entry: dict[str, Any],
    *,
    project_id: str,
    slug: str = "",
    lookup_key: str | None = None,
) -> dict[str, Any]:
    """Store one project and map its stable lookup aliases to the project id."""
    projects = cache.get("projects")
    aliases = cache.get("aliases")
    errors = cache.get("errors")
    if not isinstance(projects, dict) or not isinstance(aliases, dict) or not isinstance(errors, dict):
        raise ProjectCacheError("Structured project cache has an invalid shape.")

    projects[project_id] = entry
    aliases[project_id] = project_id

    lookup_refs = {project_id}
    if lookup_key:
        aliases[lookup_key] = project_id
        lookup_refs.add(lookup_key)
    if slug:
        normalized_slug = slug.lower()
        aliases[normalized_slug] = project_id
        lookup_refs.add(normalized_slug)

    for lookup_ref in lookup_refs:
        errors.pop(lookup_ref, None)
    return entry
