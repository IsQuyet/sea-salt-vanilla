# Immersive Vanilla

[English](README.md) | [简体中文](README.zh-CN.md)

Immersive Vanilla is a primarily client-side Fabric modpack that enhances the vanilla Minecraft experience without requiring server-side gameplay content.

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

## Directory layout

```text
mods/            # Mods, as packwiz metadata or local files
config/          # Client/common configs shipped with the pack
defaultconfigs/  # Default configs copied into new worlds
resourcepacks/   # Resource packs, as packwiz metadata or local files
shaderpacks/     # Shader packs, as packwiz metadata or local files
dist/            # Local export output, not committed
```

## License notes

This repository is intended to contain only modpack configuration, metadata, documentation, and custom scripts/assets made for the pack. Third-party mods, resource packs, shader packs, data packs, and other external content remain owned by their original authors and follow their own licenses.
