"""CurseForge project cache and API access."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_cache import (
    ProjectCacheError,
    ProjectCacheSpec,
    get_project_cache_entry,
    load_project_cache,
    project_cache_has_entry,
    remove_project_cache_entry,
    set_project_cache_error,
    store_project_cache_entry,
)


ROOT = Path(__file__).resolve().parents[1]
CURSEFORGE_CACHE = ROOT / "cache" / "curseforge"
CURSEFORGE_PROJECT_CACHE = CURSEFORGE_CACHE / "curseforge-projects.json"
CURSEFORGE_MANIFEST_CACHE = CURSEFORGE_CACHE / "manifest.json"
CURSEFORGE_PROJECT_CACHE_SPEC = ProjectCacheSpec(
    path=CURSEFORGE_PROJECT_CACHE,
    refresh_command="python tools/refresh_curseforge_cache.py",
)

CURSEFORGE_API = "https://api.curseforge.com/v1"
CFWIDGET_API = "https://api.cfwidget.com"
CURSEFORGE_CATEGORY_PATHS = {
    "mod": "mc-mods",
    "resourcepack": "texture-packs",
    "shader": "shaders",
    "datapack": "data-packs",
    "plugin": "bukkit-plugins",
}
CURSEFORGE_TYPES_BY_PATH = {
    category_path: project_type
    for project_type, category_path in CURSEFORGE_CATEGORY_PATHS.items()
}


class CurseForgeCacheError(RuntimeError):
    """Raised when local CurseForge cache data cannot be loaded."""


class CurseForgeFetchError(RuntimeError):
    """Raised when an explicit CurseForge refresh cannot fetch required metadata."""


class CurseForgeMetadataError(RuntimeError):
    """Raised when a metadata provider returns an unusable project response."""


@dataclass(frozen=True)
class CurseForgeProjectRef:
    """Identify one CurseForge project and its category-aware slug lookup."""

    project_id: str = ""
    slug: str = ""
    project_type: str = "mod"

    @property
    def category_path(self) -> str:
        return CURSEFORGE_CATEGORY_PATHS.get(self.project_type, "mc-mods")

    @property
    def lookup_key(self) -> str:
        return self.project_id or self.slug

    @property
    def cache_keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(key for key in (self.project_id, self.slug) if key))


def load_curseforge_project_cache() -> dict[str, Any]:
    """Load the structured CurseForge project cache."""
    try:
        return load_project_cache(
            CURSEFORGE_PROJECT_CACHE_SPEC,
            migrate_legacy_entry=normalize_legacy_curseforge_project,
        )
    except ProjectCacheError as error:
        raise CurseForgeCacheError(str(error)) from error


def curseforge_api_key() -> str:
    """Return the CurseForge API key from common local environment variable names."""
    return os.environ.get("CURSEFORGE_API_KEY") or os.environ.get("CF_API_KEY") or ""


def curseforge_api_request(url: str) -> urllib.request.Request:
    """Build an authenticated CurseForge API request."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "SeaSaltVanillaModDataTools/0.1 (local script)",
    }
    if api_key := curseforge_api_key():
        headers["x-api-key"] = api_key
    return urllib.request.Request(url, headers=headers)


def cfwidget_request(url: str) -> urllib.request.Request:
    """Build an unauthenticated CFWidget metadata request."""
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "SeaSaltVanillaModDataTools/0.1 (local script)",
        },
    )


def read_json_response(request: urllib.request.Request) -> Any:
    """Read and decode one JSON HTTP response."""
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def project_slug_from_url(project_url: str) -> str:
    """Extract the final CurseForge project slug from a project URL."""
    path_parts = [part for part in urllib.parse.urlparse(project_url).path.split("/") if part]
    return path_parts[-1].lower() if path_parts else ""


def curseforge_type_from_project_url(project_url: str) -> str:
    """Infer a normalized project type from a CurseForge project URL."""
    path_parts = [part for part in urllib.parse.urlparse(project_url).path.split("/") if part]
    if len(path_parts) < 2:
        return ""
    return CURSEFORGE_TYPES_BY_PATH.get(path_parts[-2], "")


def normalize_legacy_curseforge_project(data: dict[str, Any]) -> dict[str, str]:
    """Migrate a schema-2 CurseForge entry into the minimal shared shape."""
    urls = data.get("urls") if isinstance(data.get("urls"), dict) else {}
    links = data.get("links") if isinstance(data.get("links"), dict) else {}
    project_url = str(
        urls.get("project")
        or urls.get("curseforge")
        or links.get("websiteUrl")
        or ""
    )
    return {
        "id": str(data.get("id") or ""),
        "slug": str(data.get("slug") or project_slug_from_url(project_url) or "").lower(),
        "name": str(data.get("name") or data.get("title") or ""),
        "type": str(data.get("type") or curseforge_type_from_project_url(project_url) or "mod"),
    }


def normalize_curseforge_project(
    data: dict[str, Any],
    *,
    project_type: str,
    fallback_slug: str = "",
) -> dict[str, str]:
    """Convert CurseForge or CFWidget metadata into the shared minimal shape."""
    urls = data.get("urls") if isinstance(data.get("urls"), dict) else {}
    project_url = str(urls.get("project") or urls.get("curseforge") or "")
    return {
        "id": str(data.get("id") or ""),
        "slug": str(
            data.get("slug")
            or project_slug_from_url(project_url)
            or fallback_slug
        ).lower(),
        "name": str(data.get("name") or data.get("title") or ""),
        "type": project_type,
    }


def cache_curseforge_project(
    data: dict[str, Any],
    cache: dict[str, Any],
    *,
    project_type: str,
    lookup_key: str | None = None,
    fallback_slug: str = "",
) -> dict[str, Any]:
    """Store a normalized CurseForge project."""
    normalized_project = normalize_curseforge_project(
        data,
        project_type=project_type,
        fallback_slug=fallback_slug,
    )
    project_id = normalized_project["id"]
    if not project_id:
        raise CurseForgeMetadataError("CurseForge project response is missing a project id.")

    return store_project_cache_entry(
        cache,
        normalized_project,
        project_id=project_id,
        slug=normalized_project["slug"],
        lookup_key=lookup_key,
    )


def fetch_official_curseforge_project(project_ref: CurseForgeProjectRef) -> dict[str, Any]:
    """Fetch one project through the authenticated official CurseForge API."""
    if project_ref.project_id:
        encoded_project_id = urllib.parse.quote(project_ref.project_id, safe="")
        payload = read_json_response(
            curseforge_api_request(f"{CURSEFORGE_API}/mods/{encoded_project_id}")
        )
        project = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(project, dict):
            return project
        raise CurseForgeMetadataError("Missing CurseForge project data")

    query = urllib.parse.urlencode({"gameId": 432, "slug": project_ref.slug})
    payload = read_json_response(
        curseforge_api_request(f"{CURSEFORGE_API}/mods/search?{query}")
    )
    projects = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(projects, list):
        raise CurseForgeMetadataError("Missing CurseForge search data")

    for project in projects:
        returned_slug = str(project.get("slug") or "").lower() if isinstance(project, dict) else ""
        if returned_slug == project_ref.slug:
            return project
    raise CurseForgeMetadataError("Project not returned by CurseForge API")


def fetch_cfwidget_project(project_ref: CurseForgeProjectRef) -> dict[str, Any]:
    """Fetch one project through the unauthenticated CFWidget metadata API."""
    if project_ref.project_id:
        encoded_project_id = urllib.parse.quote(project_ref.project_id, safe="")
        request = cfwidget_request(f"{CFWIDGET_API}/{encoded_project_id}")
    else:
        encoded_category = urllib.parse.quote(project_ref.category_path, safe="")
        encoded_slug = urllib.parse.quote(project_ref.slug, safe="")
        request = cfwidget_request(f"{CFWIDGET_API}/minecraft/{encoded_category}/{encoded_slug}")

    payload = read_json_response(request)
    if not isinstance(payload, dict) or not payload.get("id"):
        raise CurseForgeMetadataError("Missing CFWidget project data")
    return payload


def fetch_curseforge_project(
    project_ref: CurseForgeProjectRef,
    cache: dict[str, Any],
    *,
    force: bool = False,
) -> dict[str, Any] | None:
    """Fetch one project from the official API or the keyless CFWidget API."""
    if not force and all(project_cache_has_entry(key, cache) for key in project_ref.cache_keys):
        return get_project_cache_entry(project_ref.lookup_key, cache)
    if force:
        for cache_key in project_ref.cache_keys:
            remove_project_cache_entry(cache_key, cache)

    provider_name = "CurseForge API" if curseforge_api_key() else "CFWidget"
    try:
        project = (
            fetch_official_curseforge_project(project_ref)
            if curseforge_api_key()
            else fetch_cfwidget_project(project_ref)
        )
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        CurseForgeMetadataError,
    ) as error:
        error_message = f"{provider_name}: {error}"
        for cache_key in project_ref.cache_keys:
            set_project_cache_error(cache_key, cache, error_message)
        return None

    try:
        return cache_curseforge_project(
            project,
            cache,
            project_type=project_ref.project_type,
            lookup_key=project_ref.slug or project_ref.project_id,
            fallback_slug=project_ref.slug,
        )
    except ProjectCacheError as error:
        for cache_key in project_ref.cache_keys:
            set_project_cache_error(cache_key, cache, str(error))
        return None


def fetch_missing_curseforge_projects(
    project_refs: list[CurseForgeProjectRef],
    cache: dict[str, Any],
    *,
    force: bool = False,
) -> None:
    """Fetch missing CurseForge project metadata by structured project reference."""
    for project_ref in project_refs:
        fetch_curseforge_project(project_ref, cache, force=force)
