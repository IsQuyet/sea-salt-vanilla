#!/usr/bin/env python3
"""Generate target project sets and the all-version documentation catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from curseforge_cache import load_curseforge_project_cache
from modrinth_cache import load_modrinth_project_cache
from project_cache import get_project_cache_entry
from project_data_common import (
    OPTIONAL_PATH,
    PROJECTS_PATH,
    PROJECT_CATALOG_PATH,
)
from project_data_contract import (
    collect_project_set_overlap_issues,
    collect_documentation_project_refs,
)
from project_data_identity import normalize_project_source, project_entry_key, provider_ref_key


def project_json_text(data: dict[str, dict[str, Any]]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Order the stable generated project fields for readable diffs."""
    ordered_entry: dict[str, Any] = {}
    for field_name in ["name", "type", "source", "slug", "id"]:
        if entry.get(field_name):
            ordered_entry[field_name] = entry[field_name]
    return ordered_entry


def resolve_cached_project(
    ref: dict[str, Any],
    project_caches: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Resolve one documented ref through its provider project cache."""
    source = normalize_project_source(ref.get("source"))
    if source not in {"modrinth", "curseforge"}:
        raise ValueError(f"Unsupported project source {source!r} in docs config.")

    project_slug = str(ref.get("slug") or ref.get("key") or "").lower()
    lookup_ref = str(ref.get("id") or project_slug)
    if not lookup_ref:
        raise ValueError(f"Project ref {ref!r} has neither an id nor a slug.")

    project_cache = project_caches.get(source, {})
    cached_project = get_project_cache_entry(lookup_ref, project_cache)
    if not cached_project:
        raise ValueError(
            f"Missing {source} project metadata for {lookup_ref}. "
            f"Run python tools/refresh_{source}_cache.py before generating project data."
        )

    return normalize_entry(
        {
            "name": cached_project.get("name"),
            "type": ref.get("type") or cached_project.get("type"),
            "source": source,
            "slug": cached_project.get("slug"),
            "id": cached_project.get("id"),
        }
    )


def build_project_catalog(
    refs: dict[str, dict[str, Any]],
    project_caches: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Resolve refs into a canonical slug-keyed generated catalog."""
    catalog: dict[str, dict[str, Any]] = {}

    for fallback_key, ref in refs.items():
        entry = resolve_cached_project(ref, project_caches)
        catalog_key = project_entry_key(entry, fallback_key)
        if not catalog_key:
            raise ValueError(f"Project ref {ref!r} has no canonical catalog slug.")

        existing_entry = catalog.get(catalog_key)
        if existing_entry:
            existing_identity = provider_ref_key(existing_entry)
            candidate_identity = provider_ref_key(entry)
            if existing_identity != candidate_identity:
                raise ValueError(
                    f"Catalog slug {catalog_key} is used by both "
                    f"{existing_identity} and {candidate_identity}."
                )
            continue
        catalog[catalog_key] = entry

    return dict(sorted(catalog.items()))


def main() -> None:
    documented_refs = collect_documentation_project_refs()
    project_caches = {
        "modrinth": load_modrinth_project_cache(),
        "curseforge": load_curseforge_project_cache(),
    }

    default_catalog = build_project_catalog(documented_refs.defaults, project_caches)
    optional_catalog = build_project_catalog(documented_refs.optional, project_caches)
    documentation_catalog = build_project_catalog(
        documented_refs.all_versions,
        project_caches,
    )

    catalog_contract_issues = collect_project_set_overlap_issues(
        default_catalog,
        optional_catalog,
        left_label="P",
        right_label="O",
    )
    if catalog_contract_issues:
        raise ValueError("\n".join(catalog_contract_issues))

    expected_files = {
        PROJECTS_PATH: project_json_text(default_catalog),
        OPTIONAL_PATH: project_json_text(optional_catalog),
        PROJECT_CATALOG_PATH: project_json_text(documentation_catalog),
    }
    for output_path, output_text in expected_files.items():
        output_path.write_text(output_text, encoding="utf-8", newline="\n")
        print(f"Generated {Path('data') / output_path.name}")


if __name__ == "__main__":
    main()
