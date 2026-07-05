# Sea Salt Vanilla

[English](README.md) | [简体中文](README.zh-CN.md)

Sea Salt Vanilla is a client-first Fabric modpack that improves the everyday Minecraft client experience across singleplayer and multiplayer.

The goal: keep the vanilla experience recognizable, then quietly improve visuals, sound, interaction, ambience, and quality-of-life. Think vanilla ice cream with a pinch of sea salt: still vanilla, but with a quietly upgraded recipe.

## Project status

- Loader: **Fabric**
- Minecraft: **1.21.1**
- Scope: **primarily client-side**
- Maintenance format: **packwiz** (TOML metadata, no committed mod jars)
- Version control: Git/GitHub

## Distribution

- Releases are exported as Modrinth `.mrpack` packages
- CurseForge packages may be provided when needed
- Release notes are published through GitHub Releases and Modrinth version pages

## Project documentation

- [Mods](docs/mods.md)
- [Resource packs](docs/resourcepacks.md)
- [Shader packs](docs/shaderpacks.md)
- [Data packs](docs/datapacks.md)
- [Tooling guide](tools/README.md)

## Data and tooling workflow

The source of truth for the public project matrix is `docs/config/`. Generated files under `data/` and `docs/*.md` should be updated with the tooling instead of edited by hand.

Recommended commands:

```bash
python tools/update_project_data.py generate
python tools/update_project_data.py check
```

- `generate` updates generated project registries, dependency data, and public documentation.
- `check` verifies generated files, docs config, packwiz metadata, dependency data, and project uniqueness without writing generated outputs.

Current generated data semantics:

- `data/projects.json`: default projects declared by `docs/config/**/matrix/*.json`.
- `data/optional.json`: optional projects and alternatives declared by `docs/config/**/optional.json` and matrix alternatives.
- `data/dependencies.json`: dependency-only projects installed by packwiz but not presented as public feature entries.

Packwiz metadata remains the installation fact used by consistency checks. If documentation and packwiz disagree, update `docs/config/` first, run the check, then add or remove packwiz projects according to the reported result.

## Directory layout

```text
sea-salt-vanilla/
|-- mods/                 # Mod packwiz metadata
|-- resourcepacks/        # Resource pack packwiz metadata
|-- shaderpacks/          # Shader pack packwiz metadata
|-- datapacks/            # Data pack content and packwiz metadata
|-- config/               # shipped game config
|-- defaultconfigs/       # default configs copied into new worlds
|-- docs/
|   |-- config/
|   |   `-- <category>/                # mods, resourcepacks, shaderpacks, ...
|   |       |-- meta.json              # generated document metadata
|   |       |-- matrix/*.json          # visible project matrices
|   |       `-- optional.json          # documented optional projects
|   `-- *.md                           # generated public documentation
|-- data/
|   |-- projects.json                  # generated visible project registry
|   |-- optional.json                  # generated optional/alternative registry
|   `-- dependencies.json              # generated dependency-only registry
`-- tools/                             # generation and check scripts
```

## Acknowledgements

Sea Salt Vanilla exists not only because Minecraft itself offers a world worth returning to, but also because open-source projects like Sodium, Iris, and many others are sustained by developers who often give their time, skill, and care with little expectation of reward. These projects are not just convenient downloads; behind them are real people, real labor, and persistence that is often far from easy.

If this pack helps you enjoy Minecraft, please consider learning about the projects it includes, leaving kind feedback, reporting issues responsibly, and supporting the original authors when you can. Even a little attention and appreciation can help keep this community healthier.

## License notes

This repository is intended to contain only modpack configuration, metadata, documentation, and custom scripts/assets made for the pack. Third-party mods, resource packs, shader packs, data packs, and other external content remain owned by their original authors and follow their own licenses.
