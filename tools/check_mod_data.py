#!/usr/bin/env python3
"""Check packwiz mod metadata against structured mod data."""

from __future__ import annotations

import argparse
import json
from typing import Any

from mod_data_common import (
    CACHE,
    DATA,
    DEPENDENCY_CACHE,
    TARGET_VERSION,
    build_documented_sets,
    build_required_by,
    is_documented,
    load_declared_dependencies,
    load_dependency_cache,
    load_installed_mods,
    markdown_escape,
    markdown_link,
    read_json,
    required_by_names,
    write_json,
    write_text,
)


OUTPUT = CACHE / "mod-data-check.zh-CN.md"
FEATURE_GROUP_FILES = [
    "core-foundation.json",
    "visual-and-audio-enhancements.json",
    "utility-features.json",
    "optional-capabilities.json",
]


def project_from_ref(project_meta: dict[str, dict[str, Any]], ref: Any) -> dict[str, Any] | None:
    if ref is None:
        return None
    if isinstance(ref, dict):
        return ref
    return project_meta.get(str(ref))


def is_project_installed(project: dict[str, Any] | None, installed: list[dict[str, Any]]) -> bool:
    if project is None:
        return False

    slug = str(project.get("slug") or "").lower()
    name = str(project.get("name") or "").lower()
    modrinth_id = str(project.get("modrinth_id") or "")

    for mod in installed:
        if slug and slug == str(mod["slug"]):
            return True
        if name and name == str(mod["name"]).lower():
            return True
        if modrinth_id and modrinth_id == str(mod["modrinth_id"]):
            return True
    return False


def load_feature_groups() -> list[dict[str, Any]]:
    return [read_json(DATA / file_name) for file_name in FEATURE_GROUP_FILES]


def policy_conflicts(
    groups: list[dict[str, Any]],
    project_meta: dict[str, dict[str, Any]],
    installed: list[dict[str, Any]],
) -> list[str]:
    conflicts: list[str] = []

    for group in groups:
        for section in group["sections"]:
            for row in section["rows"]:
                if row.get("policy") not in {"optional", "skipped"}:
                    continue
                status = str(row["policy"])
                for version, version_data in row.get("versions", {}).items():
                    project = project_from_ref(project_meta, version_data.get("selected"))
                    if is_project_installed(project, installed):
                        conflicts.append(
                            f"{row['id']} ({version}): {project['name']} is marked {status} but is installed"
                        )
                    for ref in version_data.get("alternatives", []):
                        alternative = project_from_ref(project_meta, ref)
                        if is_project_installed(alternative, installed):
                            conflicts.append(
                                f"{row['id']} ({version}): {alternative['name']} is marked {status} alternative but is installed"
                            )
    return conflicts


def table(lines: list[str], rows: list[dict[str, object]], required_by: dict[str, list[dict[str, object]]]) -> None:
    lines.extend(
        [
            "| Mod | Slug | Side | Pack file | Required by |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for mod in rows:
        project_id = str(mod.get("modrinth_id") or "")
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_link(str(mod["name"]), project_id),
                    markdown_escape(mod["slug"]),
                    markdown_escape(mod["side"]),
                    markdown_escape(mod["file"]),
                    markdown_escape(required_by_names(project_id, required_by)),
                ]
            )
            + " |"
        )


def check() -> dict[str, object]:
    installed = load_installed_mods()
    project_meta: dict[str, dict[str, object]] = read_json(DATA / "projects.json")
    documented = build_documented_sets(project_meta)
    declared_dependencies = load_declared_dependencies()
    dependency_cache = load_dependency_cache()
    required_by = build_required_by(installed, dependency_cache)
    write_json(DEPENDENCY_CACHE, dependency_cache)

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

    return {
        "installed": installed,
        "required_by": required_by,
        "documented_installed": documented_installed,
        "dependency_declared": dependency_declared,
        "unexplained": unexplained,
        "policy_conflicts": policy_conflicts(load_feature_groups(), project_meta, installed),
    }


def render_report(result: dict[str, object]) -> str:
    installed = result["installed"]
    documented_installed = result["documented_installed"]
    dependency_declared = result["dependency_declared"]
    unexplained = result["unexplained"]
    conflicts = result["policy_conflicts"]
    required_by = result["required_by"]

    assert isinstance(installed, list)
    assert isinstance(documented_installed, list)
    assert isinstance(dependency_declared, list)
    assert isinstance(unexplained, list)
    assert isinstance(conflicts, list)
    assert isinstance(required_by, dict)

    lines = [
        "# Mod 数据一致性检查",
        "",
        "这份报告对比 packwiz 实际安装的 `mods/*.pw.toml` 与 `data/mods/*.json` 数据层，并通过 Modrinth versions API 解析 required 依赖关系。",
        "",
        f"- 目标 Minecraft 版本：{TARGET_VERSION}",
        f"- 已安装 packwiz Mod：{len(installed)}",
        f"- 功能矩阵覆盖：{len(documented_installed)}",
        f"- dependencies.json 覆盖：{len(dependency_declared)}",
        f"- 未解释项目：{len(unexplained)}",
        f"- policy 冲突：{len(conflicts)}",
        "",
        "## policy 冲突",
        "",
    ]
    if conflicts:
        lines.extend(f"- {conflict}" for conflict in conflicts)
    else:
        lines.append("无。")

    lines.extend(["", "## 未解释项目", ""])
    if unexplained:
        lines.append("这些项目已经进入默认包，但当前既没有进入功能矩阵，也没有进入 `data/mods/dependencies.json`。需要补功能矩阵、补依赖清单、修 alias，或手动归类。")
        lines.append("")
        table(lines, unexplained, required_by)
    else:
        lines.append("无。")

    lines.extend(["", "## dependencies.json 覆盖", ""])
    if dependency_declared:
        lines.append("这些项目没有进入公开功能矩阵，但已经在 `data/mods/dependencies.json` 中声明为 dependency-only。")
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

    result = check()
    report = render_report(result)
    write_text(OUTPUT, report)

    unexplained = result["unexplained"]
    conflicts = result["policy_conflicts"]
    assert isinstance(unexplained, list)
    assert isinstance(conflicts, list)

    summary = {
        "installed": len(result["installed"]),
        "documented": len(result["documented_installed"]),
        "dependencies": len(result["dependency_declared"]),
        "unexplained": len(unexplained),
        "policy_conflicts": len(conflicts),
        "output": str(OUTPUT.relative_to(CACHE.parents[1])),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.check and (unexplained or conflicts):
        issues = []
        if unexplained:
            issues.extend(f"- undocumented: {mod['name']} ({mod['slug']})" for mod in unexplained)
        if conflicts:
            issues.extend(f"- policy: {conflict}" for conflict in conflicts)
        raise SystemExit("Mod data check failed:\n" + "\n".join(issues))


if __name__ == "__main__":
    main()
