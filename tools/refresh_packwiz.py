"""Normalize LF-managed files, then refresh the packwiz index."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repository_root = get_repository_root()
    normalize_script = repository_root / "tools" / "normalize_line_endings.py"

    subprocess.run([sys.executable, str(normalize_script)], check=True, cwd=repository_root)
    subprocess.run(["packwiz", "refresh", *sys.argv[1:]], check=True, cwd=repository_root)
    return 0


def get_repository_root() -> Path:
    completed_process = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return Path(completed_process.stdout.strip())


if __name__ == "__main__":
    sys.exit(main())
