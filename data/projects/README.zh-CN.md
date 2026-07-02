# 项目数据

这个目录包含用于生成公开项目文档和一致性报告的结构化源数据。

工具链把每个条目都建模为 Modrinth 风格的*项目（project）*，而不仅仅是 Mod：它会扫描 `mods/`、`resourcepacks/`、`shaderpacks/`、`datapacks/`、`plugins/` 目录下的 packwiz `*.pw.toml` 元文件，生成的项目条目带有 `type` 字段（`mod`、`resourcepack`、`shader` 等），取值来自 Modrinth 的 `project_type`。依赖在项目层面解析，所以跨类型依赖（例如资源包依赖 Mod）与 Mod 之间的依赖走同一套机制。

## 目录结构

- `generated/`：所有分类共享的全局注册表。不要手动编辑。
  - `generated/projects.json`：项目注册表，用于名称、类型、链接和身份匹配。
  - `generated/dependencies.json`：dependency-only 项目注册表。
- 其余每个包含 `meta.json` 的子目录都是一个*文档分类*。每个分类渲染为 `docs/<分类名>.md` 和 `docs/<分类名>.zh-CN.md`。`mods/` 是第一个分类；需要 `resourcepacks/`、`shaderpacks/` 等时，创建相同结构的目录即可。

分类目录包含：

- `meta.json`：文档标题、支持的 Minecraft 版本和介绍文本。
- `matrix/*.json`：默认功能矩阵。表格行可以通过 slug 引用任意类型的项目——分类只决定矩阵渲染进哪份文档，不限制它能引用什么。每个矩阵文件都必须包含 `order` 数字；数字越小，渲染顺序越靠前。
- `optional.json`（可选文件）：可选能力矩阵。这里的条目会被记录为可选项，不应安装进默认整合包。

## 命令

- `python tools/update_project_data.py` 或 `python tools/update_project_data.py generate`：重新生成项目元数据、依赖元数据、公开文档和本地一致性报告。
- `python tools/update_project_data.py check` 或 `python tools/update_project_data.py --check`：检查生成数据和文档是否为最新。一致性报告还会标记两类问题：被声明为 required 但没有安装在整合包任何目录中的 Modrinth 依赖，以及安装目录与其 Modrinth 项目类型不符的项目。
- `python tools/update_project_data.py projects`：只重新生成 `generated/projects.json`。
- `python tools/update_project_data.py dependencies`：只重新生成 `generated/dependencies.json`。
- `python tools/update_project_data.py docs`：只重新生成公开文档。
- `python tools/update_project_data.py report`：只重新生成本地一致性报告。

可以在单个步骤名称后加 `--check`，只检查该步骤是否最新。例如：`python tools/update_project_data.py docs --check`。
