#!/usr/bin/env python3
"""Update or check generated mod data and documentation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check generated mod data without writing tracked files.")
    args = parser.parse_args()

    if args.check:
        run(["tools/generate_mod_dependencies.py", "--check"])
        run(["tools/generate_mod_docs.py", "--check"])
        run(["tools/check_mod_data.py", "--check"])
        return

    run(["tools/generate_mod_dependencies.py"])
    run(["tools/generate_mod_docs.py"])
    run(["tools/check_mod_data.py"])


if __name__ == "__main__":
    main()
