#!/usr/bin/env python3
"""Check packwiz project metadata (mods, resource packs, shaders, ...) against structured data."""

from __future__ import annotations

import argparse
import json
from typing import Any

from project_data_common import (
    CACHE,
    DEPENDENCY_CACHE,
    PROJECT_CACHE,
    TARGET_VERSION,
    build_documented_sets,
    build_missing_required,
    build_required_by,
    cache_entry_has_error,
    collect_cache_errors,
    is_documented,
    load_declared_dependencies,
    load_dependency_cache,
    load_feature_groups,
    load_installed_projects,
    load_project_cache,
    load_project_catalog,
    markdown_escape,
    markdown_link,
    required_by_names,
    write_json,
    write_text,
)
from project_data_invariants import generated_data_invariants
from project_data_identity import (
    build_installed_project_index,
    is_project_installed,
    project_identity,
    project_ref_key,
    resolve_project_ref,
)


OUTPUT = CACHE / "project-data-check.zh-CN.md"
EXPECTED_FOLDER_VERSION_LOADERS = {
    "datapack": "datapack",
}


def folder_type_conflicts(
    installed: list[dict[str, Any]],
    project_meta: dict[str, dict[str, Any]],
) -> list[str]:
    type_by_id: dict[str, str] = {}
    type_by_source_id: dict[tuple[str, str], str] = {}
    type_by_slug: dict[str, str] = {}
    for entry in project_meta.values():
        declared_type = str(entry.get("type") or "")
        if not declared_type:
            continue
        if entry.get("source") and entry.get("id"):
            type_by_source_id[(str(entry["source"]), str(entry["id"]))] = declared_type
        if entry.get("source") == "modrinth" and entry.get("id"):
            type_by_id[str(entry["id"])] = declared_type
        if entry.get("slug"):
            type_by_slug[str(entry["slug"]).lower()] = declared_type

    conflicts: list[str] = []
    for project in installed:
        expected = (
            type_by_source_id.get((str(project.get("source") or ""), str(project.get("id") or "")))
            or type_by_id.get(project["modrinth_id"])
            or type_by_slug.get(project["slug"])
        )
        if expected and expected != project["type"]:
            conflicts.append(
                f"{project['file']}: installed as {project['type']} but Modrinth project type is {expected}"
            )
    return conflicts


def version_loader_conflicts(
    installed: list[dict[str, Any]],
    dependency_cache: dict[str, Any],
) -> list[str]:
    conflicts: list[str] = []

    for project in installed:
        expected_loader = EXPECTED_FOLDER_VERSION_LOADERS.get(str(project.get("type") or ""))
        if not expected_loader or project.get("source") != "modrinth":
            continue

        version_id = str(project.get("modrinth_version") or "")
        version_data = dependency_cache.get(version_id)
        if not isinstance(version_data, dict) or cache_entry_has_error(version_data):
            continue

        actual_loaders = {str(loader).lower() for loader in version_data.get("loaders", [])}
        if expected_loader in actual_loaders:
            continue

        loader_summary = ", ".join(sorted(actual_loaders)) or "none"
        filename = str(project.get("filename") or "")
        conflicts.append(
            f"{project['file']}: installed as {project['type']} but Modrinth version "
            f"{version_id} loaders are [{loader_summary}]"
            + (f" (filename: {filename})" if filename else "")
        )

    return conflicts


def unexpected_installed_projects(
    groups: list[dict[str, Any]],
    project_meta: dict[str, dict[str, Any]],
    installed_index: dict[str, set[str]],
) -> list[str]:
    conflicts: list[str] = []

    for group in groups:
        is_optional_group = bool(group["_optional"])
        for section in group["sections"]:
            for row in section["rows"]:
                for version, version_data in row.get("versions", {}).items():
                    if version != TARGET_VERSION:
                        continue
                    project = resolve_project_ref(project_meta, version_data.get("selected"))
                    if is_optional_group and is_project_installed(project, installed_index):
                        conflicts.append(
                            f"{row['id']} ({version}): {project['name']} is optional but is installed"
                        )
                    for ref in version_data.get("alternatives", []):
                        alternative = resolve_project_ref(project_meta, ref)
                        if is_project_installed(alternative, installed_index):
                            conflicts.append(
                                f"{row['id']} ({version}): {alternative['name']} is an alternative but is installed"
                            )
    return conflicts


def unknown_project_refs(groups: list[dict[str, Any]], project_meta: dict[str, dict[str, Any]]) -> list[str]:
    unknown: list[str] = []

    def check_ref(ref: Any, location: str) -> None:
        if ref is None:
            return
        key = project_ref_key(ref)
        if not key:
            return
        if key not in project_meta:
            unknown.append(f"{location}: unknown project ref {ref}")

    for group in groups:
        for section in group["sections"]:
            for row in section["rows"]:
                for version, version_data in row.get("versions", {}).items():
                    location = f"{group['id']}/{section['id']}/{row['id']} ({version})"
                    check_ref(version_data.get("selected"), location)
                    for ref in version_data.get("alternatives", []):
                        check_ref(ref, f"{location} alternative")

    return unknown


def duplicate_project_refs(groups: list[dict[str, Any]], project_meta: dict[str, dict[str, Any]]) -> list[str]:
    seen: dict[tuple[str, str], str] = {}
    duplicates: list[str] = []

    def remember(ref: Any, location: str) -> None:
        identity = project_identity(resolve_project_ref(project_meta, ref), ref)
        if not identity:
            return
        key = (TARGET_VERSION, identity)
        previous = seen.get(key)
        if previous and previous != location:
            duplicates.append(f"{identity}: {previous} and {location}")
            return
        seen[key] = location

    for group in groups:
        for section in group["sections"]:
            for row in section["rows"]:
                version_data = row.get("versions", {}).get(TARGET_VERSION)
                if not version_data:
                    continue
                location = f"{group['id']}/{section['id']}/{row['id']} ({TARGET_VERSION})"
                remember(version_data.get("selected"), location)
                for ref in version_data.get("alternatives", []):
                    remember(ref, f"{location} alternative")

    return duplicates


def expected_default_projects(
    groups: list[dict[str, Any]],
    project_meta: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    expected: list[dict[str, Any]] = []
    for group in groups:
        if group["_optional"]:
            continue
        for section in group["sections"]:
            for row in section["rows"]:
                version_data = row.get("versions", {}).get(TARGET_VERSION)
                if not version_data:
                    continue
                project = resolve_project_ref(project_meta, version_data.get("selected"))
                if project is not None:
                    expected.append(project)
    return expected


def table(lines: list[str], rows: list[dict[str, object]], required_by: dict[str, list[dict[str, object]]]) -> None:
    lines.extend(
        [
            "| Project | Type | Slug | Side | Pack file | Required by |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for mod in rows:
        project_id = str(mod.get("modrinth_id") or "")
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_link(str(mod["name"]), project_id, str(mod.get("type") or "")),
                    markdown_escape(mod.get("type")),
                    markdown_escape(mod["slug"]),
                    markdown_escape(mod["side"]),
                    markdown_escape(mod["file"]),
                    markdown_escape(required_by_names(project_id, required_by)),
                ]
            )
            + " |"
        )


def check(*, persist_cache: bool = True) -> dict[str, object]:
    installed = load_installed_projects()
    installed_index = build_installed_project_index(installed)
    project_meta: dict[str, dict[str, object]] = load_project_catalog()
    groups = load_feature_groups()
    documented = build_documented_sets(project_meta)
    declared_dependencies = load_declared_dependencies()
    dependency_cache = load_dependency_cache()
    project_cache = load_project_cache()
    required_by = build_required_by(installed, dependency_cache)
    missing_dependencies = build_missing_required(installed, dependency_cache, project_cache)
    cache_errors = [
        *collect_cache_errors(dependency_cache, "dependency-cache"),
        *collect_cache_errors(project_cache, "project-cache"),
    ]
    if persist_cache:
        write_json(DEPENDENCY_CACHE, dependency_cache)
        write_json(PROJECT_CACHE, project_cache)

    documented_installed: list[dict[str, object]] = []
    dependency_declared: list[dict[str, object]] = []
    unexplained: list[dict[str, object]] = []

    for mod in installed:
        if is_documented(mod, documented):
            documented_installed.append(mod)
        elif str(mod["slug"]) in declared_dependencies:
            dependency_declared.append(mod)
        else:
            unexplained.append(mod)

    missing_defaults = [
        project
        for project in expected_default_projects(groups, project_meta)
        if not is_project_installed(project, installed_index)
    ]

    return {
        "installed": installed,
        "required_by": required_by,
        "documented_installed": documented_installed,
        "dependency_declared": dependency_declared,
        "unexplained": unexplained,
        "cache_errors": cache_errors,
        "generated_data_invariants": generated_data_invariants(groups, installed, declared_dependencies),
        "unexpected_installed": unexpected_installed_projects(groups, project_meta, installed_index),
        "unknown_refs": unknown_project_refs(groups, project_meta),
        "duplicate_refs": duplicate_project_refs(groups, project_meta),
        "missing_defaults": missing_defaults,
        "missing_dependencies": missing_dependencies,
        "folder_conflicts": folder_type_conflicts(installed, project_meta),
        "version_loader_conflicts": version_loader_conflicts(installed, dependency_cache),
    }


def render_report(result: dict[str, object]) -> str:
    installed = result["installed"]
    documented_installed = result["documented_installed"]
    dependency_declared = result["dependency_declared"]
    unexplained = result["unexplained"]
    cache_errors = result["cache_errors"]
    generated_data_invariant_issues = result["generated_data_invariants"]
    unexpected = result["unexpected_installed"]
    unknown_refs = result["unknown_refs"]
    duplicate_refs = result["duplicate_refs"]
    missing_defaults = result["missing_defaults"]
    missing_dependencies = result["missing_dependencies"]
    folder_conflicts = result["folder_conflicts"]
    version_loader_conflict_issues = result["version_loader_conflicts"]
    required_by = result["required_by"]

    assert isinstance(installed, list)
    assert isinstance(documented_installed, list)
    assert isinstance(dependency_declared, list)
    assert isinstance(unexplained, list)
    assert isinstance(cache_errors, list)
    assert isinstance(generated_data_invariant_issues, list)
    assert isinstance(unexpected, list)
    assert isinstance(unknown_refs, list)
    assert isinstance(duplicate_refs, list)
    assert isinstance(missing_defaults, list)
    assert isinstance(missing_dependencies, dict)
    assert isinstance(folder_conflicts, list)
    assert isinstance(version_loader_conflict_issues, list)
    assert isinstance(required_by, dict)

    lines = [
        "# 项目数据一致性检查",
        "",
        "这份报告对比 packwiz 实际安装的项目元文件（mods、resourcepacks、shaderpacks、datapacks 等目录下的 `*.pw.toml`）、`docs/config/` 文档配置与 `data/` 生成数据，并通过 Modrinth versions API 解析 required 依赖关系。",
        "",
        f"- 目标 Minecraft 版本：{TARGET_VERSION}",
        f"- 已安装 packwiz 项目：{len(installed)}",
        f"- 功能矩阵覆盖：{len(documented_installed)}",
        f"- dependencies.json 覆盖：{len(dependency_declared)}",
        f"- 未解释项目：{len(unexplained)}",
        f"- 缓存错误：{len(cache_errors)}",
        f"- 生成数据集合不变量问题：{len(generated_data_invariant_issues)}",
        f"- 默认包缺失：{len(missing_defaults)}",
        f"- 缺失 required 依赖：{len(missing_dependencies)}",
        f"- 安装目录不符：{len(folder_conflicts)}",
        f"- 版本加载器不符：{len(version_loader_conflict_issues)}",
        f"- 意外安装项目：{len(unexpected)}",
        f"- 未知项目引用：{len(unknown_refs)}",
        f"- 重复项目引用：{len(duplicate_refs)}",
        "",
    ]

    lines.extend(["## 缓存错误", ""])
    if cache_errors:
        lines.extend(f"- {error}" for error in cache_errors)
    else:
        lines.append("无。")

    lines.extend(["", "## 生成数据集合不变量", ""])
    if generated_data_invariant_issues:
        lines.extend(f"- {issue}" for issue in generated_data_invariant_issues)
    else:
        lines.append("无。")

    lines.extend(["", "## 默认包缺失", ""])
    if missing_defaults:
        lines.extend(f"- {project['name']}" for project in missing_defaults)
    else:
        lines.append("无。")

    lines.extend(["", "## 缺失 required 依赖", ""])
    if missing_dependencies:
        lines.append("这些 Modrinth 项目被已安装项目声明为 required 依赖，但没有安装在任何 packwiz 目录中。")
        lines.append("")
        for project_id, entry in missing_dependencies.items():
            title = markdown_link(str(entry["name"]), project_id, str(entry.get("type") or ""))
            type_note = f"（{entry['type']}）" if entry.get("type") else ""
            lines.append(f"- {title}{type_note}：被 {', '.join(entry['required_by'])} 依赖")
    else:
        lines.append("无。")

    lines.extend(["", "## 安装目录不符", ""])
    if folder_conflicts:
        lines.extend(f"- {conflict}" for conflict in folder_conflicts)
    else:
        lines.append("无。")

    lines.extend(["", "## 版本加载器不符", ""])
    if version_loader_conflict_issues:
        lines.append("这些项目安装在需要特定 Modrinth loader 的目录中，但锁定的具体版本没有声明对应 loader。")
        lines.append("")
        lines.extend(f"- {conflict}" for conflict in version_loader_conflict_issues)
    else:
        lines.append("无。")

    lines.extend(["", "## 意外安装项目", ""])
    if unexpected:
        lines.extend(f"- {conflict}" for conflict in unexpected)
    else:
        lines.append("无。")

    lines.extend(["", "## 未知项目引用", ""])
    if unknown_refs:
        lines.extend(f"- {item}" for item in unknown_refs)
    else:
        lines.append("无。")

    lines.extend(["", "## 重复项目引用", ""])
    if duplicate_refs:
        lines.extend(f"- {item}" for item in duplicate_refs)
    else:
        lines.append("无。")

    lines.extend(["", "## 未解释项目", ""])
    if unexplained:
        lines.append("这些项目已经进入默认包，但当前既没有进入功能矩阵，也没有进入 `data/dependencies.json`。需要补功能矩阵、补依赖清单、修 alias，或手动归类。")
        lines.append("")
        table(lines, unexplained, required_by)
    else:
        lines.append("无。")

    lines.extend(["", "## dependencies.json 覆盖", ""])
    if dependency_declared:
        lines.append("这些项目没有进入公开功能矩阵，但已经在 `data/dependencies.json` 中声明为 dependency-only。")
        lines.append("")
        table(lines, dependency_declared, required_by)
    else:
        lines.append("无。")

    lines.extend(["", "## 功能矩阵覆盖", ""])
    table(lines, documented_installed, required_by)

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if packwiz mods and structured mod data are inconsistent.")
    args = parser.parse_args()

    result = check(persist_cache=not args.check)
    report = render_report(result)
    if not args.check:
        write_text(OUTPUT, report)

    unexplained = result["unexplained"]
    cache_errors = result["cache_errors"]
    generated_data_invariant_issues = result["generated_data_invariants"]
    unexpected = result["unexpected_installed"]
    unknown_refs = result["unknown_refs"]
    duplicate_refs = result["duplicate_refs"]
    missing_defaults = result["missing_defaults"]
    missing_dependencies = result["missing_dependencies"]
    folder_conflicts = result["folder_conflicts"]
    version_loader_conflict_issues = result["version_loader_conflicts"]
    assert isinstance(unexplained, list)
    assert isinstance(cache_errors, list)
    assert isinstance(generated_data_invariant_issues, list)
    assert isinstance(unexpected, list)
    assert isinstance(unknown_refs, list)
    assert isinstance(duplicate_refs, list)
    assert isinstance(missing_defaults, list)
    assert isinstance(missing_dependencies, dict)
    assert isinstance(folder_conflicts, list)
    assert isinstance(version_loader_conflict_issues, list)

    summary = {
        "installed": len(result["installed"]),
        "documented": len(result["documented_installed"]),
        "dependencies": len(result["dependency_declared"]),
        "unexplained": len(unexplained),
        "cache_errors": len(cache_errors),
        "generated_data_invariants": len(generated_data_invariant_issues),
        "missing_defaults": len(missing_defaults),
        "missing_dependencies": len(missing_dependencies),
        "folder_conflicts": len(folder_conflicts),
        "version_loader_conflicts": len(version_loader_conflict_issues),
        "unexpected_installed": len(unexpected),
        "unknown_refs": len(unknown_refs),
        "duplicate_refs": len(duplicate_refs),
        "output": str(OUTPUT.relative_to(CACHE.parents[1])),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.check and (
        unexplained
        or cache_errors
        or generated_data_invariant_issues
        or missing_defaults
        or missing_dependencies
        or folder_conflicts
        or version_loader_conflict_issues
        or unexpected
        or unknown_refs
        or duplicate_refs
    ):
        issues = []
        if unexplained:
            issues.extend(f"- undocumented: {mod['name']} ({mod['slug']})" for mod in unexplained)
        if cache_errors:
            issues.extend(f"- cache error: {error}" for error in cache_errors)
        if generated_data_invariant_issues:
            issues.extend(f"- generated data invariant: {issue}" for issue in generated_data_invariant_issues)
        if missing_defaults:
            issues.extend(f"- missing default: {project['name']}" for project in missing_defaults)
        if missing_dependencies:
            issues.extend(
                f"- missing dependency: {entry['name']} ({project_id}) required by {', '.join(entry['required_by'])}"
                for project_id, entry in missing_dependencies.items()
            )
        if folder_conflicts:
            issues.extend(f"- folder conflict: {conflict}" for conflict in folder_conflicts)
        if version_loader_conflict_issues:
            issues.extend(f"- version loader conflict: {conflict}" for conflict in version_loader_conflict_issues)
        if unexpected:
            issues.extend(f"- unexpected installed: {conflict}" for conflict in unexpected)
        if unknown_refs:
            issues.extend(f"- unknown ref: {item}" for item in unknown_refs)
        if duplicate_refs:
            issues.extend(f"- duplicate ref: {item}" for item in duplicate_refs)
        raise SystemExit("Project data check failed:\n" + "\n".join(issues))


if __name__ == "__main__":
    main()
