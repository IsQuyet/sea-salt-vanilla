#!/usr/bin/env python3
"""Check packwiz project metadata (mods, resource packs, shaders, ...) against structured data."""

from __future__ import annotations

import json
from typing import Any

from curseforge_cache import (
    CurseForgeCacheError,
    load_curseforge_project_cache,
)
from modrinth_cache import (
    DEPENDENCY_CACHE,
    PROJECT_CACHE,
    MissingModrinthCacheError,
    load_dependency_cache,
    load_modrinth_project_cache,
)
from project_cache import cache_entry_has_error, collect_cache_errors
from project_data_common import (
    TARGET_VERSION,
    build_documented_sets,
    build_missing_required,
    build_required_by,
    feature_row_version_location,
    is_documented,
    iter_feature_versions,
    load_declared_dependencies,
    load_feature_groups,
    load_installed_projects,
    load_project_catalog,
    selected_project_refs_from_version,
    write_json,
)
from project_data_invariants import generated_data_invariants
from project_data_identity import (
    build_installed_project_index,
    is_project_installed,
    project_identity,
    project_ref_key,
    resolve_project_ref,
)


EXPECTED_FOLDER_VERSION_LOADERS = {
    "datapack": "datapack",
}


def folder_type_conflicts(
    installed: list[dict[str, Any]],
    project_meta: dict[str, dict[str, Any]],
) -> list[str]:
    type_by_id: dict[str, str] = {}
    type_by_source_id: dict[tuple[str, str], str] = {}
    type_by_slug: dict[str, str] = {}
    for entry in project_meta.values():
        declared_type = str(entry.get("type") or "")
        if not declared_type:
            continue
        if entry.get("source") and entry.get("id"):
            type_by_source_id[(str(entry["source"]), str(entry["id"]))] = declared_type
        if entry.get("source") == "modrinth" and entry.get("id"):
            type_by_id[str(entry["id"])] = declared_type
        if entry.get("slug"):
            type_by_slug[str(entry["slug"]).lower()] = declared_type

    conflicts: list[str] = []
    for project in installed:
        expected = (
            type_by_source_id.get((str(project.get("source") or ""), str(project.get("id") or "")))
            or type_by_id.get(project["modrinth_id"])
            or type_by_slug.get(project["slug"])
        )
        if expected and expected != project["type"]:
            conflicts.append(
                f"{project['file']}: installed as {project['type']} but Modrinth project type is {expected}"
            )
    return conflicts


def version_loader_conflicts(
    installed: list[dict[str, Any]],
    dependency_cache: dict[str, Any],
) -> list[str]:
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


def unexpected_installed_projects(
    groups: list[dict[str, Any]],
    project_meta: dict[str, dict[str, Any]],
    installed_index: dict[str, set[str]],
) -> list[str]:
    conflicts: list[str] = []

    for group, section, row, version, version_data in iter_feature_versions(groups):
        if version != TARGET_VERSION:
            continue

        is_optional_group = bool(group["_optional"])
        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            version,
            version_data,
        )
        for selected_ref in selected_refs:
            project = resolve_project_ref(project_meta, selected_ref)
            if is_optional_group and is_project_installed(project, installed_index):
                conflicts.append(
                    f"{row['id']} ({version}): {project['name']} is optional but is installed"
                )
        for ref in version_data.get("alternatives", []):
            alternative = resolve_project_ref(project_meta, ref)
            if is_project_installed(alternative, installed_index):
                conflicts.append(
                    f"{row['id']} ({version}): {alternative['name']} is an alternative but is installed"
                )
    return conflicts


def unknown_project_refs(groups: list[dict[str, Any]], project_meta: dict[str, dict[str, Any]]) -> list[str]:
    unknown: list[str] = []

    def check_ref(ref: Any, location: str) -> None:
        if ref is None:
            return
        key = project_ref_key(ref)
        if not key:
            return
        if key not in project_meta:
            unknown.append(f"{location}: unknown project ref {ref}")

    for group, section, row, version, version_data in iter_feature_versions(groups):
        location = feature_row_version_location(group, section, row, version)
        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            version,
            version_data,
        )
        for selected_ref in selected_refs:
            check_ref(selected_ref, location)
        for ref in version_data.get("alternatives", []):
            check_ref(ref, f"{location} alternative")

    return unknown


def duplicate_project_refs(groups: list[dict[str, Any]], project_meta: dict[str, dict[str, Any]]) -> list[str]:
    seen: dict[tuple[str, str], str] = {}
    duplicates: list[str] = []

    def remember(ref: Any, location: str) -> None:
        identity = project_identity(resolve_project_ref(project_meta, ref), ref)
        if not identity:
            return
        key = (TARGET_VERSION, identity)
        previous = seen.get(key)
        if previous and previous != location:
            duplicates.append(f"{identity}: {previous} and {location}")
            return
        seen[key] = location

    for group, section, row, version, version_data in iter_feature_versions(groups):
        if version != TARGET_VERSION:
            continue

        location = feature_row_version_location(group, section, row, TARGET_VERSION)
        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            TARGET_VERSION,
            version_data,
        )
        for selected_ref in selected_refs:
            remember(selected_ref, location)
        for ref in version_data.get("alternatives", []):
            remember(ref, f"{location} alternative")

    return duplicates


def expected_default_projects(
    groups: list[dict[str, Any]],
    project_meta: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    expected: list[dict[str, Any]] = []
    for group, section, row, version, version_data in iter_feature_versions(groups):
        if group["_optional"] or version != TARGET_VERSION:
            continue

        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            TARGET_VERSION,
            version_data,
        )
        for selected_ref in selected_refs:
            project = resolve_project_ref(project_meta, selected_ref)
            if project is not None:
                expected.append(project)
    return expected


def check(
    *,
    persist_cache: bool = False,
    allow_network: bool = False,
    include_modrinth_cache_checks: bool = False,
) -> dict[str, object]:
    installed = load_installed_projects()
    installed_index = build_installed_project_index(installed)
    project_meta: dict[str, dict[str, object]] = load_project_catalog()
    groups = load_feature_groups()
    documented = build_documented_sets(project_meta)
    declared_dependencies = load_declared_dependencies()
    required_by: dict[str, list[dict[str, Any]]] = {}
    missing_dependencies: dict[str, dict[str, Any]] = {}
    cache_errors: list[str] = []
    version_loader_conflict_issues: list[str] = []

    curseforge_project_cache = load_curseforge_project_cache()
    cache_errors.extend(collect_cache_errors(curseforge_project_cache, "curseforge-project-cache"))

    if include_modrinth_cache_checks:
        dependency_cache = load_dependency_cache()
        project_cache = load_modrinth_project_cache()
        required_by = build_required_by(installed, dependency_cache, allow_network=allow_network)
        missing_dependencies = build_missing_required(
            installed,
            dependency_cache,
            project_cache,
            allow_network=allow_network,
        )
        cache_errors.extend(
            [
                *collect_cache_errors(dependency_cache, "dependency-cache"),
                *collect_cache_errors(project_cache, "project-cache"),
            ]
        )
        version_loader_conflict_issues = version_loader_conflicts(installed, dependency_cache)
        if persist_cache:
            write_json(DEPENDENCY_CACHE, dependency_cache)
            write_json(PROJECT_CACHE, project_cache)

    documented_installed: list[dict[str, object]] = []
    dependency_declared: list[dict[str, object]] = []
    unexplained: list[dict[str, object]] = []

    for mod in installed:
        if is_documented(mod, documented):
            documented_installed.append(mod)
        elif str(mod["slug"]) in declared_dependencies:
            dependency_declared.append(mod)
        else:
            unexplained.append(mod)

    missing_defaults = [
        project
        for project in expected_default_projects(groups, project_meta)
        if not is_project_installed(project, installed_index)
    ]

    return {
        "modrinth_cache_checks_enabled": include_modrinth_cache_checks,
        "installed": installed,
        "required_by": required_by,
        "documented_installed": documented_installed,
        "dependency_declared": dependency_declared,
        "unexplained": unexplained,
        "cache_errors": cache_errors,
        "generated_data_invariants": generated_data_invariants(groups, installed, declared_dependencies),
        "unexpected_installed": unexpected_installed_projects(groups, project_meta, installed_index),
        "unknown_refs": unknown_project_refs(groups, project_meta),
        "duplicate_refs": duplicate_project_refs(groups, project_meta),
        "missing_defaults": missing_defaults,
        "missing_dependencies": missing_dependencies,
        "folder_conflicts": folder_type_conflicts(installed, project_meta),
        "version_loader_conflicts": version_loader_conflict_issues,
    }


def result_summary(result: dict[str, object]) -> dict[str, object]:
    unexplained = result["unexplained"]
    cache_errors = result["cache_errors"]
    generated_data_invariant_issues = result["generated_data_invariants"]
    unexpected = result["unexpected_installed"]
    unknown_refs = result["unknown_refs"]
    duplicate_refs = result["duplicate_refs"]
    missing_defaults = result["missing_defaults"]
    missing_dependencies = result["missing_dependencies"]
    folder_conflicts = result["folder_conflicts"]
    version_loader_conflict_issues = result["version_loader_conflicts"]
    assert isinstance(unexplained, list)
    assert isinstance(cache_errors, list)
    assert isinstance(generated_data_invariant_issues, list)
    assert isinstance(unexpected, list)
    assert isinstance(unknown_refs, list)
    assert isinstance(duplicate_refs, list)
    assert isinstance(missing_defaults, list)
    assert isinstance(missing_dependencies, dict)
    assert isinstance(folder_conflicts, list)
    assert isinstance(version_loader_conflict_issues, list)

    return {
        "modrinth_cache_checks_enabled": result["modrinth_cache_checks_enabled"],
        "installed": len(result["installed"]),
        "documented": len(result["documented_installed"]),
        "dependencies": len(result["dependency_declared"]),
        "unexplained": len(unexplained),
        "cache_errors": len(cache_errors),
        "generated_data_invariants": len(generated_data_invariant_issues),
        "missing_defaults": len(missing_defaults),
        "missing_dependencies": len(missing_dependencies),
        "folder_conflicts": len(folder_conflicts),
        "version_loader_conflicts": len(version_loader_conflict_issues),
        "unexpected_installed": len(unexpected),
        "unknown_refs": len(unknown_refs),
        "duplicate_refs": len(duplicate_refs),
    }


def result_issues(result: dict[str, object]) -> list[str]:
    unexplained = result["unexplained"]
    cache_errors = result["cache_errors"]
    generated_data_invariant_issues = result["generated_data_invariants"]
    unexpected = result["unexpected_installed"]
    unknown_refs = result["unknown_refs"]
    duplicate_refs = result["duplicate_refs"]
    missing_defaults = result["missing_defaults"]
    missing_dependencies = result["missing_dependencies"]
    folder_conflicts = result["folder_conflicts"]
    version_loader_conflict_issues = result["version_loader_conflicts"]
    assert isinstance(unexplained, list)
    assert isinstance(cache_errors, list)
    assert isinstance(generated_data_invariant_issues, list)
    assert isinstance(unexpected, list)
    assert isinstance(unknown_refs, list)
    assert isinstance(duplicate_refs, list)
    assert isinstance(missing_defaults, list)
    assert isinstance(missing_dependencies, dict)
    assert isinstance(folder_conflicts, list)
    assert isinstance(version_loader_conflict_issues, list)

    issues: list[str] = []
    if unexplained:
        issues.extend(f"- undocumented: {mod['name']} ({mod['slug']})" for mod in unexplained)
    if cache_errors:
        issues.extend(f"- cache error: {error}" for error in cache_errors)
    if generated_data_invariant_issues:
        issues.extend(f"- generated data invariant: {issue}" for issue in generated_data_invariant_issues)
    if missing_defaults:
        issues.extend(f"- missing default: {project['name']}" for project in missing_defaults)
    if missing_dependencies:
        issues.extend(
            f"- missing dependency: {entry['name']} ({project_id}) required by {', '.join(entry['required_by'])}"
            for project_id, entry in missing_dependencies.items()
        )
    if folder_conflicts:
        issues.extend(f"- folder conflict: {conflict}" for conflict in folder_conflicts)
    if version_loader_conflict_issues:
        issues.extend(f"- version loader conflict: {conflict}" for conflict in version_loader_conflict_issues)
    if unexpected:
        issues.extend(f"- unexpected installed: {conflict}" for conflict in unexpected)
    if unknown_refs:
        issues.extend(f"- unknown ref: {item}" for item in unknown_refs)
    if duplicate_refs:
        issues.extend(f"- duplicate ref: {item}" for item in duplicate_refs)
    return issues


def main() -> None:
    try:
        result = check()
    except (CurseForgeCacheError, MissingModrinthCacheError) as error:
        raise SystemExit(str(error)) from error

    print(json.dumps(result_summary(result), ensure_ascii=False, indent=2))
    issues = result_issues(result)
    if issues:
        raise SystemExit("Project data check failed:\n" + "\n".join(issues))


if __name__ == "__main__":
    main()
