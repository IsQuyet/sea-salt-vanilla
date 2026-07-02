# Documentation config

This directory contains the human-maintained source config used to generate the public project documentation and consistency reports.

The tooling models every documented entry as a Modrinth-style *project*, not just a mod: it scans `mods/`, `resourcepacks/`, `shaderpacks/`, `datapacks/`, and `plugins/` for packwiz `*.pw.toml` metafiles, and each generated project entry carries a `type` field (`mod`, `resourcepack`, `shader`, ...) taken from the Modrinth `project_type`. Dependencies are resolved at the project level, so cross-type requirements (for example a resource pack that requires a mod) are tracked the same way as mod-to-mod dependencies.

## Layout

Every subdirectory that contains a `meta.json` is a *documentation category*. Each category renders to `docs/<category>.md` and `docs/<category>.zh-CN.md`.

A category directory contains:

- `meta.json`: document title, supported Minecraft versions, and introduction text.
- `matrix/*.json`: default feature matrices. Rows may reference any project type by slug - the category only decides which document a matrix renders into, not what it may reference. Each matrix file must include an `order` number; lower numbers render first.
- `optional.json` (optional file): optional capability matrix. Entries here are documented as optional and are not expected to be installed in the default pack.

Generated machine-readable registries live in `data/projects.json` and `data/dependencies.json`. Do not edit those generated files by hand.

## Commands

- `python tools/update_project_data.py` or `python tools/update_project_data.py generate`: regenerate project metadata, dependency metadata, documentation, and the local consistency report.
- `python tools/update_project_data.py check` or `python tools/update_project_data.py --check`: check whether generated data and documentation are up to date. The consistency report also flags required Modrinth dependencies that are not installed anywhere in the pack, and projects installed in a folder that does not match their Modrinth project type.
- `python tools/update_project_data.py projects`: regenerate only `data/projects.json`.
- `python tools/update_project_data.py dependencies`: regenerate only `data/dependencies.json`.
- `python tools/update_project_data.py docs`: regenerate only the public documentation.
- `python tools/update_project_data.py report`: regenerate only the local consistency report.

Add `--check` after a step name to check only that step, for example `python tools/update_project_data.py docs --check`.
