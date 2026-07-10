"""Provider-neutral structured project-cache mechanics."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_CACHE_SCHEMA_VERSION = 4
PROJECT_CACHE_FIELDS = {"schema_version", "projects", "errors"}
PROJECT_CACHE_ENTRY_FIELDS = {"id", "slug", "name", "type"}
LegacyProjectMigration = Callable[[dict[str, Any]], dict[str, str]]


@dataclass(frozen=True)
class ProjectCacheSpec:
    """Describe one provider's structured project cache."""

    path: Path
    refresh_command: str


class ProjectCacheError(RuntimeError):
    """Raised when a structured project cache cannot be loaded or updated."""


def empty_project_cache() -> dict[str, Any]:
    """Return the structured project-cache shape used by provider tooling."""
    return {
        "schema_version": PROJECT_CACHE_SCHEMA_VERSION,
        "projects": {},
        "errors": {},
    }


def load_project_cache(
    spec: ProjectCacheSpec,
    *,
    migrate_legacy_entry: LegacyProjectMigration | None = None,
) -> dict[str, Any]:
    """Load and validate a provider project cache, migrating legacy schemas."""
    if not spec.path.exists():
        return empty_project_cache()

    cache = json.loads(spec.path.read_text(encoding="utf-8-sig"))
    if isinstance(cache, dict) and cache.get("schema_version") in {2, 3}:
        if migrate_legacy_entry is None:
            raise ProjectCacheError(
                f"{spec.path} uses a legacy schema. "
                f"Delete it and run {spec.refresh_command} to rebuild the cache."
            )
        cache = migrate_project_cache(cache, migrate_legacy_entry)
    return normalize_project_cache(cache, spec)


def normalize_project_cache(cache: Any, spec: ProjectCacheSpec) -> dict[str, Any]:
    """Validate and return the common normalized project-cache shape."""
    has_supported_shape = (
        isinstance(cache, dict)
        and cache.get("schema_version") == PROJECT_CACHE_SCHEMA_VERSION
        and isinstance(cache.get("projects"), dict)
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
    if set(cache) != PROJECT_CACHE_FIELDS:
        raise ProjectCacheError(
            f"{spec.path} must contain exactly schema_version, projects, and errors. "
            f"Delete it and run {spec.refresh_command} to rebuild the cache."
        )

    validate_project_cache_entries(cache, spec)
    return cache


def migrate_project_cache(
    legacy_cache: dict[str, Any],
    migrate_legacy_entry: LegacyProjectMigration,
) -> dict[str, Any]:
    """Project legacy entries into the normalized schema-4 shape."""
    migrated_cache = empty_project_cache()
    legacy_projects = legacy_cache.get("projects", {})
    legacy_errors = legacy_cache.get("errors", {})

    if not isinstance(legacy_projects, dict):
        raise ProjectCacheError("Legacy project cache has an invalid shape.")

    for project_id, legacy_entry in legacy_projects.items():
        if not isinstance(legacy_entry, dict):
            raise ProjectCacheError(f"Legacy project cache entry {project_id} is not an object.")
        migrated_entry = migrate_legacy_entry(legacy_entry)
        store_project_cache_entry(
            migrated_cache,
            migrated_entry,
            project_id=str(migrated_entry["id"]),
            slug=str(migrated_entry["slug"]),
        )

    if isinstance(legacy_errors, dict):
        for project_ref, error_entry in legacy_errors.items():
            if cache_entry_has_error(error_entry):
                set_project_cache_error(
                    str(project_ref),
                    migrated_cache,
                    str(error_entry.get("error")),
                )
    return migrated_cache


def validate_project_cache_entries(cache: dict[str, Any], spec: ProjectCacheSpec) -> None:
    """Require every project entry to use the minimal normalized field set."""
    projects = cache["projects"]
    project_ids_by_slug: dict[str, str] = {}
    for project_key, entry in projects.items():
        if not isinstance(entry, dict) or set(entry) != PROJECT_CACHE_ENTRY_FIELDS:
            raise ProjectCacheError(
                f"{spec.path} project {project_key} must contain exactly "
                "id, slug, name, and type. Rebuild the cache."
            )

        normalized_id = str(entry.get("id") or "")
        normalized_slug = str(entry.get("slug") or "").lower()
        normalized_name = str(entry.get("name") or "")
        normalized_type = str(entry.get("type") or "")
        if not all([normalized_id, normalized_slug, normalized_name, normalized_type]):
            raise ProjectCacheError(
                f"{spec.path} project {project_key} has an empty required field. Rebuild the cache."
            )
        if str(project_key) != normalized_id:
            raise ProjectCacheError(
                f"{spec.path} project key {project_key} does not match entry id {normalized_id}."
            )
        if entry["id"] != normalized_id or entry["slug"] != normalized_slug:
            raise ProjectCacheError(
                f"{spec.path} project {project_key} has non-normalized id or slug values."
            )
        existing_project_id = project_ids_by_slug.get(normalized_slug)
        if existing_project_id and existing_project_id != normalized_id:
            raise ProjectCacheError(
                f"{spec.path} slug {normalized_slug} maps to both "
                f"{existing_project_id} and {normalized_id}."
            )
        project_ids_by_slug[normalized_slug] = normalized_id


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
    if not isinstance(projects, dict):
        return None

    entry = projects.get(project_ref)
    if entry is None:
        normalized_ref = project_ref.lower()
        entry = next(
            (
                candidate
                for candidate in projects.values()
                if isinstance(candidate, dict)
                and str(candidate.get("slug") or "").lower() == normalized_ref
            ),
            None,
        )
    if not isinstance(entry, dict) or cache_entry_has_error(entry):
        return None
    return entry


def get_project_cache_error(project_ref: str, cache: dict[str, Any]) -> dict[str, Any] | None:
    """Return a stored fetch error without normalizing case-sensitive IDs."""
    errors = cache.get("errors", {})
    if not isinstance(errors, dict):
        return None

    error_entry = errors.get(project_ref)
    if cache_entry_has_error(error_entry):
        return error_entry

    project = get_project_cache_entry(project_ref, cache)
    project_id = str((project or {}).get("id") or "")
    error_entry = errors.get(project_id) if project_id else None
    return error_entry if cache_entry_has_error(error_entry) else None


def project_cache_has_entry(project_ref: str, cache: dict[str, Any]) -> bool:
    return get_project_cache_entry(project_ref, cache) is not None


def project_cache_project_count(cache: dict[str, Any]) -> int:
    """Return the number of unique project metadata entries in a project cache."""
    projects = cache.get("projects", {})
    return len(projects) if isinstance(projects, dict) else 0


def remove_project_cache_entry(project_ref: str, cache: dict[str, Any]) -> None:
    """Remove the canonical entry resolved by one provider lookup coordinate."""
    projects = cache.get("projects", {})
    if not isinstance(projects, dict):
        raise ProjectCacheError("Structured project cache has an invalid projects section.")

    project = get_project_cache_entry(project_ref, cache)
    project_id = str((project or {}).get("id") or "")
    if project_id:
        projects.pop(project_id, None)


def retain_project_cache_entries(
    project_refs: list[str],
    cache: dict[str, Any],
) -> None:
    """Keep only projects required by the completed refresh plan."""
    retained_projects: dict[str, dict[str, Any]] = {}
    for project_ref in project_refs:
        project = get_project_cache_entry(project_ref, cache)
        if not project:
            raise ProjectCacheError(
                f"Cannot retain missing project cache entry {project_ref}."
            )
        project_id = str(project.get("id") or "")
        retained_projects[project_id] = project

    cache["projects"] = retained_projects
    cache["errors"] = {}


def set_project_cache_error(
    project_ref: str,
    cache: dict[str, Any],
    error: str,
) -> None:
    """Store a project fetch error under the lookup ref that failed."""
    errors = cache.get("errors")
    if not isinstance(errors, dict):
        raise ProjectCacheError("Structured project cache has no valid errors section.")
    errors[project_ref] = {"error": error}


def store_project_cache_entry(
    cache: dict[str, Any],
    entry: dict[str, Any],
    *,
    project_id: str,
    slug: str = "",
    lookup_key: str | None = None,
) -> dict[str, Any]:
    """Store one canonical project and clear errors for its lookup coordinates."""
    projects = cache.get("projects")
    errors = cache.get("errors")
    if not isinstance(projects, dict) or not isinstance(errors, dict):
        raise ProjectCacheError("Structured project cache has an invalid shape.")

    normalized_project_id = str(project_id)
    normalized_slug = str(slug).lower()
    normalized_entry = {
        "id": normalized_project_id,
        "slug": normalized_slug,
        "name": str(entry.get("name") or ""),
        "type": str(entry.get("type") or ""),
    }
    if not all(normalized_entry.values()):
        raise ProjectCacheError(
            f"Project {normalized_project_id or lookup_key or '<unknown>'} "
            "is missing id, slug, name, or type."
        )

    existing_entry = projects.get(normalized_project_id)
    if existing_entry and existing_entry != normalized_entry:
        existing_slug = str(existing_entry.get("slug") or "")
        existing_type = str(existing_entry.get("type") or "")
        if existing_slug and existing_slug != normalized_slug:
            raise ProjectCacheError(
                f"Project {normalized_project_id} changed slug from {existing_slug} "
                f"to {normalized_slug}. Delete the cache before refreshing."
            )
        if existing_type and existing_type != normalized_entry["type"]:
            raise ProjectCacheError(
                f"Project {normalized_project_id} changed type from {existing_type} "
                f"to {normalized_entry['type']}. Delete the cache before refreshing."
            )
    for other_project_id, other_entry in projects.items():
        if other_project_id == normalized_project_id or not isinstance(other_entry, dict):
            continue
        if str(other_entry.get("slug") or "").lower() == normalized_slug:
            raise ProjectCacheError(
                f"Project slug {normalized_slug} already maps to {other_project_id}, "
                f"not {normalized_project_id}."
            )
    projects[normalized_project_id] = normalized_entry

    lookup_refs = {normalized_project_id}
    if lookup_key:
        normalized_lookup_key = str(lookup_key)
        lookup_refs.add(normalized_lookup_key)
    if normalized_slug:
        lookup_refs.add(normalized_slug)

    for lookup_ref in lookup_refs:
        errors.pop(lookup_ref, None)
    return normalized_entry
