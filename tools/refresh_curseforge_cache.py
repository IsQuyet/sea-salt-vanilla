#!/usr/bin/env python3
"""Refresh CurseForge project metadata used by project-data generation."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from typing import Any

from curseforge_cache import (
    CURSEFORGE_MANIFEST_CACHE,
    CURSEFORGE_PROJECT_CACHE,
    CurseForgeFetchError,
    CurseForgeProjectRef,
    curseforge_api_key,
    fetch_missing_curseforge_projects,
    load_curseforge_project_cache,
)
from project_cache import (
    get_project_cache_entry,
    get_project_cache_error,
    project_cache_alias_count,
    project_cache_project_count,
)
from project_cache_refresh import (
    format_refresh_error_report,
    verbose_print,
)
from project_data_common import (
    PROJECT_TYPE_CURSEFORGE_PATHS,
    TARGET_VERSION,
    collect_matrix_project_refs,
    load_installed_projects,
    write_json,
)


def curseforge_category_path(project_type: str) -> str:
    """Return the CurseForge URL category for one normalized project type."""
    return PROJECT_TYPE_CURSEFORGE_PATHS.get(project_type, "mc-mods")


def project_ref_from_installed(project: dict[str, Any]) -> CurseForgeProjectRef | None:
    """Build a category-aware CurseForge ref from installed packwiz metadata."""
    if project.get("source") != "curseforge":
        return None

    project_id = str(project.get("id") or "")
    slug = str(project.get("slug") or "").lower()
    if not project_id and not slug:
        return None

    project_type = str(project.get("type") or "mod")
    return CurseForgeProjectRef(
        project_id=project_id,
        slug=slug,
        category_path=curseforge_category_path(project_type),
    )


def project_ref_from_matrix(ref: dict[str, Any]) -> CurseForgeProjectRef | None:
    """Build a category-aware CurseForge ref from a docs/config project ref."""
    if str(ref.get("source") or "").lower() != "curseforge":
        return None

    project_id = str(ref.get("id") or "")
    slug = str(ref.get("slug") or ref.get("key") or "").lower()
    if not project_id and not slug:
        return None

    project_type = str(ref.get("type") or "mod")
    return CurseForgeProjectRef(
        project_id=project_id,
        slug=slug,
        category_path=curseforge_category_path(project_type),
    )


def project_refs_identify_same_project(
    existing: CurseForgeProjectRef,
    candidate: CurseForgeProjectRef,
) -> bool:
    """Return whether two refs identify the same CurseForge project."""
    same_project_id = bool(
        existing.project_id
        and candidate.project_id
        and existing.project_id == candidate.project_id
    )
    same_category_slug = bool(
        existing.slug
        and candidate.slug
        and existing.slug == candidate.slug
        and existing.category_path == candidate.category_path
    )
    return same_project_id or same_category_slug


def remember_project_ref(
    project_refs: list[CurseForgeProjectRef],
    candidate: CurseForgeProjectRef | None,
) -> None:
    """Merge duplicate ID and slug forms into one structured project ref."""
    if candidate is None:
        return

    for index, existing in enumerate(project_refs):
        if not project_refs_identify_same_project(existing, candidate):
            continue

        project_refs[index] = CurseForgeProjectRef(
            project_id=existing.project_id or candidate.project_id,
            slug=existing.slug or candidate.slug,
            category_path=existing.category_path or candidate.category_path,
        )
        return

    project_refs.append(candidate)


def collect_project_refs_to_refresh(
    installed_projects: list[dict[str, Any]],
) -> list[CurseForgeProjectRef]:
    """Collect unique category-aware CurseForge projects from docs and packwiz."""
    project_refs: list[CurseForgeProjectRef] = []
    for project in installed_projects:
        remember_project_ref(project_refs, project_ref_from_installed(project))

    for ref in collect_matrix_project_refs():
        remember_project_ref(project_refs, project_ref_from_matrix(ref))

    return sorted(
        project_refs,
        key=lambda ref: (ref.category_path, ref.slug, ref.project_id),
    )


def project_ref_is_cached(
    project_ref: CurseForgeProjectRef,
    project_cache: dict[str, Any],
) -> bool:
    """Return whether every known ID and slug alias resolves from the cache."""
    return bool(project_ref.cache_keys) and all(
        get_project_cache_entry(cache_key, project_cache) is not None
        for cache_key in project_ref.cache_keys
    )


def missing_curseforge_project_refs(
    project_refs: list[CurseForgeProjectRef],
    project_cache: dict[str, Any],
    *,
    force: bool,
) -> list[CurseForgeProjectRef]:
    """Return projects that would be fetched in the current refresh mode."""
    return [
        project_ref
        for project_ref in project_refs
        if force or not project_ref_is_cached(project_ref, project_cache)
    ]


def collect_curseforge_refresh_errors(
    project_refs: list[CurseForgeProjectRef],
    project_cache: dict[str, Any],
) -> list[str]:
    """Collect one clear provider error for each unresolved project."""
    errors: list[str] = []
    for project_ref in project_refs:
        if project_ref_is_cached(project_ref, project_cache):
            continue

        error_entry = None
        for cache_key in project_ref.cache_keys:
            error_entry = get_project_cache_error(cache_key, project_cache)
            if error_entry:
                break

        display_ref = project_ref.slug or project_ref.project_id
        if error_entry:
            errors.append(f"{display_ref}: {error_entry.get('error')}")
        else:
            errors.append(f"{display_ref}: missing project metadata")
    return errors


def refresh_project_cache(
    installed_projects: list[dict[str, Any]],
    project_cache: dict[str, Any],
    *,
    force: bool,
    dry_run: bool,
    verbose: bool,
) -> tuple[list[CurseForgeProjectRef], list[CurseForgeProjectRef]]:
    verbose_print(
        "Collecting CurseForge project refs from docs and packwiz metadata...",
        verbose=verbose,
    )
    project_refs = collect_project_refs_to_refresh(installed_projects)
    missing_project_refs = missing_curseforge_project_refs(
        project_refs,
        project_cache,
        force=force,
    )
    metadata_source = "CurseForge API" if curseforge_api_key() else "CFWidget"
    verbose_print(f"Metadata source: {metadata_source}", verbose=verbose)
    verbose_print(
        f"Projects: {len(project_refs)} total, {len(missing_project_refs)} to fetch",
        verbose=verbose,
    )

    if not dry_run:
        verbose_print("Fetching missing CurseForge project metadata...", verbose=verbose)
        fetch_missing_curseforge_projects(missing_project_refs, project_cache, force=force)

    project_errors = collect_curseforge_refresh_errors(project_refs, project_cache)
    if project_errors and not dry_run:
        raise CurseForgeFetchError(
            "Could not refresh all required CurseForge project metadata. "
            "The existing cache files were not updated.\n"
            f"{format_refresh_error_report(project_errors)}"
        )

    return project_refs, missing_project_refs


def build_refresh_summary(
    *,
    force: bool,
    dry_run: bool,
    installed_projects: list[dict[str, Any]],
    project_refs: list[CurseForgeProjectRef],
    missing_project_refs: list[CurseForgeProjectRef],
    project_cache: dict[str, Any],
) -> dict[str, int | str | bool]:
    return {
        "force": force,
        "dry_run": dry_run,
        "metadata_source": "curseforge-api" if curseforge_api_key() else "cfwidget",
        "target_minecraft_version": TARGET_VERSION,
        "installed_projects": len(installed_projects),
        "curseforge_projects": len(project_refs),
        "curseforge_projects_to_fetch": len(missing_project_refs),
        "project_cache_projects": project_cache_project_count(project_cache),
        "project_cache_aliases": project_cache_alias_count(project_cache),
    }


def write_refresh_outputs(*, summary: dict[str, int | str | bool], project_cache: dict[str, Any]) -> None:
    write_json(CURSEFORGE_PROJECT_CACHE, project_cache)
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "generator": "tools/refresh_curseforge_cache.py",
        **summary,
    }
    write_json(CURSEFORGE_MANIFEST_CACHE, manifest)


def refresh_cache(
    *,
    force: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, int | str | bool]:
    installed_projects = load_installed_projects()
    project_cache = load_curseforge_project_cache()
    project_refs, missing_project_refs = refresh_project_cache(
        installed_projects,
        project_cache,
        force=force,
        dry_run=dry_run,
        verbose=verbose,
    )
    summary = build_refresh_summary(
        force=force,
        dry_run=dry_run,
        installed_projects=installed_projects,
        project_refs=project_refs,
        missing_project_refs=missing_project_refs,
        project_cache=project_cache,
    )

    if not dry_run:
        write_refresh_outputs(summary=summary, project_cache=project_cache)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Refetch projects even if cached.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be refreshed without writing caches.")
    parser.add_argument("--verbose", action="store_true", help="Print refresh progress before the JSON summary.")
    args = parser.parse_args()

    try:
        summary = refresh_cache(force=args.force, dry_run=args.dry_run, verbose=args.verbose)
    except CurseForgeFetchError as error:
        raise SystemExit(str(error)) from error

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
