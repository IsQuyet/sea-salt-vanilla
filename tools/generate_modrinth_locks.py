#!/usr/bin/env python3
"""Generate the tracked Modrinth lock graph used by offline dependency checks."""

from __future__ import annotations

from modrinth_cache import load_dependency_cache
from modrinth_dependency_closure import build_modrinth_lock_snapshot
from project_data_common import (
    MODRINTH_LOCKS_PATH,
    load_installed_projects,
    write_json,
)


def main() -> None:
    snapshot = build_modrinth_lock_snapshot(
        load_installed_projects(),
        load_dependency_cache(),
    )
    write_json(MODRINTH_LOCKS_PATH, snapshot)
    print("Generated data\\modrinth-locks.json")


if __name__ == "__main__":
    main()
