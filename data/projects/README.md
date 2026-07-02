# Mod data

This directory contains the structured source data used to generate the public mod documentation and consistency reports.

## Edit these files

- `matrix/*.json`: default feature matrices. Add new default mod feature groups here. Each matrix file must include an `order` number; lower numbers render first.
- `optional.json`: optional capability matrix. This filename is reserved by the tools. Entries here are documented as optional and are not expected to be installed in the default pack.
- `meta.json`: shared metadata for generated documentation, including supported Minecraft versions and introduction text.

## Do not edit generated files by hand

- `generated/projects.json`: generated project registry used for names, links, and identity matching.
- `generated/dependencies.json`: generated dependency-only mod registry.

## Commands

- `python tools/update_mod_data.py` or `python tools/update_mod_data.py generate`: regenerate project metadata, dependency metadata, documentation, and the local consistency report.
- `python tools/update_mod_data.py check` or `python tools/update_mod_data.py --check`: check whether generated data and documentation are up to date.
- `python tools/update_mod_data.py projects`: regenerate only `generated/projects.json`.
- `python tools/update_mod_data.py dependencies`: regenerate only `generated/dependencies.json`.
- `python tools/update_mod_data.py docs`: regenerate only public mod documentation.
- `python tools/update_mod_data.py report`: regenerate only the local consistency report.

Add `--check` after a step name to check only that step, for example `python tools/update_mod_data.py docs --check`.
