#!/usr/bin/env python3
"""Generate bilingual project documentation, one document per data category."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from project_data_common import (
    CATEGORIES,
    PROJECT_TYPE_CURSEFORGE_PATHS,
    load_documentation_catalog,
    load_feature_groups,
    markdown_escape,
    read_json,
    selected_project_refs_from_version,
    write_text,
)
from project_data_identity import resolve_project_ref


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"


def load_category_data(
    category: dict[str, Any],
    all_groups: list[dict[str, Any]],
    project_catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    meta = read_json(category["meta_path"])
    return {
        "name": category["name"],
        "title": meta["title"],
        "versions": meta["versions"],
        "introduction": meta["introduction"],
        "projects": project_catalog,
        "groups": [group for group in all_groups if group["_category"] == category["name"]],
    }


def project_from_ref(data: dict[str, Any], ref: Any) -> dict[str, Any] | None:
    return resolve_project_ref(data.get("projects", {}), ref)


def project_link(project: dict[str, Any]) -> str | None:
    if project.get("source") == "modrinth" and project.get("slug"):
        return f"https://modrinth.com/{project.get('type') or 'mod'}/{project['slug']}"
    if project.get("source") == "curseforge" and project.get("slug"):
        curseforge_path = PROJECT_TYPE_CURSEFORGE_PATHS.get(str(project.get("type") or "mod"), "mc-mods")
        return f"https://www.curseforge.com/minecraft/{curseforge_path}/{project['slug']}"
    if project.get("url"):
        return str(project["url"])
    return None


def render_project(project: dict[str, Any] | None) -> str:
    if project is None:
        return ""

    name = markdown_escape(str(project.get("name") or project.get("slug") or project.get("id") or ""))
    link = project_link(project)
    if not link:
        return name
    return f"[{name}]({link})"


def version_projects(
    data: dict[str, Any],
    group: dict[str, Any],
    section: dict[str, Any],
    row: dict[str, Any],
    version: str,
) -> list[dict[str, Any]]:
    version_data = row.get("versions", {}).get(version, {})
    selected_refs = selected_project_refs_from_version(
        group,
        section,
        row,
        version,
        version_data,
    )
    return [project for ref in selected_refs if (project := project_from_ref(data, ref)) is not None]


def version_alternatives(data: dict[str, Any], row: dict[str, Any], version: str) -> list[dict[str, Any]]:
    version_data = row.get("versions", {}).get(version, {})
    return [
        project
        for ref in version_data.get("alternatives", [])
        if (project := project_from_ref(data, ref)) is not None
    ]


def render_projects(projects: list[dict[str, Any]]) -> str:
    return ", ".join(render_project(project) for project in projects)


def render_header(data: dict[str, Any], language: str) -> list[str]:
    readme_label = "返回 README" if language == "zh" else "Back to README"
    readme_path = "../README.zh-CN.md" if language == "zh" else "../README.md"
    return [
        f"# {data['title'][language]}",
        "",
        f"[{readme_label}]({readme_path})",
        "",
        data["introduction"][language],
        "",
    ]


def render_group_intro(group: dict[str, Any], language: str) -> list[str]:
    return [
        f"## {group['title'][language]}",
        "",
        group["description"][language],
        "",
    ]


def render_section_intro(section: dict[str, Any], language: str) -> list[str]:
    return [
        f"### {section['title'][language]}",
        "",
        section["description"][language],
        "",
    ]


def section_has_alternatives(
    data: dict[str, Any],
    section: dict[str, Any],
    versions: list[str],
) -> bool:
    return any(
        version_alternatives(data, row, version)
        for row in section["rows"]
        for version in versions
    )


def table_headers(versions: list[str], language: str, show_alternatives: bool) -> list[str]:
    headers = ["功能", *versions] if language == "zh" else ["Feature", *versions]
    if not show_alternatives:
        return headers

    headers.append("可选替代" if language == "zh" else "Alternatives")
    return headers


def render_feature_row(
    data: dict[str, Any],
    group: dict[str, Any],
    section: dict[str, Any],
    row: dict[str, Any],
    versions: list[str],
    language: str,
    show_alternatives: bool,
) -> str:
    cells = [markdown_escape(str(row["feature"][language]))]

    for version in versions:
        projects = version_projects(data, group, section, row, version)
        cells.append(render_projects(projects))

    if show_alternatives:
        alternatives = [
            render_project(alternative)
            for version in versions
            for alternative in version_alternatives(data, row, version)
        ]
        cells.append(", ".join(alternatives))

    return f"| {' | '.join(cells)} |"


def render_section(
    data: dict[str, Any],
    group: dict[str, Any],
    section: dict[str, Any],
    versions: list[str],
    language: str,
) -> list[str]:
    lines = render_section_intro(section, language)
    show_alternatives = section_has_alternatives(data, section, versions)
    headers = table_headers(versions, language, show_alternatives)

    lines.append(f"| {' | '.join(headers)} |")
    lines.append(f"| {' | '.join('---' for _ in headers)} |")
    for row in section["rows"]:
        lines.append(render_feature_row(data, group, section, row, versions, language, show_alternatives))
    lines.append("")
    return lines


def render_matrix(data: dict[str, Any], language: str) -> str:
    versions = list(data["versions"])
    lines = render_header(data, language)

    for group in data["groups"]:
        lines.extend(render_group_intro(group, language))
        for section in group["sections"]:
            lines.extend(render_section(data, group, section, versions, language))

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines) + "\n"


def category_outputs(
    category: dict[str, Any],
    all_groups: list[dict[str, Any]],
    project_catalog: dict[str, dict[str, Any]],
) -> dict[Path, str]:
    data = load_category_data(category, all_groups, project_catalog)
    return {
        DOCS_DIR / f"{category['name']}.md": render_matrix(data, "en"),
        DOCS_DIR / f"{category['name']}.zh-CN.md": render_matrix(data, "zh"),
    }


def main() -> None:
    all_groups = load_feature_groups()
    project_catalog = load_documentation_catalog()

    outputs: dict[Path, str] = {}
    for category in CATEGORIES:
        outputs.update(category_outputs(category, all_groups, project_catalog))

    for path, text in outputs.items():
        write_text(path, text)
        print(f"Generated {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
