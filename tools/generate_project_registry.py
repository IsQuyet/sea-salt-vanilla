#!/usr/bin/env python3
"""Sync project metadata used by the mod feature matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mod_data_common import (
    PROJECTS_PATH,
    PROJECT_CACHE,
    collect_matrix_project_refs,
    fetch_modrinth_project,
    load_installed_mods,
    load_project_cache,
    load_project_meta,
    write_json,
)


def project_json_text(data: dict[str, dict[str, Any]]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in ["name", "source", "slug", "modrinth_id", "links"]:
        if key in entry and entry[key]:
            ordered[key] = entry[key]
    for key in sorted(entry):
        if key not in ordered and entry[key]:
            ordered[key] = entry[key]
    return ordered


def entry_from_modrinth(project: dict[str, Any]) -> dict[str, Any]:
    return normalize_entry(
        {
            "name": project.get("title"),
            "source": "modrinth",
            "slug": project.get("slug"),
            "modrinth_id": project.get("id"),
        }
    )


def entry_from_installed(mod: dict[str, Any], project_cache: dict[str, Any]) -> dict[str, Any]:
    if mod.get("modrinth_id"):
        project = fetch_modrinth_project(str(mod["modrinth_id"]), project_cache)
        if project:
            return entry_from_modrinth(project)

    return normalize_entry(
        {
            "name": mod.get("name"),
            "source": "modrinth" if mod.get("modrinth_id") else "unknown",
            "slug": mod.get("slug"),
            "modrinth_id": mod.get("modrinth_id"),
        }
    )


def missing_entry(ref: str, installed: list[dict[str, Any]], project_cache: dict[str, Any]) -> dict[str, Any]:
    ref_lower = ref.lower()
    for mod in installed:
        if ref_lower in {str(mod.get("slug", "")).lower(), str(mod.get("name", "")).lower()}:
            return entry_from_installed(mod, project_cache)
        if ref == str(mod.get("modrinth_id") or ""):
            return entry_from_installed(mod, project_cache)

    project = fetch_modrinth_project(ref, project_cache)
    if project:
        return entry_from_modrinth(project)

    return normalize_entry({"name": ref, "source": "unknown", "slug": ref})


def expected_projects() -> dict[str, dict[str, Any]]:
    current = load_project_meta()
    installed = load_installed_mods()
    project_cache = load_project_cache()
    refs = collect_matrix_project_refs()

    expected = {key: normalize_entry(value) for key, value in current.items()}
    for ref in refs:
        if ref not in expected:
            expected[ref] = missing_entry(ref, installed, project_cache)

    write_json(PROJECT_CACHE, project_cache)
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
            raise SystemExit("data/mods/generated/projects.json is not up to date. Run python tools/generate_mod_projects.py")
        print("data/mods/generated/projects.json is up to date")
        return

    PROJECTS_PATH.write_text(expected_text, encoding="utf-8", newline="\n")
    print(f"Generated {Path('data/mods/generated/projects.json')}")


if __name__ == "__main__":
    main()
