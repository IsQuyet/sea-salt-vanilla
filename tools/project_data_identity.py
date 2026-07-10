"""Shared project identity and reference-resolution helpers."""

from __future__ import annotations

from typing import Any


def normalize_project_source(source: Any) -> str:
    """Return a normalized provider name, defaulting compact refs to Modrinth."""
    return str(source or "modrinth").lower()


def project_refs_from_selected(selected: Any, location: str = "selected") -> list[Any]:
    """Return default project refs from a required docs/config selected list."""
    if isinstance(selected, list):
        return selected
    raise TypeError(f"{location}: selected must be a list of project refs")


def project_ref_key(ref: Any) -> str | None:
    """Return the human-facing catalog key for a compact project reference."""
    if ref is None:
        return None
    if isinstance(ref, dict):
        for key in ["key", "slug", "id", "name"]:
            if value := ref.get(key):
                return str(value).lower()
        return None
    return str(ref).lower()


def provider_ref_key(ref: Any, fallback_type: str = "mod") -> str | None:
    """Return a provider-qualified identity key without conflating catalog slugs."""
    if ref is None:
        return None
    if not isinstance(ref, dict):
        return f"modrinth:slug:{fallback_type}:{str(ref).lower()}"

    source = normalize_project_source(ref.get("source"))
    if project_id := ref.get("id"):
        return f"{source}:id:{project_id}"
    if slug := ref.get("slug") or ref.get("key"):
        project_type = str(ref.get("type") or fallback_type)
        return f"{source}:slug:{project_type}:{str(slug).lower()}"
    if name := ref.get("name"):
        return f"{source}:name:{str(name).lower()}"
    return None


def project_entry_key(project: dict[str, Any], fallback: Any = None) -> str | None:
    """Return the generated catalog key for a project metadata entry."""
    if slug := project.get("slug"):
        return str(slug).lower()
    if key := project.get("key"):
        return str(key).lower()
    if fallback is not None:
        return str(fallback).lower()
    return None


def resolve_project_ref(project_meta: dict[str, dict[str, Any]], ref: Any) -> dict[str, Any] | None:
    """Resolve a docs/config project reference against generated project metadata."""
    if ref is None:
        return None
    key = project_ref_key(ref)
    if key and key in project_meta:
        project = project_meta[key]
        expected_source = normalize_project_source(
            ref.get("source") if isinstance(ref, dict) else None
        )
        actual_source = normalize_project_source(project.get("source"))
        if expected_source != actual_source:
            return None
        return project
    if isinstance(ref, dict):
        return ref
    return None


def project_identity(project: dict[str, Any] | None, fallback: Any = None) -> str | None:
    """Return a stable identity string suitable for duplicate and set checks."""
    if project is None:
        return str(fallback).lower() if fallback else None

    if source := normalize_project_source(project.get("source")):
        if project_id := project.get("id"):
            return f"{source}:{project_id}"
        if slug := project.get("slug"):
            project_type = str(project.get("type") or "mod")
            return f"{source}:{project_type}:{str(slug).lower()}"
    if slug := project.get("slug"):
        return f"slug:{str(slug).lower()}"
    if name := project.get("name"):
        return f"name:{str(name).lower()}"
    return str(fallback).lower() if fallback else None


def build_installed_project_index(installed: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Index installed packwiz projects by the identities used throughout checks."""
    installed_index: dict[str, set[str]] = {
        "slugs": set(),
        "names": set(),
        "ids": set(),
        "source_ids": set(),
        "source_slugs": set(),
    }

    for project in installed:
        if slug := project.get("slug"):
            normalized_slug = str(slug).lower()
            installed_index["slugs"].add(normalized_slug)
            if source := project.get("source"):
                installed_index["source_slugs"].add(
                    f"{normalize_project_source(source)}:{normalized_slug}"
                )
        if name := project.get("name"):
            installed_index["names"].add(str(name).lower())
        if project_id := project.get("id"):
            installed_index["ids"].add(str(project_id))
            if source := project.get("source"):
                installed_index["source_ids"].add(
                    f"{normalize_project_source(source)}:{project_id}"
                )
        if modrinth_id := project.get("modrinth_id"):
            installed_index["ids"].add(str(modrinth_id))

    return installed_index


def is_project_installed(project: dict[str, Any] | None, installed_index: dict[str, set[str]]) -> bool:
    """Return whether a project metadata entry is represented in the installed project index."""
    if project is None:
        return False

    source = normalize_project_source(project.get("source")) if project.get("source") else ""
    if project_id := project.get("id"):
        if source:
            return f"{source}:{project_id}" in installed_index["source_ids"]
        return str(project_id) in installed_index["ids"]
    if slug := project.get("slug"):
        normalized_slug = str(slug).lower()
        if source:
            return f"{source}:{normalized_slug}" in installed_index["source_slugs"]
        return normalized_slug in installed_index["slugs"]
    if name := project.get("name"):
        if str(name).lower() in installed_index["names"]:
            return True
    if modrinth_id := project.get("modrinth_id"):
        if str(modrinth_id) in installed_index["ids"]:
            return True

    return False
