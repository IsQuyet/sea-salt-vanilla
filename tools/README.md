# Sea Salt Vanilla tooling guide

[Back to README](../README.md)

Run these commands from the repository root. This guide covers the normal maintenance workflow only.

## Where changes belong

| Path | Role | Edit by hand? |
| --- | --- | --- |
| `docs/config/` | Public classification: feature rows, optional projects, alternatives, and display order | Yes |
| `mods/`, `resourcepacks/`, `shaderpacks/`, `datapacks/` | Default packwiz projects. A `.pw.toml` file here means the project ships by default | Yes |
| `cache/modrinth/` | Local Modrinth metadata cache for generation | No. Refresh it and do not commit it |
| `data/projects.json` | Generated catalog of documented default projects | No |
| `data/optional.json` | Generated catalog of optional projects and alternatives | No |
| `data/dependencies.json` | Generated catalog of dependency-only projects pulled by defaults | No |
| `docs/*.md` | Generated public docs | No |

## Add default Modrinth projects

Use this flow when a project should be included in the default pack and documented in a matrix.

```bash
packwiz modrinth install <slug> --yes
python tools/refresh_modrinth_cache.py
# edit docs/config/**/matrix/*.json
python tools/update_project_data.py generate
python tools/refresh_packwiz.py
python tools/update_project_data.py check
git diff --check
```

Order matters:

- Install first so packwiz records the project and locked version.
- Refresh the Modrinth cache before generation so dependency data is available.
- Edit the matrix before `generate` so docs explain why the project ships.
- Run `python tools/refresh_packwiz.py` and `check` last to update indexes and verify consistency.

## Move a default project to optional

Use this flow when a project should remain recognized by the pack but should no longer ship by default.

```bash
# remove the project from docs/config/**/matrix/*.json
# add the project to docs/config/**/optional.json
git rm <packwiz-project-file>.pw.toml
python tools/update_project_data.py generate
python tools/refresh_packwiz.py
python tools/update_project_data.py check
git diff --check
```

Remove the default `.pw.toml`; otherwise the project still ships by default.

## Edit only docs classification

Use this flow when no installed project version changes.

```bash
# edit docs/config/**/*.json
python tools/update_project_data.py generate
python tools/update_project_data.py check
git diff --check
```

Run `python tools/refresh_modrinth_cache.py` first only if generation says required Modrinth cache entries are missing.

## Edit packwiz or shipped config files

Use this flow after changing packwiz metadata or files that ship through packwiz.

```bash
python tools/refresh_packwiz.py
python tools/update_project_data.py check
git diff --check
```

If you added or updated Modrinth project versions, refresh the Modrinth cache and regenerate data/docs too:

```bash
python tools/refresh_modrinth_cache.py
python tools/update_project_data.py generate
python tools/refresh_packwiz.py
python tools/update_project_data.py check
git diff --check
```

## Command reference

| Command | Use | Writes files? |
| --- | --- | --- |
| `python tools/update_project_data.py generate` | Regenerate `data/*.json` and public docs | Yes |
| `python tools/update_project_data.py check` | Check docs config, generated data, packwiz metadata, and generated docs | No |
| `python tools/refresh_modrinth_cache.py` | Refresh local Modrinth metadata after adding or changing Modrinth versions, or when generation reports missing cache entries | Yes, cache only |
| `python tools/normalize_line_endings.py` | Normalize tracked files managed as `eol=lf` before hash-sensitive operations | Yes, only line endings |
| `python tools/normalize_line_endings.py --check` | Report tracked `eol=lf` files whose working-tree line endings need normalization | No |
| `python tools/refresh_packwiz.py` | Normalize LF-managed files, then refresh `index.toml` and the index hash in `pack.toml` | Yes |

Supporting scripts:

- `generate_project_registry.py`: writes `data/projects.json` and `data/optional.json`
- `generate_project_dependencies.py`: writes `data/dependencies.json`
- `generate_project_docs.py`: writes public Markdown docs
- `check_project_data.py`: checks docs config, generated data, and packwiz metadata
- `check_generated_docs.py`: checks generated Markdown freshness

## Common check failures

- `missing_defaults`: a default docs matrix row names a project that is not installed by packwiz.
- `unexpected_installed`: an optional or alternative project is installed in the default pack.
- `unexplained`: packwiz installs a project that is not documented as default and is not dependency-only.
- `unknown_refs`: docs config names a project that is missing from generated catalogs.
- `duplicate_refs`: the same project appears more than once in target-version docs config.

Before committing, inspect the diff. Commit only real content changes. Ignore Windows line-ending warnings unless `git diff` shows a patch.
