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
MODRINTH_PROJECT_CACHE_FIELDS = [
    "id",
    "slug",
    "title",
    "project_type",
    "description",
    "client_side",
    "server_side",
    "categories",
    "additional_categories",
    "loaders",
    "game_versions",
    "license",
    "icon_url",
    "color",
    "published",
    "updated",
    "approved",
    "queued",
    "status",
]


class MissingModrinthCacheError(RuntimeError):
    """Raised when offline project-data tooling needs metadata that is not cached."""


class ModrinthFetchError(RuntimeError):
    """Raised when an explicit Modrinth refresh cannot fetch required metadata."""


def load_modrinth_project_cache() -> dict[str, Any]:
    """Load the structured Modrinth project cache."""
    try:
        return load_project_cache(MODRINTH_PROJECT_CACHE_SPEC)
    except ProjectCacheError as error:
        raise MissingModrinthCacheError(str(error)) from error


def load_dependency_cache() -> dict[str, Any]:
    """Load the flat Modrinth version/dependency cache."""
    if not DEPENDENCY_CACHE.exists():
        return {}
    return json.loads(DEPENDENCY_CACHE.read_text(encoding="utf-8-sig"))


def is_complete_version_cache_entry(entry: Any) -> bool:
    """Return whether a cached Modrinth version entry has the fields used by checks."""
    return isinstance(entry, dict) and not cache_entry_has_error(entry) and "loaders" in entry


def compact_modrinth_project(data: dict[str, Any]) -> dict[str, Any]:
    """Keep only Modrinth project metadata used by project-data tooling."""
    return {
        field_name: value
        for field_name in MODRINTH_PROJECT_CACHE_FIELDS
        if (value := data.get(field_name)) not in (None, "", [], {})
    }


def cache_modrinth_project(
    data: dict[str, Any],
    cache: dict[str, Any],
    *,
    lookup_key: str | None = None,
) -> dict[str, Any]:
    """Store a Modrinth project and its id/slug aliases."""
    project_id = str(data.get("id") or lookup_key or "")
    compact_project = compact_modrinth_project(data)
    if not project_id:
        return compact_project

    return store_project_cache_entry(
        cache,
        compact_project,
        project_id=project_id,
        slug=str(data.get("slug") or ""),
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

    request = urllib.request.Request(
        f"{MODRINTH_PROJECT_API}/{urllib.parse.quote(project_ref, safe='')}",
        headers={"User-Agent": "SeaSaltVanillaModDataTools/0.1 (local script)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            project = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        set_project_cache_error(project_ref, cache, str(error), retryable=True)
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
            compact_project = cache_modrinth_project(project, cache)
            if project_id := compact_project.get("id"):
                found_refs.add(str(project_id))
            if slug := compact_project.get("slug"):
                found_refs.add(str(slug))

        for project_ref in batch:
            if project_ref not in found_refs and not project_cache_has_entry(project_ref, cache):
                set_project_cache_error(
                    project_ref,
                    cache,
                    "Project not returned by Modrinth API",
                    retryable=False,
                )


def cache_version(data: dict[str, Any], cache: dict[str, Any]) -> None:
    version_id = str(data.get("id") or "")
    if not version_id:
        return
    cache[version_id] = {
        "id": data.get("id"),
        "project_id": data.get("project_id"),
        "version_number": data.get("version_number"),
        "loaders": data.get("loaders", []),
        "files": [file.get("filename") for file in data.get("files", []) if file.get("filename")],
        "dependencies": data.get("dependencies", []),
    }


def missing_modrinth_version_cache_ids(version_ids: list[str], cache: dict[str, Any]) -> list[str]:
    """Return Modrinth version ids that are absent or incomplete in the local cache."""
    return [
        version_id
        for version_id in sorted(set(version_ids))
        if version_id and not is_complete_version_cache_entry(cache.get(version_id))
    ]


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
                cache[version_id] = {"error": str(error), "retryable": True}
            continue

        found_ids: set[str] = set()
        for version in versions:
            cache_version(version, cache)
            if version_id := version.get("id"):
                found_ids.add(str(version_id))

        for version_id in batch:
            if version_id not in found_ids and version_id not in cache:
                cache[version_id] = {
                    "error": "Version not returned by Modrinth API",
                    "retryable": False,
                }
