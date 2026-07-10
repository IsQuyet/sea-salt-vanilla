# Sea Salt Vanilla tooling guide

[Back to README](../README.md)

Run all commands from the repository root through one entrypoint:

```bash
python tools/maintain.py <command>
```

## Data model

Each persisted source owns one kind of fact:

| Path | Purpose | Commit? |
| --- | --- | --- |
| `docs/config/` | Default, optional, and alternative project intent | Yes |
| Packwiz `.pw.toml` files | Installed projects and provider locks | Yes |
| `data/project-metadata.json` | Modrinth and CurseForge project names, slugs, and pages | Yes |
| `cache/modrinth/versions.json` | Rebuildable Modrinth version owners, loaders, and required edges | No |
| `data/modrinth-dependencies.json` | Minimal required edges for offline checks | Yes |
| `docs/*.md` | Generated public project documentation | Yes |

Project metadata queries use the union of all documented and installed projects. Dependencies do not add query roots because an installed dependency already appears in Packwiz.

Version queries use the concrete Modrinth version IDs locked by Packwiz. The tooling does not analyze CurseForge dependencies, so it does not maintain a CurseForge version pool.

The inventory derives `default`, `optional`, `dependency`, `installed`, and `unexplained` in memory. Canonical identity is `provider + provider project ID`; these classifications are not written as separate registries.

## Consistency rules

For the Minecraft version in `pack.toml`:

- **P**: default documented projects
- **O**: optional projects and alternatives
- **D**: required dependency-only Modrinth projects reachable from P
- **A**: all Packwiz-installed projects

Checks require P, O, and D to be pairwise disjoint and require `A = P union D`. This detects missing defaults, installed optional projects, and orphaned dependencies.

Dependency analysis is Modrinth-only. Prefer Modrinth for dependency-sensitive mods. A default CurseForge mod produces a warning because its dependency closure cannot be verified.

## Commands

| Command | Purpose | Writes |
| --- | --- | --- |
| `python tools/maintain.py status` | Show resource, provider, status, and health counts | Nothing |
| `python tools/maintain.py check` | Run the offline consistency and documentation check | Nothing |
| `python tools/maintain.py check --deep` | Compare tracked dependency edges with the local version pool | Nothing |
| `python tools/maintain.py refresh --scope projects` | Refresh Modrinth and CurseForge project metadata | `data/project-metadata.json` |
| `python tools/maintain.py refresh --scope versions` | Refresh installed Modrinth version facts | `cache/modrinth/versions.json` |
| `python tools/maintain.py refresh` | Run both refresh scopes | Both files above |
| `python tools/maintain.py generate` | Regenerate dependency data and public documentation | `data/modrinth-dependencies.json`, `docs/*.md` |
| `python tools/maintain.py index` | Normalize LF-managed files and run `packwiz refresh` | Changed LF-managed files, `index.toml`, `pack.toml` |
| `python tools/maintain.py sync` | Run refresh, generate, index, and deep check | All outputs above |

Use `--provider modrinth|curseforge|all`, `--scope projects|versions|all`, `--force`, or `--dry-run` to control refreshes. Reporting commands support `--json`.

## Maintenance workflows

| Change | Run |
| --- | --- |
| Documentation classification only | `generate`, then `check` |
| Packwiz metadata or shipped files | `index`, then `check` |
| Add or update a Modrinth project | `refresh --provider modrinth`, `generate`, `index`, then `check --deep` |
| Add a CurseForge project | `refresh --provider curseforge --scope projects`, `generate`, `index`, then `check` |

CurseForge project refresh uses CFWidget without a key. Set `CURSEFORGE_API_KEY` or `CF_API_KEY` to use the official API.

Before committing, run:

```bash
python tools/maintain.py generate
python tools/maintain.py index
python tools/maintain.py check
python tools/maintain.py check --deep
git diff --check
```

## Module boundaries

- `maintain.py`: CLI and reports
- `inventory.py`: inventory and consistency rules
- `dependencies.py`: pure required-dependency analysis
- `project_metadata.py`: project metadata and provider queries
- `modrinth_versions.py`: local Modrinth version pool
- `documents.py`: Markdown generation and freshness checks
- `packwiz.py`: repository paths, Packwiz facts, line endings, and index refresh
