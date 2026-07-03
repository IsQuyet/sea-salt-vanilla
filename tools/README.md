# Sea Salt Vanilla tooling guide

[English](README.md) | [简体中文](README.zh-CN.md)

The scripts in this directory maintain the generated project data and public documentation for the pack. They are intended to be run from the repository root.

## Source-of-truth model

- `docs/config/` is the source of truth for the public project matrix.
- `packwiz` metadata is the installation fact used by checks.
- `data/*.json` and `docs/*.md` are generated outputs.

Do not hand-edit generated files unless you are debugging the generator itself.

## Recommended commands

Generate everything after editing `docs/config/` or packwiz metadata:

```bash
python tools/update_project_data.py generate
```

Check everything before committing:

```bash
python tools/update_project_data.py check
```

The `check` command verifies generated files and consistency invariants without writing generated outputs or cache/report files.

## Generated data semantics

- `data/projects.json`: default projects declared by docs config matrix files.
- `data/optional.json`: optional projects and alternatives declared by docs config.
- `data/dependencies.json`: dependency-only projects installed by packwiz but not documented as public feature entries.

The checker expects these sets to stay disjoint. It also verifies:

- `projects.json + optional.json = docs/config project refs`
- `projects.json + dependencies.json = packwiz installed project refs`
- no duplicate project refs exist in the target-version docs config

## Script reference

### `update_project_data.py`

Main entry point for day-to-day work.

```bash
python tools/update_project_data.py generate
python tools/update_project_data.py check
```

Single-step commands are also available:

```bash
python tools/update_project_data.py projects
python tools/update_project_data.py dependencies
python tools/update_project_data.py docs
python tools/update_project_data.py report
```

Add `--check` to any single step to verify without writing that step's generated output.

### `generate_project_registry.py`

Generates:

- `data/projects.json`
- `data/optional.json`

Inputs:

- `docs/config/**/matrix/*.json`
- `docs/config/**/optional.json`
- local Modrinth project cache for optional metadata enrichment

This script does not require live network access.

### `generate_project_dependencies.py`

Generates:

- `data/dependencies.json`

Inputs:

- packwiz metadata under `mods/`, `resourcepacks/`, `shaderpacks/`, and other supported project folders
- generated project catalogs
- Modrinth version dependency cache/API data

In generate mode, this script may refresh the local dependency cache. In check mode, it does not write the cache.

### `generate_project_docs.py`

Generates bilingual public docs:

- `docs/mods.md`
- `docs/mods.zh-CN.md`
- `docs/resourcepacks.md`
- `docs/resourcepacks.zh-CN.md`
- `docs/shaderpacks.md`
- `docs/shaderpacks.zh-CN.md`

Inputs:

- `docs/config/**/meta.json`
- `docs/config/**/matrix/*.json`
- `docs/config/**/optional.json`
- generated project catalogs

### `check_project_data.py`

Checks generated data, docs config, packwiz metadata, dependencies, cache health, and project uniqueness.

Generate mode writes the human-readable report:

```text
reference/modrinth-collections/project-data-check.zh-CN.md
```

Check mode prints the same summary but does not write the report or cache files.

Important summary fields:

- `unexplained`: installed packwiz projects not explained by docs or dependency data.
- `cache_errors`: unresolved Modrinth cache/API errors.
- `generated_data_invariants`: broken set-equation or disjointness rules.
- `missing_defaults`: docs default projects missing from packwiz.
- `unexpected_installed`: optional or alternative projects installed in the default pack.
- `unknown_refs`: docs refs missing from generated catalogs.
- `duplicate_refs`: the same project appears more than once in target-version docs config.

### Shared helper modules

- `project_data_common.py`: shared filesystem, packwiz, Modrinth, dependency, and markdown helpers.
- `project_data_identity.py`: shared project identity and reference-resolution helpers.
- `project_data_invariants.py`: generated-data set invariant checks.

These helper modules are not meant to be run directly.

## Suggested workflow

1. Edit `docs/config/` first.
2. Run `python tools/update_project_data.py generate`.
3. If the checker reports missing or unexpected packwiz projects, update packwiz metadata accordingly.
4. Run `python tools/update_project_data.py generate` again.
5. Run `python tools/update_project_data.py check` before committing.

