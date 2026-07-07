"""Normalize tracked LF-managed text files in the working tree."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize tracked files with eol=lf to LF line endings.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report files that need normalization without writing changes.",
    )
    args = parser.parse_args()

    repository_root = get_repository_root()
    tracked_paths = get_tracked_paths(repository_root)
    lf_managed_paths = get_lf_managed_paths(repository_root, tracked_paths)

    changed_paths = []
    for relative_path in lf_managed_paths:
        absolute_path = repository_root / relative_path
        if not absolute_path.is_file():
            continue

        original_bytes = absolute_path.read_bytes()
        normalized_bytes = original_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if normalized_bytes == original_bytes:
            continue

        changed_paths.append(relative_path)
        if not args.check:
            absolute_path.write_bytes(normalized_bytes)

    if changed_paths:
        action = "Need normalization" if args.check else "Normalized"
        for relative_path in changed_paths:
            print(f"{action}: {relative_path.as_posix()}")
        return 1 if args.check else 0

    return 0


def get_repository_root() -> Path:
    completed_process = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return Path(completed_process.stdout.strip())


def get_tracked_paths(repository_root: Path) -> list[Path]:
    completed_process = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        cwd=repository_root,
        stdout=subprocess.PIPE,
    )
    return [Path(path.decode("utf-8")) for path in completed_process.stdout.split(b"\0") if path]


def get_lf_managed_paths(repository_root: Path, tracked_paths: list[Path]) -> list[Path]:
    if not tracked_paths:
        return []

    stdin_bytes = b"\0".join(path.as_posix().encode("utf-8") for path in tracked_paths) + b"\0"
    completed_process = subprocess.run(
        ["git", "check-attr", "-z", "eol", "--stdin"],
        check=True,
        cwd=repository_root,
        input=stdin_bytes,
        stdout=subprocess.PIPE,
    )

    output_parts = completed_process.stdout.split(b"\0")
    lf_managed_paths = []
    for part_index in range(0, len(output_parts) - 2, 3):
        relative_path = output_parts[part_index].decode("utf-8")
        attribute_value = output_parts[part_index + 2].decode("utf-8")
        if attribute_value == "lf":
            lf_managed_paths.append(Path(relative_path))

    return lf_managed_paths


if __name__ == "__main__":
    sys.exit(main())
