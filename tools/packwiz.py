"""Repository paths, packwiz facts, JSON I/O, and index maintenance."""

from __future__ import annotations

import json
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOCS_CONFIG = ROOT / "docs" / "config"
DOCS = ROOT / "docs"
PACK = ROOT / "pack.toml"
PROJECT_METADATA_PATH = DATA / "project-metadata.json"
DEPENDENCY_SNAPSHOT_PATH = DATA / "modrinth-dependencies.json"
MODRINTH_VERSION_POOL_PATH = ROOT / "cache" / "modrinth" / "versions.json"

RESOURCE_TYPES = ("mod", "resourcepack", "shader", "datapack", "plugin")
RESOURCE_TYPE_DETAILS = (
    {
        "resource_type": "mod",
        "folder": "mods",
        "curseforge_path": "mc-mods",
        "display_name": "Mods",
    },
    {
        "resource_type": "resourcepack",
        "folder": "resourcepacks",
        "curseforge_path": "texture-packs",
        "display_name": "Resource packs",
    },
    {
        "resource_type": "shader",
        "folder": "shaderpacks",
        "curseforge_path": "shaders",
        "display_name": "Shaders",
    },
    {
        "resource_type": "datapack",
        "folder": "datapacks",
        "curseforge_path": "data-packs",
        "display_name": "Data packs",
    },
    {
        "resource_type": "plugin",
        "folder": "plugins",
        "curseforge_path": "bukkit-plugins",
        "display_name": "Plugins",
    },
)
RESOURCE_TYPE_BY_FOLDER = {
    details["folder"]: details["resource_type"]
    for details in RESOURCE_TYPE_DETAILS
}
CURSEFORGE_PATH_BY_RESOURCE_TYPE = {
    details["resource_type"]: details["curseforge_path"]
    for details in RESOURCE_TYPE_DETAILS
}
RESOURCE_TYPE_DISPLAY_NAMES = {
    details["resource_type"]: details["display_name"]
    for details in RESOURCE_TYPE_DETAILS
}


@dataclass(frozen=True)
class InstalledProject:
    """One installed packwiz project with provider lock facts."""

    provider: str
    project_id: str
    resource_type: str
    file: str
    name: str
    local_slug: str
    filename: str = ""
    side: str = ""
    version_id: str = ""
    file_id: str = ""
    provider_conflict: bool = False

    @property
    def identity(self) -> str:
        if not self.provider or not self.project_id:
            return ""
        return f"{self.provider}:{self.project_id}"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def write_text_if_changed(path: Path, text: str) -> str:
    """Write deterministic text and report created, updated, or unchanged."""
    existing_text = path.read_text(encoding="utf-8-sig") if path.exists() else None
    if existing_text == text:
        return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return "updated" if existing_text is not None else "created"


def write_json_if_changed(path: Path, data: Any) -> str:
    return write_text_if_changed(path, json_text(data))


def load_pack_metadata() -> dict[str, Any]:
    with PACK.open("rb") as metadata_file:
        return tomllib.load(metadata_file)


def target_minecraft_version() -> str:
    versions = load_pack_metadata().get("versions")
    if not isinstance(versions, dict):
        raise ValueError("pack.toml must contain a versions table.")
    target_version = versions.get("minecraft")
    if not isinstance(target_version, str) or not target_version.strip():
        raise ValueError("pack.toml must declare one non-empty Minecraft version.")
    return target_version.strip()


def pack_name() -> str:
    return str(load_pack_metadata().get("name") or "Sea Salt Vanilla")


def pack_version() -> str:
    return str(load_pack_metadata().get("version") or "")


def feature_group_order(path: Path) -> tuple[int, str]:
    try:
        group = read_json(path)
        order = int(group.get("order", 9999))
    except (OSError, json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return (9999, path.name)
    return (order, path.name)


def discover_categories() -> list[dict[str, Any]]:
    """Discover documentation categories and their hand-maintained sources."""
    categories: list[dict[str, Any]] = []
    if not DOCS_CONFIG.is_dir():
        return categories

    for category_directory in sorted(DOCS_CONFIG.iterdir()):
        if not category_directory.is_dir():
            continue
        meta_path = category_directory / "meta.json"
        if not meta_path.exists():
            continue

        matrix_directory = category_directory / "matrix"
        matrix_paths = (
            sorted(matrix_directory.glob("*.json"), key=feature_group_order)
            if matrix_directory.is_dir()
            else []
        )
        optional_path = category_directory / "optional.json"
        resource_type = RESOURCE_TYPE_BY_FOLDER.get(category_directory.name)
        if not resource_type:
            raise ValueError(
                f"Unsupported documentation category: {category_directory.name}"
            )
        categories.append(
            {
                "name": category_directory.name,
                "resource_type": resource_type,
                "meta_path": meta_path,
                "matrix_paths": matrix_paths,
                "optional_path": optional_path if optional_path.exists() else None,
            }
        )
    return categories


def load_installed_projects() -> list[InstalledProject]:
    """Read provider identities and locks from supported packwiz folders."""
    installed_projects: list[InstalledProject] = []

    for folder, resource_type in RESOURCE_TYPE_BY_FOLDER.items():
        project_directory = ROOT / folder
        if not project_directory.is_dir():
            continue

        for metadata_path in sorted(project_directory.glob("*.pw.toml")):
            with metadata_path.open("rb") as metadata_file:
                metadata = tomllib.load(metadata_file)

            update_metadata = metadata.get("update", {})
            if not isinstance(update_metadata, dict):
                raise ValueError(f"{metadata_path} update must be a TOML table.")
            modrinth_metadata = update_metadata.get("modrinth", {})
            curseforge_metadata = update_metadata.get("curseforge", {})
            if not isinstance(modrinth_metadata, dict) or not isinstance(
                curseforge_metadata,
                dict,
            ):
                raise ValueError(
                    f"{metadata_path} provider updates must be TOML tables."
                )
            provider_conflict = bool(modrinth_metadata and curseforge_metadata)

            provider = ""
            project_id = ""
            version_id = ""
            file_id = ""
            if modrinth_metadata:
                provider = "modrinth"
                project_id = str(modrinth_metadata.get("mod-id") or "")
                version_id = str(modrinth_metadata.get("version") or "")
            elif curseforge_metadata:
                provider = "curseforge"
                project_id = str(curseforge_metadata.get("project-id") or "")
                file_id = str(curseforge_metadata.get("file-id") or "")

            local_slug = metadata_path.name.removesuffix(".pw.toml").lower()
            installed_projects.append(
                InstalledProject(
                    provider=provider,
                    project_id=project_id,
                    resource_type=resource_type,
                    file=f"{folder}/{metadata_path.name}",
                    name=str(metadata.get("name") or local_slug),
                    local_slug=local_slug,
                    filename=str(metadata.get("filename") or ""),
                    side=str(metadata.get("side") or ""),
                    version_id=version_id,
                    file_id=file_id,
                    provider_conflict=provider_conflict,
                )
            )

    installed_projects.sort(
        key=lambda project: (project.resource_type, project.local_slug)
    )
    return installed_projects


def git_repository_root() -> Path:
    completed_process = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        text=True,
    )
    return Path(completed_process.stdout.strip())


def tracked_paths(repository_root: Path) -> list[Path]:
    completed_process = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        cwd=repository_root,
        stdout=subprocess.PIPE,
    )
    return [
        Path(encoded_path.decode("utf-8"))
        for encoded_path in completed_process.stdout.split(b"\0")
        if encoded_path
    ]


def lf_managed_paths(
    repository_root: Path,
    repository_paths: Iterable[Path],
) -> list[Path]:
    normalized_paths = list(repository_paths)
    if not normalized_paths:
        return []

    stdin_bytes = (
        b"\0".join(path.as_posix().encode("utf-8") for path in normalized_paths)
        + b"\0"
    )
    completed_process = subprocess.run(
        ["git", "check-attr", "-z", "eol", "--stdin"],
        check=True,
        cwd=repository_root,
        input=stdin_bytes,
        stdout=subprocess.PIPE,
    )

    output_parts = completed_process.stdout.split(b"\0")
    managed_paths: list[Path] = []
    for part_index in range(0, len(output_parts) - 2, 3):
        relative_path = Path(output_parts[part_index].decode("utf-8"))
        attribute_value = output_parts[part_index + 2].decode("utf-8")
        if attribute_value == "lf":
            managed_paths.append(relative_path)
    return managed_paths


def normalize_line_endings(*, check: bool) -> list[Path]:
    """Normalize tracked LF-managed files or report those needing changes."""
    repository_root = git_repository_root()
    changed_paths: list[Path] = []
    for relative_path in lf_managed_paths(
        repository_root,
        tracked_paths(repository_root),
    ):
        absolute_path = repository_root / relative_path
        if not absolute_path.is_file():
            continue
        original_bytes = absolute_path.read_bytes()
        normalized_bytes = original_bytes.replace(b"\r\n", b"\n").replace(
            b"\r",
            b"\n",
        )
        if normalized_bytes == original_bytes:
            continue
        changed_paths.append(relative_path)
        if not check:
            absolute_path.write_bytes(normalized_bytes)
    return changed_paths


def refresh_index(
    packwiz_arguments: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Normalize LF-managed files and refresh packwiz metadata."""
    normalize_line_endings(check=False)
    return subprocess.run(
        ["packwiz", "refresh", *(packwiz_arguments or [])],
        check=True,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
