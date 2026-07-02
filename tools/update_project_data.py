#!/usr/bin/env python3
"""Update or check generated project data and documentation."""

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
    "report": "tools/check_project_data.py",
}


def run(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def run_step(name: str, *, check: bool = False) -> None:
    args = [COMMANDS[name]]
    if check:
        args.append("--check")
    run(args)


def run_all(*, check: bool = False) -> None:
    for name in ["projects", "dependencies", "docs", "report"]:
        run_step(name, check=check)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="generate",
        choices=["generate", "check", *COMMANDS],
        help="Action to run. Defaults to generate. Use a step name to run only that step.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check instead of writing. With no step, this is the same as the check command.",
    )
    args = parser.parse_args()

    if args.command == "generate":
        run_all(check=args.check)
        return

    if args.command == "check":
        run_all(check=True)
        return

    run_step(args.command, check=args.check)


if __name__ == "__main__":
    main()
