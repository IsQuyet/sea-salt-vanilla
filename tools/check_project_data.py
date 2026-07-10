#!/usr/bin/env python3
"""Check docs intent, dependency closure, and installed packwiz project facts."""

from __future__ import annotations

import json
from typing import Any

from curseforge_cache import CurseForgeCacheError, load_curseforge_project_cache
from modrinth_cache import (
    DEPENDENCY_CACHE,
    PROJECT_CACHE,
    MissingModrinthCacheError,
    load_dependency_cache,
    load_modrinth_project_cache,
)
from modrinth_dependency_closure import (
    build_required_modrinth_closure,
    collect_declared_dependency_closure_issues,
    collect_modrinth_lock_snapshot_issues,
)
from project_cache import cache_entry_has_error, collect_cache_errors
from project_data_common import (
    TARGET_VERSION,
    category_project_type,
    feature_row_version_location,
    iter_feature_versions,
    load_declared_dependencies,
    load_documentation_catalog,
    load_feature_groups,
    load_installed_projects,
    load_modrinth_locks,
    load_optional_meta,
    load_project_meta,
    selected_project_refs_from_version,
    write_json,
)
from project_data_contract import (
    build_project_data_indexes,
    curseforge_dependency_coverage,
    installed_project_classification,
    provider_project_identity,
    resolve_documented_ref,
)
from project_data_invariants import generated_data_invariants
from project_data_identity import normalize_project_source


EXPECTED_FOLDER_VERSION_LOADERS = {
    "datapack": "datapack",
}


def folder_type_conflicts(
    installed: list[dict[str, Any]],
    expected_installed_catalog: dict[str, dict[str, Any]],
) -> list[str]:
    """Compare packwiz folders with P/D project types by provider identity."""
    expected_types = {
        identity: str(project.get("type") or "")
        for project in expected_installed_catalog.values()
        if (identity := provider_project_identity(project))
    }

    conflicts: list[str] = []
    for project in installed:
        identity = provider_project_identity(project)
        expected_type = expected_types.get(identity or "")
        if expected_type and expected_type != project.get("type"):
            conflicts.append(
                f"{project['file']}: installed as {project['type']} "
                f"but generated project type is {expected_type}"
            )
    return conflicts


def version_loader_conflicts(
    installed: list[dict[str, Any]],
    dependency_cache: dict[str, Any],
) -> list[str]:
    """Check folder-sensitive loader metadata when the local cache is requested."""
    conflicts: list[str] = []

    for project in installed:
        expected_loader = EXPECTED_FOLDER_VERSION_LOADERS.get(str(project.get("type") or ""))
        if not expected_loader or project.get("source") != "modrinth":
            continue

        version_id = str(project.get("modrinth_version") or "")
        version_data = dependency_cache.get(version_id)
        if not isinstance(version_data, dict) or cache_entry_has_error(version_data):
            continue

        actual_loaders = {str(loader).lower() for loader in version_data.get("loaders", [])}
        if expected_loader in actual_loaders:
            continue

        loader_summary = ", ".join(sorted(actual_loaders)) or "none"
        filename = str(project.get("filename") or "")
        conflicts.append(
            f"{project['file']}: installed as {project['type']} but Modrinth version "
            f"{version_id} loaders are [{loader_summary}]"
            + (f" (filename: {filename})" if filename else "")
        )
    return conflicts


def installed_project_identity_conflicts(
    installed: list[dict[str, Any]],
) -> list[str]:
    """Report contradictory providers and duplicate provider project IDs."""
    conflicts: list[str] = []
    files_by_identity: dict[str, str] = {}

    for project in installed:
        project_file = str(project.get("file") or "<unknown-packwiz-file>")
        if project.get("provider_conflict"):
            conflicts.append(
                f"{project_file}: declares both Modrinth and CurseForge update metadata"
            )

        identity = provider_project_identity(project)
        if not identity:
            conflicts.append(f"{project_file}: has no supported provider project ID")
            continue

        previous_file = files_by_identity.get(identity)
        if previous_file:
            conflicts.append(
                f"{identity}: declared by both {previous_file} and {project_file}"
            )
            continue
        files_by_identity[identity] = project_file

    return conflicts


def unknown_project_refs(
    groups: list[dict[str, Any]],
    documentation_catalog: dict[str, dict[str, Any]],
) -> list[str]:
    """Report refs from any rendered version missing from project-catalog.json."""
    unknown: list[str] = []

    def check_ref(ref: Any, project_type: str, location: str) -> None:
        project = resolve_documented_ref(
            ref,
            documentation_catalog,
            project_type=project_type,
        )
        if project is None:
            unknown.append(f"{location}: unknown project ref {ref}")

    for group, section, row, version, version_data in iter_feature_versions(groups):
        project_type = category_project_type(str(group.get("_category") or ""))
        location = feature_row_version_location(group, section, row, version)
        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            version,
            version_data,
        )
        for selected_index, selected_ref in enumerate(selected_refs):
            check_ref(
                selected_ref,
                project_type,
                f"{location} selected[{selected_index}]",
            )
        for alternative_index, alternative_ref in enumerate(
            version_data.get("alternatives", [])
        ):
            check_ref(
                alternative_ref,
                project_type,
                f"{location} alternatives[{alternative_index}]",
            )
    return unknown


def duplicate_project_refs(
    groups: list[dict[str, Any]],
    documentation_catalog: dict[str, dict[str, Any]],
) -> list[str]:
    """Report repeated provider identities in target-version docs intent."""
    seen_locations: dict[str, str] = {}
    duplicates: list[str] = []

    def remember(ref: Any, project_type: str, location: str) -> None:
        project = resolve_documented_ref(
            ref,
            documentation_catalog,
            project_type=project_type,
        )
        identity = provider_project_identity(project or {})
        if not identity:
            return

        previous_location = seen_locations.get(identity)
        if previous_location:
            duplicates.append(f"{identity}: {previous_location} and {location}")
            return
        seen_locations[identity] = location

    for group, section, row, version, version_data in iter_feature_versions(groups):
        if version != TARGET_VERSION:
            continue

        project_type = category_project_type(str(group.get("_category") or ""))
        location = feature_row_version_location(group, section, row, TARGET_VERSION)
        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            TARGET_VERSION,
            version_data,
        )
        for selected_index, selected_ref in enumerate(selected_refs):
            remember(
                selected_ref,
                project_type,
                f"{location} selected[{selected_index}]",
            )
        for alternative_index, alternative_ref in enumerate(
            version_data.get("alternatives", [])
        ):
            remember(
                alternative_ref,
                project_type,
                f"{location} alternatives[{alternative_index}]",
            )
    return duplicates


def check(
    *,
    persist_cache: bool = False,
    allow_network: bool = False,
    include_modrinth_cache_checks: bool = False,
) -> dict[str, object]:
    """Evaluate the complete project-data contract without network access."""
    del allow_network

    installed = load_installed_projects()
    groups = load_feature_groups()
    default_projects = load_project_meta()
    optional_projects = load_optional_meta()
    declared_dependencies = load_declared_dependencies()
    documentation_catalog = load_documentation_catalog()
    modrinth_locks = load_modrinth_locks()

    indexes = build_project_data_indexes(
        defaults=default_projects,
        optional=optional_projects,
        dependencies=declared_dependencies,
        installed=installed,
    )
    documented_installed, dependency_declared, unexplained = (
        installed_project_classification(indexes)
    )

    modrinth_lock_conflicts = collect_modrinth_lock_snapshot_issues(
        installed,
        modrinth_locks,
    )
    dependency_closure = build_required_modrinth_closure(
        default_projects=default_projects,
        optional_projects=optional_projects,
        installed_projects=installed,
        lock_snapshot=modrinth_locks,
    )
    dependency_closure_conflicts = collect_declared_dependency_closure_issues(
        closure=dependency_closure,
        default_projects=default_projects,
        declared_dependencies=declared_dependencies,
    )

    installed_identities = set(indexes.installed)
    missing_defaults = [
        project
        for identity, project in indexes.defaults.items()
        if identity not in installed_identities
    ]
    missing_dependency_ids = {
        project_id
        for project_id in dependency_closure.dependency_project_ids
        if f"modrinth:{project_id}" not in installed_identities
    }
    missing_dependencies = {
        project_id: {
            "name": project_id,
            "required_by": sorted(
                dependency_closure.required_by_project_id.get(project_id, set())
            ),
        }
        for project_id in sorted(missing_dependency_ids)
    }
    unexpected_installed = [
        f"{project.get('name') or identity} is optional but installed as "
        f"{indexes.installed[identity].get('file')}"
        for identity, project in indexes.optional.items()
        if identity in indexes.installed
    ]

    expected_installed_catalog = dict(default_projects)
    expected_installed_catalog.update(declared_dependencies)
    cache_errors: list[str] = []
    version_loader_conflict_issues: list[str] = []

    curseforge_project_cache = load_curseforge_project_cache()
    modrinth_project_cache = load_modrinth_project_cache()
    cache_errors.extend(
        collect_cache_errors(curseforge_project_cache, "curseforge-project-cache")
    )
    cache_errors.extend(
        collect_cache_errors(modrinth_project_cache, "modrinth-project-cache")
    )

    if include_modrinth_cache_checks:
        dependency_cache = load_dependency_cache()
        cache_errors.extend(collect_cache_errors(dependency_cache, "dependency-cache"))
        version_loader_conflict_issues = version_loader_conflicts(
            installed,
            dependency_cache,
        )
        if persist_cache:
            write_json(DEPENDENCY_CACHE, dependency_cache)
            write_json(PROJECT_CACHE, modrinth_project_cache)

    return {
        "modrinth_cache_checks_enabled": include_modrinth_cache_checks,
        "installed": installed,
        "documented_installed": documented_installed,
        "dependency_declared": dependency_declared,
        "unexplained": unexplained,
        "cache_errors": cache_errors,
        "generated_data_invariants": generated_data_invariants(
            groups,
            installed,
            declared_dependencies,
        ),
        "missing_defaults": missing_defaults,
        "missing_dependencies": missing_dependencies,
        "folder_conflicts": folder_type_conflicts(
            installed,
            expected_installed_catalog,
        ),
        "installed_identity_conflicts": installed_project_identity_conflicts(installed),
        "version_loader_conflicts": version_loader_conflict_issues,
        "unexpected_installed": unexpected_installed,
        "unknown_refs": unknown_project_refs(groups, documentation_catalog),
        "duplicate_refs": duplicate_project_refs(groups, documentation_catalog),
        "modrinth_lock_conflicts": modrinth_lock_conflicts,
        "dependency_closure_conflicts": dependency_closure_conflicts,
        "curseforge_dependency_unverified": curseforge_dependency_coverage(
            default_projects
        ),
    }


def result_summary(result: dict[str, object]) -> dict[str, object]:
    """Return stable counts for human and CI output."""
    list_fields = [
        "unexplained",
        "cache_errors",
        "generated_data_invariants",
        "missing_defaults",
        "folder_conflicts",
        "installed_identity_conflicts",
        "version_loader_conflicts",
        "unexpected_installed",
        "unknown_refs",
        "duplicate_refs",
        "modrinth_lock_conflicts",
        "dependency_closure_conflicts",
        "curseforge_dependency_unverified",
    ]
    for field_name in list_fields:
        assert isinstance(result[field_name], list)
    assert isinstance(result["missing_dependencies"], dict)

    return {
        "modrinth_cache_checks_enabled": result["modrinth_cache_checks_enabled"],
        "dependency_analysis_provider": "modrinth",
        "installed": len(result["installed"]),
        "documented": len(result["documented_installed"]),
        "dependencies": len(result["dependency_declared"]),
        "unexplained": len(result["unexplained"]),
        "cache_errors": len(result["cache_errors"]),
        "generated_data_invariants": len(result["generated_data_invariants"]),
        "missing_defaults": len(result["missing_defaults"]),
        "missing_dependencies": len(result["missing_dependencies"]),
        "folder_conflicts": len(result["folder_conflicts"]),
        "installed_identity_conflicts": len(result["installed_identity_conflicts"]),
        "version_loader_conflicts": len(result["version_loader_conflicts"]),
        "unexpected_installed": len(result["unexpected_installed"]),
        "unknown_refs": len(result["unknown_refs"]),
        "duplicate_refs": len(result["duplicate_refs"]),
        "modrinth_lock_conflicts": len(result["modrinth_lock_conflicts"]),
        "dependency_closure_conflicts": len(result["dependency_closure_conflicts"]),
        "curseforge_dependency_unverified": len(
            result["curseforge_dependency_unverified"]
        ),
    }


def result_issues(result: dict[str, object]) -> list[str]:
    """Render every contract violation; coverage notices remain informational."""
    issues: list[str] = []
    issues.extend(
        f"- unexplained: {project['name']} ({project['file']})"
        for project in result["unexplained"]
    )
    issues.extend(f"- cache error: {error}" for error in result["cache_errors"])
    issues.extend(
        f"- generated data invariant: {issue}"
        for issue in result["generated_data_invariants"]
    )
    issues.extend(
        f"- missing default: {project['name']}"
        for project in result["missing_defaults"]
    )
    for project_id, entry in result["missing_dependencies"].items():
        issues.append(
            f"- missing dependency: {entry['name']} ({project_id}) required by "
            f"{', '.join(entry['required_by'])}"
        )
    issues.extend(
        f"- folder conflict: {conflict}"
        for conflict in result["folder_conflicts"]
    )
    issues.extend(
        f"- installed identity conflict: {conflict}"
        for conflict in result["installed_identity_conflicts"]
    )
    issues.extend(
        f"- version loader conflict: {conflict}"
        for conflict in result["version_loader_conflicts"]
    )
    issues.extend(
        f"- unexpected installed: {conflict}"
        for conflict in result["unexpected_installed"]
    )
    issues.extend(f"- unknown ref: {item}" for item in result["unknown_refs"])
    issues.extend(f"- duplicate ref: {item}" for item in result["duplicate_refs"])
    issues.extend(
        f"- Modrinth lock conflict: {conflict}"
        for conflict in result["modrinth_lock_conflicts"]
    )
    issues.extend(
        f"- dependency closure conflict: {conflict}"
        for conflict in result["dependency_closure_conflicts"]
    )
    return issues


def main() -> None:
    try:
        result = check()
    except (CurseForgeCacheError, MissingModrinthCacheError, ValueError) as error:
        raise SystemExit(str(error)) from error

    print(json.dumps(result_summary(result), ensure_ascii=False, indent=2))
    issues = result_issues(result)
    if issues:
        raise SystemExit("Project data check failed:\n" + "\n".join(issues))


if __name__ == "__main__":
    main()
