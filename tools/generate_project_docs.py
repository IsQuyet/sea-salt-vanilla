#!/usr/bin/env python3
"""Generate bilingual project documentation, one document per data category."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from project_data_common import (
    CATEGORIES,
    PROJECTS_PATH,
    load_feature_groups,
)


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def load_category_data(category: dict[str, Any], all_groups: list[dict[str, Any]]) -> dict[str, Any]:
    meta = read_json(category["meta_path"])
    return {
        "name": category["name"],
        "title": meta["title"],
        "versions": meta["versions"],
        "introduction": meta["introduction"],
        "projects": read_json(PROJECTS_PATH),
        "groups": [group for group in all_groups if group["_category"] == category["name"]],
    }


def project_from_ref(data: dict[str, Any], ref: Any) -> dict[str, Any] | None:
    if ref is None:
        return None
    if isinstance(ref, dict):
        return ref
    return data.get("projects", {}).get(str(ref))


def markdown_escape(value: str) -> str:
    return value.replace("|", r"\|")


def project_link(project: dict[str, Any]) -> str | None:
    links = project.get("links", {})
    if links.get("modrinth"):
        return str(links["modrinth"])
    if project.get("source") == "modrinth" and project.get("slug"):
        return f"https://modrinth.com/{project.get('type') or 'mod'}/{project['slug']}"
    if links.get("curseforge"):
        return str(links["curseforge"])
    if project.get("source") == "curseforge" and project.get("slug"):
        return f"https://www.curseforge.com/minecraft/mc-mods/{project['slug']}"
    return None


def render_project(project: dict[str, Any] | None) -> str:
    if project is None:
        return ""

    name = markdown_escape(str(project["name"]))
    link = project_link(project)
    if not link:
        return name
    return f"[{name}]({link})"


def version_project(data: dict[str, Any], row: dict[str, Any], version: str) -> dict[str, Any] | None:
    version_data = row.get("versions", {}).get(version, {})
    return project_from_ref(data, version_data.get("selected"))


def version_alternatives(data: dict[str, Any], row: dict[str, Any], version: str) -> list[dict[str, Any]]:
    version_data = row.get("versions", {}).get(version, {})
    return [
        project
        for ref in version_data.get("alternatives", [])
        if (project := project_from_ref(data, ref)) is not None
    ]


def render_header(data: dict[str, Any], language: str) -> list[str]:
    name = data["name"]
    return [
        f"# {data['title'][language]}",
        "",
        f"[English]({name}.md) | [简体中文]({name}.zh-CN.md)",
        "",
        data["introduction"][language],
        "",
    ]


def render_matrix(data: dict[str, Any], language: str) -> str:
    versions = list(data["versions"])
    lines = render_header(data, language)

    for group in data["groups"]:
        lines.extend([
            f"## {group['title'][language]}",
            "",
            group["description"][language],
            "",
        ])

        for section in group["sections"]:
            lines.extend([
                f"### {section['title'][language]}",
                "",
                section["description"][language],
                "",
            ])

            show_alternatives = any(
                version_alternatives(data, row, version)
                for row in section["rows"]
                for version in versions
            )

            if language == "zh":
                headers = ["功能", *versions]
                if show_alternatives:
                    headers.append("可选替代")
            else:
                headers = ["Feature", *versions]
                if show_alternatives:
                    headers.append("Alternatives")

            lines.append(f"| {' | '.join(headers)} |")
            lines.append(f"| {' | '.join('---' for _ in headers)} |")

            for row in section["rows"]:
                cells = [markdown_escape(str(row["feature"][language]))]

                for version in versions:
                    project = version_project(data, row, version)
                    cells.append(render_project(project))

                if show_alternatives:
                    alternatives = [
                        render_project(alternative)
                        for version in versions
                        for alternative in version_alternatives(data, row, version)
                    ]
                    cells.append(", ".join(alternatives))

                lines.append(f"| {' | '.join(cells)} |")

            lines.append("")

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines) + "\n"


def category_outputs(category: dict[str, Any], all_groups: list[dict[str, Any]]) -> dict[Path, str]:
    data = load_category_data(category, all_groups)
    return {
        DOCS_DIR / f"{category['name']}.md": render_matrix(data, "en"),
        DOCS_DIR / f"{category['name']}.zh-CN.md": render_matrix(data, "zh"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check whether generated docs are up to date without writing them.")
    args = parser.parse_args()

    all_groups = load_feature_groups()

    outputs: dict[Path, str] = {}
    for category in CATEGORIES:
        outputs.update(category_outputs(category, all_groups))

    if args.check:
        mismatches = [
            str(path.relative_to(ROOT))
            for path, text in outputs.items()
            if not path.exists() or path.read_text(encoding="utf-8-sig") != text
        ]
        if mismatches:
            details = "\n".join(f"- {path}" for path in mismatches)
            raise SystemExit(f"Generated project docs are not up to date:\n{details}")
        print("Generated project docs are up to date")
        return

    for path, text in outputs.items():
        write_text(path, text)
        print(f"Generated {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
