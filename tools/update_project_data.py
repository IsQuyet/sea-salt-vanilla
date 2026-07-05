#!/usr/bin/env python3
"""Generate project data, or check repository-internal project consistency."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COMMANDS = {
    "projects": "tools/generate_project_registry.py",
    "dependencies": "tools/generate_project_dependencies.py",
    "docs": "tools/generate_project_docs.py",
}
GENERATE_STEPS = ["projects", "dependencies", "docs"]
CHECK_STEPS = ["tools/check_project_data.py", "tools/check_generated_docs.py"]


def run(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def run_step(name: str) -> None:
    args = [COMMANDS[name]]
    run(args)


def generate_all() -> None:
    for name in GENERATE_STEPS:
        run_step(name)


def check_consistency() -> None:
    for script_path in CHECK_STEPS:
        run([script_path])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="generate",
        choices=["generate", "check", *COMMANDS],
        help="Action to run. Defaults to generate. Use a step name to run only that step.",
    )
    args = parser.parse_args()

    if args.command == "generate":
        generate_all()
        return

    if args.command == "check":
        check_consistency()
        return

    run_step(args.command)


if __name__ == "__main__":
    main()
