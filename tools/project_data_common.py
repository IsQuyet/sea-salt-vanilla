"""Shared helpers for packwiz project data tooling (mods, resource packs, shaders, ...)."""

from __future__ import annotations

import json
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOCS_CONFIG = ROOT / "docs" / "config"
# packwiz folder name -> Modrinth project_type
PROJECT_TYPE_DIRS = {
    "mods": "mod",
    "resourcepacks": "resourcepack",
    "shaderpacks": "shader",
    "datapacks": "datapack",
    "plugins": "plugin",
}
PROJECT_TYPE_CURSEFORGE_PATHS = {
    "mod": "mc-mods",
    "resourcepack": "texture-packs",
    "shader": "customization",
    "datapack": "data-packs",
    "plugin": "bukkit-plugins",
}
DEFAULT_PROJECT_TYPE = "mod"
PACK = ROOT / "pack.toml"
CACHE = ROOT / "reference" / "modrinth-collections"
DEPENDENCY_CACHE = CACHE / "modrinth-version-dependencies.json"
PROJECT_CACHE = CACHE / "modrinth-projects.json"
PROJECTS_PATH = DATA / "projects.json"
OPTIONAL_PATH = DATA / "optional.json"
DEPENDENCIES_PATH = DATA / "dependencies.json"
MODRINTH_VERSIONS_API = "https://api.modrinth.com/v2/versions"
MODRINTH_PROJECT_API = "https://api.modrinth.com/v2/project"


def feature_group_order(path: Path) -> tuple[int, str]:
    try:
        group = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return (9999, path.name)
    return (int(group.get("order", 9999)), path.name)


def discover_categories() -> list[dict[str, Any]]:
    """Each documentation category is a subdirectory of DOCS_CONFIG holding a meta.json."""
    categories: list[dict[str, Any]] = []
    if not DOCS_CONFIG.is_dir():
        return categories
    for directory in sorted(DOCS_CONFIG.iterdir()):
        if not directory.is_dir():
            continue
        meta_path = directory / "meta.json"
        if not meta_path.exists():
            continue
        matrix_dir = directory / "matrix"
        default_files = (
            sorted(matrix_dir.glob("*.json"), key=feature_group_order) if matrix_dir.is_dir() else []
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


def load_feature_groups() -> list[dict[str, Any]]:
    """Load every feature group across categories, tagged with its category and optional flag."""
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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("|", r"\|").replace("\n", "<br>")


def markdown_link(title: str, project_id: str | None, project_type: str | None = None) -> str:
    escaped = markdown_escape(title)
    if not project_id:
        return escaped
    return f"[{escaped}](https://modrinth.com/{project_type or DEFAULT_PROJECT_TYPE}/{project_id})"


def category_project_type(category_name: str | None) -> str:
    """Infer a project type from a docs/config category directory name."""
    if not category_name:
        return DEFAULT_PROJECT_TYPE
    return PROJECT_TYPE_DIRS.get(category_name, DEFAULT_PROJECT_TYPE)


def project_ref_key(ref: Any) -> str | None:
    """Return the registry key used for a string or compact object project reference."""
    if ref is None:
        return None
    if isinstance(ref, dict):
        for key in ["key", "slug", "id", "name"]:
            if value := ref.get(key):
                return str(value).lower()
        return None
    return str(ref).lower()


def normalize_project_ref(ref: Any, category_name: str | None = None) -> dict[str, Any] | None:
    """Normalize a docs/config project reference into a compact metadata object."""
    if ref is None:
        return None
    if isinstance(ref, dict):
        normalized = dict(ref)
        normalized.setdefault("type", category_project_type(category_name))
        return normalized
    return {"key": str(ref).lower(), "slug": str(ref).lower(), "type": category_project_type(category_name)}


def load_installed_projects() -> list[dict[str, Any]]:
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
                    "side": str(metadata.get("side") or ""),
                    "source": source,
                    "id": project_id,
                    "modrinth_id": modrinth_id,
                    "modrinth_version": modrinth_version,
                    "curseforge_file_id": curseforge_file_id,
                }
            )
    installed.sort(key=lambda project: (project["slug"], project["type"]))
    return installed


def load_dependency_cache() -> dict[str, Any]:
    if not DEPENDENCY_CACHE.exists():
        return {}
    return read_json(DEPENDENCY_CACHE)


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


def load_project_catalog() -> dict[str, dict[str, Any]]:
    """Return all projects declared by docs config, with defaults overriding optional entries."""
    catalog = load_optional_meta()
    catalog.update(load_project_meta())
    return catalog


def load_project_cache() -> dict[str, Any]:
    if not PROJECT_CACHE.exists():
        return {}
    return read_json(PROJECT_CACHE)


def collect_matrix_project_refs() -> list[dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}

    def remember(ref: Any, category_name: str | None) -> None:
        normalized = normalize_project_ref(ref, category_name)
        if not normalized:
            return
        key = project_ref_key(normalized)
        if not key:
            return
        refs.setdefault(key, normalized)

    for group in load_feature_groups():
        for section in group.get("sections", []):
            for row in section.get("rows", []):
                for version_data in row.get("versions", {}).values():
                    remember(version_data.get("selected"), group.get("_category"))
                    for ref in version_data.get("alternatives", []):
                        remember(ref, group.get("_category"))

    return [refs[key] for key in sorted(refs)]


def fetch_modrinth_project(project_ref: str, cache: dict[str, Any]) -> dict[str, Any] | None:
    if project_ref in cache:
        cached = cache[project_ref]
        return cached if isinstance(cached, dict) and "error" not in cached else None

    request = urllib.request.Request(
        f"{MODRINTH_PROJECT_API}/{urllib.parse.quote(project_ref, safe='')}",
        headers={"User-Agent": "SeaSaltVanillaModDataTools/0.1 (local script)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            project = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        cache[project_ref] = {"error": str(error)}
        return None

    cache[project_ref] = project
    if project.get("id"):
        cache[str(project["id"])] = project
    if project.get("slug"):
        cache[str(project["slug"])] = project
    return project


def cache_version(data: dict[str, Any], cache: dict[str, Any]) -> None:
    version_id = str(data.get("id") or "")
    if not version_id:
        return
    cache[version_id] = {
        "id": data.get("id"),
        "project_id": data.get("project_id"),
        "version_number": data.get("version_number"),
        "dependencies": data.get("dependencies", []),
    }


def fetch_missing_modrinth_versions(version_ids: list[str], cache: dict[str, Any]) -> None:
    missing = [version_id for version_id in sorted(set(version_ids)) if version_id and version_id not in cache]
    if not missing:
        return

    for index in range(0, len(missing), 50):
        batch = missing[index : index + 50]
        query = urllib.parse.urlencode({"ids": json.dumps(batch)})
        request = urllib.request.Request(
            f"{MODRINTH_VERSIONS_API}?{query}",
            headers={"User-Agent": "SeaSaltVanillaModDataTools/0.1 (local script)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                versions = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            for version_id in batch:
                cache[version_id] = {"error": str(error), "dependencies": []}
            continue

        found_ids = set()
        for version in versions:
            cache_version(version, cache)
            if version.get("id"):
                found_ids.add(str(version["id"]))

        for version_id in batch:
            if version_id not in found_ids and version_id not in cache:
                cache[version_id] = {"error": "Version not returned by Modrinth API", "dependencies": []}


def build_required_by(installed: list[dict[str, Any]], cache: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    installed_ids = {mod["modrinth_id"] for mod in installed if mod["modrinth_id"]}
    required_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    fetch_missing_modrinth_versions([mod["modrinth_version"] for mod in installed], cache)

    for mod in installed:
        version_data = cache.get(mod["modrinth_version"])
        if not version_data:
            continue
        for dependency in version_data.get("dependencies", []):
            if dependency.get("dependency_type") != "required":
                continue
            project_id = str(dependency.get("project_id") or "")
            if project_id and project_id in installed_ids:
                required_by[project_id].append(mod)

    return required_by


def build_missing_required(
    installed: list[dict[str, Any]],
    cache: dict[str, Any],
    project_cache: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Collect required Modrinth dependencies that are not installed in any project folder."""
    installed_ids = {project["modrinth_id"] for project in installed if project["modrinth_id"]}
    fetch_missing_modrinth_versions([project["modrinth_version"] for project in installed], cache)

    dependents_by_id: dict[str, set[str]] = defaultdict(set)
    for project in installed:
        version_data = cache.get(project["modrinth_version"])
        if not version_data:
            continue
        for dependency in version_data.get("dependencies", []):
            if dependency.get("dependency_type") != "required":
                continue
            project_id = str(dependency.get("project_id") or "")
            if project_id and project_id not in installed_ids:
                dependents_by_id[project_id].add(project["slug"])

    missing: dict[str, dict[str, Any]] = {}
    for project_id, dependents in sorted(dependents_by_id.items()):
        dependency_project = fetch_modrinth_project(project_id, project_cache)
        missing[project_id] = {
            "name": str((dependency_project or {}).get("title") or project_id),
            "type": str((dependency_project or {}).get("project_type") or ""),
            "slug": str((dependency_project or {}).get("slug") or ""),
            "required_by": sorted(dependents),
        }
    return missing


def build_documented_sets(project_meta: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    documented = {"refs": set(), "slugs": set(), "names": set(), "ids": set(), "source_ids": set()}

    def remember_project(project: dict[str, Any]) -> None:
        if slug := project.get("slug"):
            documented["slugs"].add(str(slug).lower())
        if name := project.get("name"):
            documented["names"].add(str(name).lower())
        if project_id := project.get("id"):
            documented["ids"].add(str(project_id))
            if source := project.get("source"):
                documented["source_ids"].add(f"{source}:{project_id}")
        if modrinth_id := project.get("modrinth_id"):
            documented["ids"].add(str(modrinth_id))

    def remember_ref(ref: Any) -> None:
        if not ref:
            return
        if isinstance(ref, dict):
            remember_project(ref)
            key = project_ref_key(ref)
            if key and (project := project_meta.get(key)):
                remember_project(project)
            return

        key = str(ref)
        documented["refs"].add(key.lower())
        project = project_meta.get(key)
        if not project:
            return
        remember_project(project)

    def walk_rows(value: Any) -> None:
        if isinstance(value, dict):
            if "versions" in value:
                for version_data in value.get("versions", {}).values():
                    remember_ref(version_data.get("selected"))
                    for ref in version_data.get("alternatives", []):
                        remember_ref(ref)
            for child in value.values():
                walk_rows(child)
        elif isinstance(value, list):
            for child in value:
                walk_rows(child)

    for file_name in FEATURE_GROUP_FILES:
        walk_rows(read_json(file_name))

    return documented


def is_documented(mod: dict[str, Any], documented: dict[str, set[str]]) -> bool:
    source_id = f"{mod.get('source')}:{mod.get('id')}" if mod.get("source") and mod.get("id") else ""
    return (
        mod["slug"] in documented["refs"]
        or mod["slug"] in documented["slugs"]
        or mod["name"].lower() in documented["names"]
        or (source_id and source_id in documented["source_ids"])
        or (mod.get("id") and str(mod["id"]) in documented["ids"])
        or (mod["modrinth_id"] and mod["modrinth_id"] in documented["ids"])
    )


def required_by_names(project_id: str, required_by: dict[str, list[dict[str, Any]]]) -> str:
    names = sorted({mod["name"] for mod in required_by.get(project_id, [])})
    return ", ".join(names)


def expected_dependency_data(
    installed: list[dict[str, Any]],
    documented: dict[str, set[str]],
    required_by: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for mod in installed:
        if is_documented(mod, documented):
            continue
        dependents = required_by.get(mod["modrinth_id"], [])
        if not dependents:
            continue
        entries[mod["slug"]] = {
            "name": mod["name"],
            "type": mod["type"],
            "source": mod.get("source") or "unknown",
            "slug": mod["slug"],
            "id": mod.get("id") or mod["modrinth_id"],
            "required_by": sorted({dependent["slug"] for dependent in dependents}),
        }
    return dict(sorted(entries.items()))
