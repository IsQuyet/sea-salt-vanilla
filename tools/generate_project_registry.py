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
    category_project_type,
    load_feature_groups,
    load_project_cache,
    project_ref_key,
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


def remember_project_ref(refs: dict[str, dict[str, Any]], ref: Any, project_type: str) -> None:
    if ref is None:
        return

    if isinstance(ref, dict):
        documented_ref = dict(ref)
    else:
        documented_ref = {"source": "unknown", "slug": str(ref).lower()}

    documented_ref.setdefault("type", project_type)
    key = project_ref_key(documented_ref)
    if key:
        refs.setdefault(key, documented_ref)


def collect_documented_project_refs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    default_refs: dict[str, dict[str, Any]] = {}
    optional_refs: dict[str, dict[str, Any]] = {}

    for group in load_feature_groups():
        is_optional_group = bool(group.get("_optional"))
        project_type = category_project_type(str(group.get("_category") or ""))
        for section in group.get("sections", []):
            for row in section.get("rows", []):
                for version_data in row.get("versions", {}).values():
                    selected_ref = version_data.get("selected")
                    if is_optional_group:
                        remember_project_ref(optional_refs, selected_ref, project_type)
                    else:
                        remember_project_ref(default_refs, selected_ref, project_type)

                    for alternative_ref in version_data.get("alternatives", []):
                        remember_project_ref(optional_refs, alternative_ref, project_type)

    for key in list(optional_refs):
        if key in default_refs:
            del optional_refs[key]

    return default_refs, optional_refs


def build_project_catalog(refs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    project_cache = load_project_cache()
    entries = {
        str(ref.get("slug") or ref.get("key") or key).lower(): entry_from_documented_ref(ref, project_cache)
        for key, ref in refs.items()
    }
    return dict(sorted(entries.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check whether generated project catalogs are up to date without writing them.")
    args = parser.parse_args()

    default_refs, optional_refs = collect_documented_project_refs()
    expected_default_catalog = build_project_catalog(default_refs)
    expected_optional_catalog = build_project_catalog(optional_refs)
    expected_files = {
        PROJECTS_PATH: project_json_text(expected_default_catalog),
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
