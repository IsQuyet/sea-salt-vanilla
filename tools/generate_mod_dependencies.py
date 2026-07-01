#!/usr/bin/env python3
"""Generate dependency-only mod data from packwiz and Modrinth metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mod_data_common import (
    DATA,
    DEPENDENCY_CACHE,
    build_documented_sets,
    build_required_by,
    expected_dependency_data,
    load_dependency_cache,
    load_installed_mods,
    read_json,
    write_json,
)


DEPENDENCIES_PATH = DATA / "dependencies.json"


def dependency_json_text(data: dict[str, dict[str, Any]]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load_expected_dependencies() -> dict[str, dict[str, Any]]:
    installed = load_installed_mods()
    project_meta: dict[str, dict[str, Any]] = read_json(DATA / "projects.json")
    documented = build_documented_sets(project_meta)
    dependency_cache = load_dependency_cache()
    required_by = build_required_by(installed, dependency_cache)
    write_json(DEPENDENCY_CACHE, dependency_cache)
    return expected_dependency_data(installed, documented, required_by)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check whether dependencies.json is up to date without writing it.")
    args = parser.parse_args()

    expected = load_expected_dependencies()
    expected_text = dependency_json_text(expected)

    if args.check:
        current_text = ""
        if DEPENDENCIES_PATH.exists():
            current_text = DEPENDENCIES_PATH.read_text(encoding="utf-8-sig")
        if current_text != expected_text:
            raise SystemExit("data/mods/dependencies.json is not up to date. Run python tools/generate_mod_dependencies.py")
        print("data/mods/dependencies.json is up to date")
        return

    DEPENDENCIES_PATH.write_text(expected_text, encoding="utf-8", newline="\n")
    print(f"Generated {Path('data/mods/dependencies.json')}")


if __name__ == "__main__":
    main()
