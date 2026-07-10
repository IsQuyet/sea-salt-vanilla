#!/usr/bin/env python3
"""Check generated Markdown documentation without writing files."""

from __future__ import annotations

from generate_project_docs import ROOT, category_outputs
from project_data_common import (
    CATEGORIES,
    load_documentation_catalog,
    load_feature_groups,
)


def main() -> None:
    all_groups = load_feature_groups()
    project_catalog = load_documentation_catalog()

    mismatched_paths: list[str] = []
    for category in CATEGORIES:
        expected_outputs = category_outputs(category, all_groups, project_catalog)
        for path, expected_text in expected_outputs.items():
            current_text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
            if current_text != expected_text:
                mismatched_paths.append(str(path.relative_to(ROOT)))

    if mismatched_paths:
        details = "\n".join(f"- {path}" for path in mismatched_paths)
        raise SystemExit(
            "Generated Markdown docs do not match the docs generator output. "
            "Run python tools/update_project_data.py docs, review the diff, and commit the generated files.\n"
            f"{details}"
        )

    print("Generated Markdown docs match the docs generator output")


if __name__ == "__main__":
    main()
