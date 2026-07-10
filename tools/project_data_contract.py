"""Define the provider-neutral project-data sets and their invariants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from project_data_common import (
    TARGET_VERSION,
    category_project_type,
    iter_feature_versions,
    selected_project_refs_from_version,
)
from project_data_identity import (
    normalize_project_source,
    project_ref_key,
    provider_ref_key,
)


SUPPORTED_PROJECT_SOURCES = {"modrinth", "curseforge"}


@dataclass
class DocumentationProjectRefs:
    """Separate target-version intent from all-version documentation metadata."""

    target_version: str
    defaults: dict[str, dict[str, Any]] = field(default_factory=dict)
    optional: dict[str, dict[str, Any]] = field(default_factory=dict)
    all_versions: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class ProjectDataIndexes:
    """Index P, O, D, and A by canonical provider identity."""

    defaults: dict[str, dict[str, Any]]
    optional: dict[str, dict[str, Any]]
    dependencies: dict[str, dict[str, Any]]
    installed: dict[str, dict[str, Any]]
    issues: list[str]


def normalize_documented_ref(ref: Any, project_type: str) -> dict[str, Any] | None:
    """Normalize one docs/config ref without resolving provider metadata."""
    if ref is None:
        return None
    if isinstance(ref, dict):
        normalized_ref = dict(ref)
    else:
        normalized_ref = {
            "source": "modrinth",
            "slug": str(ref).lower(),
        }

    normalized_ref.setdefault("source", "modrinth")
    normalized_ref.setdefault("type", project_type)
    return normalized_ref


def remember_documented_ref(
    refs: dict[str, dict[str, Any]],
    ref: Any,
    *,
    project_type: str,
    location: str,
) -> None:
    """Store one human-facing ref while rejecting catalog-key ambiguity."""
    normalized_ref = normalize_documented_ref(ref, project_type)
    if not normalized_ref:
        return

    catalog_key = project_ref_key(normalized_ref)
    provider_identity = provider_ref_key(normalized_ref, project_type)
    if not catalog_key or not provider_identity:
        raise ValueError(f"{location}: project ref {ref!r} has no provider coordinate.")

    existing_ref = refs.get(catalog_key)
    if not existing_ref:
        refs[catalog_key] = normalized_ref
        return

    existing_identity = provider_ref_key(existing_ref, project_type)
    if existing_identity != provider_identity:
        raise ValueError(
            f"{location}: catalog key {catalog_key} maps to both "
            f"{existing_identity} and {provider_identity}."
        )


def collect_documentation_project_refs(
    groups: list[dict[str, Any]] | None = None,
    *,
    target_version: str = TARGET_VERSION,
) -> DocumentationProjectRefs:
    """Collect target P/O refs and the all-version documentation catalog refs."""
    collected = DocumentationProjectRefs(target_version=target_version)

    for group, section, row, version, version_data in iter_feature_versions(groups):
        project_type = category_project_type(str(group.get("_category") or ""))
        base_location = (
            f"{group.get('_source_file')}:{row.get('id', '<unknown-row>')} ({version})"
        )
        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            version,
            version_data,
        )

        for selected_index, selected_ref in enumerate(selected_refs):
            location = f"{base_location} selected[{selected_index}]"
            remember_documented_ref(
                collected.all_versions,
                selected_ref,
                project_type=project_type,
                location=location,
            )
            if version != target_version:
                continue

            target_refs = collected.optional if group.get("_optional") else collected.defaults
            remember_documented_ref(
                target_refs,
                selected_ref,
                project_type=project_type,
                location=location,
            )

        for alternative_index, alternative_ref in enumerate(
            version_data.get("alternatives", [])
        ):
            location = f"{base_location} alternatives[{alternative_index}]"
            remember_documented_ref(
                collected.all_versions,
                alternative_ref,
                project_type=project_type,
                location=location,
            )
            if version == target_version:
                remember_documented_ref(
                    collected.optional,
                    alternative_ref,
                    project_type=project_type,
                    location=location,
                )

    return collected


def provider_project_identity(project: dict[str, Any]) -> str | None:
    """Return the canonical semantic identity shared by generated and installed data."""
    source = normalize_project_source(project.get("source"))
    project_id = str(project.get("id") or "")
    if source not in SUPPORTED_PROJECT_SOURCES or not project_id:
        return None
    return f"{source}:{project_id}"


def index_projects_by_identity(
    projects: dict[str, dict[str, Any]] | list[dict[str, Any]],
    *,
    label: str,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Index projects by provider ID and report malformed or duplicate identities."""
    project_items = projects.items() if isinstance(projects, dict) else enumerate(projects)
    indexed_projects: dict[str, dict[str, Any]] = {}
    issues: list[str] = []

    for project_key, project in project_items:
        identity = provider_project_identity(project)
        if not identity:
            issues.append(
                f"{label}[{project_key}] has no supported provider source and project id."
            )
            continue

        existing_project = indexed_projects.get(identity)
        if existing_project:
            existing_location = existing_project.get("file") or existing_project.get("slug")
            current_location = project.get("file") or project.get("slug") or project_key
            issues.append(
                f"{label} contains duplicate identity {identity}: "
                f"{existing_location} and {current_location}."
            )
            continue
        indexed_projects[identity] = project

    return indexed_projects, issues


def collect_project_set_overlap_issues(
    left_projects: dict[str, dict[str, Any]],
    right_projects: dict[str, dict[str, Any]],
    *,
    left_label: str,
    right_label: str,
) -> list[str]:
    """Report provider identities shared by two semantic project sets."""
    left_index, left_issues = index_projects_by_identity(
        left_projects,
        label=left_label,
    )
    right_index, right_issues = index_projects_by_identity(
        right_projects,
        label=right_label,
    )
    issues = [*left_issues, *right_issues]

    overlap = set(left_index) & set(right_index)
    if overlap:
        issues.append(
            f"{left_label} intersects {right_label}: "
            f"{', '.join(sorted(overlap))}"
        )
    return issues


def resolve_documented_ref(
    ref: Any,
    documentation_catalog: dict[str, dict[str, Any]],
    *,
    project_type: str,
) -> dict[str, Any] | None:
    """Resolve a docs ref through the tracked all-version metadata catalog."""
    normalized_ref = normalize_documented_ref(ref, project_type)
    if not normalized_ref:
        return None

    expected_source = normalize_project_source(normalized_ref.get("source"))
    expected_id = str(normalized_ref.get("id") or "")
    expected_slug = str(
        normalized_ref.get("slug") or normalized_ref.get("key") or ""
    ).lower()

    for candidate in documentation_catalog.values():
        if normalize_project_source(candidate.get("source")) != expected_source:
            continue
        if expected_id and str(candidate.get("id") or "") != expected_id:
            continue
        if expected_slug and str(candidate.get("slug") or "").lower() != expected_slug:
            continue
        if expected_id or expected_slug:
            return candidate
    return None


def resolved_ref_identities(
    refs: dict[str, dict[str, Any]],
    documentation_catalog: dict[str, dict[str, Any]],
    *,
    label: str,
) -> tuple[set[str], list[str]]:
    """Resolve documentation refs to provider identities for source-of-truth checks."""
    identities: set[str] = set()
    issues: list[str] = []

    for catalog_key, ref in refs.items():
        project_type = str(ref.get("type") or "mod")
        project = resolve_documented_ref(
            ref,
            documentation_catalog,
            project_type=project_type,
        )
        identity = provider_project_identity(project or {})
        if not identity:
            issues.append(f"{label} ref {catalog_key} is missing from project-catalog.json.")
            continue
        identities.add(identity)

    return identities, issues


def build_project_data_indexes(
    *,
    defaults: dict[str, dict[str, Any]],
    optional: dict[str, dict[str, Any]],
    dependencies: dict[str, dict[str, Any]],
    installed: list[dict[str, Any]],
) -> ProjectDataIndexes:
    """Build the P/O/D/A indexes and enforce their provider-neutral contract."""
    default_index, default_issues = index_projects_by_identity(defaults, label="P")
    optional_index, optional_issues = index_projects_by_identity(optional, label="O")
    dependency_index, dependency_issues = index_projects_by_identity(
        dependencies,
        label="D",
    )
    installed_index, installed_issues = index_projects_by_identity(installed, label="A")

    issues = [
        *default_issues,
        *optional_issues,
        *dependency_issues,
        *installed_issues,
    ]

    default_identities = set(default_index)
    optional_identities = set(optional_index)
    dependency_identities = set(dependency_index)
    installed_identities = set(installed_index)

    pairwise_overlaps = [
        ("P intersects O", default_identities & optional_identities),
        ("P intersects D", default_identities & dependency_identities),
        ("O intersects D", optional_identities & dependency_identities),
    ]
    for label, overlap in pairwise_overlaps:
        if overlap:
            issues.append(f"{label}: {', '.join(sorted(overlap))}")

    expected_installed_identities = default_identities | dependency_identities
    missing_installed = expected_installed_identities - installed_identities
    unexplained_installed = installed_identities - expected_installed_identities
    if missing_installed:
        issues.append(
            "P union D contains projects missing from A: "
            f"{', '.join(sorted(missing_installed))}"
        )
    if unexplained_installed:
        issues.append(
            "A contains projects outside P union D: "
            f"{', '.join(sorted(unexplained_installed))}"
        )

    non_modrinth_dependencies = {
        identity
        for identity, project in dependency_index.items()
        if normalize_project_source(project.get("source")) != "modrinth"
    }
    if non_modrinth_dependencies:
        issues.append(
            "D contains non-Modrinth projects even though dependency analysis is "
            f"Modrinth-only: {', '.join(sorted(non_modrinth_dependencies))}"
        )

    return ProjectDataIndexes(
        defaults=default_index,
        optional=optional_index,
        dependencies=dependency_index,
        installed=installed_index,
        issues=issues,
    )


def installed_project_classification(
    indexes: ProjectDataIndexes,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify A into direct, dependency-only, and unexplained projects."""
    documented: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    unexplained: list[dict[str, Any]] = []

    for identity, project in indexes.installed.items():
        if identity in indexes.defaults:
            documented.append(project)
        elif identity in indexes.dependencies:
            dependencies.append(project)
        else:
            unexplained.append(project)
    return documented, dependencies, unexplained


def curseforge_dependency_coverage(
    defaults: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return default CurseForge mods whose dependency closure is not verified."""
    return [
        project
        for project in defaults.values()
        if normalize_project_source(project.get("source")) == "curseforge"
        and str(project.get("type") or "mod") == "mod"
    ]
