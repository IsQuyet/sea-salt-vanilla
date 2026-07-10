"""Shared repository paths, matrix traversal, packwiz loading, and file I/O."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, Iterator

from project_data_identity import project_refs_from_selected


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOCS_CONFIG = ROOT / "docs" / "config"
PACK = ROOT / "pack.toml"
PROJECTS_PATH = DATA / "projects.json"
OPTIONAL_PATH = DATA / "optional.json"
DEPENDENCIES_PATH = DATA / "dependencies.json"
PROJECT_CATALOG_PATH = DATA / "project-catalog.json"
MODRINTH_LOCKS_PATH = DATA / "modrinth-locks.json"

DEFAULT_PROJECT_TYPE = "mod"
PROJECT_TYPE_METADATA = [
    {
        "folder": "mods",
        "modrinth_type": "mod",
        "curseforge_path": "mc-mods",
    },
    {
        "folder": "resourcepacks",
        "modrinth_type": "resourcepack",
        "curseforge_path": "texture-packs",
    },
    {
        "folder": "shaderpacks",
        "modrinth_type": "shader",
        "curseforge_path": "shaders",
    },
    {
        "folder": "datapacks",
        "modrinth_type": "datapack",
        "curseforge_path": "data-packs",
    },
    {
        "folder": "plugins",
        "modrinth_type": "plugin",
        "curseforge_path": "bukkit-plugins",
    },
]
PROJECT_TYPE_DIRS = {
    metadata["folder"]: metadata["modrinth_type"]
    for metadata in PROJECT_TYPE_METADATA
}
PROJECT_TYPE_CURSEFORGE_PATHS = {
    metadata["modrinth_type"]: metadata["curseforge_path"]
    for metadata in PROJECT_TYPE_METADATA
}


def feature_group_order(path: Path) -> tuple[int, str]:
    try:
        group = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return (9999, path.name)
    return (int(group.get("order", 9999)), path.name)


def discover_categories() -> list[dict[str, Any]]:
    """Discover documentation categories containing a meta.json file."""
    categories: list[dict[str, Any]] = []
    if not DOCS_CONFIG.is_dir():
        return categories

    for directory in sorted(DOCS_CONFIG.iterdir()):
        if not directory.is_dir():
            continue

        meta_path = directory / "meta.json"
        if not meta_path.exists():
            continue

        matrix_directory = directory / "matrix"
        default_files = (
            sorted(matrix_directory.glob("*.json"), key=feature_group_order)
            if matrix_directory.is_dir()
            else []
        )
        optional_path = directory / "optional.json"
        categories.append(
            {
                "name": directory.name,
                "meta_path": meta_path,
                "default_files": default_files,
                "optional_file": optional_path if optional_path.exists() else None,
            }
        )
    return categories


CATEGORIES = discover_categories()
DEFAULT_FEATURE_FILES = [path for category in CATEGORIES for path in category["default_files"]]
FEATURE_GROUP_FILES = [
    *DEFAULT_FEATURE_FILES,
    *[category["optional_file"] for category in CATEGORIES if category["optional_file"]],
]


def load_target_version() -> str:
    with PACK.open("rb") as file:
        metadata = tomllib.load(file)
    return str(metadata.get("versions", {}).get("minecraft") or "1.21.1")


TARGET_VERSION = load_target_version()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("|", r"\|").replace("\n", "<br>")


def markdown_link(title: str, project_id: str | None, project_type: str | None = None) -> str:
    escaped_title = markdown_escape(title)
    if not project_id:
        return escaped_title
    return f"[{escaped_title}](https://modrinth.com/{project_type or DEFAULT_PROJECT_TYPE}/{project_id})"


def category_project_type(category_name: str | None) -> str:
    """Infer a project type from a docs/config category directory name."""
    if not category_name:
        return DEFAULT_PROJECT_TYPE
    return PROJECT_TYPE_DIRS.get(category_name, DEFAULT_PROJECT_TYPE)


def load_feature_groups() -> list[dict[str, Any]]:
    """Load every feature group, tagged with its category and optional status."""
    groups: list[dict[str, Any]] = []
    for category in CATEGORIES:
        files = [(path, False) for path in category["default_files"]]
        if category["optional_file"]:
            files.append((category["optional_file"], True))

        for path, is_optional in files:
            group = read_json(path)
            group["_source_file"] = path
            group["_category"] = category["name"]
            group["_optional"] = is_optional
            groups.append(group)
    return groups


def feature_row_version_location(
    group: dict[str, Any],
    section: dict[str, Any],
    row: dict[str, Any],
    version: str,
) -> str:
    """Return a compact human-readable docs/config row location."""
    group_id = group.get("id", "<unknown-group>")
    section_id = section.get("id", "<unknown-section>")
    row_id = row.get("id", "<unknown-row>")
    return f"{group_id}/{section_id}/{row_id} ({version})"


def selected_project_refs_from_version(
    group: dict[str, Any],
    section: dict[str, Any],
    row: dict[str, Any],
    version: str,
    version_data: dict[str, Any],
) -> list[Any]:
    """Return the selected refs for a docs/config version entry."""
    return project_refs_from_selected(
        version_data.get("selected"),
        feature_row_version_location(group, section, row, version),
    )


def iter_feature_versions(
    groups: list[dict[str, Any]] | None = None,
) -> Iterator[tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, dict[str, Any]]]:
    """Yield every docs/config version row with its surrounding context."""
    feature_groups = load_feature_groups() if groups is None else groups
    for group in feature_groups:
        for section in group.get("sections", []):
            for row in section.get("rows", []):
                for version, version_data in row.get("versions", {}).items():
                    yield group, section, row, version, version_data


def load_installed_projects() -> list[dict[str, Any]]:
    """Load packwiz project metadata from every supported project folder."""
    installed: list[dict[str, Any]] = []
    for folder, project_type in PROJECT_TYPE_DIRS.items():
        directory = ROOT / folder
        if not directory.is_dir():
            continue

        for path in sorted(directory.glob("*.pw.toml")):
            with path.open("rb") as file:
                metadata = tomllib.load(file)

            updates = metadata.get("update", {})
            modrinth = updates.get("modrinth", {})
            curseforge = updates.get("curseforge", {})
            provider_conflict = bool(modrinth and curseforge)
            source = "unknown"
            project_id = ""
            modrinth_id = ""
            modrinth_version = ""
            curseforge_file_id = ""

            if modrinth:
                source = "modrinth"
                modrinth_id = str(modrinth.get("mod-id") or "")
                modrinth_version = str(modrinth.get("version") or "")
                project_id = modrinth_id
            elif curseforge:
                source = "curseforge"
                project_id = str(curseforge.get("project-id") or "")
                curseforge_file_id = str(curseforge.get("file-id") or "")

            installed.append(
                {
                    "file": f"{folder}/{path.name}",
                    "type": project_type,
                    "slug": path.name.removesuffix(".pw.toml").lower(),
                    "name": str(metadata.get("name") or path.name.removesuffix(".pw.toml")),
                    "filename": str(metadata.get("filename") or ""),
                    "side": str(metadata.get("side") or ""),
                    "source": source,
                    "id": project_id,
                    "modrinth_id": modrinth_id,
                    "modrinth_version": modrinth_version,
                    "curseforge_file_id": curseforge_file_id,
                    "provider_conflict": provider_conflict,
                }
            )

    installed.sort(key=lambda project: (project["slug"], project["type"]))
    return installed


def load_declared_dependencies() -> dict[str, dict[str, Any]]:
    if not DEPENDENCIES_PATH.exists():
        return {}
    data = read_json(DEPENDENCIES_PATH)
    return {str(slug).lower(): value for slug, value in data.items()}


def load_project_meta() -> dict[str, dict[str, Any]]:
    if not PROJECTS_PATH.exists():
        return {}
    return read_json(PROJECTS_PATH)


def load_optional_meta() -> dict[str, dict[str, Any]]:
    if not OPTIONAL_PATH.exists():
        return {}
    return read_json(OPTIONAL_PATH)


def load_documentation_catalog() -> dict[str, dict[str, Any]]:
    """Return metadata for every project referenced by rendered documentation."""
    if not PROJECT_CATALOG_PATH.exists():
        return {}
    return read_json(PROJECT_CATALOG_PATH)


def load_modrinth_locks() -> dict[str, Any]:
    """Return the tracked locked-version graph used by offline checks."""
    if not MODRINTH_LOCKS_PATH.exists():
        return {}
    return read_json(MODRINTH_LOCKS_PATH)
