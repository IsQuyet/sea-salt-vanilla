#!/usr/bin/env python3
"""Refresh Modrinth metadata used by project-data generation and diagnostics."""

from __future__ import annotations

import argparse
import json
from typing import Any

from modrinth_cache import (
    DEPENDENCY_CACHE,
    MANIFEST_CACHE,
    PROJECT_CACHE,
    MissingModrinthCacheError,
    ModrinthFetchError,
    fetch_missing_modrinth_projects,
    fetch_missing_modrinth_versions,
    is_complete_version_cache_entry,
    load_dependency_cache,
    load_modrinth_project_cache,
    missing_modrinth_version_cache_ids,
    retain_modrinth_version_cache_entries,
)
from project_cache import (
    cache_entry_has_error,
    empty_project_cache,
    retain_project_cache_entries,
)
from project_cache_manifest import build_provider_manifest
from project_cache_refresh import (
    collect_planned_project_refresh_errors,
    format_refresh_error_report,
    planned_project_is_cached,
    planned_projects_requiring_refresh,
    verbose_print,
)
from project_data_common import TARGET_VERSION, load_installed_projects, write_json
from project_refresh_plan import (
    PlannedProject,
    ProjectRefreshPlan,
    build_project_refresh_plan,
)


def installed_modrinth_version_ids(
    installed_projects: list[dict[str, Any]],
) -> list[str]:
    """Return unique locked Modrinth version IDs from packwiz metadata."""
    return sorted(
        {
            str(project.get("modrinth_version") or "")
            for project in installed_projects
            if project.get("modrinth_version")
        }
    )


def collect_version_cache_errors(
    version_ids: list[str],
    dependency_cache: dict[str, Any],
) -> list[str]:
    """Collect missing or failed version entries after a refresh attempt."""
    errors: list[str] = []
    for version_id in version_ids:
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
) -> dict[str, int]:
    """Refresh locked version metadata and return manifest counters."""
    version_ids_to_fetch = (
        list(version_ids)
        if force
        else missing_modrinth_version_cache_ids(version_ids, dependency_cache)
    )
    verbose_print(
        f"Versions: {len(version_ids)} required, {len(version_ids_to_fetch)} to fetch",
        verbose=verbose,
    )

    if not dry_run and version_ids_to_fetch:
        verbose_print("Fetching Modrinth version metadata...", verbose=verbose)
        fetch_missing_modrinth_versions(version_ids, dependency_cache, force=force)

    version_errors = collect_version_cache_errors(version_ids, dependency_cache)
    if version_errors and not dry_run:
        raise ModrinthFetchError(
            "Could not refresh all required Modrinth version metadata. "
            "The existing cache files were not updated.\n"
            f"{format_refresh_error_report(version_errors)}"
        )

    fetched_count = 0
    if not dry_run:
        fetched_count = sum(
            is_complete_version_cache_entry(dependency_cache.get(version_id))
            for version_id in version_ids_to_fetch
        )

    return {
        "required": len(version_ids),
        "to_fetch": len(version_ids_to_fetch),
        "fetched": fetched_count,
        "failed": 0 if dry_run else len(version_errors),
        "cached": sum(
            is_complete_version_cache_entry(entry)
            for entry in dependency_cache.values()
        ),
        "errors": sum(
            cache_entry_has_error(entry)
            for entry in dependency_cache.values()
        ),
    }


def require_conflict_free_plan(plan: ProjectRefreshPlan) -> None:
    """Stop before provider access when same-provider identities contradict."""
    if not plan.conflicts:
        return
    raise ModrinthFetchError(
        "Project refresh plan contains identity conflicts.\n"
        f"{format_refresh_error_report(plan.conflicts)}"
    )


def refresh_project_cache(
    plan: ProjectRefreshPlan,
    project_cache: dict[str, Any],
    *,
    force: bool,
    dry_run: bool,
    verbose: bool,
) -> tuple[list[PlannedProject], int, int, int]:
    """Refresh every planned Modrinth project exactly once."""
    require_conflict_free_plan(plan)
    provider_projects = plan.projects_for("modrinth")
    pending_projects = planned_projects_requiring_refresh(
        provider_projects,
        project_cache,
        force=force,
    )
    verbose_print(
        f"Projects: {len(provider_projects)} unique, {len(pending_projects)} to fetch",
        verbose=verbose,
    )

    if not dry_run and pending_projects:
        verbose_print("Fetching Modrinth project metadata...", verbose=verbose)
        lookup_keys = [project.lookup_key for project in pending_projects]
        fetch_missing_modrinth_projects(lookup_keys, project_cache, force=force)

    project_errors = collect_planned_project_refresh_errors(
        provider_projects,
        project_cache,
    )
    if project_errors and not dry_run:
        raise ModrinthFetchError(
            "Could not refresh all required Modrinth project metadata. "
            "The existing cache files were not updated.\n"
            f"{format_refresh_error_report(project_errors)}"
        )

    fetched_count = 0
    if not dry_run:
        fetched_count = sum(
            planned_project_is_cached(project, project_cache)
            for project in pending_projects
        )
    failed_count = 0 if dry_run else len(project_errors)
    return provider_projects, len(pending_projects), fetched_count, failed_count


def refresh_cache(
    *,
    force: bool = False,
    only_projects: bool = False,
    only_versions: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Refresh selected Modrinth cache scopes and return their common manifest."""
    if only_projects and only_versions:
        raise ModrinthFetchError("Use either --only-projects or --only-versions, not both.")

    installed_projects = load_installed_projects()
    dependency_cache = {} if only_projects else load_dependency_cache()
    project_cache = empty_project_cache() if only_versions else load_modrinth_project_cache()
    plan = (
        ProjectRefreshPlan(target_minecraft_version=TARGET_VERSION)
        if only_versions
        else build_project_refresh_plan(
            installed_projects,
            {"modrinth": project_cache},
        )
    )

    scopes: list[str] = []
    version_summary: dict[str, int] | None = None
    version_ids = installed_modrinth_version_ids(installed_projects)
    if not only_projects:
        scopes.append("versions")
        version_summary = refresh_version_cache(
            version_ids,
            dependency_cache,
            force=force,
            dry_run=dry_run,
            verbose=verbose,
        )

    provider_projects = plan.projects_for("modrinth")
    projects_to_fetch_count = 0
    projects_fetched_count = 0
    projects_failed_count = 0
    if not only_versions:
        scopes.append("projects")
        (
            provider_projects,
            projects_to_fetch_count,
            projects_fetched_count,
            projects_failed_count,
        ) = refresh_project_cache(
            plan,
            project_cache,
            force=force,
            dry_run=dry_run,
            verbose=verbose,
        )

    manifest = build_provider_manifest(
        provider="modrinth",
        metadata_source="modrinth-api",
        target_minecraft_version=plan.target_minecraft_version,
        force=force,
        dry_run=dry_run,
        scopes=scopes,
        plan=plan,
        provider_projects=provider_projects,
        projects_to_fetch=projects_to_fetch_count,
        projects_fetched=projects_fetched_count,
        projects_failed=projects_failed_count,
        project_cache=project_cache,
        versions=version_summary,
    )

    if not dry_run:
        if "versions" in scopes:
            retain_modrinth_version_cache_entries(version_ids, dependency_cache)
            if version_summary is not None:
                version_summary["cached"] = sum(
                    is_complete_version_cache_entry(entry)
                    for entry in dependency_cache.values()
                )
                version_summary["errors"] = sum(
                    cache_entry_has_error(entry)
                    for entry in dependency_cache.values()
                )
            write_json(DEPENDENCY_CACHE, dependency_cache)
        if "projects" in scopes:
            retain_project_cache_entries(
                [project.lookup_key for project in provider_projects],
                project_cache,
            )
            write_json(PROJECT_CACHE, project_cache)
        manifest = build_provider_manifest(
            provider="modrinth",
            metadata_source="modrinth-api",
            target_minecraft_version=plan.target_minecraft_version,
            force=force,
            dry_run=dry_run,
            scopes=scopes,
            plan=plan,
            provider_projects=provider_projects,
            projects_to_fetch=projects_to_fetch_count,
            projects_fetched=projects_fetched_count,
            projects_failed=projects_failed_count,
            project_cache=project_cache,
            versions=version_summary,
        )
        write_json(MANIFEST_CACHE, manifest)
    return manifest


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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print refresh progress before the JSON manifest.",
    )
    args = parser.parse_args()

    try:
        manifest = refresh_cache(
            force=args.force,
            only_projects=args.only_projects,
            only_versions=args.only_versions,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    except (MissingModrinthCacheError, ModrinthFetchError) as error:
        raise SystemExit(str(error)) from error

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
