#!/usr/bin/env python3
"""Refresh CurseForge project metadata used by project-data generation."""

from __future__ import annotations

import argparse
import json
from typing import Any

from curseforge_cache import (
    CURSEFORGE_MANIFEST_CACHE,
    CURSEFORGE_PROJECT_CACHE,
    CurseForgeCacheError,
    CurseForgeFetchError,
    CurseForgeProjectRef,
    curseforge_api_key,
    fetch_missing_curseforge_projects,
    load_curseforge_project_cache,
)
from project_cache import retain_project_cache_entries
from project_cache_manifest import build_provider_manifest
from project_cache_refresh import (
    collect_planned_project_refresh_errors,
    format_refresh_error_report,
    planned_project_is_cached,
    planned_projects_requiring_refresh,
    verbose_print,
)
from project_data_common import load_installed_projects, write_json
from project_refresh_plan import PlannedProject, ProjectRefreshPlan, build_project_refresh_plan


def curseforge_metadata_source() -> str:
    """Return the active CurseForge metadata adapter name."""
    return "curseforge-api" if curseforge_api_key() else "cfwidget"


def curseforge_ref_from_planned_project(
    project: PlannedProject,
) -> CurseForgeProjectRef:
    """Adapt one provider-neutral plan entry to a CurseForge request."""
    return CurseForgeProjectRef(
        project_id=project.project_id,
        slug=project.slug,
        project_type=project.project_type or "mod",
    )


def require_conflict_free_plan(plan: ProjectRefreshPlan) -> None:
    """Stop before provider access when same-provider identities contradict."""
    if not plan.conflicts:
        return
    raise CurseForgeFetchError(
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
    """Refresh every planned CurseForge project exactly once."""
    require_conflict_free_plan(plan)
    provider_projects = plan.projects_for("curseforge")
    pending_projects = planned_projects_requiring_refresh(
        provider_projects,
        project_cache,
        force=force,
    )
    verbose_print(
        f"Metadata source: {curseforge_metadata_source()}",
        verbose=verbose,
    )
    verbose_print(
        f"Projects: {len(provider_projects)} unique, {len(pending_projects)} to fetch",
        verbose=verbose,
    )

    if not dry_run and pending_projects:
        verbose_print("Fetching CurseForge project metadata...", verbose=verbose)
        provider_refs = [
            curseforge_ref_from_planned_project(project)
            for project in pending_projects
        ]
        fetch_missing_curseforge_projects(provider_refs, project_cache, force=force)

    project_errors = collect_planned_project_refresh_errors(
        provider_projects,
        project_cache,
    )
    if project_errors and not dry_run:
        raise CurseForgeFetchError(
            "Could not refresh all required CurseForge project metadata. "
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
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Refresh the CurseForge project cache and return its common manifest."""
    installed_projects = load_installed_projects()
    project_cache = load_curseforge_project_cache()
    plan = build_project_refresh_plan(
        installed_projects,
        {"curseforge": project_cache},
    )
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
        provider="curseforge",
        metadata_source=curseforge_metadata_source(),
        target_minecraft_version=plan.target_minecraft_version,
        force=force,
        dry_run=dry_run,
        scopes=["projects"],
        plan=plan,
        provider_projects=provider_projects,
        projects_to_fetch=projects_to_fetch_count,
        projects_fetched=projects_fetched_count,
        projects_failed=projects_failed_count,
        project_cache=project_cache,
    )

    if not dry_run:
        retain_project_cache_entries(
            [project.lookup_key for project in provider_projects],
            project_cache,
        )
        write_json(CURSEFORGE_PROJECT_CACHE, project_cache)
        manifest = build_provider_manifest(
            provider="curseforge",
            metadata_source=curseforge_metadata_source(),
            target_minecraft_version=plan.target_minecraft_version,
            force=force,
            dry_run=dry_run,
            scopes=["projects"],
            plan=plan,
            provider_projects=provider_projects,
            projects_to_fetch=projects_to_fetch_count,
            projects_fetched=projects_fetched_count,
            projects_failed=projects_failed_count,
            project_cache=project_cache,
        )
        write_json(CURSEFORGE_MANIFEST_CACHE, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fetch every required CurseForge project even when already cached.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the project refresh plan without fetching or writing caches.",
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
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    except (CurseForgeCacheError, CurseForgeFetchError) as error:
        raise SystemExit(str(error)) from error

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
