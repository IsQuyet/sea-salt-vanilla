"""Shared project identity and reference-resolution helpers."""

from __future__ import annotations

from typing import Any


def project_refs_from_selected(selected: Any, location: str = "selected") -> list[Any]:
    """Return default project refs from a required docs/config selected list."""
    if isinstance(selected, list):
        return selected
    raise TypeError(f"{location}: selected must be a list of project refs")


def project_ref_key(ref: Any) -> str | None:
    """Return the canonical catalog key for a string or compact object reference."""
    if ref is None:
        return None
    if isinstance(ref, dict):
        for key in ["key", "slug", "id", "name"]:
            if value := ref.get(key):
                return str(value).lower()
        return None
    return str(ref).lower()


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
        return project_meta[key]
    if isinstance(ref, dict):
        return ref
    return None


def project_identity(project: dict[str, Any] | None, fallback: Any = None) -> str | None:
    """Return a stable identity string suitable for duplicate and set checks."""
    if project is None:
        return str(fallback).lower() if fallback else None

    if source := project.get("source"):
        if project_id := project.get("id"):
            return f"{source}:{project_id}"
        if slug := project.get("slug"):
            return f"{source}:{str(slug).lower()}"
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
    }

    for project in installed:
        if slug := project.get("slug"):
            installed_index["slugs"].add(str(slug).lower())
        if name := project.get("name"):
            installed_index["names"].add(str(name).lower())
        if project_id := project.get("id"):
            installed_index["ids"].add(str(project_id))
            if source := project.get("source"):
                installed_index["source_ids"].add(f"{source}:{project_id}")
        if modrinth_id := project.get("modrinth_id"):
            installed_index["ids"].add(str(modrinth_id))

    return installed_index


def is_project_installed(project: dict[str, Any] | None, installed_index: dict[str, set[str]]) -> bool:
    """Return whether a project metadata entry is represented in the installed project index."""
    if project is None:
        return False

    if slug := project.get("slug"):
        if str(slug).lower() in installed_index["slugs"]:
            return True
    if name := project.get("name"):
        if str(name).lower() in installed_index["names"]:
            return True
    if project_id := project.get("id"):
        if str(project_id) in installed_index["ids"]:
            return True
        if source := project.get("source"):
            if f"{source}:{project_id}" in installed_index["source_ids"]:
                return True
    if modrinth_id := project.get("modrinth_id"):
        if str(modrinth_id) in installed_index["ids"]:
            return True

    return False
