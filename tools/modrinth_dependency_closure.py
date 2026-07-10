"""Build and verify the required dependency closure of locked Modrinth projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modrinth_cache import MissingModrinthCacheError, is_complete_version_cache_entry
from project_cache import get_project_cache_entry
from project_data_identity import normalize_project_source


MODRINTH_LOCK_SCHEMA_VERSION = 1


@dataclass
class ModrinthDependencyClosure:
    """Describe dependency-only project IDs and their required parent projects."""

    dependency_project_ids: set[str] = field(default_factory=set)
    required_by_project_id: dict[str, set[str]] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


def required_project_ids(version_entry: dict[str, Any]) -> list[str]:
    """Return the normalized required dependency IDs from one cached version."""
    return sorted(
        {
            str(dependency.get("project_id") or "")
            for dependency in version_entry.get("dependencies", [])
            if dependency.get("dependency_type") == "required"
            and dependency.get("project_id")
        }
    )


def build_modrinth_lock_snapshot(
    installed_projects: list[dict[str, Any]],
    version_cache: dict[str, Any],
) -> dict[str, Any]:
    """Project the local version cache into the tracked offline lock graph."""
    locked_versions: dict[str, dict[str, Any]] = {}

    for project in installed_projects:
        if normalize_project_source(project.get("source")) != "modrinth":
            continue

        project_id = str(project.get("modrinth_id") or project.get("id") or "")
        version_id = str(project.get("modrinth_version") or "")
        if not project_id or not version_id:
            raise MissingModrinthCacheError(
                f"{project.get('file', '<unknown-packwiz-file>')} has no complete "
                "Modrinth project/version lock."
            )

        version_entry = version_cache.get(version_id)
        if not is_complete_version_cache_entry(version_entry):
            raise MissingModrinthCacheError(
                f"Missing Modrinth version metadata for {version_id}. "
                "Run python tools/refresh_modrinth_cache.py before generation."
            )
        if str(version_entry.get("project_id") or "") != project_id:
            raise MissingModrinthCacheError(
                f"Modrinth version {version_id} belongs to "
                f"{version_entry.get('project_id')}, not packwiz project {project_id}."
            )

        locked_versions[version_id] = {
            "project_id": project_id,
            "required_project_ids": required_project_ids(version_entry),
        }

    return {
        "schema_version": MODRINTH_LOCK_SCHEMA_VERSION,
        "versions": dict(sorted(locked_versions.items())),
    }


def normalize_modrinth_lock_snapshot(snapshot: Any) -> dict[str, Any]:
    """Validate and normalize the tracked Modrinth lock graph."""
    if not isinstance(snapshot, dict) or set(snapshot) != {"schema_version", "versions"}:
        raise ValueError(
            "data/modrinth-locks.json must contain exactly schema_version and versions."
        )
    if snapshot.get("schema_version") != MODRINTH_LOCK_SCHEMA_VERSION:
        raise ValueError("data/modrinth-locks.json uses an unsupported schema version.")

    versions = snapshot.get("versions")
    if not isinstance(versions, dict):
        raise ValueError("data/modrinth-locks.json versions must be an object.")

    normalized_versions: dict[str, dict[str, Any]] = {}
    for version_id, version_entry in versions.items():
        if not isinstance(version_entry, dict) or set(version_entry) != {
            "project_id",
            "required_project_ids",
        }:
            raise ValueError(
                f"Modrinth lock {version_id} must contain project_id and "
                "required_project_ids."
            )

        project_id = str(version_entry.get("project_id") or "")
        dependencies = version_entry.get("required_project_ids")
        if not project_id or not isinstance(dependencies, list):
            raise ValueError(f"Modrinth lock {version_id} has invalid values.")

        normalized_dependencies = sorted({str(project_id) for project_id in dependencies})
        if any(not dependency_id for dependency_id in normalized_dependencies):
            raise ValueError(f"Modrinth lock {version_id} has an empty dependency ID.")

        normalized_versions[str(version_id)] = {
            "project_id": project_id,
            "required_project_ids": normalized_dependencies,
        }

    return {
        "schema_version": MODRINTH_LOCK_SCHEMA_VERSION,
        "versions": normalized_versions,
    }


def collect_modrinth_lock_snapshot_issues(
    installed_projects: list[dict[str, Any]],
    snapshot: dict[str, Any],
) -> list[str]:
    """Verify that the tracked graph matches every current packwiz Modrinth lock."""
    try:
        normalized_snapshot = normalize_modrinth_lock_snapshot(snapshot)
    except ValueError as error:
        return [str(error)]

    expected_versions: dict[str, str] = {}
    issues: list[str] = []
    for project in installed_projects:
        if normalize_project_source(project.get("source")) != "modrinth":
            continue

        project_id = str(project.get("modrinth_id") or project.get("id") or "")
        version_id = str(project.get("modrinth_version") or "")
        if not project_id or not version_id:
            issues.append(
                f"{project.get('file', '<unknown-packwiz-file>')} has no complete "
                "Modrinth project/version lock."
            )
            continue
        expected_versions[version_id] = project_id

    actual_versions = normalized_snapshot["versions"]
    missing_versions = set(expected_versions) - set(actual_versions)
    stale_versions = set(actual_versions) - set(expected_versions)
    if missing_versions:
        issues.append(
            "modrinth-locks.json is missing packwiz versions: "
            f"{', '.join(sorted(missing_versions))}"
        )
    if stale_versions:
        issues.append(
            "modrinth-locks.json contains stale versions: "
            f"{', '.join(sorted(stale_versions))}"
        )

    for version_id, expected_project_id in expected_versions.items():
        version_entry = actual_versions.get(version_id)
        if not version_entry:
            continue
        actual_project_id = str(version_entry.get("project_id") or "")
        if actual_project_id != expected_project_id:
            issues.append(
                f"Modrinth lock {version_id} belongs to {actual_project_id}, "
                f"not packwiz project {expected_project_id}."
            )
    return issues


def installed_modrinth_projects_by_id(
    installed_projects: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Index installed Modrinth projects and reject duplicate project IDs."""
    indexed_projects: dict[str, dict[str, Any]] = {}
    issues: list[str] = []

    for project in installed_projects:
        if normalize_project_source(project.get("source")) != "modrinth":
            continue
        project_id = str(project.get("modrinth_id") or project.get("id") or "")
        if not project_id:
            continue

        previous_project = indexed_projects.get(project_id)
        if previous_project:
            issues.append(
                f"Modrinth project {project_id} is installed by both "
                f"{previous_project.get('file')} and {project.get('file')}."
            )
            continue
        indexed_projects[project_id] = project
    return indexed_projects, issues


def build_required_modrinth_closure(
    *,
    default_projects: dict[str, dict[str, Any]],
    optional_projects: dict[str, dict[str, Any]],
    installed_projects: list[dict[str, Any]],
    lock_snapshot: dict[str, Any],
) -> ModrinthDependencyClosure:
    """Derive D from the required graph rooted at Modrinth members of P."""
    closure = ModrinthDependencyClosure()
    try:
        normalized_snapshot = normalize_modrinth_lock_snapshot(lock_snapshot)
    except ValueError as error:
        closure.issues.append(str(error))
        return closure

    installed_by_id, installed_issues = installed_modrinth_projects_by_id(
        installed_projects
    )
    closure.issues.extend(installed_issues)

    default_project_ids = {
        str(project.get("id") or "")
        for project in default_projects.values()
        if normalize_project_source(project.get("source")) == "modrinth"
        and project.get("id")
    }
    optional_project_ids = {
        str(project.get("id") or "")
        for project in optional_projects.values()
        if normalize_project_source(project.get("source")) == "modrinth"
        and project.get("id")
    }

    pending_project_ids = sorted(default_project_ids)
    visited_project_ids: set[str] = set()
    versions = normalized_snapshot["versions"]

    while pending_project_ids:
        current_project_id = pending_project_ids.pop(0)
        if current_project_id in visited_project_ids:
            continue
        visited_project_ids.add(current_project_id)

        installed_project = installed_by_id.get(current_project_id)
        if not installed_project:
            closure.issues.append(
                f"Modrinth project {current_project_id} is required by P or D but is not "
                "installed with a packwiz version lock."
            )
            continue

        version_id = str(installed_project.get("modrinth_version") or "")
        version_entry = versions.get(version_id)
        if not version_entry:
            closure.issues.append(
                f"Installed Modrinth project {current_project_id} has no tracked lock "
                f"entry for version {version_id}."
            )
            continue
        if str(version_entry.get("project_id") or "") != current_project_id:
            closure.issues.append(
                f"Tracked version {version_id} belongs to {version_entry.get('project_id')}, "
                f"not {current_project_id}."
            )
            continue

        for dependency_project_id in version_entry["required_project_ids"]:
            closure.required_by_project_id.setdefault(
                dependency_project_id,
                set(),
            ).add(current_project_id)

            if dependency_project_id in optional_project_ids:
                closure.issues.append(
                    f"Modrinth project {dependency_project_id} is optional but is a "
                    f"required dependency of {current_project_id}."
                )

            if dependency_project_id not in default_project_ids:
                closure.dependency_project_ids.add(dependency_project_id)

            if dependency_project_id not in installed_by_id:
                closure.issues.append(
                    f"Required Modrinth dependency {dependency_project_id} of "
                    f"{current_project_id} is not installed. Add it with packwiz, refresh "
                    "the Modrinth cache, and regenerate project data."
                )
                continue
            if dependency_project_id not in visited_project_ids:
                pending_project_ids.append(dependency_project_id)

    closure.issues = list(dict.fromkeys(closure.issues))
    return closure


def project_slug_by_id(
    project_id: str,
    *catalogs: dict[str, dict[str, Any]],
) -> str:
    """Resolve one canonical slug from generated project catalogs."""
    for catalog in catalogs:
        for project in catalog.values():
            if (
                normalize_project_source(project.get("source")) == "modrinth"
                and str(project.get("id") or "") == project_id
            ):
                return str(project.get("slug") or "").lower()
    return ""


def build_dependency_catalog(
    *,
    closure: ModrinthDependencyClosure,
    default_projects: dict[str, dict[str, Any]],
    project_cache: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Attach canonical metadata to the dependency-only closure D."""
    dependency_catalog: dict[str, dict[str, Any]] = {}
    issues = list(closure.issues)

    cached_projects = project_cache.get("projects", {})
    for dependency_project_id in sorted(closure.dependency_project_ids):
        cached_project = get_project_cache_entry(dependency_project_id, project_cache)
        if not cached_project:
            issues.append(
                f"Missing Modrinth project metadata for dependency {dependency_project_id}. "
                "Run python tools/refresh_modrinth_cache.py after installing it."
            )
            continue

        dependency_slug = str(cached_project.get("slug") or "").lower()
        required_by_slugs: list[str] = []
        for parent_project_id in sorted(
            closure.required_by_project_id.get(dependency_project_id, set())
        ):
            parent_slug = project_slug_by_id(
                parent_project_id,
                default_projects,
                cached_projects,
            )
            if not parent_slug:
                issues.append(
                    f"Missing canonical slug for dependency parent {parent_project_id}."
                )
                continue
            required_by_slugs.append(parent_slug)

        dependency_catalog[dependency_slug] = {
            "name": str(cached_project.get("name") or dependency_project_id),
            "type": str(cached_project.get("type") or ""),
            "source": "modrinth",
            "slug": dependency_slug,
            "id": dependency_project_id,
            "required_by": sorted(set(required_by_slugs)),
        }

    return dict(sorted(dependency_catalog.items())), list(dict.fromkeys(issues))


def collect_declared_dependency_closure_issues(
    *,
    closure: ModrinthDependencyClosure,
    default_projects: dict[str, dict[str, Any]],
    declared_dependencies: dict[str, dict[str, Any]],
) -> list[str]:
    """Compare tracked D with the closure derived from the offline lock graph."""
    issues = list(closure.issues)
    declared_by_id = {
        str(project.get("id") or ""): project
        for project in declared_dependencies.values()
        if normalize_project_source(project.get("source")) == "modrinth"
        and project.get("id")
    }

    expected_ids = set(closure.dependency_project_ids)
    declared_ids = set(declared_by_id)
    missing_ids = expected_ids - declared_ids
    stale_ids = declared_ids - expected_ids
    if missing_ids:
        issues.append(
            "dependencies.json is missing required Modrinth projects: "
            f"{', '.join(sorted(missing_ids))}"
        )
    if stale_ids:
        issues.append(
            "dependencies.json contains projects outside the required closure: "
            f"{', '.join(sorted(stale_ids))}"
        )

    combined_catalog = dict(default_projects)
    combined_catalog.update(declared_dependencies)
    project_ids_by_slug = {
        str(project.get("slug") or catalog_key).lower(): str(project.get("id") or "")
        for catalog_key, project in combined_catalog.items()
        if project.get("id")
    }

    for dependency_project_id in sorted(expected_ids & declared_ids):
        declared_entry = declared_by_id[dependency_project_id]
        declared_parent_ids = {
            project_ids_by_slug.get(str(parent_slug).lower(), "")
            for parent_slug in declared_entry.get("required_by", [])
        }
        declared_parent_ids.discard("")
        expected_parent_ids = closure.required_by_project_id.get(
            dependency_project_id,
            set(),
        )
        if declared_parent_ids != expected_parent_ids:
            issues.append(
                f"dependencies.json required_by for {dependency_project_id} resolves to "
                f"{sorted(declared_parent_ids)}, expected {sorted(expected_parent_ids)}."
            )

    return list(dict.fromkeys(issues))
