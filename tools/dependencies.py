"""Pure Modrinth required-dependency analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol


DEPENDENCY_SNAPSHOT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ModrinthInstallation:
    """One project/version lock declared by packwiz."""

    project_id: str
    version_id: str
    origin: str = ""


class DependencyVersionFacts(Protocol):
    """Minimal version facts required by dependency validation."""

    project_id: str
    required_project_ids: frozenset[str]


@dataclass(frozen=True)
class DependencySnapshot:
    """Tracked required edges keyed by concrete Modrinth version ID."""

    required_project_ids_by_version: Mapping[str, frozenset[str]]


@dataclass(frozen=True)
class DependencyIssue:
    """One structured dependency validation problem."""

    code: str
    message: str
    project_id: str = ""
    version_id: str = ""
    related_project_id: str = ""


@dataclass
class DependencyAnalysis:
    """Required closure and forward edges reachable from explicit roots."""

    root_project_ids: frozenset[str]
    reachable_project_ids: set[str] = field(default_factory=set)
    dependency_project_ids: set[str] = field(default_factory=set)
    required_project_ids_by_project: dict[str, frozenset[str]] = field(
        default_factory=dict
    )
    issues: list[DependencyIssue] = field(default_factory=list)


class DependencySnapshotFormatError(ValueError):
    """Raised when tracked dependency snapshot data is malformed."""


def normalize_nonempty_string(value: Any, *, label: str) -> str:
    normalized_value = str(value or "")
    if not normalized_value:
        raise DependencySnapshotFormatError(f"{label} must be a non-empty string.")
    return normalized_value


def normalize_project_ids(values: Any, *, version_id: str) -> frozenset[str]:
    if not isinstance(values, list):
        raise DependencySnapshotFormatError(
            f"Dependency snapshot version {version_id} must contain a project ID list."
        )

    normalized_values: set[str] = set()
    for project_id in values:
        if not isinstance(project_id, str) or not project_id:
            raise DependencySnapshotFormatError(
                f"Dependency snapshot version {version_id} contains an invalid project ID."
            )
        normalized_values.add(project_id)
    return frozenset(normalized_values)


def parse_dependency_snapshot(raw_data: Any) -> DependencySnapshot:
    """Strictly parse the tracked offline dependency snapshot."""
    if not isinstance(raw_data, dict) or set(raw_data) != {
        "schema_version",
        "versions",
    }:
        raise DependencySnapshotFormatError(
            "Dependency snapshot must contain exactly schema_version and versions."
        )
    if raw_data.get("schema_version") != DEPENDENCY_SNAPSHOT_SCHEMA_VERSION:
        raise DependencySnapshotFormatError(
            "Dependency snapshot uses an unsupported schema version."
        )

    raw_versions = raw_data.get("versions")
    if not isinstance(raw_versions, dict):
        raise DependencySnapshotFormatError(
            "Dependency snapshot versions must be an object."
        )

    normalized_versions: dict[str, frozenset[str]] = {}
    for raw_version_id, raw_project_ids in raw_versions.items():
        version_id = normalize_nonempty_string(
            raw_version_id,
            label="Dependency snapshot version ID",
        )
        normalized_versions[version_id] = normalize_project_ids(
            raw_project_ids,
            version_id=version_id,
        )
    return DependencySnapshot(required_project_ids_by_version=normalized_versions)


def dependency_snapshot_data(snapshot: DependencySnapshot) -> dict[str, Any]:
    """Return deterministic JSON-compatible dependency snapshot data."""
    return {
        "schema_version": DEPENDENCY_SNAPSHOT_SCHEMA_VERSION,
        "versions": {
            version_id: sorted(project_ids)
            for version_id, project_ids in sorted(
                snapshot.required_project_ids_by_version.items()
            )
        },
    }


def index_installations(
    installations: Iterable[ModrinthInstallation],
) -> tuple[dict[str, ModrinthInstallation], dict[str, ModrinthInstallation], list[DependencyIssue]]:
    """Index installations by project and version while reporting conflicts."""
    installations_by_project: dict[str, ModrinthInstallation] = {}
    installations_by_version: dict[str, ModrinthInstallation] = {}
    issues: list[DependencyIssue] = []

    for installation in installations:
        if not installation.project_id or not installation.version_id:
            issues.append(
                DependencyIssue(
                    code="incomplete_installation",
                    message=(
                        f"{installation.origin or '<unknown-packwiz-file>'} has no complete "
                        "Modrinth project/version lock."
                    ),
                    project_id=installation.project_id,
                    version_id=installation.version_id,
                )
            )
            continue

        previous_project_installation = installations_by_project.get(
            installation.project_id
        )
        if previous_project_installation:
            issues.append(
                DependencyIssue(
                    code="duplicate_project_installation",
                    message=(
                        f"Modrinth project {installation.project_id} is installed by both "
                        f"{previous_project_installation.origin} and {installation.origin}."
                    ),
                    project_id=installation.project_id,
                    version_id=installation.version_id,
                )
            )
        else:
            installations_by_project[installation.project_id] = installation

        previous_version_installation = installations_by_version.get(
            installation.version_id
        )
        if (
            previous_version_installation
            and previous_version_installation.project_id != installation.project_id
        ):
            issues.append(
                DependencyIssue(
                    code="duplicate_version_installation",
                    message=(
                        f"Modrinth version {installation.version_id} is assigned to both "
                        f"{previous_version_installation.project_id} and "
                        f"{installation.project_id}."
                    ),
                    project_id=installation.project_id,
                    version_id=installation.version_id,
                    related_project_id=previous_version_installation.project_id,
                )
            )
        else:
            installations_by_version[installation.version_id] = installation

    return installations_by_project, installations_by_version, issues


def validate_snapshot_coverage(
    installations: Iterable[ModrinthInstallation],
    snapshot: DependencySnapshot,
) -> list[DependencyIssue]:
    """Verify exact version coverage between packwiz and the tracked snapshot."""
    _, installations_by_version, issues = index_installations(installations)
    installed_version_ids = set(installations_by_version)
    snapshot_version_ids = set(snapshot.required_project_ids_by_version)

    for version_id in sorted(installed_version_ids - snapshot_version_ids):
        installation = installations_by_version[version_id]
        issues.append(
            DependencyIssue(
                code="missing_snapshot_version",
                message=(
                    f"Dependency snapshot is missing installed Modrinth version {version_id} "
                    f"for project {installation.project_id}."
                ),
                project_id=installation.project_id,
                version_id=version_id,
            )
        )
    for version_id in sorted(snapshot_version_ids - installed_version_ids):
        issues.append(
            DependencyIssue(
                code="stale_snapshot_version",
                message=f"Dependency snapshot contains stale Modrinth version {version_id}.",
                version_id=version_id,
            )
        )
    return issues


def build_dependency_snapshot(
    installations: Iterable[ModrinthInstallation],
    version_facts_by_id: Mapping[str, DependencyVersionFacts],
) -> tuple[DependencySnapshot, list[DependencyIssue]]:
    """Project validated local version facts into the tracked snapshot."""
    _, installations_by_version, issues = index_installations(installations)
    required_project_ids_by_version: dict[str, frozenset[str]] = {}

    for version_id, installation in sorted(installations_by_version.items()):
        version_facts = version_facts_by_id.get(version_id)
        if not version_facts:
            issues.append(
                DependencyIssue(
                    code="missing_version_facts",
                    message=(
                        f"Local Modrinth version pool is missing {version_id} for project "
                        f"{installation.project_id}."
                    ),
                    project_id=installation.project_id,
                    version_id=version_id,
                )
            )
            continue
        if version_facts.project_id != installation.project_id:
            issues.append(
                DependencyIssue(
                    code="version_owner_mismatch",
                    message=(
                        f"Modrinth version {version_id} belongs to "
                        f"{version_facts.project_id}, not installed project "
                        f"{installation.project_id}."
                    ),
                    project_id=installation.project_id,
                    version_id=version_id,
                    related_project_id=version_facts.project_id,
                )
            )
            continue
        required_project_ids_by_version[version_id] = (
            version_facts.required_project_ids
        )

    return (
        DependencySnapshot(
            required_project_ids_by_version=required_project_ids_by_version
        ),
        issues,
    )


def validate_snapshot_against_version_facts(
    installations: Iterable[ModrinthInstallation],
    snapshot: DependencySnapshot,
    version_facts_by_id: Mapping[str, DependencyVersionFacts],
) -> list[DependencyIssue]:
    """Compare tracked edges and ownership with the local provider version pool."""
    _, installations_by_version, issues = index_installations(installations)

    for version_id, installation in sorted(installations_by_version.items()):
        version_facts = version_facts_by_id.get(version_id)
        if not version_facts:
            issues.append(
                DependencyIssue(
                    code="missing_version_facts",
                    message=f"Local Modrinth version pool is missing {version_id}.",
                    project_id=installation.project_id,
                    version_id=version_id,
                )
            )
            continue
        if version_facts.project_id != installation.project_id:
            issues.append(
                DependencyIssue(
                    code="version_owner_mismatch",
                    message=(
                        f"Modrinth version {version_id} belongs to "
                        f"{version_facts.project_id}, not installed project "
                        f"{installation.project_id}."
                    ),
                    project_id=installation.project_id,
                    version_id=version_id,
                    related_project_id=version_facts.project_id,
                )
            )

        tracked_project_ids = snapshot.required_project_ids_by_version.get(version_id)
        if tracked_project_ids is None:
            continue
        missing_tracked_edges = version_facts.required_project_ids - tracked_project_ids
        stale_tracked_edges = tracked_project_ids - version_facts.required_project_ids
        for dependency_project_id in sorted(missing_tracked_edges):
            issues.append(
                DependencyIssue(
                    code="missing_snapshot_edge",
                    message=(
                        f"Dependency snapshot version {version_id} is missing required "
                        f"project {dependency_project_id}."
                    ),
                    project_id=installation.project_id,
                    version_id=version_id,
                    related_project_id=dependency_project_id,
                )
            )
        for dependency_project_id in sorted(stale_tracked_edges):
            issues.append(
                DependencyIssue(
                    code="stale_snapshot_edge",
                    message=(
                        f"Dependency snapshot version {version_id} contains stale required "
                        f"project {dependency_project_id}."
                    ),
                    project_id=installation.project_id,
                    version_id=version_id,
                    related_project_id=dependency_project_id,
                )
            )
    return issues


def analyze_required_dependencies(
    root_project_ids: Iterable[str],
    installations: Iterable[ModrinthInstallation],
    snapshot: DependencySnapshot,
) -> DependencyAnalysis:
    """Resolve the installed required closure of explicit Modrinth roots."""
    normalized_root_project_ids = frozenset(
        project_id for project_id in root_project_ids if project_id
    )
    analysis = DependencyAnalysis(root_project_ids=normalized_root_project_ids)
    installations_by_project, _, installation_issues = index_installations(
        installations
    )
    analysis.issues.extend(installation_issues)

    pending_project_ids = list(sorted(normalized_root_project_ids))
    visited_project_ids: set[str] = set()

    while pending_project_ids:
        project_id = pending_project_ids.pop(0)
        if project_id in visited_project_ids:
            continue
        visited_project_ids.add(project_id)

        installation = installations_by_project.get(project_id)
        if not installation:
            analysis.issues.append(
                DependencyIssue(
                    code="missing_required_installation",
                    message=(
                        f"Required Modrinth project {project_id} is not installed with a "
                        "packwiz version lock."
                    ),
                    project_id=project_id,
                )
            )
            continue

        required_project_ids = snapshot.required_project_ids_by_version.get(
            installation.version_id
        )
        if required_project_ids is None:
            analysis.issues.append(
                DependencyIssue(
                    code="missing_snapshot_version",
                    message=(
                        f"Installed Modrinth project {project_id} has no dependency snapshot "
                        f"entry for version {installation.version_id}."
                    ),
                    project_id=project_id,
                    version_id=installation.version_id,
                )
            )
            continue

        analysis.reachable_project_ids.add(project_id)
        analysis.required_project_ids_by_project[project_id] = required_project_ids

        for dependency_project_id in sorted(required_project_ids):
            if dependency_project_id not in installations_by_project:
                analysis.issues.append(
                    DependencyIssue(
                        code="missing_required_installation",
                        message=(
                            f"Required Modrinth dependency {dependency_project_id} of "
                            f"{project_id} is not installed."
                        ),
                        project_id=project_id,
                        version_id=installation.version_id,
                        related_project_id=dependency_project_id,
                    )
                )
                continue
            if dependency_project_id not in visited_project_ids:
                pending_project_ids.append(dependency_project_id)

    analysis.dependency_project_ids = (
        analysis.reachable_project_ids - normalized_root_project_ids
    )
    return analysis


def required_by_project(
    analysis: DependencyAnalysis,
) -> dict[str, frozenset[str]]:
    """Invert the reachable forward graph for diagnostics only."""
    parent_project_ids_by_dependency: dict[str, set[str]] = {}
    for parent_project_id, dependency_project_ids in (
        analysis.required_project_ids_by_project.items()
    ):
        for dependency_project_id in dependency_project_ids:
            parent_project_ids_by_dependency.setdefault(
                dependency_project_id,
                set(),
            ).add(parent_project_id)
    return {
        project_id: frozenset(parent_project_ids)
        for project_id, parent_project_ids in parent_project_ids_by_dependency.items()
    }
