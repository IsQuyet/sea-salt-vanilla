# Sea Salt Vanilla tooling guide

[Back to README](../README.md)

Run these commands from the repository root. This guide covers the normal maintenance workflow only.

## Where changes belong

| Path | Role | Edit by hand? |
| --- | --- | --- |
| `docs/config/` | Public classification: feature rows, optional projects, alternatives, and display order | Yes |
| `mods/`, `resourcepacks/`, `shaderpacks/`, `datapacks/`, `plugins/` | Default packwiz projects. A `.pw.toml` file here means the project ships by default | Yes |
| `cache/modrinth/`, `cache/curseforge/` | Local provider metadata caches for generation | No. Refresh them and do not commit them |
| `data/projects.json` | Generated catalog of documented default projects | No |
| `data/optional.json` | Generated catalog of optional projects and alternatives | No |
| `data/dependencies.json` | Generated catalog of dependency-only projects pulled by defaults | No |
| `data/project-catalog.json` | Generated metadata catalog for projects referenced by every rendered documentation version | No |
| `data/modrinth-locks.json` | Generated minimal required-dependency graph for current packwiz Modrinth locks | No |
| `docs/*.md` | Generated public docs | No |

## Metadata ownership and cache model

Each source has one responsibility:

- `docs/config/` declares project intent: feature role, default or optional status, and alternatives.
- Packwiz `.pw.toml` files declare installed facts: provider project ID and locked version or file.
- Provider project caches supply canonical `id`, `slug`, `name`, and `type` metadata.
- The Modrinth version cache supplies only locked-version loaders and dependency relationships.

Conflicting facts are reported instead of being resolved through an implicit priority order.

Modrinth and CurseForge caches remain in separate provider directories, but their project entries use the same minimal shape:

```json
{
  "id": "417768",
  "slug": "lottweaks",
  "name": "LotTweaks",
  "type": "mod"
}
```

The Modrinth version cache retains only `project_id`, `loaders`, and `dependencies`; each dependency retains only `project_id` and `dependency_type`. It is a local snapshot of the releases currently locked by packwiz. Generation projects its required edges into tracked `data/modrinth-locks.json`, so ordinary checks can recompute dependency closure without provider caches or network access. Both refresh commands write provider-specific manifests with the same summary structure.

The project refresh plan is controlled only by every documented project and every project installed by packwiz. Dependencies never expand the project query roots. Known ID and slug coordinates are reconciled into provider-qualified logical projects, preferring provider IDs. Project caches are snapshots of those roots and do not persist a separate derived alias table.

## Project-data contract

The generated data has four semantic sets, compared by provider-qualified project ID rather than local packwiz filename:

- **P**: target-version default projects from non-optional documentation matrices, stored in `data/projects.json`.
- **O**: target-version optional selections and alternatives, stored in `data/optional.json`.
- **D**: required dependency-only Modrinth closure derived from P and concrete packwiz version locks, stored in `data/dependencies.json`.
- **A**: every project currently installed by packwiz.

The checker enforces:

```text
P intersects O = empty
P intersects D = empty
O intersects D = empty
A = P union D
```

This is what detects orphaned packwiz projects: after a default project is removed, a dependency left installed without another required path falls outside `P union D` and becomes `unexplained`.

`data/project-catalog.json` is intentionally separate from P and O. It contains canonical metadata for projects referenced by every rendered Minecraft version, so historical documentation remains complete while P and O describe only the current target version.

Dependency analysis is deliberately Modrinth-only. Prefer a Modrinth source when a project exists on both providers, especially for mods with dependencies. CurseForge remains supported for direct projects and self-contained resources, but the checker cannot prove their dependency closure without the CurseForge API. If a CurseForge source is unavoidable, prefer resources without known external mod dependencies. Provider-specific dependency IDs are not treated as cross-provider project identities.

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

## Add default CurseForge projects

Use this flow when a project is available only from CurseForge.

```bash
packwiz curseforge add <slug-or-url> --yes
# edit docs/config/**/matrix/*.json
python tools/refresh_curseforge_cache.py
python tools/update_project_data.py generate
python tools/refresh_packwiz.py
python tools/update_project_data.py check
git diff --check
```

The CurseForge refresh uses the keyless CFWidget metadata API by default. If
`CURSEFORGE_API_KEY` or `CF_API_KEY` is configured, it uses the official
CurseForge API instead. Slug lookups preserve the matrix project type so mods,
resource packs, shaders, data packs, and plugins use the correct CurseForge
category path.

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
| `python tools/update_project_data.py projects` | Regenerate P, O, and the all-version project catalog | Yes |
| `python tools/update_project_data.py locks` | Regenerate the tracked Modrinth lock graph from the local version cache | Yes |
| `python tools/update_project_data.py dependencies` | Recompute D from P and the tracked Modrinth lock graph | Yes |
| `python tools/update_project_data.py docs` | Regenerate public Markdown from the all-version catalog | Yes |
| `python tools/update_project_data.py check` | Check docs config, generated data, packwiz metadata, and generated docs | No |
| `python tools/refresh_modrinth_cache.py` | Refresh local Modrinth metadata after adding or changing Modrinth versions, or when generation reports missing cache entries | Yes, cache only |
| `python tools/refresh_curseforge_cache.py` | Refresh local CurseForge project metadata through CFWidget, or the official API when a key is configured | Yes, cache only |
| `python tools/normalize_line_endings.py` | Normalize tracked files managed as `eol=lf` before hash-sensitive operations | Yes, only line endings |
| `python tools/normalize_line_endings.py --check` | Report tracked `eol=lf` files whose working-tree line endings need normalization | No |
| `python tools/refresh_packwiz.py` | Normalize LF-managed files, then refresh `index.toml` and the index hash in `pack.toml` | Yes |

Supporting scripts:

- `generate_project_registry.py`: writes `data/projects.json`, `data/optional.json`, and `data/project-catalog.json`
- `generate_modrinth_locks.py`: writes `data/modrinth-locks.json` from the local Modrinth version cache
- `generate_project_dependencies.py`: writes `data/dependencies.json`
- `generate_project_docs.py`: writes public Markdown docs
- `refresh_curseforge_cache.py`: caches normalized CurseForge project IDs, slugs, names, and types without downloading project files
- `check_project_data.py`: checks docs config, generated data, and packwiz metadata
- `check_generated_docs.py`: checks generated Markdown freshness

## Common check failures

- `missing_defaults`: a default docs matrix row names a project that is not installed by packwiz.
- `unexpected_installed`: an optional or alternative project is installed in the default pack.
- `unexplained`: packwiz installs a project that is not documented as default and is not dependency-only.
- `generated_data_invariants`: P, O, D, and A violate disjointness, identity, catalog, or `A = P union D` rules.
- `modrinth_lock_conflicts`: tracked Modrinth locks are stale or do not match current packwiz version locks.
- `dependency_closure_conflicts`: `data/dependencies.json` does not match the required Modrinth closure recomputed from P.
- `unknown_refs`: docs config names a project that is missing from generated catalogs.
- `duplicate_refs`: the same project appears more than once in target-version docs config.
- `installed_identity_conflicts`: packwiz files duplicate a provider ID or slug, or one file declares both providers.

Before committing, inspect the diff. Commit only real content changes. Ignore Windows line-ending warnings unless `git diff` shows a patch.
