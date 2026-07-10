"""Single-target documentation, installation, and dependency inventory."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from dependencies import (
    DependencyAnalysis,
    DependencyIssue,
    DependencySnapshot,
    ModrinthInstallation,
    analyze_required_dependencies,
    parse_dependency_snapshot,
    required_by_project,
    validate_snapshot_coverage,
)
from packwiz import (
    DEPENDENCY_SNAPSHOT_PATH,
    PROJECT_METADATA_PATH,
    RESOURCE_TYPES,
    InstalledProject,
    discover_categories,
    load_installed_projects,
    read_json,
    target_minecraft_version,
)
from project_metadata import (
    ProjectLookup,
    ProjectMetadata,
    ProjectMetadataError,
    normalize_provider,
    parse_project_metadata_pool,
    project_identity,
    resolve_project_ref,
)


PROVIDERS = ("modrinth", "curseforge")
STATUS_NAMES = ("default", "optional", "dependency", "installed", "unexplained")
HEALTH_SECTIONS = (
    "Installation",
    "Dependencies",
    "Documentation",
    "Metadata",
    "Packwiz",
)


@dataclass(frozen=True)
class DocumentationOccurrence:
    """One selected or alternative project occurrence in docs config."""

    ref: Any
    provider: str
    resource_type: str
    role: str
    location: str
    project_id: str = ""
    slug: str = ""
    identity: str = ""


@dataclass(frozen=True)
class InventoryIssue:
    """One maintainer-facing validation problem or coverage notice."""

    section: str
    code: str
    message: str
    severity: str = "error"
    identity: str = ""


@dataclass
class Inventory:
    """One normalized view shared by status, checks, docs, and refresh."""

    target_version: str
    categories: list[dict[str, Any]]
    groups: list[dict[str, Any]]
    metadata: dict[str, ProjectMetadata]
    occurrences: list[DocumentationOccurrence]
    installed: list[InstalledProject]
    dependency_snapshot: DependencySnapshot
    dependency_analysis: DependencyAnalysis
    defaults: dict[str, DocumentationOccurrence] = field(default_factory=dict)
    optional: dict[str, DocumentationOccurrence] = field(default_factory=dict)
    installed_by_identity: dict[str, InstalledProject] = field(default_factory=dict)
    dependency_identities: set[str] = field(default_factory=set)
    unexplained_identities: set[str] = field(default_factory=set)
    issues: list[InventoryIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[InventoryIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[InventoryIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]


def normalize_ref(ref: Any) -> tuple[str, str, str]:
    normalized_ref = dict(ref) if isinstance(ref, dict) else {"slug": str(ref)}
    provider = normalize_provider(normalized_ref.get("source"))
    project_id = str(normalized_ref.get("id") or "")
    slug = str(normalized_ref.get("slug") or normalized_ref.get("key") or "").lower()
    return provider, project_id, slug


def selected_refs(value: Any, *, location: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{location}: selected must be a list.")
    return value


def row_target_data(row: dict[str, Any], _target_version: str) -> dict[str, Any]:
    """Read the only supported direct single-target row shape."""
    if "versions" in row:
        raise ValueError(
            "Documentation rows must use direct selected and alternatives fields."
        )
    return {
        "selected": row.get("selected", []),
        "alternatives": row.get("alternatives", []),
    }


def load_documentation_sources() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[DocumentationOccurrence],
    list[InventoryIssue],
]:
    """Load categories, groups, and normalized target-version occurrences."""
    target_version = target_minecraft_version()
    categories = discover_categories()
    groups: list[dict[str, Any]] = []
    occurrences: list[DocumentationOccurrence] = []
    issues: list[InventoryIssue] = []

    for category in categories:
        source_paths = [(path, False) for path in category["matrix_paths"]]
        if category["optional_path"]:
            source_paths.append((category["optional_path"], True))

        for source_path, optional_group in source_paths:
            group = read_json(source_path)
            if not isinstance(group, dict):
                issues.append(
                    InventoryIssue(
                        section="Documentation",
                        code="invalid_group",
                        message=f"{source_path}: documentation group must be an object.",
                    )
                )
                continue
            group["_source_path"] = source_path
            group["_category"] = category["name"]
            group["_resource_type"] = category["resource_type"]
            group["_optional"] = optional_group
            groups.append(group)

            for section in group.get("sections", []):
                for row in section.get("rows", []):
                    row_location = (
                        f"{source_path}:{group.get('id', '<group>')}/"
                        f"{section.get('id', '<section>')}/{row.get('id', '<row>')}"
                    )
                    try:
                        target_data = row_target_data(row, target_version)
                        row_selected_refs = selected_refs(
                            target_data.get("selected"),
                            location=row_location,
                        )
                    except ValueError as error:
                        issues.append(
                            InventoryIssue(
                                section="Documentation",
                                code="invalid_row",
                                message=str(error),
                            )
                        )
                        continue

                    selected_role = "optional" if optional_group else "default"
                    for ref_index, ref in enumerate(row_selected_refs):
                        provider, project_id, slug = normalize_ref(ref)
                        occurrences.append(
                            DocumentationOccurrence(
                                ref=ref,
                                provider=provider,
                                project_id=project_id,
                                slug=slug,
                                resource_type=category["resource_type"],
                                role=selected_role,
                                location=f"{row_location} selected[{ref_index}]",
                            )
                        )

                    alternatives = target_data.get("alternatives", [])
                    if not isinstance(alternatives, list):
                        issues.append(
                            InventoryIssue(
                                section="Documentation",
                                code="invalid_alternatives",
                                message=f"{row_location}: alternatives must be a list.",
                            )
                        )
                        continue
                    for ref_index, ref in enumerate(alternatives):
                        provider, project_id, slug = normalize_ref(ref)
                        occurrences.append(
                            DocumentationOccurrence(
                                ref=ref,
                                provider=provider,
                                project_id=project_id,
                                slug=slug,
                                resource_type=category["resource_type"],
                                role="optional",
                                location=f"{row_location} alternatives[{ref_index}]",
                            )
                        )

    return categories, groups, occurrences, issues


def documentation_lookups(
    occurrences: Iterable[DocumentationOccurrence],
) -> list[ProjectLookup]:
    return [
        ProjectLookup(
            provider=occurrence.provider,
            project_id=occurrence.project_id,
            slug=occurrence.slug,
            resource_type=occurrence.resource_type,
            location=occurrence.location,
        )
        for occurrence in occurrences
    ]


def installed_lookups(installed: Iterable[InstalledProject]) -> list[ProjectLookup]:
    return [
        ProjectLookup(
            provider=project.provider,
            project_id=project.project_id,
            resource_type=project.resource_type,
            location=project.file,
        )
        for project in installed
        if project.provider in PROVIDERS and project.project_id
    ]


def modrinth_installations(
    installed: Iterable[InstalledProject],
) -> list[ModrinthInstallation]:
    return [
        ModrinthInstallation(
            project_id=project.project_id,
            version_id=project.version_id,
            origin=project.file,
        )
        for project in installed
        if project.provider == "modrinth"
    ]


def dependency_issue_to_inventory(issue: DependencyIssue) -> InventoryIssue:
    return InventoryIssue(
        section="Dependencies",
        code=issue.code,
        message=issue.message,
        identity=(
            project_identity("modrinth", issue.related_project_id or issue.project_id)
        ),
    )


def resolve_occurrences(
    occurrences: Iterable[DocumentationOccurrence],
    metadata: dict[str, ProjectMetadata],
) -> tuple[list[DocumentationOccurrence], list[InventoryIssue]]:
    resolved_occurrences: list[DocumentationOccurrence] = []
    issues: list[InventoryIssue] = []

    for occurrence in occurrences:
        try:
            project = resolve_project_ref(occurrence.ref, metadata)
        except ProjectMetadataError as error:
            issues.append(
                InventoryIssue(
                    section="Metadata",
                    code="missing_project_metadata",
                    message=f"{occurrence.location}: {error}",
                )
            )
            resolved_occurrences.append(occurrence)
            continue
        resolved_occurrences.append(
            DocumentationOccurrence(
                ref=occurrence.ref,
                provider=project.provider,
                project_id=project.project_id,
                slug=project.slug,
                resource_type=occurrence.resource_type,
                role=occurrence.role,
                location=occurrence.location,
                identity=project.identity,
            )
        )
    return resolved_occurrences, issues


def index_documentation_occurrences(
    occurrences: Iterable[DocumentationOccurrence],
) -> tuple[
    dict[str, DocumentationOccurrence],
    dict[str, DocumentationOccurrence],
    list[InventoryIssue],
]:
    defaults: dict[str, DocumentationOccurrence] = {}
    optional: dict[str, DocumentationOccurrence] = {}
    issues: list[InventoryIssue] = []

    for occurrence in occurrences:
        if not occurrence.identity:
            continue
        target = defaults if occurrence.role == "default" else optional
        previous_occurrence = target.get(occurrence.identity)
        if previous_occurrence:
            issues.append(
                InventoryIssue(
                    section="Documentation",
                    code="duplicate_project_ref",
                    message=(
                        f"{occurrence.identity} appears at both "
                        f"{previous_occurrence.location} and {occurrence.location}."
                    ),
                    identity=occurrence.identity,
                )
            )
            continue
        target[occurrence.identity] = occurrence

    for identity in sorted(set(defaults) & set(optional)):
        issues.append(
            InventoryIssue(
                section="Documentation",
                code="default_optional_overlap",
                message=f"{identity} is classified as both default and optional.",
                identity=identity,
            )
        )
    return defaults, optional, issues


def index_installed_projects(
    installed: Iterable[InstalledProject],
) -> tuple[dict[str, InstalledProject], list[InventoryIssue]]:
    installed_by_identity: dict[str, InstalledProject] = {}
    issues: list[InventoryIssue] = []

    for project in installed:
        if project.provider_conflict:
            issues.append(
                InventoryIssue(
                    section="Installation",
                    code="provider_conflict",
                    message=f"{project.file} declares both Modrinth and CurseForge metadata.",
                )
            )
        if not project.identity:
            issues.append(
                InventoryIssue(
                    section="Installation",
                    code="missing_provider_identity",
                    message=f"{project.file} has no supported provider project ID.",
                )
            )
            continue
        previous_project = installed_by_identity.get(project.identity)
        if previous_project:
            issues.append(
                InventoryIssue(
                    section="Installation",
                    code="duplicate_installed_identity",
                    message=(
                        f"{project.identity} is installed by both {previous_project.file} "
                        f"and {project.file}."
                    ),
                    identity=project.identity,
                )
            )
            continue
        installed_by_identity[project.identity] = project
    return installed_by_identity, issues


def build_inventory() -> Inventory:
    """Build the complete single-target inventory without network access."""
    categories, groups, raw_occurrences, issues = load_documentation_sources()
    installed = load_installed_projects()

    metadata: dict[str, ProjectMetadata] = {}
    try:
        metadata = parse_project_metadata_pool(read_json(PROJECT_METADATA_PATH))
    except (OSError, ValueError, ProjectMetadataError) as error:
        issues.append(
            InventoryIssue(
                section="Metadata",
                code="invalid_project_metadata_pool",
                message=str(error),
            )
        )

    resolved_occurrences, metadata_issues = resolve_occurrences(
        raw_occurrences,
        metadata,
    )
    issues.extend(metadata_issues)
    defaults, optional, documentation_issues = index_documentation_occurrences(
        resolved_occurrences
    )
    issues.extend(documentation_issues)
    installed_by_identity, installation_issues = index_installed_projects(installed)
    issues.extend(installation_issues)

    empty_snapshot = DependencySnapshot(required_project_ids_by_version={})
    dependency_snapshot = empty_snapshot
    try:
        dependency_snapshot = parse_dependency_snapshot(
            read_json(DEPENDENCY_SNAPSHOT_PATH)
        )
    except (OSError, ValueError) as error:
        issues.append(
            InventoryIssue(
                section="Dependencies",
                code="invalid_dependency_snapshot",
                message=str(error),
            )
        )

    installations = modrinth_installations(installed)
    coverage_issues = validate_snapshot_coverage(installations, dependency_snapshot)
    issues.extend(dependency_issue_to_inventory(issue) for issue in coverage_issues)
    root_project_ids = {
        occurrence.project_id
        for occurrence in defaults.values()
        if occurrence.provider == "modrinth" and occurrence.project_id
    }
    dependency_analysis = analyze_required_dependencies(
        root_project_ids,
        installations,
        dependency_snapshot,
    )
    issues.extend(
        dependency_issue_to_inventory(issue)
        for issue in dependency_analysis.issues
    )
    dependency_identities = {
        project_identity("modrinth", project_id)
        for project_id in dependency_analysis.dependency_project_ids
    }

    optional_required_identities = dependency_identities & set(optional)
    for identity in sorted(optional_required_identities):
        issues.append(
            InventoryIssue(
                section="Dependencies",
                code="required_project_marked_optional",
                message=f"{identity} is optional but required by a default project.",
                identity=identity,
            )
        )

    expected_installed_identities = set(defaults) | dependency_identities
    installed_identities = set(installed_by_identity)
    for identity in sorted(expected_installed_identities - installed_identities):
        issues.append(
            InventoryIssue(
                section="Installation",
                code="missing_installed_project",
                message=f"Expected project {identity} is not installed by packwiz.",
                identity=identity,
            )
        )
    unexplained_identities = installed_identities - expected_installed_identities
    for identity in sorted(unexplained_identities):
        project = installed_by_identity[identity]
        issues.append(
            InventoryIssue(
                section="Installation",
                code="unexplained_installed_project",
                message=f"{project.name} ({project.file}) is installed without an explanation.",
                identity=identity,
            )
        )

    for identity in sorted(set(optional) & installed_identities):
        project = installed_by_identity[identity]
        issues.append(
            InventoryIssue(
                section="Installation",
                code="optional_project_installed",
                message=f"Optional project {identity} is installed as {project.file}.",
                identity=identity,
            )
        )

    for identity, occurrence in defaults.items():
        installed_project = installed_by_identity.get(identity)
        if (
            installed_project
            and installed_project.resource_type != occurrence.resource_type
        ):
            issues.append(
                InventoryIssue(
                    section="Installation",
                    code="resource_type_mismatch",
                    message=(
                        f"{identity} is documented as {occurrence.resource_type} but "
                        f"installed as {installed_project.resource_type} in "
                        f"{installed_project.file}."
                    ),
                    identity=identity,
                )
            )

    for identity, occurrence in defaults.items():
        if occurrence.provider == "curseforge" and occurrence.resource_type == "mod":
            project = metadata.get(identity)
            issues.append(
                InventoryIssue(
                    section="Dependencies",
                    code="curseforge_dependency_unverified",
                    message=(
                        f"{project.name if project else identity} uses CurseForge; its "
                        "dependency closure is not automatically verified."
                    ),
                    severity="warning",
                    identity=identity,
                )
            )

    return Inventory(
        target_version=target_minecraft_version(),
        categories=categories,
        groups=groups,
        metadata=metadata,
        occurrences=resolved_occurrences,
        installed=installed,
        dependency_snapshot=dependency_snapshot,
        dependency_analysis=dependency_analysis,
        defaults=defaults,
        optional=optional,
        installed_by_identity=installed_by_identity,
        dependency_identities=dependency_identities,
        unexplained_identities=unexplained_identities,
        issues=list(dict.fromkeys(issues)),
    )


def identity_resource_type(inventory: Inventory, identity: str, status: str) -> str:
    if status == "default":
        occurrence = inventory.defaults.get(identity)
        return occurrence.resource_type if occurrence else ""
    if status == "optional":
        occurrence = inventory.optional.get(identity)
        return occurrence.resource_type if occurrence else ""
    installed = inventory.installed_by_identity.get(identity)
    return installed.resource_type if installed else ""


def identities_for_status(inventory: Inventory, status: str) -> set[str]:
    if status == "default":
        return set(inventory.defaults)
    if status == "optional":
        return set(inventory.optional)
    if status == "dependency":
        return set(inventory.dependency_identities)
    if status == "installed":
        return set(inventory.installed_by_identity)
    if status == "unexplained":
        return set(inventory.unexplained_identities)
    raise ValueError(f"Unsupported inventory status: {status}")


def resource_status_counts(inventory: Inventory) -> dict[str, dict[str, dict[str, int]]]:
    """Count unique projects by resource type, provider, and semantic status."""
    counts = {
        resource_type: {
            provider: {status: 0 for status in STATUS_NAMES}
            for provider in PROVIDERS
        }
        for resource_type in RESOURCE_TYPES
    }

    for status in STATUS_NAMES:
        for identity in identities_for_status(inventory, status):
            provider = identity.partition(":")[0]
            resource_type = identity_resource_type(inventory, identity, status)
            if resource_type not in counts or provider not in PROVIDERS:
                continue
            counts[resource_type][provider][status] += 1
    return counts


def required_by_names(inventory: Inventory, identity: str) -> list[str]:
    """Return human names for direct dependency parents without persisting them."""
    provider, _, project_id = identity.partition(":")
    if provider != "modrinth" or not project_id:
        return []
    parent_ids = required_by_project(inventory.dependency_analysis).get(
        project_id,
        frozenset(),
    )
    names: list[str] = []
    for parent_id in sorted(parent_ids):
        parent_identity = project_identity("modrinth", parent_id)
        metadata = inventory.metadata.get(parent_identity)
        installed = inventory.installed_by_identity.get(parent_identity)
        names.append(metadata.name if metadata else installed.name if installed else parent_id)
    return names


def source_path(group: dict[str, Any]) -> Path:
    return Path(group["_source_path"])
