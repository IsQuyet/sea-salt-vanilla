"""Generated data invariant checks for docs, packwiz, and data catalogs."""

from __future__ import annotations

from typing import Any

from project_data_common import TARGET_VERSION, load_optional_meta, load_project_meta
from project_data_identity import project_ref_key


def collect_documented_ref_sets(groups: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Return the project keys declared by docs config for the target Minecraft version."""
    default_refs: set[str] = set()
    optional_refs: set[str] = set()

    def ref_key(ref: Any) -> str | None:
        key = project_ref_key(ref)
        return key.lower() if key else None

    for group in groups:
        is_optional_group = bool(group["_optional"])
        for section in group["sections"]:
            for row in section["rows"]:
                version_data = row.get("versions", {}).get(TARGET_VERSION)
                if not version_data:
                    continue

                selected_key = ref_key(version_data.get("selected"))
                if selected_key:
                    if is_optional_group:
                        optional_refs.add(selected_key)
                    else:
                        default_refs.add(selected_key)

                for alternative in version_data.get("alternatives", []):
                    alternative_key = ref_key(alternative)
                    if alternative_key:
                        optional_refs.add(alternative_key)

    optional_refs -= default_refs
    return {
        "default": default_refs,
        "optional": optional_refs,
        "all": default_refs | optional_refs,
    }


def generated_data_invariants(
    groups: list[dict[str, Any]],
    installed: list[dict[str, Any]],
    declared_dependencies: dict[str, dict[str, Any]],
) -> list[str]:
    """Verify generated data catalogs remain disjoint and match their source sets."""
    project_keys = set(load_project_meta())
    optional_keys = set(load_optional_meta())
    dependency_keys = set(declared_dependencies)
    installed_keys = {str(project["slug"]).lower() for project in installed}
    documented_refs = collect_documented_ref_sets(groups)

    issues: list[str] = []

    def remember_set_difference(label: str, values: set[str]) -> None:
        if values:
            issues.append(f"{label}: {', '.join(sorted(values))}")

    remember_set_difference("projects.json intersects optional.json", project_keys & optional_keys)
    remember_set_difference("projects.json intersects dependencies.json", project_keys & dependency_keys)
    remember_set_difference("optional.json intersects dependencies.json", optional_keys & dependency_keys)
    remember_set_difference("projects.json contains entries outside docs default refs", project_keys - documented_refs["default"])
    remember_set_difference("docs default refs missing from projects.json", documented_refs["default"] - project_keys)
    remember_set_difference("optional.json contains entries outside docs optional refs", optional_keys - documented_refs["optional"])
    remember_set_difference("docs optional refs missing from optional.json", documented_refs["optional"] - optional_keys)
    remember_set_difference("projects.json + optional.json contains entries outside docs refs", (project_keys | optional_keys) - documented_refs["all"])
    remember_set_difference("docs refs missing from projects.json + optional.json", documented_refs["all"] - (project_keys | optional_keys))
    remember_set_difference("projects.json + dependencies.json contains entries outside packwiz", (project_keys | dependency_keys) - installed_keys)
    remember_set_difference("packwiz installed entries missing from projects.json + dependencies.json", installed_keys - (project_keys | dependency_keys))

    return issues
