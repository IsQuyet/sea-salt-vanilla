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
CURSEFORGE_PROJECT_CACHE_FIELDS = [
    "id",
    "slug",
    "name",
    "summary",
    "classId",
    "authors",
    "categories",
    "links",
    "logo",
    "dateCreated",
    "dateModified",
    "dateReleased",
    "isAvailable",
    "latestFilesIndexes",
]


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
    category_path: str = "mc-mods"

    @property
    def lookup_key(self) -> str:
        return self.project_id or self.slug

    @property
    def cache_keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(key for key in (self.project_id, self.slug) if key))


def load_curseforge_project_cache() -> dict[str, Any]:
    """Load the structured CurseForge project cache."""
    try:
        return load_project_cache(CURSEFORGE_PROJECT_CACHE_SPEC)
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


def normalize_cfwidget_project(data: dict[str, Any], fallback_slug: str) -> dict[str, Any]:
    """Convert a CFWidget response into the local CurseForge cache shape."""
    urls = data.get("urls") if isinstance(data.get("urls"), dict) else {}
    project_url = str(urls.get("project") or urls.get("curseforge") or "")
    members = data.get("members") if isinstance(data.get("members"), list) else []
    authors = [
        {"name": member.get("username")}
        for member in members
        if isinstance(member, dict) and member.get("username")
    ]

    return {
        "id": data.get("id"),
        "slug": project_slug_from_url(project_url) or fallback_slug,
        "name": data.get("title"),
        "summary": data.get("summary"),
        "authors": authors,
        "categories": data.get("categories"),
        "links": {"websiteUrl": project_url} if project_url else {},
        "logo": {"url": data.get("thumbnail")} if data.get("thumbnail") else {},
        "dateCreated": data.get("created_at"),
    }


def compact_curseforge_project(data: dict[str, Any]) -> dict[str, Any]:
    """Keep only CurseForge project metadata used by project-data tooling."""
    return {
        field_name: value
        for field_name in CURSEFORGE_PROJECT_CACHE_FIELDS
        if (value := data.get(field_name)) not in (None, "", [], {})
    }


def cache_curseforge_project(
    data: dict[str, Any],
    cache: dict[str, Any],
    *,
    lookup_key: str | None = None,
    fallback_slug: str = "",
) -> dict[str, Any]:
    """Store a CurseForge project and its id/slug aliases."""
    project_id = str(data.get("id") or lookup_key or "")
    compact_project = compact_curseforge_project(data)
    if not project_id:
        return compact_project

    return store_project_cache_entry(
        cache,
        compact_project,
        project_id=project_id,
        slug=str(data.get("slug") or fallback_slug),
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
    return normalize_cfwidget_project(payload, project_ref.slug)


def fetch_curseforge_project(
    project_ref: CurseForgeProjectRef,
    cache: dict[str, Any],
    *,
    force: bool = False,
) -> dict[str, Any] | None:
    """Fetch one project from the official API or the keyless CFWidget API."""
    if not force and all(project_cache_has_entry(key, cache) for key in project_ref.cache_keys):
        return get_project_cache_entry(project_ref.lookup_key, cache)

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
            set_project_cache_error(cache_key, cache, error_message, retryable=True)
        return None

    return cache_curseforge_project(
        project,
        cache,
        lookup_key=project_ref.slug or project_ref.project_id,
        fallback_slug=project_ref.slug,
    )


def fetch_missing_curseforge_projects(
    project_refs: list[CurseForgeProjectRef],
    cache: dict[str, Any],
    *,
    force: bool = False,
) -> None:
    """Fetch missing CurseForge project metadata by structured project reference."""
    for project_ref in project_refs:
        fetch_curseforge_project(project_ref, cache, force=force)
