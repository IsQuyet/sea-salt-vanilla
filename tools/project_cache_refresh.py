"""Shared presentation and validation helpers for project-cache refresh commands."""

from __future__ import annotations

from typing import Any

from project_cache import get_project_cache_entry, get_project_cache_error
from project_refresh_plan import PlannedProject


MAX_DISPLAYED_REFRESH_ERRORS = 50


def verbose_print(message: str, *, verbose: bool) -> None:
    if verbose:
        print(message, flush=True)


def planned_project_is_cached(
    project: PlannedProject,
    project_cache: dict[str, Any],
) -> bool:
    """Return whether every known provider coordinate resolves from the cache."""
    return bool(project.cache_keys) and all(
        get_project_cache_entry(cache_key, project_cache) is not None
        for cache_key in project.cache_keys
    )


def planned_projects_requiring_refresh(
    projects: list[PlannedProject],
    project_cache: dict[str, Any],
    *,
    force: bool,
) -> list[PlannedProject]:
    """Return logical provider projects requiring one lookup each."""
    return [
        project
        for project in projects
        if force or not planned_project_is_cached(project, project_cache)
    ]


def collect_planned_project_refresh_errors(
    projects: list[PlannedProject],
    project_cache: dict[str, Any],
) -> list[str]:
    """Collect one clear error for each unresolved logical provider project."""
    errors: list[str] = []
    for project in projects:
        if planned_project_is_cached(project, project_cache):
            continue

        error_entry = next(
            (
                cached_error
                for cache_key in project.cache_keys
                if (cached_error := get_project_cache_error(cache_key, project_cache))
            ),
            None,
        )
        display_ref = project.slug or project.project_id
        if error_entry:
            errors.append(f"{display_ref}: {error_entry.get('error')}")
            continue

        missing_keys = [
            cache_key
            for cache_key in project.cache_keys
            if get_project_cache_entry(cache_key, project_cache) is None
        ]
        errors.append(
            f"{display_ref}: missing project metadata for {', '.join(missing_keys)}"
        )
    return errors


def format_refresh_error_report(errors: list[str]) -> str:
    displayed_errors = errors[:MAX_DISPLAYED_REFRESH_ERRORS]
    joined_errors = "\n".join(f"- {error}" for error in displayed_errors)
    if len(errors) <= MAX_DISPLAYED_REFRESH_ERRORS:
        return joined_errors

    hidden_error_count = len(errors) - MAX_DISPLAYED_REFRESH_ERRORS
    return f"{joined_errors}\n... {hidden_error_count} more"
