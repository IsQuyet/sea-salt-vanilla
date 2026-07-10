#!/usr/bin/env python3
"""Refresh Modrinth metadata used by project-data generation and diagnostics."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from typing import Any

from generate_project_dependencies import (
    build_installed_indexes,
    collect_target_version_project_refs,
    find_installed_project_for_ref,
)
from modrinth_cache import (
    DEPENDENCY_CACHE,
    MANIFEST_CACHE,
    PROJECT_CACHE,
    ModrinthFetchError,
    fetch_missing_modrinth_projects,
    fetch_missing_modrinth_versions,
    is_complete_version_cache_entry,
    load_dependency_cache,
    load_modrinth_project_cache,
)
from project_cache import (
    cache_entry_has_error,
    get_project_cache_entry,
    project_cache_alias_count,
    project_cache_project_count,
)
from project_cache_refresh import (
    collect_project_refresh_errors,
    format_refresh_error_report,
    missing_project_cache_refs,
    verbose_print,
)
from project_data_common import (
    TARGET_VERSION,
    load_installed_projects,
    write_json,
)


def modrinth_ref_value(ref: dict[str, Any]) -> str:
    """Return the best Modrinth project lookup key for a docs/config project ref."""
    source = str(ref.get("source") or "").lower()
    if source and source != "modrinth":
        return ""

    # Most docs refs are slugs, while some explicit refs may carry only an id.
    return str(ref.get("slug") or ref.get("id") or ref.get("key") or "")


def required_dependency_project_ids(
    installed_projects: list[dict[str, Any]],
    dependency_cache: dict[str, Any],
) -> set[str]:
    """Return required Modrinth dependency project ids that are not installed."""
    installed_project_ids = {
        str(project.get("modrinth_id") or "")
        for project in installed_projects
        if project.get("modrinth_id")
    }
    required_project_ids: set[str] = set()

    for project in installed_projects:
        version_id = str(project.get("modrinth_version") or "")
        version_data = dependency_cache.get(version_id)
        if not isinstance(version_data, dict) or cache_entry_has_error(version_data):
            continue

        for dependency in version_data.get("dependencies", []):
            if dependency.get("dependency_type") != "required":
                continue
            project_id = str(dependency.get("project_id") or "")
            if project_id and project_id not in installed_project_ids:
                required_project_ids.add(project_id)

    return required_project_ids


def collect_project_refs_to_refresh(
    installed_projects: list[dict[str, Any]],
    dependency_cache: dict[str, Any],
    project_cache: dict[str, Any],
) -> list[str]:
    """Collect Modrinth project ids/slugs needed for docs, packwiz metadata, and dependencies."""
    installed_indexes = build_installed_indexes(installed_projects)
    default_refs, optional_refs = collect_target_version_project_refs()
    project_refs = {
        str(project.get("modrinth_id") or "")
        for project in installed_projects
        if project.get("modrinth_id")
    }

    for ref in [*default_refs, *optional_refs]:
        if ref_value := modrinth_ref_value(ref):
            project_refs.add(ref_value)

    root_projects = [
        installed_project
        for ref in default_refs
        if (installed_project := find_installed_project_for_ref(ref, project_cache, installed_indexes))
    ]
    queued_projects = list(root_projects)
    visited_version_ids: set[str] = set()

    while queued_projects:
        current_project = queued_projects.pop(0)
        current_version_id = str(current_project.get("modrinth_version") or "")
        if not current_version_id or current_version_id in visited_version_ids:
            continue
        visited_version_ids.add(current_version_id)

        version_data = dependency_cache.get(current_version_id)
        if not isinstance(version_data, dict) or cache_entry_has_error(version_data):
            continue

        for dependency in version_data.get("dependencies", []):
            if dependency.get("dependency_type") != "required":
                continue
            project_id = str(dependency.get("project_id") or "")
            if not project_id:
                continue
            project_refs.add(project_id)
            installed_dependency = installed_indexes["modrinth_ids"].get(project_id)
            if installed_dependency:
                queued_projects.append(installed_dependency)

    project_refs.update(required_dependency_project_ids(installed_projects, dependency_cache))
    return sorted(ref for ref in project_refs if ref)


def collect_version_cache_errors(version_ids: list[str], dependency_cache: dict[str, Any]) -> list[str]:
    """Collect missing or failed version entries after a refresh attempt."""
    errors: list[str] = []
    for version_id in sorted(set(version_ids)):
        if not version_id:
            continue
        entry = dependency_cache.get(version_id)
        if cache_entry_has_error(entry):
            errors.append(f"{version_id}: {entry.get('error')}")
        elif not is_complete_version_cache_entry(entry):
            errors.append(f"{version_id}: missing or incomplete version metadata")
    return errors


def refresh_version_cache(
    version_ids: list[str],
    dependency_cache: dict[str, Any],
    *,
    force: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    verbose_print(f"Version refs: {len(set(version_ids))}", verbose=verbose)
    if not dry_run:
        verbose_print("Fetching missing Modrinth version metadata...", verbose=verbose)
        fetch_missing_modrinth_versions(version_ids, dependency_cache, force=force)

    version_errors = collect_version_cache_errors(version_ids, dependency_cache)
    if version_errors and not dry_run:
        raise ModrinthFetchError(
            "Could not refresh all required Modrinth version metadata. "
            "The existing cache files were not updated.\n"
            f"{format_refresh_error_report(version_errors)}"
        )


def refresh_project_cache(
    installed_projects: list[dict[str, Any]],
    dependency_cache: dict[str, Any],
    project_cache: dict[str, Any],
    *,
    force: bool,
    dry_run: bool,
    verbose: bool,
) -> tuple[list[str], list[str]]:
    verbose_print(
        "Collecting Modrinth project refs from docs, packwiz metadata, and dependencies...",
        verbose=verbose,
    )
    project_refs = collect_project_refs_to_refresh(installed_projects, dependency_cache, project_cache)
    missing_project_refs = missing_project_cache_refs(project_refs, project_cache, force=force)
    verbose_print(
        f"Project refs: {len(project_refs)} total, {len(missing_project_refs)} to fetch",
        verbose=verbose,
    )

    if not dry_run:
        verbose_print("Fetching missing Modrinth project metadata...", verbose=verbose)
        fetch_missing_modrinth_projects(project_refs, project_cache, force=force)

    project_errors = collect_project_refresh_errors(project_refs, project_cache)
    if project_errors and not dry_run:
        raise ModrinthFetchError(
            "Could not refresh all required Modrinth project metadata. "
            "The existing cache files were not updated.\n"
            f"{format_refresh_error_report(project_errors)}"
        )

    return project_refs, missing_project_refs


def build_refresh_summary(
    *,
    force: bool,
    dry_run: bool,
    only_projects: bool,
    only_versions: bool,
    installed_projects: list[dict[str, Any]],
    version_ids: list[str],
    dependency_cache: dict[str, Any],
    project_refs: list[str],
    missing_project_refs: list[str],
    project_cache: dict[str, Any],
) -> dict[str, int | str | bool]:
    installed_modrinth_version_refs = {
        version_id
        for version_id in version_ids
        if version_id
    }

    return {
        "force": force,
        "dry_run": dry_run,
        "only_projects": only_projects,
        "only_versions": only_versions,
        "target_minecraft_version": TARGET_VERSION,
        "installed_projects": len(installed_projects),
        "installed_modrinth_version_refs": len(installed_modrinth_version_refs),
        "version_cache_entries": len(dependency_cache),
        "project_refs": len(project_refs),
        "project_refs_to_fetch": len(missing_project_refs),
        "project_cache_projects": project_cache_project_count(project_cache),
        "project_cache_aliases": project_cache_alias_count(project_cache),
    }


def write_refresh_outputs(
    *,
    summary: dict[str, int | str | bool],
    dependency_cache: dict[str, Any],
    project_cache: dict[str, Any],
    only_projects: bool,
    only_versions: bool,
) -> None:
    if not only_projects:
        write_json(DEPENDENCY_CACHE, dependency_cache)
    if not only_versions:
        write_json(PROJECT_CACHE, project_cache)

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "generator": "tools/refresh_modrinth_cache.py",
        **summary,
    }
    write_json(MANIFEST_CACHE, manifest)


def refresh_cache(
    *,
    force: bool = False,
    only_projects: bool = False,
    only_versions: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, int | str | bool]:
    if only_projects and only_versions:
        raise ModrinthFetchError("Use either --only-projects or --only-versions, not both.")

    installed_projects = load_installed_projects()
    dependency_cache = load_dependency_cache()
    project_cache = load_modrinth_project_cache()

    version_ids = [str(project.get("modrinth_version") or "") for project in installed_projects]
    if not only_projects:
        refresh_version_cache(
            version_ids,
            dependency_cache,
            force=force,
            dry_run=dry_run,
            verbose=verbose,
        )

    project_refs: list[str] = []
    missing_project_refs: list[str] = []
    if not only_versions:
        project_refs, missing_project_refs = refresh_project_cache(
            installed_projects,
            dependency_cache,
            project_cache,
            force=force,
            dry_run=dry_run,
            verbose=verbose,
        )

    summary = build_refresh_summary(
        force=force,
        dry_run=dry_run,
        only_projects=only_projects,
        only_versions=only_versions,
        installed_projects=installed_projects,
        version_ids=version_ids,
        dependency_cache=dependency_cache,
        project_refs=project_refs,
        missing_project_refs=missing_project_refs,
        project_cache=project_cache,
    )

    if not dry_run:
        write_refresh_outputs(
            summary=summary,
            dependency_cache=dependency_cache,
            project_cache=project_cache,
            only_projects=only_projects,
            only_versions=only_versions,
        )

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fetch all required Modrinth metadata even when cache entries already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print refresh scope without fetching or writing cache files.",
    )
    parser.add_argument(
        "--only-projects",
        action="store_true",
        help="Refresh only Modrinth project metadata.",
    )
    parser.add_argument(
        "--only-versions",
        action="store_true",
        help="Refresh only Modrinth version metadata.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print progress while refreshing metadata.")
    args = parser.parse_args()

    try:
        summary = refresh_cache(
            force=args.force,
            only_projects=args.only_projects,
            only_versions=args.only_versions,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    except ModrinthFetchError as error:
        raise SystemExit(str(error)) from error

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
