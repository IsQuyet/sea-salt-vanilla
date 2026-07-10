"""Canonical project metadata pool and provider project queries."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable

from packwiz import CURSEFORGE_PATH_BY_RESOURCE_TYPE


PROJECT_METADATA_SCHEMA_VERSION = 1
SUPPORTED_PROVIDERS = ("modrinth", "curseforge")
MODRINTH_PROJECT_API = "https://api.modrinth.com/v2/project"
CURSEFORGE_API = "https://api.curseforge.com/v1"
CFWIDGET_API = "https://api.cfwidget.com"
USER_AGENT = "SeaSaltVanillaMaintainer/1.0"


@dataclass(frozen=True)
class ProjectMetadata:
    """Display metadata stored once for one canonical provider project."""

    provider: str
    project_id: str
    slug: str
    name: str
    page: str

    @property
    def identity(self) -> str:
        return project_identity(self.provider, self.project_id)


@dataclass(frozen=True)
class ProjectLookup:
    """One project metadata root and its repository resource context."""

    provider: str
    resource_type: str
    project_id: str = ""
    slug: str = ""
    location: str = ""

    @property
    def lookup_key(self) -> str:
        if self.project_id:
            return project_identity(self.provider, self.project_id)
        return f"{self.provider}:slug:{self.resource_type}:{self.slug}"


@dataclass(frozen=True)
class ProjectRefreshOutcome:
    """One requested project and the result of this refresh invocation."""

    lookup: ProjectLookup
    status: str
    identity: str = ""
    message: str = ""


class ProjectMetadataError(RuntimeError):
    """Raised when project metadata is missing, malformed, or contradictory."""


def normalize_provider(value: Any) -> str:
    provider = str(value or "modrinth").lower()
    return provider


def project_identity(provider: str, project_id: str) -> str:
    normalized_provider = normalize_provider(provider)
    normalized_project_id = str(project_id or "")
    if normalized_provider not in SUPPORTED_PROVIDERS or not normalized_project_id:
        return ""
    return f"{normalized_provider}:{normalized_project_id}"


def split_project_identity(identity: str) -> tuple[str, str]:
    provider, separator, project_id = str(identity).partition(":")
    if separator != ":" or provider not in SUPPORTED_PROVIDERS or not project_id:
        raise ProjectMetadataError(f"Invalid canonical project identity: {identity!r}")
    return provider, project_id


def parse_project_metadata_pool(raw_data: Any) -> dict[str, ProjectMetadata]:
    """Strictly parse the tracked canonical project metadata pool."""
    if not isinstance(raw_data, dict) or set(raw_data) != {
        "schema_version",
        "projects",
    }:
        raise ProjectMetadataError(
            "Project metadata must contain exactly schema_version and projects."
        )
    if raw_data.get("schema_version") != PROJECT_METADATA_SCHEMA_VERSION:
        raise ProjectMetadataError("Project metadata uses an unsupported schema version.")
    raw_projects = raw_data.get("projects")
    if not isinstance(raw_projects, dict):
        raise ProjectMetadataError("Project metadata projects must be an object.")

    projects: dict[str, ProjectMetadata] = {}
    slugs_by_provider: dict[tuple[str, str], str] = {}
    for identity, raw_project in raw_projects.items():
        provider, project_id = split_project_identity(str(identity))
        if not isinstance(raw_project, dict) or set(raw_project) != {
            "slug",
            "name",
            "page",
        }:
            raise ProjectMetadataError(
                f"Project metadata entry {identity} must contain slug, name, and page."
            )
        slug = str(raw_project.get("slug") or "").lower()
        name = str(raw_project.get("name") or "")
        page = str(raw_project.get("page") or "")
        if not slug or not name or not page:
            raise ProjectMetadataError(
                f"Project metadata entry {identity} contains an empty field."
            )
        slug_key = (provider, slug)
        previous_identity = slugs_by_provider.get(slug_key)
        if previous_identity and previous_identity != identity:
            raise ProjectMetadataError(
                f"{provider} slug {slug} belongs to both {previous_identity} and {identity}."
            )
        slugs_by_provider[slug_key] = identity
        projects[identity] = ProjectMetadata(
            provider=provider,
            project_id=project_id,
            slug=slug,
            name=name,
            page=page,
        )
    return projects


def project_metadata_pool_data(
    projects: dict[str, ProjectMetadata],
) -> dict[str, Any]:
    """Return deterministic JSON-compatible project metadata."""
    for identity, project in projects.items():
        if identity != project.identity:
            raise ProjectMetadataError(
                f"Project metadata key {identity!r} disagrees with {project.identity!r}."
            )

    data = {
        "schema_version": PROJECT_METADATA_SCHEMA_VERSION,
        "projects": {
            identity: {
                "slug": project.slug,
                "name": project.name,
                "page": project.page,
            }
            for identity, project in sorted(projects.items())
        },
    }
    parse_project_metadata_pool(data)
    return data


def project_slug_index(
    projects: dict[str, ProjectMetadata],
) -> dict[tuple[str, str], str]:
    return {
        (project.provider, project.slug): identity
        for identity, project in projects.items()
    }


def resolve_project_ref(
    ref: Any,
    projects: dict[str, ProjectMetadata],
) -> ProjectMetadata:
    """Resolve one compact provider ref through the canonical metadata pool."""
    normalized_ref = dict(ref) if isinstance(ref, dict) else {"slug": str(ref)}
    provider = normalize_provider(normalized_ref.get("source"))
    project_id = str(normalized_ref.get("id") or "")
    slug = str(normalized_ref.get("slug") or normalized_ref.get("key") or "").lower()

    if project_id:
        identity = project_identity(provider, project_id)
        project = projects.get(identity)
        if not project:
            raise ProjectMetadataError(f"Project metadata is missing {identity}.")
        if slug and slug != project.slug:
            raise ProjectMetadataError(
                f"Project ref {provider}:{slug} disagrees with canonical slug "
                f"{project.slug} for {identity}."
            )
        return project

    if not slug:
        raise ProjectMetadataError(f"Project ref {ref!r} has neither id nor slug.")
    identity = project_slug_index(projects).get((provider, slug))
    if not identity:
        raise ProjectMetadataError(f"Project metadata is missing {provider}:{slug}.")
    return projects[identity]


def request_json(request: urllib.request.Request) -> Any:
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def modrinth_request(project_ref: str) -> urllib.request.Request:
    encoded_ref = urllib.parse.quote(project_ref, safe="")
    return urllib.request.Request(
        f"{MODRINTH_PROJECT_API}/{encoded_ref}",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )


def curseforge_api_key() -> str:
    return os.environ.get("CURSEFORGE_API_KEY") or os.environ.get("CF_API_KEY") or ""


def curseforge_request(url: str) -> urllib.request.Request:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if api_key := curseforge_api_key():
        headers["x-api-key"] = api_key
    return urllib.request.Request(url, headers=headers)


def curseforge_project_page(data: dict[str, Any]) -> str:
    links = data.get("links") if isinstance(data.get("links"), dict) else {}
    urls = data.get("urls") if isinstance(data.get("urls"), dict) else {}
    return str(
        links.get("websiteUrl")
        or urls.get("project")
        or urls.get("curseforge")
        or ""
    )


def fetch_modrinth_project(lookup: ProjectLookup) -> ProjectMetadata:
    project_ref = lookup.project_id or lookup.slug
    raw_project = request_json(modrinth_request(project_ref))
    if not isinstance(raw_project, dict):
        raise ProjectMetadataError(f"Modrinth returned no project for {project_ref}.")
    project_id = str(raw_project.get("id") or "")
    slug = str(raw_project.get("slug") or "").lower()
    name = str(raw_project.get("title") or raw_project.get("name") or "")
    if not project_id or not slug or not name:
        raise ProjectMetadataError(f"Modrinth returned incomplete data for {project_ref}.")
    page_type = {
        "mod": "mod",
        "resourcepack": "resourcepack",
        "shader": "shader",
        "datapack": "datapack",
        "plugin": "plugin",
    }.get(lookup.resource_type, str(raw_project.get("project_type") or "mod"))
    return ProjectMetadata(
        provider="modrinth",
        project_id=project_id,
        slug=slug,
        name=name,
        page=f"https://modrinth.com/{page_type}/{slug}",
    )


def fetch_official_curseforge_project(lookup: ProjectLookup) -> dict[str, Any]:
    if lookup.project_id:
        encoded_project_id = urllib.parse.quote(lookup.project_id, safe="")
        payload = request_json(
            curseforge_request(f"{CURSEFORGE_API}/mods/{encoded_project_id}")
        )
        project = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(project, dict):
            return project
        raise ProjectMetadataError(
            f"CurseForge returned no project for {lookup.project_id}."
        )

    query = urllib.parse.urlencode({"gameId": 432, "slug": lookup.slug})
    payload = request_json(
        curseforge_request(f"{CURSEFORGE_API}/mods/search?{query}")
    )
    projects = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(projects, list):
        raise ProjectMetadataError(f"CurseForge returned no results for {lookup.slug}.")
    for project in projects:
        if (
            isinstance(project, dict)
            and str(project.get("slug") or "").lower() == lookup.slug
        ):
            return project
    raise ProjectMetadataError(f"CurseForge returned no project for {lookup.slug}.")


def fetch_cfwidget_project(lookup: ProjectLookup) -> dict[str, Any]:
    if lookup.project_id:
        encoded_project_id = urllib.parse.quote(lookup.project_id, safe="")
        url = f"{CFWIDGET_API}/{encoded_project_id}"
    else:
        category_path = CURSEFORGE_PATH_BY_RESOURCE_TYPE.get(
            lookup.resource_type,
            "mc-mods",
        )
        encoded_category = urllib.parse.quote(category_path, safe="")
        encoded_slug = urllib.parse.quote(lookup.slug, safe="")
        url = f"{CFWIDGET_API}/minecraft/{encoded_category}/{encoded_slug}"
    payload = request_json(curseforge_request(url))
    if not isinstance(payload, dict) or not payload.get("id"):
        raise ProjectMetadataError(
            f"CFWidget returned no project for {lookup.project_id or lookup.slug}."
        )
    return payload


def fetch_curseforge_project(lookup: ProjectLookup) -> ProjectMetadata:
    raw_project = (
        fetch_official_curseforge_project(lookup)
        if curseforge_api_key()
        else fetch_cfwidget_project(lookup)
    )
    project_id = str(raw_project.get("id") or "")
    slug = str(raw_project.get("slug") or lookup.slug or "").lower()
    name = str(raw_project.get("name") or raw_project.get("title") or "")
    page = curseforge_project_page(raw_project)
    if not page and slug:
        category_path = CURSEFORGE_PATH_BY_RESOURCE_TYPE.get(
            lookup.resource_type,
            "mc-mods",
        )
        page = f"https://www.curseforge.com/minecraft/{category_path}/{slug}"
    if not project_id or not slug or not name or not page:
        raise ProjectMetadataError(
            f"CurseForge returned incomplete data for {lookup.project_id or lookup.slug}."
        )
    return ProjectMetadata(
        provider="curseforge",
        project_id=project_id,
        slug=slug,
        name=name,
        page=page,
    )


def fetch_project(lookup: ProjectLookup) -> ProjectMetadata:
    if lookup.provider == "modrinth":
        return fetch_modrinth_project(lookup)
    if lookup.provider == "curseforge":
        return fetch_curseforge_project(lookup)
    raise ProjectMetadataError(f"Unsupported project provider: {lookup.provider}")


def normalize_project_page(
    project: ProjectMetadata,
    lookup: ProjectLookup,
) -> ProjectMetadata:
    """Normalize Modrinth page routes from repository occurrence context."""
    if project.provider != "modrinth":
        return project
    page_type = {
        "mod": "mod",
        "resourcepack": "resourcepack",
        "shader": "shader",
        "datapack": "datapack",
        "plugin": "plugin",
    }.get(lookup.resource_type)
    if not page_type:
        return project
    expected_page = f"https://modrinth.com/{page_type}/{project.slug}"
    if project.page == expected_page:
        return project
    return ProjectMetadata(
        provider=project.provider,
        project_id=project.project_id,
        slug=project.slug,
        name=project.name,
        page=expected_page,
    )


def deduplicate_lookups(
    lookups: Iterable[ProjectLookup],
    projects: dict[str, ProjectMetadata],
) -> list[ProjectLookup]:
    slug_index = project_slug_index(projects)
    unique_lookups: dict[str, ProjectLookup] = {}
    for lookup in lookups:
        if lookup.provider not in SUPPORTED_PROVIDERS:
            continue
        if not lookup.project_id and not lookup.slug:
            continue
        existing_identity = (
            project_identity(lookup.provider, lookup.project_id)
            if lookup.project_id
            else slug_index.get((lookup.provider, lookup.slug), "")
        )
        unique_lookups.setdefault(existing_identity or lookup.lookup_key, lookup)
    return sorted(
        unique_lookups.values(),
        key=lambda lookup: (
            lookup.resource_type,
            lookup.provider,
            lookup.project_id or lookup.slug,
        ),
    )


def refresh_project_metadata(
    lookups: Iterable[ProjectLookup],
    projects: dict[str, ProjectMetadata],
    *,
    providers: set[str],
    force: bool,
    dry_run: bool,
) -> tuple[dict[str, ProjectMetadata], list[ProjectRefreshOutcome]]:
    """Refresh required project metadata and prune projects outside current roots."""
    refreshed_projects = dict(projects)
    outcomes: list[ProjectRefreshOutcome] = []
    slug_index = project_slug_index(refreshed_projects)
    required_identities: set[str] = set()

    for lookup in deduplicate_lookups(lookups, refreshed_projects):
        if lookup.provider not in providers:
            existing_identity = (
                project_identity(lookup.provider, lookup.project_id)
                if lookup.project_id
                else slug_index.get((lookup.provider, lookup.slug), "")
            )
            if existing_identity:
                required_identities.add(existing_identity)
            continue

        existing_identity = (
            project_identity(lookup.provider, lookup.project_id)
            if lookup.project_id
            else slug_index.get((lookup.provider, lookup.slug), "")
        )
        existing_project = refreshed_projects.get(existing_identity)
        if existing_project and not force:
            normalized_project = normalize_project_page(existing_project, lookup)
            refreshed_projects[existing_identity] = normalized_project
            required_identities.add(existing_identity)
            outcomes.append(
                ProjectRefreshOutcome(
                    lookup=lookup,
                    status=(
                        "normalized"
                        if normalized_project != existing_project
                        else "cached"
                    ),
                    identity=existing_identity,
                )
            )
            continue
        if dry_run:
            outcomes.append(
                ProjectRefreshOutcome(
                    lookup=lookup,
                    status="would_fetch",
                    identity=existing_identity,
                )
            )
            if existing_identity:
                required_identities.add(existing_identity)
            continue

        try:
            fetched_project = fetch_project(lookup)
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            ProjectMetadataError,
        ) as error:
            outcomes.append(
                ProjectRefreshOutcome(
                    lookup=lookup,
                    status="failed",
                    identity=existing_identity,
                    message=str(error),
                )
            )
            if existing_identity:
                required_identities.add(existing_identity)
            continue

        fetched_identity = fetched_project.identity
        previous_project = refreshed_projects.get(fetched_identity)
        refreshed_projects[fetched_identity] = fetched_project
        required_identities.add(fetched_identity)
        slug_index[(fetched_project.provider, fetched_project.slug)] = fetched_identity
        outcomes.append(
            ProjectRefreshOutcome(
                lookup=lookup,
                status="updated" if previous_project else "fetched",
                identity=fetched_identity,
            )
        )

    if not dry_run and providers == set(SUPPORTED_PROVIDERS):
        for identity in sorted(set(refreshed_projects) - required_identities):
            project = refreshed_projects.pop(identity)
            outcomes.append(
                ProjectRefreshOutcome(
                    lookup=ProjectLookup(
                        provider=project.provider,
                        resource_type="",
                        project_id=project.project_id,
                        slug=project.slug,
                    ),
                    status="pruned",
                    identity=identity,
                )
            )

    return refreshed_projects, outcomes
