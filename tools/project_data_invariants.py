"""Validate generated project data against the formal P/O/D/A contract."""

from __future__ import annotations

from typing import Any

from project_data_common import (
    load_documentation_catalog,
    load_optional_meta,
    load_project_meta,
)
from project_data_contract import (
    build_project_data_indexes,
    collect_documentation_project_refs,
    index_projects_by_identity,
    resolved_ref_identities,
)


def remember_set_difference(
    issues: list[str],
    label: str,
    values: set[str],
) -> None:
    if values:
        issues.append(f"{label}: {', '.join(sorted(values))}")


def catalog_shape_issues(
    catalogs: dict[str, dict[str, dict[str, Any]]],
) -> list[str]:
    """Keep human-facing slug keys consistent and globally unambiguous."""
    issues: list[str] = []
    keys_by_catalog = {
        label: set(catalog)
        for label, catalog in catalogs.items()
    }

    for label, catalog in catalogs.items():
        for catalog_key, project in catalog.items():
            canonical_slug = str(project.get("slug") or "").lower()
            if canonical_slug != catalog_key:
                issues.append(
                    f"{label} key {catalog_key} does not match canonical slug "
                    f"{canonical_slug or '<missing>'}."
                )

    labels = list(catalogs)
    for left_index, left_label in enumerate(labels):
        for right_label in labels[left_index + 1 :]:
            overlap = keys_by_catalog[left_label] & keys_by_catalog[right_label]
            remember_set_difference(
                issues,
                f"{left_label} intersects {right_label} by catalog key",
                overlap,
            )
    return issues


def documentation_source_issues(
    groups: list[dict[str, Any]],
    default_projects: dict[str, dict[str, Any]],
    optional_projects: dict[str, dict[str, Any]],
    documentation_catalog: dict[str, dict[str, Any]],
) -> list[str]:
    """Verify P/O and the all-version catalog are generated from the right docs scope."""
    documented_refs = collect_documentation_project_refs(groups)
    issues: list[str] = []

    expected_default_ids, default_ref_issues = resolved_ref_identities(
        documented_refs.defaults,
        documentation_catalog,
        label="P",
    )
    expected_optional_ids, optional_ref_issues = resolved_ref_identities(
        documented_refs.optional,
        documentation_catalog,
        label="O",
    )
    expected_catalog_ids, catalog_ref_issues = resolved_ref_identities(
        documented_refs.all_versions,
        documentation_catalog,
        label="project-catalog",
    )
    issues.extend(default_ref_issues)
    issues.extend(optional_ref_issues)
    issues.extend(catalog_ref_issues)

    actual_default_index, actual_default_issues = index_projects_by_identity(
        default_projects,
        label="P",
    )
    actual_optional_index, actual_optional_issues = index_projects_by_identity(
        optional_projects,
        label="O",
    )
    actual_catalog_index, actual_catalog_issues = index_projects_by_identity(
        documentation_catalog,
        label="project-catalog",
    )
    issues.extend(actual_default_issues)
    issues.extend(actual_optional_issues)
    issues.extend(actual_catalog_issues)

    remember_set_difference(
        issues,
        "projects.json contains identities outside target-version defaults",
        set(actual_default_index) - expected_default_ids,
    )
    remember_set_difference(
        issues,
        "target-version defaults missing from projects.json",
        expected_default_ids - set(actual_default_index),
    )
    remember_set_difference(
        issues,
        "optional.json contains identities outside target-version optional refs",
        set(actual_optional_index) - expected_optional_ids,
    )
    remember_set_difference(
        issues,
        "target-version optional refs missing from optional.json",
        expected_optional_ids - set(actual_optional_index),
    )
    remember_set_difference(
        issues,
        "project-catalog.json contains identities outside documented versions",
        set(actual_catalog_index) - expected_catalog_ids,
    )
    remember_set_difference(
        issues,
        "documented-version identities missing from project-catalog.json",
        expected_catalog_ids - set(actual_catalog_index),
    )
    return issues


def generated_data_invariants(
    groups: list[dict[str, Any]],
    installed: list[dict[str, Any]],
    declared_dependencies: dict[str, dict[str, Any]],
) -> list[str]:
    """Verify target intent, dependency-only data, and packwiz installed facts."""
    default_projects = load_project_meta()
    optional_projects = load_optional_meta()
    documentation_catalog = load_documentation_catalog()

    indexes = build_project_data_indexes(
        defaults=default_projects,
        optional=optional_projects,
        dependencies=declared_dependencies,
        installed=installed,
    )
    issues = list(indexes.issues)
    issues.extend(
        catalog_shape_issues(
            {
                "projects.json": default_projects,
                "optional.json": optional_projects,
                "dependencies.json": declared_dependencies,
            }
        )
    )
    issues.extend(
        documentation_source_issues(
            groups,
            default_projects,
            optional_projects,
            documentation_catalog,
        )
    )
    return list(dict.fromkeys(issues))
