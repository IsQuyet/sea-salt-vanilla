from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_DIRECTORY = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIRECTORY))

from dependencies import DependencyAnalysis, DependencySnapshot  # noqa: E402
from inventory import (  # noqa: E402
    DocumentationOccurrence,
    Inventory,
    resource_status_counts,
    row_target_data,
)
from maintain import format_count_table  # noqa: E402
from packwiz import InstalledProject  # noqa: E402
from project_metadata import (  # noqa: E402
    ProjectLookup,
    ProjectMetadata,
    ProjectMetadataError,
    deduplicate_lookups,
    project_metadata_pool_data,
)


class SingleTargetConfigTests(unittest.TestCase):
    def test_row_rejects_legacy_version_map(self) -> None:
        with self.assertRaises(ValueError):
            row_target_data(
                {"versions": {"1.21.1": {"selected": []}}},
                "1.21.1",
            )


class InventoryReportingTests(unittest.TestCase):
    def test_counts_are_grouped_by_resource_type_provider_and_status(self) -> None:
        default_occurrence = DocumentationOccurrence(
            ref={"source": "modrinth", "slug": "default-project"},
            provider="modrinth",
            project_id="default-project",
            slug="default-project",
            resource_type="mod",
            role="default",
            location="default",
            identity="modrinth:default-project",
        )
        optional_occurrence = DocumentationOccurrence(
            ref={"source": "curseforge", "slug": "optional-pack"},
            provider="curseforge",
            project_id="optional-pack",
            slug="optional-pack",
            resource_type="resourcepack",
            role="optional",
            location="optional",
            identity="curseforge:optional-pack",
        )
        installed_default = InstalledProject(
            provider="modrinth",
            project_id="default-project",
            resource_type="mod",
            file="mods/default.pw.toml",
            name="Default",
            local_slug="default",
            version_id="version-default",
        )
        installed_dependency = InstalledProject(
            provider="modrinth",
            project_id="dependency-project",
            resource_type="mod",
            file="mods/dependency.pw.toml",
            name="Dependency",
            local_slug="dependency",
            version_id="version-dependency",
        )
        inventory = Inventory(
            target_version="1.21.1",
            categories=[],
            groups=[],
            metadata={},
            occurrences=[default_occurrence, optional_occurrence],
            installed=[installed_default, installed_dependency],
            dependency_snapshot=DependencySnapshot(
                required_project_ids_by_version={}
            ),
            dependency_analysis=DependencyAnalysis(
                root_project_ids=frozenset({"default-project"})
            ),
            defaults={default_occurrence.identity: default_occurrence},
            optional={optional_occurrence.identity: optional_occurrence},
            installed_by_identity={
                installed_default.identity: installed_default,
                installed_dependency.identity: installed_dependency,
            },
            dependency_identities={installed_dependency.identity},
        )

        counts = resource_status_counts(inventory)

        self.assertEqual(counts["mod"]["modrinth"]["default"], 1)
        self.assertEqual(counts["mod"]["modrinth"]["dependency"], 1)
        self.assertEqual(counts["mod"]["modrinth"]["installed"], 2)
        self.assertEqual(
            counts["resourcepack"]["curseforge"]["optional"],
            1,
        )

    def test_human_table_is_deterministic(self) -> None:
        provider_counts = {
            "modrinth": {
                "default": 1,
                "optional": 2,
                "dependency": 3,
                "installed": 4,
                "unexplained": 0,
            },
            "curseforge": {
                "default": 5,
                "optional": 6,
                "dependency": 0,
                "installed": 5,
                "unexplained": 0,
            },
        }

        lines = format_count_table(provider_counts)

        self.assertEqual(lines[0].split(), [
            "Provider",
            "Default",
            "Optional",
            "Dependency",
            "Installed",
            "Unexplained",
        ])
        self.assertEqual(lines[-1].split(), ["Total", "6", "8", "3", "9", "0"])


class ProjectMetadataSerializationTests(unittest.TestCase):
    def test_slug_and_id_lookups_collapse_to_one_project(self) -> None:
        project = ProjectMetadata(
            provider="modrinth",
            project_id="project-id",
            slug="project",
            name="Project",
            page="https://modrinth.com/mod/project",
        )
        lookups = [
            ProjectLookup(
                provider="modrinth",
                resource_type="mod",
                slug="project",
            ),
            ProjectLookup(
                provider="modrinth",
                resource_type="mod",
                project_id="project-id",
            ),
        ]

        deduplicated = deduplicate_lookups(
            lookups,
            {project.identity: project},
        )

        self.assertEqual(len(deduplicated), 1)

    def test_serializer_rejects_mismatched_identity_key(self) -> None:
        project = ProjectMetadata(
            provider="modrinth",
            project_id="correct-id",
            slug="project",
            name="Project",
            page="https://modrinth.com/mod/project",
        )

        with self.assertRaises(ProjectMetadataError):
            project_metadata_pool_data({"modrinth:wrong-id": project})


if __name__ == "__main__":
    unittest.main()
