# Documentation config

This directory contains the human-maintained source config used to generate the public project documentation and project data.

The tooling models every documented entry as a provider-neutral *project*, not just a mod. It scans `mods/`, `resourcepacks/`, `shaderpacks/`, `datapacks/`, and `plugins/` for packwiz `*.pw.toml` metafiles. The documentation category supplies the intended project `type` (`mod`, `resourcepack`, `shader`, ...), while local Modrinth and CurseForge caches supply canonical IDs, slugs, and names.

Project refs use `source` to select a provider and normally use a compact `slug`. `selected` is always a list and contains every default implementation for the feature; `alternatives` uses the same ref shape for optional substitutes. Do not add display names merely to compensate for missing cache metadata: refresh the relevant provider cache instead.

The generated catalog remains keyed by human-facing slug, but identity checks are provider-qualified. Distinct projects from the same provider may not repeat across target-version rows, and different provider identities may not silently claim the same generated catalog key.

## Project-data contract

The current target version is described by four sets:

- **P**: non-optional selected projects from the target-version matrices.
- **O**: optional selections and alternatives from the target-version matrices.
- **D**: required dependency-only Modrinth projects derived from P and concrete packwiz locks.
- **A**: all projects installed by packwiz.

Checks compare projects by provider-qualified ID and require P, O, and D to be pairwise disjoint, with `A = P union D`. This makes an installed project invalid when it is neither directly documented nor reachable as a required Modrinth dependency of P.

Automatic dependency analysis is intentionally Modrinth-only. Prefer Modrinth for mods with dependency relationships. Use CurseForge for direct or self-contained projects when necessary; without the CurseForge API, their dependency closure is reported as unverified rather than guessed.

## Layout

Every subdirectory that contains a `meta.json` is a *documentation category*. Each category renders to `docs/<category>.md` and `docs/<category>.zh-CN.md`.

A category directory contains:

- `meta.json`: document title, supported Minecraft versions, and introduction text.
- `matrix/*.json`: default feature matrices. Rows may reference any project type by slug - the category only decides which document a matrix renders into, not what it may reference. Each matrix file must include an `order` number; lower numbers render first.
- `optional.json` (optional file): optional capability matrix. Entries here are documented as optional and are not expected to be installed in the default pack.

Generated machine-readable artifacts are:

- `data/projects.json`: P for the current target version.
- `data/optional.json`: O for the current target version.
- `data/dependencies.json`: D for the current target version.
- `data/project-catalog.json`: canonical metadata for projects referenced by every rendered version.
- `data/modrinth-locks.json`: minimal required edges for current packwiz Modrinth version locks, used by offline checks.

Do not edit these generated files by hand.

## Commands

- `python tools/update_project_data.py` or `python tools/update_project_data.py generate`: regenerate project metadata, dependency metadata, and public documentation.
- `python tools/update_project_data.py check`: check repository consistency and generated documentation freshness without writing files or making network requests.
- `python tools/update_project_data.py projects`: regenerate P, O, and the all-version project catalog.
- `python tools/update_project_data.py locks`: regenerate the tracked Modrinth lock graph from the local version cache.
- `python tools/update_project_data.py dependencies`: regenerate only `data/dependencies.json`.
- `python tools/update_project_data.py docs`: regenerate only the public documentation.
