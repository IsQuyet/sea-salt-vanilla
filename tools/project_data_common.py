"""Shared helpers for packwiz project data tooling (mods, resource packs, shaders, ...)."""

from __future__ import annotations

import json
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator

from project_data_identity import project_ref_key, project_refs_from_selected


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
MODRINTH_CACHE = ROOT / "cache" / "modrinth"
DEPENDENCY_CACHE = MODRINTH_CACHE / "modrinth-version-dependencies.json"
PROJECT_CACHE = MODRINTH_CACHE / "modrinth-projects.json"
MANIFEST_CACHE = MODRINTH_CACHE / "manifest.json"
PROJECTS_PATH = DATA / "projects.json"
OPTIONAL_PATH = DATA / "optional.json"
DEPENDENCIES_PATH = DATA / "dependencies.json"
MODRINTH_VERSIONS_API = "https://api.modrinth.com/v2/versions"
MODRINTH_PROJECT_API = "https://api.modrinth.com/v2/project"
MODRINTH_PROJECTS_API = "https://api.modrinth.com/v2/projects"
PROJECT_CACHE_FIELDS = [
    "id",
    "slug",
    "title",
    "project_type",
    "description",
    "client_side",
    "server_side",
    "categories",
    "additional_categories",
    "loaders",
    "game_versions",
    "license",
    "icon_url",
    "color",
    "published",
    "updated",
    "approved",
    "queued",
    "status",
]


class MissingModrinthCacheError(RuntimeError):
    """Raised when offline project-data tooling needs metadata that is not cached."""


class ModrinthFetchError(RuntimeError):
    """Raised when an explicit Modrinth refresh cannot fetch required metadata."""


def is_complete_version_cache_entry(entry: Any) -> bool:
    """Return whether a cached Modrinth version entry has the fields used by checks."""
    return isinstance(entry, dict) and not cache_entry_has_error(entry) and "loaders" in entry


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


def normalize_project_ref(ref: Any, category_name: str | None = None) -> dict[str, Any] | None:
    """Normalize a docs/config project reference into a compact metadata object."""
    if ref is None:
        return None
    if isinstance(ref, dict):
        normalized = dict(ref)
        normalized.setdefault("type", category_project_type(category_name))
        return normalized
    return {
        "source": "modrinth",
        "key": str(ref).lower(),
        "slug": str(ref).lower(),
        "type": category_project_type(category_name),
    }


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
                    "filename": str(metadata.get("filename") or ""),
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
    """Return the generated project catalog from data/optional.json and data/projects.json."""
    catalog = load_optional_meta()
    catalog.update(load_project_meta())
    return catalog


def load_project_cache() -> dict[str, Any]:
    if not PROJECT_CACHE.exists():
        return empty_project_cache()
    return normalize_project_cache(read_json(PROJECT_CACHE))


def empty_project_cache() -> dict[str, Any]:
    """Return the structured project-cache shape used by current tooling."""
    return {"schema_version": 2, "projects": {}, "aliases": {}, "errors": {}}


def normalize_project_cache(cache: dict[str, Any]) -> dict[str, Any]:
    """Validate and return the structured project-cache shape used by current tooling."""
    if (
        not isinstance(cache, dict)
        or cache.get("schema_version") != 2
        or not isinstance(cache.get("projects"), dict)
        or not isinstance(cache.get("aliases"), dict)
    ):
        raise MissingModrinthCacheError(
            f"{PROJECT_CACHE} uses an unsupported format. "
            "Delete it and run python tools/refresh_modrinth_cache.py to rebuild the cache."
        )

    cache.setdefault("errors", {})
    if not isinstance(cache["errors"], dict):
        raise MissingModrinthCacheError(
            f"{PROJECT_CACHE} has an invalid errors section. "
            "Delete it and run python tools/refresh_modrinth_cache.py to rebuild the cache."
        )
    return cache


def cache_entry_has_error(entry: Any) -> bool:
    """Return whether a cached API entry represents an unresolved fetch error."""
    return isinstance(entry, dict) and "error" in entry


def collect_cache_errors(cache: dict[str, Any], cache_name: str) -> list[str]:
    """Collect unresolved cache errors for human-readable check output."""
    errors: list[str] = []
    if isinstance(cache.get("errors"), dict):
        for cache_key, entry in sorted(cache["errors"].items()):
            if cache_entry_has_error(entry):
                errors.append(f"{cache_name}:{cache_key}: {entry.get('error')}")
        return errors

    for cache_key, entry in sorted(cache.items()):
        if cache_entry_has_error(entry):
            errors.append(f"{cache_name}:{cache_key}: {entry.get('error')}")
    return errors


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

    for group, section, row, version, version_data in iter_feature_versions():
        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            version,
            version_data,
        )
        for selected_ref in selected_refs:
            remember(selected_ref, group.get("_category"))
        for alternative_ref in version_data.get("alternatives", []):
            remember(alternative_ref, group.get("_category"))

    return [refs[key] for key in sorted(refs)]


def compact_project_cache_entry(data: dict[str, Any]) -> dict[str, Any]:
    """Keep only project metadata fields used by generated data and multi-version checks."""
    compact: dict[str, Any] = {}
    for field_name in PROJECT_CACHE_FIELDS:
        value = data.get(field_name)
        if value in (None, "", [], {}):
            continue
        compact[field_name] = value
    return compact


def get_project_cache_entry(project_ref: str, cache: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve a project id or slug against the structured project cache."""
    if not project_ref:
        return None

    projects = cache.get("projects", {})
    aliases = cache.get("aliases", {})
    if not isinstance(projects, dict) or not isinstance(aliases, dict):
        return None

    if project_ref in projects and not cache_entry_has_error(projects[project_ref]):
        return projects[project_ref]
    project_id = aliases.get(project_ref)
    if project_id and project_id in projects and not cache_entry_has_error(projects[project_id]):
        return projects[project_id]
    return None


def project_cache_has_entry(project_ref: str, cache: dict[str, Any]) -> bool:
    return get_project_cache_entry(project_ref, cache) is not None


def project_cache_project_count(cache: dict[str, Any]) -> int:
    """Return the number of unique project metadata entries in a project cache."""
    projects = cache.get("projects", {})
    return len(projects) if isinstance(projects, dict) else 0


def project_cache_alias_count(cache: dict[str, Any]) -> int:
    """Return the number of alias keys in a structured project cache."""
    aliases = cache.get("aliases", {})
    return len(aliases) if isinstance(aliases, dict) else 0


def set_project_cache_error(project_ref: str, cache: dict[str, Any], error: str, *, retryable: bool) -> None:
    error_entry = {"error": error, "retryable": retryable}
    if isinstance(cache.get("errors"), dict):
        cache["errors"][project_ref] = error_entry
        return
    raise MissingModrinthCacheError(
        f"{PROJECT_CACHE} uses an unsupported format. "
        "Delete it and run python tools/refresh_modrinth_cache.py to rebuild the cache."
    )


def fetch_modrinth_project(project_ref: str, cache: dict[str, Any], *, force: bool = False) -> dict[str, Any] | None:
    if not force:
        cached = get_project_cache_entry(project_ref, cache)
        if cached:
            return cached

    request = urllib.request.Request(
        f"{MODRINTH_PROJECT_API}/{urllib.parse.quote(project_ref, safe='')}",
        headers={"User-Agent": "SeaSaltVanillaModDataTools/0.1 (local script)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            project = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        set_project_cache_error(project_ref, cache, str(error), retryable=True)
        return None

    return cache_project(project, cache, lookup_key=project_ref)


def cache_project(data: dict[str, Any], cache: dict[str, Any], *, lookup_key: str | None = None) -> dict[str, Any]:
    """Store a Modrinth project once and map slugs/lookup refs through aliases."""
    compact_project = compact_project_cache_entry(data)
    if isinstance(cache.get("projects"), dict):
        project_id = str(data.get("id") or lookup_key or "")
        if project_id:
            cache["projects"][project_id] = compact_project
            if lookup_key and lookup_key != project_id:
                cache["aliases"][lookup_key] = project_id
            if slug := data.get("slug"):
                cache["aliases"][str(slug)] = project_id
        return compact_project

    raise MissingModrinthCacheError(
        f"{PROJECT_CACHE} uses an unsupported format. "
        "Delete it and run python tools/refresh_modrinth_cache.py to rebuild the cache."
    )


def fetch_missing_modrinth_projects(project_refs: list[str], cache: dict[str, Any], *, force: bool = False) -> None:
    """Batch-fetch missing Modrinth project metadata by project id or slug."""
    missing = [
        project_ref
        for project_ref in sorted(set(project_refs))
        if project_ref
        and (
            force
            or not project_cache_has_entry(project_ref, cache)
        )
    ]
    if not missing:
        return

    for index in range(0, len(missing), 100):
        batch = missing[index : index + 100]
        query = urllib.parse.urlencode({"ids": json.dumps(batch)})
        request = urllib.request.Request(
            f"{MODRINTH_PROJECTS_API}?{query}",
            headers={"User-Agent": "SeaSaltVanillaModDataTools/0.1 (local script)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                projects = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            # A mixed batch can fail because of one bad ref. Retry individually so valid
            # projects still get cached and the final error list points to the bad refs.
            for project_ref in batch:
                fetch_modrinth_project(project_ref, cache, force=force)
            continue

        found_refs: set[str] = set()
        for project in projects:
            compact_project = cache_project(project, cache)
            if compact_project.get("id"):
                found_refs.add(str(compact_project["id"]))
            if compact_project.get("slug"):
                found_refs.add(str(compact_project["slug"]))

        for project_ref in batch:
            if project_ref not in found_refs and not project_cache_has_entry(project_ref, cache):
                set_project_cache_error(project_ref, cache, "Project not returned by Modrinth API", retryable=False)


def cache_version(data: dict[str, Any], cache: dict[str, Any]) -> None:
    version_id = str(data.get("id") or "")
    if not version_id:
        return
    cache[version_id] = {
        "id": data.get("id"),
        "project_id": data.get("project_id"),
        "version_number": data.get("version_number"),
        "loaders": data.get("loaders", []),
        "files": [file.get("filename") for file in data.get("files", []) if file.get("filename")],
        "dependencies": data.get("dependencies", []),
    }


def missing_modrinth_version_cache_ids(version_ids: list[str], cache: dict[str, Any]) -> list[str]:
    """Return Modrinth version ids that are absent or incomplete in the local cache."""
    return [
        version_id
        for version_id in sorted(set(version_ids))
        if version_id and not is_complete_version_cache_entry(cache.get(version_id))
    ]


def require_modrinth_version_cache(version_ids: list[str], cache: dict[str, Any]) -> None:
    """Fail clearly when an offline check needs uncached Modrinth version metadata."""
    missing = missing_modrinth_version_cache_ids(version_ids, cache)
    if not missing:
        return

    preview = ", ".join(missing[:10])
    if len(missing) > 10:
        preview += f", ... ({len(missing)} total)"
    raise MissingModrinthCacheError(
        "Missing Modrinth version cache entries required for offline project-data checks: "
        f"{preview}. Run python tools/refresh_modrinth_cache.py before running check."
    )


def fetch_missing_modrinth_versions(version_ids: list[str], cache: dict[str, Any], *, force: bool = False) -> None:
    missing = [
        version_id
        for version_id in sorted(set(version_ids))
        if version_id
        and (force or not is_complete_version_cache_entry(cache.get(version_id)))
    ]
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
                cache[version_id] = {"error": str(error), "retryable": True}
            continue

        found_ids = set()
        for version in versions:
            cache_version(version, cache)
            if version.get("id"):
                found_ids.add(str(version["id"]))

        for version_id in batch:
            if version_id not in found_ids and version_id not in cache:
                cache[version_id] = {"error": "Version not returned by Modrinth API", "retryable": False}


def build_required_by(
    installed: list[dict[str, Any]],
    cache: dict[str, Any],
    *,
    allow_network: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    installed_ids = {mod["modrinth_id"] for mod in installed if mod["modrinth_id"]}
    required_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    version_ids = [mod["modrinth_version"] for mod in installed]
    if allow_network:
        fetch_missing_modrinth_versions(version_ids, cache)
    else:
        require_modrinth_version_cache(version_ids, cache)

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
    *,
    allow_network: bool = True,
) -> dict[str, dict[str, Any]]:
    """Collect required Modrinth dependencies that are not installed in any project folder."""
    installed_ids = {project["modrinth_id"] for project in installed if project["modrinth_id"]}
    version_ids = [project["modrinth_version"] for project in installed]
    if allow_network:
        fetch_missing_modrinth_versions(version_ids, cache)
    else:
        require_modrinth_version_cache(version_ids, cache)

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
        if allow_network:
            dependency_project = fetch_modrinth_project(project_id, project_cache)
        else:
            dependency_project = project_cache.get(project_id)

        missing_offline_project = not isinstance(dependency_project, dict) or cache_entry_has_error(
            dependency_project
        )
        if not allow_network and missing_offline_project:
            raise MissingModrinthCacheError(
                "Missing Modrinth project cache entry required for offline project-data checks: "
                f"{project_id}. Run python tools/refresh_modrinth_cache.py before running check."
            )
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

    for group, section, row, version, version_data in iter_feature_versions():
        selected_refs = selected_project_refs_from_version(
            group,
            section,
            row,
            version,
            version_data,
        )
        for selected_ref in selected_refs:
            remember_ref(selected_ref)
        for alternative_ref in version_data.get("alternatives", []):
            remember_ref(alternative_ref)

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
