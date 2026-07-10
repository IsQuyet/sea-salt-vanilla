"""Build consistent provider cache refresh manifests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from project_cache import project_cache_project_count
from project_refresh_plan import PlannedProject, ProjectRefreshPlan


MANIFEST_SCHEMA_VERSION = 2
DOCUMENTED_ORIGINS = {"docs-default", "docs-optional", "docs-alternative"}


def project_cache_error_count(project_cache: dict[str, Any]) -> int:
    """Return the number of unresolved project-cache errors."""
    errors = project_cache.get("errors", {})
    return len(errors) if isinstance(errors, dict) else 0


def count_projects_with_any_origin(
    projects: list[PlannedProject],
    origins: set[str],
) -> int:
    """Count unique planned projects carrying at least one selected origin."""
    return sum(bool(project.origins & origins) for project in projects)


def build_provider_manifest(
    *,
    provider: str,
    metadata_source: str,
    target_minecraft_version: str,
    force: bool,
    dry_run: bool,
    scopes: list[str],
    plan: ProjectRefreshPlan,
    provider_projects: list[PlannedProject],
    projects_to_fetch: int,
    projects_fetched: int,
    projects_failed: int,
    project_cache: dict[str, Any],
    versions: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build the common manifest shape used by every provider refresh."""
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "provider": provider,
        "metadata_source": metadata_source,
        "generated_at": datetime.now(UTC).isoformat(),
        "target_minecraft_version": target_minecraft_version,
        "request": {
            "force": force,
            "dry_run": dry_run,
            "scopes": scopes,
        },
        "projects": {
            "installed": count_projects_with_any_origin(provider_projects, {"installed"}),
            "documented": count_projects_with_any_origin(provider_projects, DOCUMENTED_ORIGINS),
            "unique": len(provider_projects),
            "to_fetch": projects_to_fetch,
            "fetched": projects_fetched,
            "failed": projects_failed,
            "cached": project_cache_project_count(project_cache),
            "errors": project_cache_error_count(project_cache),
        },
        "plan": {
            "conflicts": list(plan.conflicts),
        },
    }
    if versions is not None:
        manifest["versions"] = versions
    return manifest
