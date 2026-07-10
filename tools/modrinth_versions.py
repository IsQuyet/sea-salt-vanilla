"""Independent local Modrinth version pool and API refresh."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterable

from dependencies import ModrinthInstallation, index_installations


VERSION_POOL_SCHEMA_VERSION = 1
MODRINTH_VERSIONS_API = "https://api.modrinth.com/v2/versions"
USER_AGENT = "SeaSaltVanillaMaintainer/1.0"


@dataclass
class ModrinthVersionPool:
    """Local provider facts and fetch errors keyed by version ID."""

    versions: dict[str, ModrinthVersionFacts] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ModrinthVersionFacts:
    """Provider facts for one concrete Modrinth version."""

    project_id: str
    required_project_ids: frozenset[str]
    loaders: frozenset[str]


@dataclass(frozen=True)
class VersionRefreshOutcome:
    """One version and the result of this refresh invocation."""

    version_id: str
    status: str
    project_id: str = ""
    message: str = ""


class ModrinthVersionError(RuntimeError):
    """Raised when Modrinth version metadata is malformed or unavailable."""


def parse_nonempty_strings(values: Any, *, label: str) -> frozenset[str]:
    if not isinstance(values, list):
        raise ModrinthVersionError(f"{label} must be a list.")

    normalized_values: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ModrinthVersionError(f"{label} contains an invalid value.")
        normalized_values.append(value.strip())
    if len(normalized_values) != len(set(normalized_values)):
        raise ModrinthVersionError(f"{label} contains duplicate values.")
    return frozenset(normalized_values)


def parse_required_project_ids(raw_dependencies: Any, *, version_id: str) -> frozenset[str]:
    if not isinstance(raw_dependencies, list):
        raise ModrinthVersionError(
            f"Modrinth version {version_id} dependencies must be a list."
        )

    required_project_ids: set[str] = set()
    for dependency in raw_dependencies:
        if not isinstance(dependency, dict):
            raise ModrinthVersionError(
                f"Modrinth version {version_id} contains a malformed dependency."
            )
        relationship = str(dependency.get("dependency_type") or "")
        if relationship != "required":
            continue
        project_id = str(dependency.get("project_id") or "")
        if not project_id:
            dependency_version_id = str(dependency.get("version_id") or "")
            detail = (
                f" version {dependency_version_id}" if dependency_version_id else ""
            )
            raise ModrinthVersionError(
                f"Required dependency{detail} of Modrinth version {version_id} has no "
                "project ID. Resolve the provider metadata before dependency analysis."
            )
        required_project_ids.add(project_id)
    return frozenset(required_project_ids)


def version_facts_from_api(raw_version: Any) -> tuple[str, ModrinthVersionFacts]:
    if not isinstance(raw_version, dict):
        raise ModrinthVersionError("Modrinth returned a malformed version response.")
    version_id = str(raw_version.get("id") or "")
    project_id = str(raw_version.get("project_id") or "")
    raw_loaders = raw_version.get("loaders")
    if not version_id or not project_id or not isinstance(raw_loaders, list):
        raise ModrinthVersionError("Modrinth returned incomplete version metadata.")
    return (
        version_id,
        ModrinthVersionFacts(
            project_id=project_id,
            loaders=frozenset(
                loader.lower()
                for loader in parse_nonempty_strings(
                    raw_loaders,
                    label=f"Modrinth version {version_id} loaders",
                )
            ),
            required_project_ids=parse_required_project_ids(
                raw_version.get("dependencies", []),
                version_id=version_id,
            ),
        ),
    )


def parse_version_pool(raw_data: Any) -> ModrinthVersionPool:
    """Strictly parse the schema-wrapped local version pool."""
    if not isinstance(raw_data, dict) or set(raw_data) != {
        "schema_version",
        "versions",
        "errors",
    }:
        raise ModrinthVersionError(
            "Modrinth version pool must contain schema_version, versions, and errors."
        )
    if raw_data.get("schema_version") != VERSION_POOL_SCHEMA_VERSION:
        raise ModrinthVersionError("Modrinth version pool uses an unsupported schema.")
    raw_versions = raw_data.get("versions")
    raw_errors = raw_data.get("errors")
    if not isinstance(raw_versions, dict) or not isinstance(raw_errors, dict):
        raise ModrinthVersionError(
            "Modrinth version pool versions and errors must be objects."
        )

    pool = ModrinthVersionPool()
    for raw_version_id, raw_version in raw_versions.items():
        version_id = str(raw_version_id or "")
        if not version_id or not isinstance(raw_version, dict) or set(raw_version) != {
            "project_id",
            "loaders",
            "required_project_ids",
        }:
            raise ModrinthVersionError(
                f"Modrinth version pool entry {raw_version_id!r} has an invalid shape."
            )
        project_id = str(raw_version.get("project_id") or "")
        if not project_id:
            raise ModrinthVersionError(
                f"Modrinth version pool entry {version_id} contains invalid values."
            )
        loaders = parse_nonempty_strings(
            raw_version.get("loaders"),
            label=f"Modrinth version {version_id} loaders",
        )
        required_project_ids = parse_nonempty_strings(
            raw_version.get("required_project_ids"),
            label=f"Modrinth version {version_id} required project IDs",
        )
        pool.versions[version_id] = ModrinthVersionFacts(
            project_id=project_id,
            loaders=frozenset(loader.lower() for loader in loaders),
            required_project_ids=required_project_ids,
        )

    for raw_version_id, raw_message in raw_errors.items():
        version_id = str(raw_version_id or "")
        message = str(raw_message or "")
        if not version_id or not message:
            raise ModrinthVersionError("Modrinth version pool contains an invalid error.")
        pool.errors[version_id] = message
    return pool


def version_pool_data(pool: ModrinthVersionPool) -> dict[str, Any]:
    """Return deterministic JSON-compatible local version data."""
    return {
        "schema_version": VERSION_POOL_SCHEMA_VERSION,
        "versions": {
            version_id: {
                "project_id": facts.project_id,
                "loaders": sorted(facts.loaders),
                "required_project_ids": sorted(facts.required_project_ids),
            }
            for version_id, facts in sorted(pool.versions.items())
        },
        "errors": dict(sorted(pool.errors.items())),
    }


def modrinth_versions_request(version_ids: list[str]) -> urllib.request.Request:
    query = urllib.parse.urlencode({"ids": json.dumps(version_ids)})
    return urllib.request.Request(
        f"{MODRINTH_VERSIONS_API}?{query}",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )


def fetch_version_batch(version_ids: list[str]) -> dict[str, ModrinthVersionFacts]:
    try:
        with urllib.request.urlopen(
            modrinth_versions_request(version_ids),
            timeout=30,
        ) as response:
            raw_versions = json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as error:
        raise ModrinthVersionError(str(error)) from error
    if not isinstance(raw_versions, list):
        raise ModrinthVersionError("Modrinth returned a malformed versions response.")

    fetched_versions: dict[str, ModrinthVersionFacts] = {}
    for raw_version in raw_versions:
        version_id, version_facts = version_facts_from_api(raw_version)
        fetched_versions[version_id] = version_facts
    return fetched_versions


def refresh_version_pool(
    installations: Iterable[ModrinthInstallation],
    pool: ModrinthVersionPool,
    *,
    force: bool,
    dry_run: bool,
) -> tuple[ModrinthVersionPool, list[VersionRefreshOutcome]]:
    """Refresh installed version facts and prune versions outside packwiz."""
    _, required_versions, installation_issues = index_installations(installations)
    if installation_issues:
        raise ModrinthVersionError(
            "\n".join(issue.message for issue in installation_issues)
        )
    refreshed_pool = ModrinthVersionPool(
        versions=dict(pool.versions),
        errors=dict(pool.errors),
    )
    outcomes: list[VersionRefreshOutcome] = []
    version_ids_to_fetch = [
        version_id
        for version_id in sorted(required_versions)
        if force or version_id not in refreshed_pool.versions
    ]

    for version_id in sorted(set(refreshed_pool.versions) - set(required_versions)):
        outcomes.append(
            VersionRefreshOutcome(
                version_id=version_id,
                status="would_prune" if dry_run else "pruned",
                project_id=refreshed_pool.versions[version_id].project_id,
            )
        )
        if not dry_run:
            refreshed_pool.versions.pop(version_id, None)
            refreshed_pool.errors.pop(version_id, None)

    if not dry_run:
        for version_id in set(refreshed_pool.errors) - set(required_versions):
            refreshed_pool.errors.pop(version_id, None)

    for version_id in sorted(set(required_versions) - set(version_ids_to_fetch)):
        outcomes.append(
            VersionRefreshOutcome(
                version_id=version_id,
                status="cached",
                project_id=required_versions[version_id].project_id,
            )
        )

    if dry_run:
        outcomes.extend(
            VersionRefreshOutcome(
                version_id=version_id,
                status="would_fetch",
                project_id=required_versions[version_id].project_id,
            )
            for version_id in version_ids_to_fetch
        )
        return refreshed_pool, outcomes

    for batch_start in range(0, len(version_ids_to_fetch), 50):
        batch = version_ids_to_fetch[batch_start : batch_start + 50]
        try:
            fetched_versions = fetch_version_batch(batch)
        except ModrinthVersionError as error:
            for version_id in batch:
                refreshed_pool.errors[version_id] = str(error)
                outcomes.append(
                    VersionRefreshOutcome(
                        version_id=version_id,
                        status="failed",
                        project_id=required_versions[version_id].project_id,
                        message=str(error),
                    )
                )
            continue

        for version_id in batch:
            version_facts = fetched_versions.get(version_id)
            if not version_facts:
                failure_message = "Version was not returned by the Modrinth API."
                refreshed_pool.errors[version_id] = failure_message
                outcomes.append(
                    VersionRefreshOutcome(
                        version_id=version_id,
                        status="failed",
                        project_id=required_versions[version_id].project_id,
                        message=failure_message,
                    )
                )
                continue
            previous_facts = refreshed_pool.versions.get(version_id)
            refreshed_pool.versions[version_id] = version_facts
            refreshed_pool.errors.pop(version_id, None)
            outcomes.append(
                VersionRefreshOutcome(
                    version_id=version_id,
                    status="updated" if previous_facts else "fetched",
                    project_id=version_facts.project_id,
                )
            )

    return refreshed_pool, outcomes
