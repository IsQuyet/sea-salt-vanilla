# Documentation config

This directory is the human-maintained source for the public project tables.
The repository currently targets only the Minecraft version declared in
`pack.toml`; rows therefore use direct `selected` and `alternatives` fields and
do not contain a version map.

## Project references

Project references stay compact:

```json
{ "source": "modrinth", "slug": "fabric-api" }
```

- `source` is `modrinth` or `curseforge`.
- `selected` is always a list and contains every default implementation for a feature.
- `alternatives` uses the same shape for optional substitutes.
- Do not copy display names into matrix refs. Refresh project metadata instead.

Canonical identity is `provider + provider project ID`. Slugs are lookup and
display coordinates, not identity. The same provider project may not be
declared more than once, while cross-provider equivalence is intentionally not
guessed.

## Inventory contract

The maintainer inventory derives four sets in memory:

- **P**: default projects selected by non-optional matrices.
- **O**: optional selections and alternatives.
- **D**: required dependency-only Modrinth projects reachable from P.
- **A**: all projects installed by packwiz.

Checks require P, O, and D to be pairwise disjoint and require `A = P union D`.
This detects packwiz projects left behind after a default project is removed.

Dependency analysis is deliberately Modrinth-only. Prefer Modrinth for mods
with external dependencies. CurseForge remains supported for direct projects
and self-contained resources, but a default CurseForge mod is reported as
having an unverified dependency closure.

## Layout

Every category directory with a `meta.json` renders to
`docs/<category>.md` and `docs/<category>.zh-CN.md`.

- `meta.json`: bilingual title and introduction.
- `matrix/*.json`: ordered default feature groups.
- `optional.json`: optional capabilities that do not ship by default.

Persisted support data has one purpose per file:

- `data/project-metadata.json`: tracked canonical slug, name, and project page.
- `data/modrinth-dependencies.json`: tracked required edges for offline checks.
- `cache/modrinth/versions.json`: ignored local provider version facts.

The inventory classifications P, O, D, and A are not written as separate
registries.

## Commands

```bash
python tools/maintain.py status
python tools/maintain.py check
python tools/maintain.py refresh --dry-run
python tools/maintain.py refresh
python tools/maintain.py generate
python tools/maintain.py index
```

- `status` is read-only and shows resource/provider/status counts.
- `check` is the ordinary offline, cache-free consistency check.
- `check --deep` additionally compares the tracked dependency snapshot with the local version pool.
- `refresh` queries provider metadata; use `--provider`, `--scope`, `--force`, or `--dry-run` as needed.
- `generate` writes the dependency snapshot and public Markdown.
- `index` normalizes LF-managed files and refreshes packwiz indexes.
- `sync` runs refresh, generate, index, and deep check in sequence.

All reporting commands support `--json` for machine-readable output.
