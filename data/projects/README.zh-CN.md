# Mod 数据

这个目录包含用于生成公开 Mod 文档和一致性报告的结构化源数据。

## 编辑这些文件

- `matrix/*.json`：默认功能矩阵。新增默认 Mod 功能大类时放在这里。每个矩阵文件都必须包含 `order` 数字；数字越小，渲染顺序越靠前。
- `optional.json`：可选能力矩阵。这个文件名由工具保留。这里的条目会被记录为可选项，不应安装进默认整合包。
- `meta.json`：生成文档时使用的共享元数据，包括支持的 Minecraft 版本和介绍文本。

## 不要手动编辑生成文件

- `generated/projects.json`：生成的项目注册表，用于名称、链接和身份匹配。
- `generated/dependencies.json`：生成的 dependency-only Mod 注册表。

## 命令

- `python tools/update_mod_data.py` 或 `python tools/update_mod_data.py generate`：重新生成项目元数据、依赖元数据、公开文档和本地一致性报告。
- `python tools/update_mod_data.py check` 或 `python tools/update_mod_data.py --check`：检查生成数据和文档是否为最新。
- `python tools/update_mod_data.py projects`：只重新生成 `generated/projects.json`。
- `python tools/update_mod_data.py dependencies`：只重新生成 `generated/dependencies.json`。
- `python tools/update_mod_data.py docs`：只重新生成公开 Mod 文档。
- `python tools/update_mod_data.py report`：只重新生成本地一致性报告。

可以在单个步骤名称后加 `--check`，只检查该步骤是否最新。例如：`python tools/update_mod_data.py docs --check`。
