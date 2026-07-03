#!/usr/bin/env python3
"""Sync the global project registry used by the feature matrices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from project_data_common import (
    OPTIONAL_PATH,
    PROJECTS_PATH,
    collect_matrix_project_refs,
    load_installed_projects,
    load_project_cache,
)


def project_json_text(data: dict[str, dict[str, Any]]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in ["name", "type", "source", "slug", "id"]:
        if key in entry and entry[key]:
            ordered[key] = entry[key]
    for key in sorted(entry):
        if key not in ordered and entry[key]:
            ordered[key] = entry[key]
    return ordered


def display_name_from_slug(slug: str) -> str:
    """Create a readable fallback name without requiring network metadata."""
    return " ".join(word.capitalize() for word in slug.replace("_", "-").split("-") if word)


def cached_modrinth_project(project_ref: str, project_cache: dict[str, Any]) -> dict[str, Any] | None:
    """Read cached Modrinth project metadata without blocking registry generation on the network."""
    cached_project = project_cache.get(project_ref)
    if isinstance(cached_project, dict) and "error" not in cached_project:
        return cached_project
    return None


def entry_from_modrinth(project: dict[str, Any]) -> dict[str, Any]:
    return normalize_entry(
        {
            "name": project.get("title"),
            "source": "modrinth",
            "type": project.get("project_type"),
            "slug": project.get("slug"),
            "id": project.get("id"),
        }
    )


def entry_from_documented_ref(ref: dict[str, Any], project_cache: dict[str, Any]) -> dict[str, Any]:
    source = str(ref.get("source") or "unknown")
    slug = str(ref.get("slug") or ref.get("key") or "").lower()
    project_type = str(ref.get("type") or "mod")

    if source == "modrinth" and slug:
        project = cached_modrinth_project(slug, project_cache)
        if project:
            return entry_from_modrinth(project)

    return normalize_entry(
        {
            "name": display_name_from_slug(slug),
            "type": project_type,
            "source": source,
            "slug": slug,
            "id": ref.get("id"),
        }
    )


def entry_from_installed(mod: dict[str, Any], project_cache: dict[str, Any]) -> dict[str, Any]:
    if mod.get("source") == "modrinth" and mod.get("id"):
        project = cached_modrinth_project(str(mod["id"]), project_cache)
        if project:
            return entry_from_modrinth(project)

    return normalize_entry(
        {
            "name": mod.get("name"),
            "type": mod.get("type"),
            "source": mod.get("source") or "unknown",
            "slug": mod.get("slug"),
            "id": mod.get("id"),
        }
    )


def expected_projects() -> dict[str, dict[str, Any]]:
    installed = load_installed_projects()
    project_cache = load_project_cache()
    return dict(sorted((str(mod["slug"]), entry_from_installed(mod, project_cache)) for mod in installed))


def expected_optional_projects(installed_projects: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    project_cache = load_project_cache()
    optional_projects: dict[str, dict[str, Any]] = {}

    for ref in collect_matrix_project_refs():
        slug = str(ref.get("slug") or ref.get("key") or "").lower()
        if not slug or slug in installed_projects:
            continue
        optional_projects[slug] = entry_from_documented_ref(ref, project_cache)

    return dict(sorted(optional_projects.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check whether generated project catalogs are up to date without writing them.")
    args = parser.parse_args()

    expected_installed_projects = expected_projects()
    expected_optional_catalog = expected_optional_projects(expected_installed_projects)
    expected_files = {
        PROJECTS_PATH: project_json_text(expected_installed_projects),
        OPTIONAL_PATH: project_json_text(expected_optional_catalog),
    }

    if args.check:
        stale_paths: list[str] = []
        for path, expected_text in expected_files.items():
            current_text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
            if current_text != expected_text:
                stale_paths.append(str(path.relative_to(Path.cwd())))
        if stale_paths:
            raise SystemExit(
                f"{', '.join(stale_paths)} is not up to date. Run python tools/generate_project_registry.py"
            )
        print("Generated project catalogs are up to date")
        return

    PROJECTS_PATH.write_text(expected_files[PROJECTS_PATH], encoding="utf-8", newline="\n")
    OPTIONAL_PATH.write_text(expected_files[OPTIONAL_PATH], encoding="utf-8", newline="\n")
    print(f"Generated {Path('data/projects.json')}")
    print(f"Generated {Path('data/optional.json')}")


if __name__ == "__main__":
    main()
