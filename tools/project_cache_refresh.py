"""Shared presentation and validation helpers for project-cache refresh commands."""

from __future__ import annotations

from typing import Any

from project_cache import get_project_cache_entry, get_project_cache_error


MAX_DISPLAYED_REFRESH_ERRORS = 50


def verbose_print(message: str, *, verbose: bool) -> None:
    if verbose:
        print(message, flush=True)


def missing_project_cache_refs(
    project_refs: list[str],
    project_cache: dict[str, Any],
    *,
    force: bool = False,
) -> list[str]:
    """Return project refs that would be fetched in the current refresh mode."""
    return [
        project_ref
        for project_ref in sorted(set(project_refs))
        if project_ref and (force or get_project_cache_entry(project_ref, project_cache) is None)
    ]


def collect_project_refresh_errors(
    project_refs: list[str],
    project_cache: dict[str, Any],
) -> list[str]:
    """Collect stored fetch errors or missing metadata for required project refs."""
    errors: list[str] = []
    for project_ref in sorted(set(project_refs)):
        if not project_ref:
            continue

        error_entry = get_project_cache_error(project_ref, project_cache)
        if error_entry:
            errors.append(f"{project_ref}: {error_entry.get('error')}")
            continue

        if get_project_cache_entry(project_ref, project_cache) is None:
            errors.append(f"{project_ref}: missing project metadata")
    return errors


def format_refresh_error_report(errors: list[str]) -> str:
    displayed_errors = errors[:MAX_DISPLAYED_REFRESH_ERRORS]
    joined_errors = "\n".join(f"- {error}" for error in displayed_errors)
    if len(errors) <= MAX_DISPLAYED_REFRESH_ERRORS:
        return joined_errors

    hidden_error_count = len(errors) - MAX_DISPLAYED_REFRESH_ERRORS
    return f"{joined_errors}\n... {hidden_error_count} more"
