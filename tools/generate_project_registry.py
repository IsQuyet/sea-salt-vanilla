#!/usr/bin/env python3
"""Sync the global project registry used by the feature matrices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from project_data_common import (
    PROJECTS_PATH,
    PROJECT_CACHE,
    collect_matrix_project_refs,
    load_installed_projects,
    load_project_cache,
    project_ref_key,
    write_json,
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


def entry_from_ref(ref: dict[str, Any], installed: list[dict[str, Any]], project_cache: dict[str, Any]) -> dict[str, Any]:
    ref_key = str(project_ref_key(ref) or "")
    ref_source = str(ref.get("source") or "")
    ref_slug = str(ref.get("slug") or ref_key).lower()
    ref_id = str(ref.get("id") or "")

    for mod in installed:
        installed_identity_matches = bool(ref_source and ref_source == mod.get("source") and ref_slug == mod.get("slug"))
        installed_key_matches = ref_key in {str(mod.get("slug", "")).lower(), str(mod.get("name", "")).lower()}
        installed_id_matches = bool(ref_id and ref_id == str(mod.get("id") or ""))
        if installed_identity_matches or installed_key_matches or installed_id_matches:
            return entry_from_installed(mod, project_cache)

    if ref_source in ("", "modrinth"):
        lookup = ref_id or ref_slug or ref_key
        project = cached_modrinth_project(lookup, project_cache) if lookup else None
        if project:
            return entry_from_modrinth(project)

    if ref_source == "curseforge":
        return normalize_entry(
            {
                "name": ref.get("name") or display_name_from_slug(ref_slug),
                "type": ref.get("type"),
                "source": "curseforge",
                "slug": ref_slug,
                "id": ref_id,
            }
        )

    project = cached_modrinth_project(ref_key, project_cache) if ref_key else None
    if project:
        return entry_from_modrinth(project)

    fallback_slug = ref_slug or ref_key
    return normalize_entry(
        {
            "name": ref.get("name") or display_name_from_slug(fallback_slug),
            "type": ref.get("type"),
            "source": ref_source or "unknown",
            "slug": fallback_slug,
        }
    )


def expected_projects() -> dict[str, dict[str, Any]]:
    installed = load_installed_projects()
    project_cache = load_project_cache()
    refs = collect_matrix_project_refs()

    expected = {str(mod["slug"]): entry_from_installed(mod, project_cache) for mod in installed}
    for ref in refs:
        key = project_ref_key(ref)
        if key and key not in expected:
            expected[key] = entry_from_ref(ref, installed, project_cache)

    return dict(sorted(expected.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check whether projects.json is up to date without writing it.")
    args = parser.parse_args()

    expected = expected_projects()
    expected_text = project_json_text(expected)

    if args.check:
        current_text = ""
        if PROJECTS_PATH.exists():
            current_text = PROJECTS_PATH.read_text(encoding="utf-8-sig")
        if current_text != expected_text:
            raise SystemExit("data/projects.json is not up to date. Run python tools/generate_project_registry.py")
        print("data/projects.json is up to date")
        return

    PROJECTS_PATH.write_text(expected_text, encoding="utf-8", newline="\n")
    print(f"Generated {Path('data/projects.json')}")


if __name__ == "__main__":
    main()
