from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


TOOLS_DIRECTORY = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIRECTORY))

from dependencies import ModrinthInstallation  # noqa: E402
from modrinth_versions import (  # noqa: E402
    ModrinthVersionError,
    ModrinthVersionFacts,
    ModrinthVersionPool,
    parse_version_pool,
    refresh_version_pool,
)


class VersionPoolParsingTests(unittest.TestCase):
    def test_parser_rejects_duplicate_loader_values(self) -> None:
        with self.assertRaises(ModrinthVersionError):
            parse_version_pool(
                {
                    "schema_version": 1,
                    "versions": {
                        "version-a": {
                            "project_id": "project-a",
                            "loaders": ["fabric", "fabric"],
                            "required_project_ids": [],
                        }
                    },
                    "errors": {},
                }
            )


class VersionPoolRefreshTests(unittest.TestCase):
    def test_refresh_persists_fetch_errors_and_keeps_stale_facts(self) -> None:
        existing_facts = ModrinthVersionFacts(
            project_id="project-a",
            required_project_ids=frozenset(),
            loaders=frozenset({"fabric"}),
        )
        pool = ModrinthVersionPool(versions={"version-a": existing_facts})
        installations = [
            ModrinthInstallation("project-a", "version-a", "mods/a.pw.toml")
        ]

        with patch(
            "modrinth_versions.fetch_version_batch",
            side_effect=ModrinthVersionError("network unavailable"),
        ):
            refreshed_pool, outcomes = refresh_version_pool(
                installations,
                pool,
                force=True,
                dry_run=False,
            )

        self.assertEqual(refreshed_pool.versions["version-a"], existing_facts)
        self.assertEqual(
            refreshed_pool.errors["version-a"],
            "network unavailable",
        )
        self.assertEqual([outcome.status for outcome in outcomes], ["failed"])

    def test_refresh_prunes_orphan_errors(self) -> None:
        pool = ModrinthVersionPool(errors={"version-old": "old error"})

        refreshed_pool, outcomes = refresh_version_pool(
            [],
            pool,
            force=False,
            dry_run=False,
        )

        self.assertEqual(refreshed_pool.errors, {})
        self.assertEqual(outcomes, [])


if __name__ == "__main__":
    unittest.main()
