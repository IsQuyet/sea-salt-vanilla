#!/usr/bin/env python3
"""Generate D from the locked required dependency closure of Modrinth P roots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from modrinth_cache import MissingModrinthCacheError, load_modrinth_project_cache
from modrinth_dependency_closure import (
    build_dependency_catalog,
    build_required_modrinth_closure,
)
from project_data_common import (
    DEPENDENCIES_PATH,
    load_installed_projects,
    load_modrinth_locks,
    load_optional_meta,
    load_project_meta,
)


def dependency_json_text(data: dict[str, dict[str, Any]]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def expected_dependency_catalog() -> dict[str, dict[str, Any]]:
    """Return the dependency-only catalog derived from the tracked lock graph."""
    default_projects = load_project_meta()
    optional_projects = load_optional_meta()
    closure = build_required_modrinth_closure(
        default_projects=default_projects,
        optional_projects=optional_projects,
        installed_projects=load_installed_projects(),
        lock_snapshot=load_modrinth_locks(),
    )
    dependency_catalog, issues = build_dependency_catalog(
        closure=closure,
        default_projects=default_projects,
        project_cache=load_modrinth_project_cache(),
    )
    if issues:
        raise MissingModrinthCacheError("\n".join(f"- {issue}" for issue in issues))
    return dependency_catalog


def main() -> None:
    try:
        expected_catalog = expected_dependency_catalog()
    except (MissingModrinthCacheError, ValueError) as error:
        raise SystemExit(str(error)) from error

    DEPENDENCIES_PATH.write_text(
        dependency_json_text(expected_catalog),
        encoding="utf-8",
        newline="\n",
    )
    print(f"Generated {Path('data/dependencies.json')}")


if __name__ == "__main__":
    main()
