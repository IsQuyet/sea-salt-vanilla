#!/usr/bin/env python3
"""Maintain project metadata, documentation, dependencies, and packwiz state."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
from collections import Counter
from typing import Any, Iterable

from dependencies import (
    DependencyIssue,
    build_dependency_snapshot,
    dependency_snapshot_data,
    validate_snapshot_against_version_facts,
)
from documents import document_freshness_issues, generate_documents
from inventory import (
    HEALTH_SECTIONS,
    PROVIDERS,
    STATUS_NAMES,
    Inventory,
    InventoryIssue,
    build_inventory,
    documentation_lookups,
    installed_lookups,
    load_documentation_sources,
    modrinth_installations,
    resource_status_counts,
)
from modrinth_versions import (
    ModrinthVersionError,
    ModrinthVersionPool,
    VersionRefreshOutcome,
    parse_version_pool,
    refresh_version_pool,
    version_pool_data,
)
from packwiz import (
    DEPENDENCY_SNAPSHOT_PATH,
    MODRINTH_VERSION_POOL_PATH,
    PROJECT_METADATA_PATH,
    RESOURCE_TYPE_DISPLAY_NAMES,
    RESOURCE_TYPES,
    ROOT,
    json_text,
    load_installed_projects,
    normalize_line_endings,
    pack_name,
    pack_version,
    read_json,
    refresh_index,
    write_json_if_changed,
)
from project_metadata import (
    ProjectMetadata,
    ProjectMetadataError,
    ProjectRefreshOutcome,
    SUPPORTED_PROVIDERS,
    parse_project_metadata_pool,
    project_metadata_pool_data,
    refresh_project_metadata,
)


def load_project_metadata_or_empty() -> dict[str, ProjectMetadata]:
    if not PROJECT_METADATA_PATH.exists():
        return {}
    return parse_project_metadata_pool(read_json(PROJECT_METADATA_PATH))


def load_version_pool_or_empty() -> ModrinthVersionPool:
    if not MODRINTH_VERSION_POOL_PATH.exists():
        return ModrinthVersionPool()
    return parse_version_pool(read_json(MODRINTH_VERSION_POOL_PATH))


def dependency_issues_as_inventory(
    issues: Iterable[DependencyIssue],
) -> list[InventoryIssue]:
    return [
        InventoryIssue(
            section="Dependencies",
            code=issue.code,
            message=issue.message,
        )
        for issue in issues
    ]


def deep_check_issues(inventory: Inventory) -> list[InventoryIssue]:
    issues: list[InventoryIssue] = []
    try:
        version_pool = load_version_pool_or_empty()
    except (OSError, ValueError, ModrinthVersionError) as error:
        return [
            InventoryIssue(
                section="Dependencies",
                code="invalid_modrinth_version_pool",
                message=str(error),
            )
        ]

    installations = modrinth_installations(inventory.installed)
    issues.extend(
        dependency_issues_as_inventory(
            validate_snapshot_against_version_facts(
                installations,
                inventory.dependency_snapshot,
                version_pool.versions,
            )
        )
    )

    required_version_ids = {
        installation.version_id for installation in installations if installation.version_id
    }
    for version_id in sorted(required_version_ids & set(version_pool.errors)):
        issues.append(
            InventoryIssue(
                section="Dependencies",
                code="modrinth_version_error",
                message=f"Modrinth version {version_id}: {version_pool.errors[version_id]}",
            )
        )

    for project in inventory.installed:
        if project.provider != "modrinth" or project.resource_type != "datapack":
            continue
        facts = version_pool.versions.get(project.version_id)
        if facts and "datapack" not in facts.loaders:
            loaders = ", ".join(sorted(facts.loaders)) or "none"
            issues.append(
                InventoryIssue(
                    section="Installation",
                    code="datapack_loader_mismatch",
                    message=(
                        f"{project.file} is installed as a datapack, but Modrinth version "
                        f"{project.version_id} loaders are [{loaders}]."
                    ),
                    identity=project.identity,
                )
            )
    return issues


def complete_check_issues(
    inventory: Inventory,
    *,
    deep: bool,
) -> list[InventoryIssue]:
    issues = list(inventory.issues)
    issues.extend(document_freshness_issues(inventory))
    if deep:
        issues.extend(deep_check_issues(inventory))
    for path in normalize_line_endings(check=True):
        issues.append(
            InventoryIssue(
                section="Packwiz",
                code="line_endings_need_normalization",
                message=f"{path.as_posix()} must use LF line endings.",
            )
        )
    return list(dict.fromkeys(issues))


def total_counts(
    counts: dict[str, dict[str, dict[str, int]]],
) -> dict[str, dict[str, int]]:
    totals = {
        provider: {status: 0 for status in STATUS_NAMES}
        for provider in PROVIDERS
    }
    for resource_type in RESOURCE_TYPES:
        for provider in PROVIDERS:
            for status in STATUS_NAMES:
                totals[provider][status] += counts[resource_type][provider][status]
    return totals


def provider_total(
    provider_counts: dict[str, dict[str, int]],
) -> dict[str, int]:
    return {
        status: sum(provider_counts[provider][status] for provider in PROVIDERS)
        for status in STATUS_NAMES
    }


def health_data(issues: list[InventoryIssue]) -> dict[str, Any]:
    sections: dict[str, Any] = {}
    for section in HEALTH_SECTIONS:
        section_issues = [issue for issue in issues if issue.section == section]
        errors = [issue for issue in section_issues if issue.severity == "error"]
        warnings = [issue for issue in section_issues if issue.severity == "warning"]
        sections[section.lower()] = {
            "result": "fail" if errors else "warning" if warnings else "pass",
            "errors": [
                {"code": issue.code, "message": issue.message}
                for issue in errors
            ],
            "warnings": [
                {"code": issue.code, "message": issue.message}
                for issue in warnings
            ],
        }
    return sections


def status_data(
    inventory: Inventory,
    *,
    issues: list[InventoryIssue] | None = None,
) -> dict[str, Any]:
    effective_issues = list(inventory.issues if issues is None else issues)
    counts = resource_status_counts(inventory)
    resources: list[dict[str, Any]] = []

    for resource_type in RESOURCE_TYPES:
        provider_counts = counts[resource_type]
        resources.append(
            {
                "type": resource_type,
                "providers": provider_counts,
                "total": provider_total(provider_counts),
            }
        )

    errors = [issue for issue in effective_issues if issue.severity == "error"]
    warnings = [issue for issue in effective_issues if issue.severity == "warning"]
    return {
        "schema_version": 1,
        "pack": {
            "name": pack_name(),
            "version": pack_version(),
            "minecraft": inventory.target_version,
        },
        "result": "fail" if errors else "warning" if warnings else "pass",
        "resources": resources,
        "all_resources": {
            "providers": total_counts(counts),
            "total": provider_total(total_counts(counts)),
        },
        "health": health_data(effective_issues),
        "notes": [
            "Installed overlaps Default and Dependency; columns are not additive.",
            "Counts are unique canonical projects within each resource/provider bucket.",
        ],
    }


def format_count_table(
    provider_counts: dict[str, dict[str, int]],
) -> list[str]:
    headers = ["Provider", "Default", "Optional", "Dependency", "Installed", "Unexplained"]
    rows: list[list[str]] = []
    for provider in PROVIDERS:
        counts = provider_counts[provider]
        rows.append(
            [
                provider.capitalize(),
                *(str(counts[status]) for status in STATUS_NAMES),
            ]
        )
    total = provider_total(provider_counts)
    rows.append(["Total", *(str(total[status]) for status in STATUS_NAMES)])

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    lines = [
        "  ".join(
            header.ljust(widths[index]) if index == 0 else header.rjust(widths[index])
            for index, header in enumerate(headers)
        )
    ]
    for row in rows:
        lines.append(
            "  ".join(
                value.ljust(widths[index]) if index == 0 else value.rjust(widths[index])
                for index, value in enumerate(row)
            )
        )
    return lines


def print_status(data: dict[str, Any]) -> None:
    pack = data["pack"]
    print(f"{pack['name']} {pack['version']} · Minecraft {pack['minecraft']}")
    print(f"Status: {str(data['result']).upper()}")

    for resource in data["resources"]:
        print()
        print(RESOURCE_TYPE_DISPLAY_NAMES[resource["type"]])
        for line in format_count_table(resource["providers"]):
            print(line)

    print()
    print("All resource types")
    for line in format_count_table(data["all_resources"]["providers"]):
        print(line)

    print()
    print("Health")
    for section in HEALTH_SECTIONS:
        section_data = data["health"][section.lower()]
        error_count = len(section_data["errors"])
        warning_count = len(section_data["warnings"])
        detail = ""
        if error_count or warning_count:
            detail = f" ({error_count} errors, {warning_count} warnings)"
        print(f"  {section:<16} {section_data['result'].upper()}{detail}")

    details = [
        (section, issue_type, issue)
        for section, section_data in data["health"].items()
        for issue_type in ("errors", "warnings")
        for issue in section_data[issue_type]
    ]
    if details:
        print()
        print("Details")
        for section, issue_type, issue in details:
            label = "ERROR" if issue_type == "errors" else "WARNING"
            print(f"  [{label}] {section.capitalize()}: {issue['message']}")

    print()
    for note in data["notes"]:
        print(f"Note: {note}")


def output_data(data: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_status(data)


def project_refresh_data(
    outcomes: list[ProjectRefreshOutcome],
) -> dict[str, Any]:
    buckets = {
        resource_type: {
            provider: Counter()
            for provider in PROVIDERS
        }
        for resource_type in RESOURCE_TYPES
    }
    pruned_by_provider = Counter()
    failures: list[dict[str, str]] = []

    for outcome in outcomes:
        resource_type = outcome.lookup.resource_type
        provider = outcome.lookup.provider
        if outcome.status == "pruned":
            pruned_by_provider[provider] += 1
            continue
        if resource_type in buckets and provider in PROVIDERS:
            buckets[resource_type][provider]["required"] += 1
            if outcome.status in {"cached", "updated", "normalized"}:
                buckets[resource_type][provider]["cached_before"] += 1
            if outcome.status == "fetched":
                buckets[resource_type][provider]["fetched"] += 1
            if outcome.status in {"updated", "normalized"}:
                buckets[resource_type][provider]["updated"] += 1
            if outcome.status == "would_fetch":
                buckets[resource_type][provider]["would_fetch"] += 1
            if outcome.status == "failed":
                buckets[resource_type][provider]["failed"] += 1
        if outcome.status == "failed":
            failures.append(
                {
                    "provider": provider,
                    "project": outcome.lookup.project_id or outcome.lookup.slug,
                    "message": outcome.message,
                }
            )

    return {
        "resources": {
            resource_type: {
                provider: {
                    key: counter[key]
                    for key in (
                        "required",
                        "cached_before",
                        "fetched",
                        "updated",
                        "would_fetch",
                        "failed",
                    )
                }
                for provider, counter in provider_buckets.items()
            }
            for resource_type, provider_buckets in buckets.items()
        },
        "pruned": dict(pruned_by_provider),
        "failures": failures,
    }


def version_refresh_data(
    outcomes: list[VersionRefreshOutcome],
) -> dict[str, Any]:
    counts = Counter(outcome.status for outcome in outcomes)
    failures = [
        {
            "version_id": outcome.version_id,
            "project_id": outcome.project_id,
            "message": outcome.message,
        }
        for outcome in outcomes
        if outcome.status == "failed"
    ]
    return {
        "required": sum(
            counts[status]
            for status in ("cached", "fetched", "updated", "would_fetch", "failed")
        ),
        "cached_before": counts["cached"] + counts["updated"],
        "fetched": counts["fetched"],
        "updated": counts["updated"],
        "would_fetch": counts["would_fetch"],
        "pruned": counts["pruned"] + counts["would_prune"],
        "failed": counts["failed"],
        "failures": failures,
    }


def print_refresh_report(data: dict[str, Any]) -> None:
    print("Project metadata")
    headers = [
        "Provider",
        "Required",
        "Cached",
        "Fetched",
        "Updated",
        "Would fetch",
        "Failed",
    ]
    for resource_type in RESOURCE_TYPES:
        print()
        print(RESOURCE_TYPE_DISPLAY_NAMES[resource_type])
        rows = []
        for provider in PROVIDERS:
            counts = data["projects"]["resources"][resource_type][provider]
            rows.append(
                [
                    provider.capitalize(),
                    str(counts["required"]),
                    str(counts["cached_before"]),
                    str(counts["fetched"]),
                    str(counts["updated"]),
                    str(counts["would_fetch"]),
                    str(counts["failed"]),
                ]
            )
        widths = [
            max(len(headers[index]), *(len(row[index]) for row in rows))
            for index in range(len(headers))
        ]
        print(
            "  ".join(
                header.ljust(widths[index]) if index == 0 else header.rjust(widths[index])
                for index, header in enumerate(headers)
            )
        )
        for row in rows:
            print(
                "  ".join(
                    value.ljust(widths[index]) if index == 0 else value.rjust(widths[index])
                    for index, value in enumerate(row)
                )
            )

    if data.get("versions"):
        versions = data["versions"]
        print()
        print("Modrinth version pool")
        print(
            f"  required {versions['required']}, cached before {versions['cached_before']}, "
            f"fetched {versions['fetched']}, updated {versions['updated']}, "
            f"pruned {versions['pruned']}, "
            f"failed {versions['failed']}"
        )
    pruned = data["projects"]["pruned"]
    if pruned:
        print()
        print("Pruned project metadata")
        for provider, count in sorted(pruned.items()):
            print(f"  {provider}: {count}")

    failures = list(data["projects"]["failures"])
    failures.extend((data.get("versions") or {}).get("failures", []))
    if failures:
        print()
        print("Failures")
        for failure in failures:
            print(f"  {failure['message']}")


def refresh_command(args: argparse.Namespace) -> int:
    _, _, occurrences, source_issues = load_documentation_sources()
    if source_issues:
        raise RuntimeError("\n".join(issue.message for issue in source_issues))
    installed = load_installed_projects()
    lookups = [*documentation_lookups(occurrences), *installed_lookups(installed)]
    projects = load_project_metadata_or_empty()
    version_pool = load_version_pool_or_empty()

    providers = (
        set(SUPPORTED_PROVIDERS)
        if args.provider == "all"
        else {args.provider}
    )
    project_outcomes: list[ProjectRefreshOutcome] = []
    version_outcomes: list[VersionRefreshOutcome] = []

    if args.scope in {"all", "projects"}:
        projects, project_outcomes = refresh_project_metadata(
            lookups,
            projects,
            providers=providers,
            force=args.force,
            dry_run=args.dry_run,
        )
    if args.scope in {"all", "versions"} and "modrinth" in providers:
        version_pool, version_outcomes = refresh_version_pool(
            modrinth_installations(installed),
            version_pool,
            force=args.force,
            dry_run=args.dry_run,
        )

    project_failed = any(
        outcome.status == "failed" for outcome in project_outcomes
    )
    version_failed = any(
        outcome.status == "failed" for outcome in version_outcomes
    )
    if not args.dry_run:
        if args.scope in {"all", "projects"} and not project_failed:
            write_json_if_changed(
                PROJECT_METADATA_PATH,
                project_metadata_pool_data(projects),
            )
        if args.scope in {"all", "versions"} and "modrinth" in providers:
            write_json_if_changed(
                MODRINTH_VERSION_POOL_PATH,
                version_pool_data(version_pool),
            )

    failed = project_failed or version_failed

    report = {
        "schema_version": 1,
        "dry_run": args.dry_run,
        "projects": project_refresh_data(project_outcomes),
        "versions": version_refresh_data(version_outcomes) if version_outcomes else None,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_refresh_report(report)
    return 1 if failed else 0


def generate_command(args: argparse.Namespace) -> int:
    inventory = build_inventory()
    version_pool = load_version_pool_or_empty()
    snapshot, dependency_issues = build_dependency_snapshot(
        modrinth_installations(inventory.installed),
        version_pool.versions,
    )
    if dependency_issues:
        raise RuntimeError("\n".join(issue.message for issue in dependency_issues))

    artifacts: dict[str, str] = {}
    artifacts[str(DEPENDENCY_SNAPSHOT_PATH.relative_to(ROOT))] = write_json_if_changed(
        DEPENDENCY_SNAPSHOT_PATH,
        dependency_snapshot_data(snapshot),
    )
    inventory = build_inventory()
    blocking_errors = [
        issue
        for issue in inventory.errors
        if issue.code not in {"stale_generated_document", "missing_generated_document"}
    ]
    if blocking_errors:
        raise RuntimeError("\n".join(issue.message for issue in blocking_errors))
    artifacts.update(
        {
            str(path.relative_to(ROOT)): status
            for path, status in generate_documents(inventory).items()
        }
    )

    data = {"schema_version": 1, "artifacts": dict(sorted(artifacts.items()))}
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("Artifacts")
        for path, status in data["artifacts"].items():
            print(f"  {path:<40} {status}")
    return 0


def status_command(args: argparse.Namespace) -> int:
    inventory = build_inventory()
    data = status_data(inventory)
    output_data(data, json_output=args.json)
    return 1 if data["result"] == "fail" else 0


def check_command(args: argparse.Namespace) -> int:
    inventory = build_inventory()
    issues = complete_check_issues(inventory, deep=args.deep)
    data = status_data(inventory, issues=issues)
    output_data(data, json_output=args.json)
    return 1 if data["result"] == "fail" else 0


def index_command(args: argparse.Namespace) -> int:
    completed_process = refresh_index(args.packwiz_arguments)
    data = {
        "schema_version": 1,
        "result": "refreshed",
        "stdout": completed_process.stdout,
        "stderr": completed_process.stderr,
    }
    if not args.json:
        if completed_process.stdout:
            print(completed_process.stdout, end="")
        if completed_process.stderr:
            print(completed_process.stderr, end="", file=sys.stderr)
        print("Packwiz index refreshed.")
    else:
        print(json_text(data), end="")
    return 0


def invoke_json_command(
    command: Any,
    args: argparse.Namespace,
) -> tuple[int, dict[str, Any]]:
    output_buffer = io.StringIO()
    with contextlib.redirect_stdout(output_buffer):
        result = command(args)
    raw_output = output_buffer.getvalue().strip()
    data = json.loads(raw_output) if raw_output else {}
    return result, data


def sync_command(args: argparse.Namespace) -> int:
    refresh_args = argparse.Namespace(
        provider="all",
        scope="all",
        force=args.force,
        dry_run=False,
        json=args.json,
    )
    if args.json:
        stages: dict[str, Any] = {}
        refresh_result, stages["refresh"] = invoke_json_command(
            refresh_command,
            refresh_args,
        )
        if refresh_result:
            print(
                json.dumps(
                    {"schema_version": 1, "result": "fail", "stages": stages},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return refresh_result

        generate_result, stages["generate"] = invoke_json_command(
            generate_command,
            argparse.Namespace(json=True),
        )
        if generate_result:
            print(
                json.dumps(
                    {"schema_version": 1, "result": "fail", "stages": stages},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return generate_result

        completed_process = refresh_index([])
        stages["index"] = {
            "result": "refreshed",
            "stdout": completed_process.stdout,
            "stderr": completed_process.stderr,
        }
        check_result, stages["check"] = invoke_json_command(
            check_command,
            argparse.Namespace(deep=True, json=True),
        )
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "result": stages["check"].get("result", "fail"),
                    "stages": stages,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return check_result

    refresh_result = refresh_command(refresh_args)
    if refresh_result:
        return refresh_result
    generate_result = generate_command(
        argparse.Namespace(json=args.json)
    )
    if generate_result:
        return generate_result
    index_command(argparse.Namespace(json=False, packwiz_arguments=[]))
    return check_command(argparse.Namespace(deep=True, json=args.json))


def add_output_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write machine-readable JSON instead of the human report.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show inventory and health.")
    add_output_argument(status_parser)

    check_parser = subparsers.add_parser("check", help="Validate repository state.")
    check_parser.add_argument(
        "--deep",
        action="store_true",
        help="Compare tracked dependency edges with the local Modrinth version pool.",
    )
    add_output_argument(check_parser)

    refresh_parser = subparsers.add_parser("refresh", help="Refresh provider metadata.")
    refresh_parser.add_argument(
        "--provider",
        choices=["all", *SUPPORTED_PROVIDERS],
        default="all",
    )
    refresh_parser.add_argument(
        "--scope",
        choices=["all", "projects", "versions"],
        default="all",
    )
    refresh_parser.add_argument("--force", action="store_true")
    refresh_parser.add_argument("--dry-run", action="store_true")
    add_output_argument(refresh_parser)

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate dependency snapshot and public documentation.",
    )
    add_output_argument(generate_parser)

    index_parser = subparsers.add_parser("index", help="Refresh the packwiz index.")
    index_parser.add_argument("packwiz_arguments", nargs=argparse.REMAINDER)
    add_output_argument(index_parser)

    sync_parser = subparsers.add_parser(
        "sync",
        help="Refresh metadata, generate outputs, refresh packwiz, and check.",
    )
    sync_parser.add_argument("--force", action="store_true")
    add_output_argument(sync_parser)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "status":
            return status_command(args)
        if args.command == "check":
            return check_command(args)
        if args.command == "refresh":
            return refresh_command(args)
        if args.command == "generate":
            return generate_command(args)
        if args.command == "index":
            return index_command(args)
        if args.command == "sync":
            return sync_command(args)
    except (
        OSError,
        ValueError,
        ProjectMetadataError,
        ModrinthVersionError,
        RuntimeError,
        subprocess.CalledProcessError,
    ) as error:
        message = str(error)
        if isinstance(error, subprocess.CalledProcessError):
            diagnostics = str(error.stderr or error.stdout or "").strip()
            if diagnostics:
                message = f"{message}: {diagnostics}"
        if getattr(args, "json", False):
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "result": "fail",
                        "error": {"message": message},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(message, file=sys.stderr)
        return 2
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
