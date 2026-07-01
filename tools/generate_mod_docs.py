#!/usr/bin/env python3
"""Generate bilingual mod documentation from structured data."""

from __future__ import annotations

import json
import tomllib
import argparse
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "mods"
ENGLISH_PATH = ROOT / "docs" / "mods.md"
CHINESE_PATH = ROOT / "docs" / "mods.zh-CN.md"
MODS_PATH = ROOT / "mods"

GROUP_FILES = [
    "core-foundation.json",
    "visual-and-audio-enhancements.json",
    "utility-features.json",
    "optional-capabilities.json",
]

STATUS_LABELS = {
    "added": {"en": "Added", "zh": "已加入"},
    "planned": {"en": "Planned", "zh": "计划加入"},
    "optional": {"en": "Optional", "zh": "可选"},
    "skipped": {"en": "Skipped", "zh": "暂不加入"},
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def load_data() -> dict[str, Any]:
    meta = read_json(DATA_DIR / "meta.json")
    projects = read_json(DATA_DIR / "projects.json")
    groups = [read_json(DATA_DIR / file_name) for file_name in GROUP_FILES]

    return {
        "versions": meta["versions"],
        "introduction": meta["introduction"],
        "projects": projects,
        "groups": groups,
    }


def load_installed_projects() -> dict[str, set[str]]:
    installed = {
        "slugs": set(),
        "names": set(),
        "modrinth_ids": set(),
    }

    if not MODS_PATH.exists():
        return installed

    for path in MODS_PATH.glob("*.pw.toml"):
        slug = path.name.removesuffix(".pw.toml")
        installed["slugs"].add(slug.lower())

        with path.open("rb") as file:
            metadata = tomllib.load(file)

        if name := metadata.get("name"):
            installed["names"].add(str(name).lower())

        modrinth = metadata.get("update", {}).get("modrinth", {})
        if mod_id := modrinth.get("mod-id"):
            installed["modrinth_ids"].add(str(mod_id))

    return installed


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
        return f"https://modrinth.com/mod/{project['slug']}"
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


def project_is_installed(project: dict[str, Any] | None, installed: dict[str, set[str]]) -> bool:
    if project is None:
        return False

    if project.get("slug") and str(project["slug"]).lower() in installed["slugs"]:
        return True
    if project.get("name") and str(project["name"]).lower() in installed["names"]:
        return True
    if project.get("modrinth_id") and str(project["modrinth_id"]) in installed["modrinth_ids"]:
        return True

    return False


def project_status(
    row: dict[str, Any],
    project: dict[str, Any] | None,
    installed: dict[str, set[str]],
    language: str,
) -> str:
    if row.get("policy") == "optional":
        return STATUS_LABELS["optional"][language]
    if row.get("policy") == "skipped":
        return STATUS_LABELS["skipped"][language]

    return STATUS_LABELS["added" if project_is_installed(project, installed) else "planned"][language]


def render_header(data: dict[str, Any], language: str) -> list[str]:
    if language == "zh":
        return [
            "# Mod 功能矩阵",
            "",
            "[English](mods.md) | [简体中文](mods.zh-CN.md)",
            "",
            data["introduction"]["zh"],
            "",
        ]

    return [
        "# Mod feature matrix",
        "",
        "[English](mods.md) | [简体中文](mods.zh-CN.md)",
        "",
        data["introduction"]["en"],
        "",
    ]


def render_matrix(data: dict[str, Any], language: str) -> str:
    installed = load_installed_projects()

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
                headers.append("整合包状态")
            else:
                headers = ["Feature", *versions]
                if show_alternatives:
                    headers.append("Alternatives")
                headers.append("Pack status")

            lines.append(f"| {' | '.join(headers)} |")
            lines.append(f"| {' | '.join('---' for _ in headers)} |")

            for row in section["rows"]:
                cells = [markdown_escape(str(row["feature"][language]))]
                status_project = None

                for version in versions:
                    project = version_project(data, row, version)
                    status_project = status_project or project
                    cells.append(render_project(project))

                if show_alternatives:
                    alternatives = [
                        render_project(alternative)
                        for version in versions
                        for alternative in version_alternatives(data, row, version)
                    ]
                    cells.append(", ".join(alternatives))

                cells.append(project_status(row, status_project, installed, language))
                lines.append(f"| {' | '.join(cells)} |")

            lines.append("")

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check whether generated docs are up to date without writing them.")
    args = parser.parse_args()

    data = load_data()

    english = render_matrix(data, "en")
    chinese = render_matrix(data, "zh")

    if args.check:
        mismatches = []
        if not ENGLISH_PATH.exists() or ENGLISH_PATH.read_text(encoding="utf-8-sig") != english:
            mismatches.append(str(ENGLISH_PATH.relative_to(ROOT)))
        if not CHINESE_PATH.exists() or CHINESE_PATH.read_text(encoding="utf-8-sig") != chinese:
            mismatches.append(str(CHINESE_PATH.relative_to(ROOT)))
        if mismatches:
            details = "\n".join(f"- {path}" for path in mismatches)
            raise SystemExit(f"Generated mod docs are not up to date:\n{details}")
        print("Generated mod docs are up to date")
        return

    write_text(ENGLISH_PATH, english)
    write_text(CHINESE_PATH, chinese)
    print("Generated docs/mods.md")
    print("Generated docs/mods.zh-CN.md")


if __name__ == "__main__":
    main()
