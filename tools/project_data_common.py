"""Shared helpers for packwiz mod data tooling."""

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
DATA = ROOT / "data" / "mods"
MATRIX = DATA / "matrix"
GENERATED = DATA / "generated"
MODS = ROOT / "mods"
PACK = ROOT / "pack.toml"
CACHE = ROOT / "reference" / "modrinth-collections"
DEPENDENCY_CACHE = CACHE / "modrinth-version-dependencies.json"
PROJECT_CACHE = CACHE / "modrinth-projects.json"
PROJECTS_PATH = GENERATED / "projects.json"
DEPENDENCIES_PATH = GENERATED / "dependencies.json"
MODRINTH_VERSIONS_API = "https://api.modrinth.com/v2/versions"
MODRINTH_PROJECT_API = "https://api.modrinth.com/v2/project"
OPTIONAL_FEATURE_FILE = DATA / "optional.json"


def feature_group_order(path: Path) -> tuple[int, str]:
    try:
        group = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return (9999, path.name)
    return (int(group.get("order", 9999)), path.name)


def load_default_feature_files() -> list[Path]:
    return sorted(MATRIX.glob("*.json"), key=feature_group_order)


DEFAULT_FEATURE_FILES = load_default_feature_files()
FEATURE_GROUP_FILES = [*DEFAULT_FEATURE_FILES, OPTIONAL_FEATURE_FILE]


def load_target_version() -> str:
    with PACK.open("rb") as file:
        metadata = tomllib.load(file)
    return str(metadata.get("versions", {}).get("minecraft") or "1.21.1")


TARGET_VERSION = load_target_version()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("|", r"\|").replace("\n", "<br>")


def markdown_link(title: str, project_id: str | None) -> str:
    escaped = markdown_escape(title)
    if not project_id:
        return escaped
    return f"[{escaped}](https://modrinth.com/mod/{project_id})"


def load_installed_mods() -> list[dict[str, Any]]:
    installed: list[dict[str, Any]] = []
    for path in sorted(MODS.glob("*.pw.toml")):
        with path.open("rb") as file:
            metadata = tomllib.load(file)

        modrinth = metadata.get("update", {}).get("modrinth", {})
        installed.append(
            {
                "file": path.name,
                "slug": path.name.removesuffix(".pw.toml").lower(),
                "name": str(metadata.get("name") or path.name.removesuffix(".pw.toml")),
                "side": str(metadata.get("side") or ""),
                "modrinth_id": str(modrinth.get("mod-id") or ""),
                "modrinth_version": str(modrinth.get("version") or ""),
            }
        )
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


def load_project_cache() -> dict[str, Any]:
    if not PROJECT_CACHE.exists():
        return {}
    return read_json(PROJECT_CACHE)


def collect_matrix_project_refs() -> list[str]:
    refs: set[str] = set()

    def remember(ref: Any) -> None:
        if ref is None or isinstance(ref, dict):
            return
        refs.add(str(ref))

    for file_name in FEATURE_GROUP_FILES:
        group = read_json(file_name)
        for section in group.get("sections", []):
            for row in section.get("rows", []):
                for version_data in row.get("versions", {}).values():
                    remember(version_data.get("selected"))
                    for ref in version_data.get("alternatives", []):
                        remember(ref)

    return sorted(refs)


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


def build_documented_sets(project_meta: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    documented = {"refs": set(), "slugs": set(), "names": set(), "ids": set()}

    def remember_ref(ref: Any) -> None:
        if not ref:
            return
        if isinstance(ref, dict):
            if slug := ref.get("slug"):
                documented["slugs"].add(str(slug).lower())
            if name := ref.get("name"):
                documented["names"].add(str(name).lower())
            if modrinth_id := ref.get("modrinth_id"):
                documented["ids"].add(str(modrinth_id))
            return

        key = str(ref)
        documented["refs"].add(key.lower())
        project = project_meta.get(key)
        if not project:
            return
        if slug := project.get("slug"):
            documented["slugs"].add(str(slug).lower())
        if name := project.get("name"):
            documented["names"].add(str(name).lower())
        if modrinth_id := project.get("modrinth_id"):
            documented["ids"].add(str(modrinth_id))

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
    return (
        mod["slug"] in documented["refs"]
        or mod["slug"] in documented["slugs"]
        or mod["name"].lower() in documented["names"]
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
            "source": "modrinth" if mod["modrinth_id"] else "unknown",
            "name": mod["name"],
            "modrinth_id": mod["modrinth_id"],
            "required_by": sorted({dependent["slug"] for dependent in dependents}),
        }
    return dict(sorted(entries.items()))
