from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_DIRECTORY = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIRECTORY))

from dependencies import (  # noqa: E402
    DependencySnapshot,
    ModrinthInstallation,
    analyze_required_dependencies,
    parse_dependency_snapshot,
    validate_snapshot_against_version_facts,
    validate_snapshot_coverage,
)
from modrinth_versions import ModrinthVersionFacts  # noqa: E402


class DependencySnapshotTests(unittest.TestCase):
    def test_parser_preserves_explicit_empty_edges(self) -> None:
        snapshot = parse_dependency_snapshot(
            {
                "schema_version": 1,
                "versions": {
                    "version-a": [],
                    "version-b": ["project-c"],
                },
            }
        )

        self.assertEqual(
            snapshot.required_project_ids_by_version["version-a"],
            frozenset(),
        )
        self.assertEqual(
            snapshot.required_project_ids_by_version["version-b"],
            frozenset({"project-c"}),
        )

    def test_coverage_reports_missing_and_stale_versions(self) -> None:
        installations = [
            ModrinthInstallation("project-a", "version-a", "mods/a.pw.toml")
        ]
        snapshot = DependencySnapshot(
            required_project_ids_by_version={"version-stale": frozenset()}
        )

        issue_codes = {
            issue.code
            for issue in validate_snapshot_coverage(installations, snapshot)
        }

        self.assertEqual(
            issue_codes,
            {"missing_snapshot_version", "stale_snapshot_version"},
        )


class DependencyAnalysisTests(unittest.TestCase):
    def test_required_closure_handles_cycles(self) -> None:
        installations = [
            ModrinthInstallation("project-a", "version-a"),
            ModrinthInstallation("project-b", "version-b"),
            ModrinthInstallation("project-c", "version-c"),
        ]
        snapshot = DependencySnapshot(
            required_project_ids_by_version={
                "version-a": frozenset({"project-b"}),
                "version-b": frozenset({"project-c"}),
                "version-c": frozenset({"project-a"}),
            }
        )

        analysis = analyze_required_dependencies(
            {"project-a"},
            installations,
            snapshot,
        )

        self.assertEqual(
            analysis.reachable_project_ids,
            {"project-a", "project-b", "project-c"},
        )
        self.assertEqual(
            analysis.dependency_project_ids,
            {"project-b", "project-c"},
        )
        self.assertEqual(analysis.issues, [])

    def test_missing_required_installation_is_reported(self) -> None:
        installations = [ModrinthInstallation("project-a", "version-a")]
        snapshot = DependencySnapshot(
            required_project_ids_by_version={
                "version-a": frozenset({"project-missing"})
            }
        )

        analysis = analyze_required_dependencies(
            {"project-a"},
            installations,
            snapshot,
        )

        self.assertNotIn("project-missing", analysis.reachable_project_ids)
        self.assertTrue(analysis.issues)
        self.assertTrue(
            any("project-missing" in issue.message for issue in analysis.issues)
        )

    def test_deep_comparison_detects_edge_drift(self) -> None:
        installations = [ModrinthInstallation("project-a", "version-a")]
        snapshot = DependencySnapshot(
            required_project_ids_by_version={
                "version-a": frozenset({"project-old"})
            }
        )
        version_facts = {
            "version-a": ModrinthVersionFacts(
                project_id="project-a",
                required_project_ids=frozenset({"project-new"}),
                loaders=frozenset({"fabric"}),
            )
        }

        issues = validate_snapshot_against_version_facts(
            installations,
            snapshot,
            version_facts,
        )
        messages = "\n".join(issue.message for issue in issues)

        self.assertIn("project-old", messages)
        self.assertIn("project-new", messages)


if __name__ == "__main__":
    unittest.main()
