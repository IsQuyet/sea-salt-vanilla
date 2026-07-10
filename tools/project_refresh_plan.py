"""Provider-neutral project refresh planning and identity reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from project_cache import get_project_cache_entry
from project_data_common import (
    TARGET_VERSION,
    category_project_type,
    iter_feature_versions,
    selected_project_refs_from_version,
)
from project_data_identity import normalize_project_source


@dataclass
class PlannedProject:
    """Describe one logical provider project and why it needs metadata."""

    source: str
    project_id: str = ""
    slug: str = ""
    project_type: str = ""
    origins: set[str] = field(default_factory=set)
    locations: list[str] = field(default_factory=list)

    @property
    def lookup_key(self) -> str:
        return self.project_id or self.slug

    @property
    def cache_keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(key for key in (self.project_id, self.slug) if key))


@dataclass
class ProjectRefreshPlan:
    """Collect canonical provider projects and identity conflicts for one refresh."""

    target_minecraft_version: str
    projects: list[PlannedProject] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def projects_for(self, source: str) -> list[PlannedProject]:
        normalized_source = normalize_project_source(source)
        return [project for project in self.projects if project.source == normalized_source]


def cached_project_for_ref(
    project: PlannedProject,
    project_cache: dict[str, Any],
) -> dict[str, Any] | None:
    """Resolve all known coordinates and reject identities that disagree."""
    resolved_projects = [
        cached_project
        for cache_key in project.cache_keys
        if (cached_project := get_project_cache_entry(cache_key, project_cache))
    ]
    if not resolved_projects:
        return None

    resolved_ids = {str(cached_project.get("id") or "") for cached_project in resolved_projects}
    if len(resolved_ids) > 1:
        joined_keys = ", ".join(project.cache_keys)
        raise ValueError(f"{project.source} refs [{joined_keys}] resolve to different project ids.")

    resolved_project = resolved_projects[0]
    resolved_id = str(resolved_project.get("id") or "")
    resolved_slug = str(resolved_project.get("slug") or "").lower()
    if project.project_id and project.project_id != resolved_id:
        raise ValueError(
            f"{project.source} id {project.project_id} resolves through another coordinate "
            f"to project id {resolved_id}."
        )
    if project.slug and project.slug != resolved_slug:
        raise ValueError(
            f"{project.source} slug {project.slug} resolves through another coordinate "
            f"to project slug {resolved_slug}."
        )
    return resolved_project


def enrich_project_from_cache(
    project: PlannedProject,
    project_cache: dict[str, Any],
) -> PlannedProject:
    """Fill canonical ID, slug, and type from an existing provider cache entry."""
    cached_project = cached_project_for_ref(project, project_cache)
    if not cached_project:
        return project

    cached_type = str(cached_project.get("type") or "")
    compatible_types = (
        project.project_type == cached_type
        or (
            project.source == "modrinth"
            and project.project_type == "datapack"
            and cached_type == "mod"
        )
    )
    if project.project_type and cached_type and not compatible_types:
        locations = ", ".join(project.locations) or project.lookup_key
        raise ValueError(
            f"{project.source}:{project.lookup_key} is documented as {project.project_type} "
            f"but provider metadata says {cached_type} ({locations})."
        )
    return PlannedProject(
        source=project.source,
        project_id=str(cached_project.get("id") or project.project_id),
        slug=str(cached_project.get("slug") or project.slug).lower(),
        project_type=project.project_type or cached_type,
        origins=set(project.origins),
        locations=list(project.locations),
    )


def projects_identify_same_provider_project(
    existing: PlannedProject,
    candidate: PlannedProject,
) -> bool:
    """Return whether two normalized refs identify the same provider project."""
    if existing.source != candidate.source:
        return False
    if existing.project_id and candidate.project_id:
        return existing.project_id == candidate.project_id
    return bool(
        existing.slug
        and candidate.slug
        and existing.slug == candidate.slug
    )


def project_identity_conflict(
    existing: PlannedProject,
    candidate: PlannedProject,
) -> str | None:
    """Return a clear conflict when matching coordinates disagree."""
    if existing.source != candidate.source:
        return None

    same_slug = bool(
        existing.slug
        and candidate.slug
        and existing.slug == candidate.slug
    )
    if same_slug and existing.project_type and candidate.project_type:
        if existing.project_type != candidate.project_type:
            return (
                f"{existing.source}:{existing.slug} is referenced as both "
                f"{existing.project_type} and {candidate.project_type}."
            )
    if same_slug and existing.project_id and candidate.project_id:
        if existing.project_id != candidate.project_id:
            return (
                f"{existing.source}:{existing.project_type}:{existing.slug} maps to both "
                f"{existing.project_id} and {candidate.project_id}."
            )

    same_id = bool(
        existing.project_id
        and candidate.project_id
        and existing.project_id == candidate.project_id
    )
    if same_id and existing.project_type and candidate.project_type:
        if existing.project_type != candidate.project_type:
            return (
                f"{existing.source}:{existing.project_id} is referenced as both "
                f"{existing.project_type} and {candidate.project_type}."
            )
    if same_id and existing.slug and candidate.slug and existing.slug != candidate.slug:
        return (
            f"{existing.source}:{existing.project_id} is referenced with both slugs "
            f"{existing.slug} and {candidate.slug}."
        )
    return None


def merge_planned_project(existing: PlannedProject, candidate: PlannedProject) -> None:
    """Merge provenance and missing provider coordinates into one plan entry."""
    existing.project_id = existing.project_id or candidate.project_id
    existing.slug = existing.slug or candidate.slug
    existing.project_type = existing.project_type or candidate.project_type
    existing.origins.update(candidate.origins)
    existing.locations.extend(
        location for location in candidate.locations if location not in existing.locations
    )


def remember_planned_project(
    plan: ProjectRefreshPlan,
    candidate: PlannedProject,
    project_cache: dict[str, Any],
) -> None:
    """Add one ref to the plan after cache enrichment and conflict checks."""
    if not candidate.project_id and not candidate.slug:
        return

    try:
        normalized_candidate = enrich_project_from_cache(candidate, project_cache)
    except ValueError as error:
        plan.conflicts.append(str(error))
        return

    for existing in plan.projects:
        conflict = project_identity_conflict(existing, normalized_candidate)
        if conflict:
            plan.conflicts.append(conflict)
            return
        if projects_identify_same_provider_project(existing, normalized_candidate):
            merge_planned_project(existing, normalized_candidate)
            return

    plan.projects.append(normalized_candidate)


def planned_project_from_installed(project: dict[str, Any]) -> PlannedProject | None:
    """Convert one packwiz project into a provider-neutral refresh ref."""
    source = normalize_project_source(project.get("source"))
    if source not in {"modrinth", "curseforge"}:
        return None
    project_id = str(project.get("id") or "")
    local_slug = str(project.get("slug") or "").lower()
    slug = "" if project_id else local_slug
    if not project_id and not slug:
        return None
    return PlannedProject(
        source=source,
        project_id=project_id,
        slug=slug,
        project_type=str(project.get("type") or "mod"),
        origins={"installed"},
        locations=[str(project.get("file") or local_slug or project_id)],
    )


def planned_project_from_documented_ref(
    ref: Any,
    *,
    project_type: str,
    origin: str,
    location: str,
) -> PlannedProject | None:
    """Convert one docs/config occurrence into a provider-neutral refresh ref."""
    if ref is None:
        return None
    if isinstance(ref, dict):
        normalized_ref = dict(ref)
    else:
        normalized_ref = {
            "source": "modrinth",
            "slug": str(ref).lower(),
        }
    source = normalize_project_source(normalized_ref.get("source"))
    return PlannedProject(
        source=source,
        project_id=str(normalized_ref.get("id") or ""),
        slug=str(normalized_ref.get("slug") or normalized_ref.get("key") or "").lower(),
        project_type=str(normalized_ref.get("type") or project_type),
        origins={origin},
        locations=[location],
    )


def build_project_refresh_plan(
    installed_projects: list[dict[str, Any]],
    project_caches: dict[str, dict[str, Any]],
) -> ProjectRefreshPlan:
    """Build one refresh plan from every installed and documented project."""
    plan = ProjectRefreshPlan(target_minecraft_version=TARGET_VERSION)
    for project in installed_projects:
        if project.get("provider_conflict"):
            plan.conflicts.append(
                f"{project.get('file', '<unknown-packwiz-file>')} declares both "
                "Modrinth and CurseForge update metadata."
            )
        installed_ref = planned_project_from_installed(project)
        if installed_ref:
            remember_planned_project(
                plan,
                installed_ref,
                project_caches.get(installed_ref.source, {}),
            )

    for group, section, row, version, version_data in iter_feature_versions():
        project_type = category_project_type(str(group.get("_category") or ""))
        is_optional_group = bool(group.get("_optional"))
        base_location = (
            f"{group.get('_source_file')}:{row.get('id', '<unknown-row>')} ({version})"
        )
        selected_origin = "docs-optional" if is_optional_group else "docs-default"
        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            version,
            version_data,
        )
        for index, selected_ref in enumerate(selected_refs):
            candidate = planned_project_from_documented_ref(
                selected_ref,
                project_type=project_type,
                origin=selected_origin,
                location=f"{base_location} selected[{index}]",
            )
            if candidate:
                remember_planned_project(
                    plan,
                    candidate,
                    project_caches.get(candidate.source, {}),
                )

        for index, alternative_ref in enumerate(version_data.get("alternatives", [])):
            candidate = planned_project_from_documented_ref(
                alternative_ref,
                project_type=project_type,
                origin="docs-alternative",
                location=f"{base_location} alternatives[{index}]",
            )
            if candidate:
                remember_planned_project(
                    plan,
                    candidate,
                    project_caches.get(candidate.source, {}),
                )

    plan.projects.sort(
        key=lambda project: (
            project.source,
            project.project_type,
            project.slug,
            project.project_id,
        )
    )
    return plan
