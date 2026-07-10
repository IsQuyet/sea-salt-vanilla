"""Modrinth project and version cache access."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from project_cache import (
    ProjectCacheError,
    ProjectCacheSpec,
    cache_entry_has_error,
    get_project_cache_entry,
    load_project_cache,
    project_cache_has_entry,
    remove_project_cache_entry,
    set_project_cache_error,
    store_project_cache_entry,
)


ROOT = Path(__file__).resolve().parents[1]
MODRINTH_CACHE = ROOT / "cache" / "modrinth"
DEPENDENCY_CACHE = MODRINTH_CACHE / "modrinth-version-dependencies.json"
PROJECT_CACHE = MODRINTH_CACHE / "modrinth-projects.json"
MANIFEST_CACHE = MODRINTH_CACHE / "manifest.json"
MODRINTH_PROJECT_CACHE_SPEC = ProjectCacheSpec(
    path=PROJECT_CACHE,
    refresh_command="python tools/refresh_modrinth_cache.py",
)

MODRINTH_VERSIONS_API = "https://api.modrinth.com/v2/versions"
MODRINTH_PROJECT_API = "https://api.modrinth.com/v2/project"
MODRINTH_PROJECTS_API = "https://api.modrinth.com/v2/projects"


class MissingModrinthCacheError(RuntimeError):
    """Raised when offline project-data tooling needs metadata that is not cached."""


class ModrinthFetchError(RuntimeError):
    """Raised when an explicit Modrinth refresh cannot fetch required metadata."""


def load_modrinth_project_cache() -> dict[str, Any]:
    """Load the structured Modrinth project cache."""
    try:
        return load_project_cache(
            MODRINTH_PROJECT_CACHE_SPEC,
            migrate_legacy_entry=normalize_modrinth_project,
        )
    except ProjectCacheError as error:
        raise MissingModrinthCacheError(str(error)) from error


def load_dependency_cache() -> dict[str, Any]:
    """Load the flat Modrinth version/dependency cache."""
    if not DEPENDENCY_CACHE.exists():
        return {}
    cache = json.loads(DEPENDENCY_CACHE.read_text(encoding="utf-8-sig"))
    if not isinstance(cache, dict):
        raise MissingModrinthCacheError(
            f"{DEPENDENCY_CACHE} has an unsupported format. Delete it and refresh the cache."
        )

    normalized_cache: dict[str, Any] = {}
    for version_id, entry in cache.items():
        if cache_entry_has_error(entry):
            normalized_cache[str(version_id)] = {"error": str(entry.get("error"))}
            continue
        normalized_cache[str(version_id)] = normalize_modrinth_version(entry)
    return normalized_cache


def is_complete_version_cache_entry(entry: Any) -> bool:
    """Return whether a cached Modrinth version entry has the fields used by checks."""
    return (
        isinstance(entry, dict)
        and not cache_entry_has_error(entry)
        and set(entry) == {"project_id", "loaders", "dependencies"}
        and bool(entry.get("project_id"))
        and isinstance(entry.get("loaders"), list)
        and isinstance(entry.get("dependencies"), list)
        and all(isinstance(dependency, dict) for dependency in entry["dependencies"])
    )


def normalize_modrinth_project(data: dict[str, Any]) -> dict[str, str]:
    """Convert Modrinth project metadata into the shared minimal project shape."""
    return {
        "id": str(data.get("id") or ""),
        "slug": str(data.get("slug") or "").lower(),
        "name": str(data.get("name") or data.get("title") or ""),
        "type": str(data.get("type") or data.get("project_type") or ""),
    }


def cache_modrinth_project(
    data: dict[str, Any],
    cache: dict[str, Any],
    *,
    lookup_key: str | None = None,
) -> dict[str, Any]:
    """Store a normalized Modrinth project."""
    normalized_project = normalize_modrinth_project(data)
    project_id = normalized_project["id"]
    if not project_id:
        raise ModrinthFetchError("Modrinth project response is missing a project id.")

    return store_project_cache_entry(
        cache,
        normalized_project,
        project_id=project_id,
        slug=normalized_project["slug"],
        lookup_key=lookup_key,
    )


def fetch_modrinth_project(
    project_ref: str,
    cache: dict[str, Any],
    *,
    force: bool = False,
) -> dict[str, Any] | None:
    """Fetch one Modrinth project by id or slug."""
    if not force and (cached := get_project_cache_entry(project_ref, cache)):
        return cached
    if force:
        remove_project_cache_entry(project_ref, cache)

    request = urllib.request.Request(
        f"{MODRINTH_PROJECT_API}/{urllib.parse.quote(project_ref, safe='')}",
        headers={"User-Agent": "SeaSaltVanillaModDataTools/0.1 (local script)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            project = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        set_project_cache_error(project_ref, cache, str(error))
        return None

    return cache_modrinth_project(project, cache, lookup_key=project_ref)


def fetch_missing_modrinth_projects(
    project_refs: list[str],
    cache: dict[str, Any],
    *,
    force: bool = False,
) -> None:
    """Batch-fetch missing Modrinth project metadata by project id or slug."""
    missing_refs = [
        project_ref
        for project_ref in sorted(set(project_refs))
        if project_ref and (force or not project_cache_has_entry(project_ref, cache))
    ]
    if not missing_refs:
        return

    if force:
        for project_ref in missing_refs:
            remove_project_cache_entry(project_ref, cache)

    for batch_start in range(0, len(missing_refs), 100):
        batch = missing_refs[batch_start : batch_start + 100]
        query = urllib.parse.urlencode({"ids": json.dumps(batch)})
        request = urllib.request.Request(
            f"{MODRINTH_PROJECTS_API}?{query}",
            headers={"User-Agent": "SeaSaltVanillaModDataTools/0.1 (local script)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                projects = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            for project_ref in batch:
                fetch_modrinth_project(project_ref, cache, force=force)
            continue

        found_refs: set[str] = set()
        for project in projects:
            normalized_project = cache_modrinth_project(project, cache)
            if project_id := normalized_project.get("id"):
                found_refs.add(str(project_id))
            if slug := normalized_project.get("slug"):
                found_refs.add(str(slug))

        for project_ref in batch:
            if project_ref not in found_refs and not project_cache_has_entry(project_ref, cache):
                set_project_cache_error(
                    project_ref,
                    cache,
                    "Project not returned by Modrinth API",
                )


def normalize_modrinth_dependency(dependency: Any) -> dict[str, str] | None:
    """Keep only dependency identity and relationship fields used by traversal."""
    if not isinstance(dependency, dict):
        return None
    project_id = str(dependency.get("project_id") or "")
    dependency_type = str(dependency.get("dependency_type") or "")
    if not project_id or not dependency_type:
        return None
    return {
        "project_id": project_id,
        "dependency_type": dependency_type,
    }


def normalize_modrinth_version(data: Any) -> dict[str, Any]:
    """Convert version metadata into the minimal dependency-analysis shape."""
    if not isinstance(data, dict):
        return {"project_id": "", "loaders": [], "dependencies": []}
    dependencies = [
        normalized_dependency
        for dependency in data.get("dependencies", [])
        if (normalized_dependency := normalize_modrinth_dependency(dependency))
    ]
    return {
        "project_id": str(data.get("project_id") or ""),
        "loaders": [str(loader) for loader in data.get("loaders", [])],
        "dependencies": dependencies,
    }


def cache_version(data: dict[str, Any], cache: dict[str, Any]) -> None:
    version_id = str(data.get("id") or "")
    if not version_id:
        return
    cache[version_id] = normalize_modrinth_version(data)


def missing_modrinth_version_cache_ids(version_ids: list[str], cache: dict[str, Any]) -> list[str]:
    """Return Modrinth version ids that are absent or incomplete in the local cache."""
    return [
        version_id
        for version_id in sorted(set(version_ids))
        if version_id and not is_complete_version_cache_entry(cache.get(version_id))
    ]


def retain_modrinth_version_cache_entries(
    version_ids: list[str],
    cache: dict[str, Any],
) -> None:
    """Keep only locked versions required by the current packwiz metadata."""
    retained_cache = {
        version_id: cache[version_id]
        for version_id in sorted(set(version_ids))
        if version_id in cache
    }
    cache.clear()
    cache.update(retained_cache)


def require_modrinth_version_cache(version_ids: list[str], cache: dict[str, Any]) -> None:
    """Fail clearly when an offline check needs uncached Modrinth version metadata."""
    missing_ids = missing_modrinth_version_cache_ids(version_ids, cache)
    if not missing_ids:
        return

    preview = ", ".join(missing_ids[:10])
    if len(missing_ids) > 10:
        preview += f", ... ({len(missing_ids)} total)"
    raise MissingModrinthCacheError(
        "Missing Modrinth version cache entries required for offline project-data checks: "
        f"{preview}. Run python tools/refresh_modrinth_cache.py before running check."
    )


def fetch_missing_modrinth_versions(
    version_ids: list[str],
    cache: dict[str, Any],
    *,
    force: bool = False,
) -> None:
    """Batch-fetch missing Modrinth version metadata."""
    missing_ids = [
        version_id
        for version_id in sorted(set(version_ids))
        if version_id and (force or not is_complete_version_cache_entry(cache.get(version_id)))
    ]
    if not missing_ids:
        return

    for batch_start in range(0, len(missing_ids), 50):
        batch = missing_ids[batch_start : batch_start + 50]
        query = urllib.parse.urlencode({"ids": json.dumps(batch)})
        request = urllib.request.Request(
            f"{MODRINTH_VERSIONS_API}?{query}",
            headers={"User-Agent": "SeaSaltVanillaModDataTools/0.1 (local script)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                versions = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            for version_id in batch:
                cache[version_id] = {"error": str(error)}
            continue

        found_ids: set[str] = set()
        for version in versions:
            cache_version(version, cache)
            if version_id := version.get("id"):
                found_ids.add(str(version_id))

        for version_id in batch:
            if version_id not in found_ids:
                cache[version_id] = {
                    "error": "Version not returned by Modrinth API",
                }
