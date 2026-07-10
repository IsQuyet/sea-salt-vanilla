"""Render and validate bilingual project documentation from one inventory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from inventory import Inventory, InventoryIssue, row_target_data
from packwiz import DOCS, ROOT, read_json, write_text_if_changed
from project_metadata import ProjectMetadata, resolve_project_ref


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("|", r"\|").replace("\n", "<br>")


def render_project(project: ProjectMetadata) -> str:
    name = markdown_escape(project.name)
    return f"[{name}]({project.page})"


def resolve_projects(
    refs: list[Any],
    inventory: Inventory,
) -> list[ProjectMetadata]:
    return [resolve_project_ref(ref, inventory.metadata) for ref in refs]


def row_projects(row: dict[str, Any], inventory: Inventory) -> list[ProjectMetadata]:
    target_data = row_target_data(row, inventory.target_version)
    selected = target_data.get("selected", [])
    return resolve_projects(selected if isinstance(selected, list) else [], inventory)


def row_alternatives(
    row: dict[str, Any],
    inventory: Inventory,
) -> list[ProjectMetadata]:
    target_data = row_target_data(row, inventory.target_version)
    alternatives = target_data.get("alternatives", [])
    return resolve_projects(
        alternatives if isinstance(alternatives, list) else [],
        inventory,
    )


def render_header(
    title: dict[str, str],
    introduction: dict[str, str],
    language: str,
) -> list[str]:
    readme_label = "返回 README" if language == "zh" else "Back to README"
    readme_path = "../README.zh-CN.md" if language == "zh" else "../README.md"
    return [
        f"# {title[language]}",
        "",
        f"[{readme_label}]({readme_path})",
        "",
        introduction[language],
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


def render_feature_row(
    row: dict[str, Any],
    inventory: Inventory,
    language: str,
    show_alternatives: bool,
) -> str:
    cells = [markdown_escape(row["feature"][language])]
    cells.append(
        ", ".join(render_project(project) for project in row_projects(row, inventory))
    )
    if show_alternatives:
        cells.append(
            ", ".join(
                render_project(project)
                for project in row_alternatives(row, inventory)
            )
        )
    return f"| {' | '.join(cells)} |"


def render_section(
    section: dict[str, Any],
    inventory: Inventory,
    language: str,
) -> list[str]:
    lines = render_section_intro(section, language)
    show_alternatives = any(
        row_alternatives(row, inventory) for row in section.get("rows", [])
    )
    feature_header = "功能" if language == "zh" else "Feature"
    headers = [feature_header, inventory.target_version]
    if show_alternatives:
        headers.append("可选替代" if language == "zh" else "Alternatives")

    lines.append(f"| {' | '.join(headers)} |")
    lines.append(f"| {' | '.join('---' for _ in headers)} |")
    for row in section.get("rows", []):
        lines.append(
            render_feature_row(row, inventory, language, show_alternatives)
        )
    lines.append("")
    return lines


def render_category(
    category: dict[str, Any],
    inventory: Inventory,
    language: str,
) -> str:
    metadata = read_json(category["meta_path"])
    lines = render_header(metadata["title"], metadata["introduction"], language)

    for group in inventory.groups:
        if group["_category"] != category["name"]:
            continue
        lines.extend(render_group_intro(group, language))
        for section in group.get("sections", []):
            lines.extend(render_section(section, inventory, language))

    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def expected_document_outputs(inventory: Inventory) -> dict[Path, str]:
    outputs: dict[Path, str] = {}
    for category in inventory.categories:
        outputs[DOCS / f"{category['name']}.md"] = render_category(
            category,
            inventory,
            "en",
        )
        outputs[DOCS / f"{category['name']}.zh-CN.md"] = render_category(
            category,
            inventory,
            "zh",
        )
    return outputs


def generate_documents(inventory: Inventory) -> dict[Path, str]:
    return {
        path: write_text_if_changed(path, text)
        for path, text in expected_document_outputs(inventory).items()
    }


def document_freshness_issues(inventory: Inventory) -> list[InventoryIssue]:
    if any(
        issue.severity == "error"
        and issue.section in {"Documentation", "Metadata"}
        for issue in inventory.issues
    ):
        return []

    issues: list[InventoryIssue] = []
    for path, expected_text in expected_document_outputs(inventory).items():
        if not path.exists():
            issues.append(
                InventoryIssue(
                    section="Documentation",
                    code="missing_generated_document",
                    message=f"Missing generated document {path.relative_to(ROOT)}.",
                )
            )
            continue
        actual_text = path.read_text(encoding="utf-8-sig")
        if actual_text != expected_text:
            issues.append(
                InventoryIssue(
                    section="Documentation",
                    code="stale_generated_document",
                    message=(
                        f"{path.relative_to(ROOT)} does not match the documentation source."
                    ),
                )
            )
    return issues
