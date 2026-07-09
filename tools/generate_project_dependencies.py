#!/usr/bin/env python3
"""Generate dependency-only project data from docs roots and Modrinth metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from project_data_common import (
    DEPENDENCIES_PATH,
    DEPENDENCY_CACHE,
    MissingModrinthCacheError,
    TARGET_VERSION,
    cache_entry_has_error,
    category_project_type,
    get_project_cache_entry,
    iter_feature_versions,
    load_dependency_cache,
    load_installed_projects,
    load_project_cache,
    require_modrinth_version_cache,
    selected_project_refs_from_version,
    write_json,
)
from project_data_identity import project_ref_key


def dependency_json_text(data: dict[str, dict[str, Any]]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def collect_target_version_project_refs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect target-version default roots and optional refs directly from docs config."""
    default_refs: list[dict[str, Any]] = []
    optional_refs: list[dict[str, Any]] = []
    seen_default_keys: set[str] = set()
    seen_optional_keys: set[str] = set()

    def normalize_ref(ref: Any, project_type: str) -> dict[str, Any] | None:
        if ref is None:
            return None
        if isinstance(ref, dict):
            normalized = dict(ref)
        else:
            normalized = {"slug": str(ref).lower()}
        normalized.setdefault("type", project_type)
        return normalized

    def remember(refs: list[dict[str, Any]], seen_keys: set[str], ref: Any, project_type: str) -> None:
        normalized = normalize_ref(ref, project_type)
        if not normalized:
            return
        key = project_ref_key(normalized)
        if not key or key in seen_keys:
            return
        seen_keys.add(key)
        refs.append(normalized)

    for group, section, row, version, version_data in iter_feature_versions():
        if version != TARGET_VERSION:
            continue

        is_optional_group = bool(group.get("_optional"))
        project_type = category_project_type(str(group.get("_category") or ""))
        refs = optional_refs if is_optional_group else default_refs
        seen_keys = seen_optional_keys if is_optional_group else seen_default_keys
        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            TARGET_VERSION,
            version_data,
        )
        for selected_ref in selected_refs:
            remember(refs, seen_keys, selected_ref, project_type)

        for alternative_ref in version_data.get("alternatives", []):
            remember(optional_refs, seen_optional_keys, alternative_ref, project_type)

    default_keys = {project_ref_key(ref) for ref in default_refs}
    optional_refs = [ref for ref in optional_refs if project_ref_key(ref) not in default_keys]
    return default_refs, optional_refs


def cached_modrinth_project_from_ref(ref: dict[str, Any], project_cache: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve a docs/config ref through the committed Modrinth project snapshot."""
    source = str(ref.get("source") or "modrinth").lower()
    if source != "modrinth":
        return None

    lookup_values = [
        str(ref.get("id") or ""),
        str(ref.get("slug") or ""),
        str(ref.get("key") or ""),
        str(ref.get("name") or ""),
    ]
    for lookup_value in lookup_values:
        if not lookup_value:
            continue
        cached_project = get_project_cache_entry(lookup_value, project_cache)
        if cached_project:
            return cached_project
    return None


def collect_documented_identities(
    default_refs: list[dict[str, Any]],
    optional_refs: list[dict[str, Any]],
    project_cache: dict[str, Any],
) -> dict[str, set[str]]:
    """Collect documented project ids and slugs so dependencies stay a separate bridge set."""
    identities = {"project_ids": set(), "slugs": set()}
    for ref in [*default_refs, *optional_refs]:
        if slug := ref.get("slug") or ref.get("key"):
            identities["slugs"].add(str(slug).lower())
        cached_project = cached_modrinth_project_from_ref(ref, project_cache)
        if not cached_project:
            continue
        if project_id := cached_project.get("id"):
            identities["project_ids"].add(str(project_id))
        if slug := cached_project.get("slug"):
            identities["slugs"].add(str(slug).lower())
    return identities


def build_installed_indexes(installed_projects: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """Index packwiz lock metadata without using installed projects as dependency roots."""
    indexes: dict[str, dict[str, dict[str, Any]]] = {
        "modrinth_ids": {},
        "slugs": {},
    }
    for project in installed_projects:
        if modrinth_id := project.get("modrinth_id"):
            indexes["modrinth_ids"][str(modrinth_id)] = project
        if slug := project.get("slug"):
            indexes["slugs"][str(slug).lower()] = project
    return indexes


def find_installed_project_for_ref(
    ref: dict[str, Any],
    project_cache: dict[str, Any],
    installed_indexes: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any] | None:
    """Find the packwiz lock entry for a documented default root."""
    cached_project = cached_modrinth_project_from_ref(ref, project_cache)
    if cached_project and cached_project.get("id"):
        installed_project = installed_indexes["modrinth_ids"].get(str(cached_project["id"]))
        if installed_project:
            return installed_project

    for project_id_value in [ref.get("id"), ref.get("key")]:
        if not project_id_value:
            continue
        installed_project = installed_indexes["modrinth_ids"].get(str(project_id_value))
        if installed_project:
            return installed_project

    for slug_value in [ref.get("slug"), ref.get("key"), (cached_project or {}).get("slug")]:
        if not slug_value:
            continue
        installed_project = installed_indexes["slugs"].get(str(slug_value).lower())
        if installed_project:
            return installed_project
    return None


def project_cache_entry_for_id(project_id: str, project_cache: dict[str, Any]) -> dict[str, Any] | None:
    return get_project_cache_entry(project_id, project_cache)


def dependency_entry_from_project(
    project_id: str,
    required_by: set[str],
    installed_project: dict[str, Any] | None,
    project_cache: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Build one dependencies.json entry from Modrinth snapshot metadata."""
    cached_project = project_cache_entry_for_id(project_id, project_cache)
    if not cached_project:
        raise MissingModrinthCacheError(
            "Missing Modrinth project cache entry required for dependency generation: "
            f"{project_id}. Run python tools/refresh_modrinth_cache.py before generating dependencies."
        )

    slug = str(cached_project.get("slug") or project_id).lower()
    entry = {
        "name": str(cached_project.get("title") or project_id),
        "type": str(cached_project.get("project_type") or ""),
        "source": "modrinth",
        "slug": slug,
        "id": project_id,
        "required_by": sorted(required_by),
    }
    return slug, entry


def expected_dependency_data_from_docs_roots(
    *,
    allow_network: bool,
) -> dict[str, dict[str, Any]]:
    """Generate dependency-only data from docs default roots, not from installed projects."""
    installed_projects = load_installed_projects()
    installed_indexes = build_installed_indexes(installed_projects)
    dependency_cache = load_dependency_cache()
    project_cache = load_project_cache()
    default_refs, optional_refs = collect_target_version_project_refs()
    documented = collect_documented_identities(default_refs, optional_refs, project_cache)

    root_projects = [
        installed_project
        for ref in default_refs
        if (installed_project := find_installed_project_for_ref(ref, project_cache, installed_indexes))
    ]
    root_version_ids = [str(project.get("modrinth_version") or "") for project in root_projects]
    if allow_network:
        from project_data_common import fetch_missing_modrinth_versions

        fetch_missing_modrinth_versions(root_version_ids, dependency_cache)
    else:
        require_modrinth_version_cache(root_version_ids, dependency_cache)

    dependency_required_by: dict[str, set[str]] = {}
    queued_projects = list(root_projects)
    visited_version_ids: set[str] = set()
    root_project_ids = {
        str(project.get("modrinth_id") or "")
        for project in root_projects
        if project.get("modrinth_id")
    }

    while queued_projects:
        current_project = queued_projects.pop(0)
        current_version_id = str(current_project.get("modrinth_version") or "")
        if not current_version_id or current_version_id in visited_version_ids:
            continue
        visited_version_ids.add(current_version_id)

        if allow_network:
            from project_data_common import fetch_missing_modrinth_versions

            fetch_missing_modrinth_versions([current_version_id], dependency_cache)
        else:
            require_modrinth_version_cache([current_version_id], dependency_cache)

        version_data = dependency_cache.get(current_version_id)
        if not isinstance(version_data, dict) or cache_entry_has_error(version_data):
            continue

        current_slug = str(current_project.get("slug") or current_project.get("name") or "")
        for dependency in version_data.get("dependencies", []):
            if dependency.get("dependency_type") != "required":
                continue
            dependency_project_id = str(dependency.get("project_id") or "")
            if not dependency_project_id or dependency_project_id in root_project_ids:
                continue

            installed_dependency = installed_indexes["modrinth_ids"].get(dependency_project_id)
            cached_dependency = project_cache_entry_for_id(dependency_project_id, project_cache)
            dependency_slug = str(
                (cached_dependency or {}).get("slug")
                or (installed_dependency or {}).get("slug")
                or ""
            ).lower()
            if dependency_project_id in documented["project_ids"] or dependency_slug in documented["slugs"]:
                continue

            dependency_required_by.setdefault(dependency_project_id, set()).add(current_slug)
            if installed_dependency:
                queued_projects.append(installed_dependency)

    entries: dict[str, dict[str, Any]] = {}
    for project_id, required_by in sorted(dependency_required_by.items()):
        installed_project = installed_indexes["modrinth_ids"].get(project_id)
        slug, entry = dependency_entry_from_project(project_id, required_by, installed_project, project_cache)
        entries[slug] = entry

    return dict(sorted(entries.items()))


def load_expected_dependencies(
    *,
    persist_cache: bool = True,
    allow_network: bool = False,
) -> dict[str, dict[str, Any]]:
    expected_dependencies = expected_dependency_data_from_docs_roots(allow_network=allow_network)
    if persist_cache:
        write_json(DEPENDENCY_CACHE, load_dependency_cache())
    return expected_dependencies


def main() -> None:
    try:
        expected = load_expected_dependencies(persist_cache=False, allow_network=False)
    except MissingModrinthCacheError as error:
        raise SystemExit(str(error)) from error
    expected_text = dependency_json_text(expected)

    DEPENDENCIES_PATH.write_text(expected_text, encoding="utf-8", newline="\n")
    print(f"Generated {Path('data/dependencies.json')}")


if __name__ == "__main__":
    main()
