# 文档配置

这个目录包含人工维护的源配置，用于生成公开项目文档和项目数据。

工具链把每个被记录的条目都建模为 Modrinth 风格的*项目（project）*，而不仅仅是 Mod：它会扫描 `mods/`、`resourcepacks/`、`shaderpacks/`、`datapacks/`、`plugins/` 目录下的 packwiz `*.pw.toml` 元文件，生成的项目条目带有 `type` 字段（`mod`、`resourcepack`、`shader` 等），取值来自 Modrinth 的 `project_type`。依赖在项目层面解析，所以跨类型依赖（例如资源包依赖 Mod）与 Mod 之间的依赖走同一套机制。

## 目录结构

每个包含 `meta.json` 的子目录都是一个*文档分类*。每个分类渲染为 `docs/<分类名>.md` 和 `docs/<分类名>.zh-CN.md`。

分类目录包含：

- `meta.json`：文档标题、支持的 Minecraft 版本和介绍文本。
- `matrix/*.json`：默认功能矩阵。表格行可以通过 slug 引用任意类型的项目；分类只决定矩阵渲染进哪份文档，不限制它能引用什么。每个矩阵文件都必须包含 `order` 数字；数字越小，渲染顺序越靠前。
- `optional.json`（可选文件）：可选能力矩阵。这里的条目会被记录为可选项，不应安装进默认整合包。

生成的机器可读注册表位于 `data/projects.json` 和 `data/dependencies.json`。不要手动编辑这些生成文件。

## 命令

- `python tools/update_project_data.py` 或 `python tools/update_project_data.py generate`：重新生成项目元数据、依赖元数据和公开文档。
- `python tools/update_project_data.py check`：只读检查仓库一致性和生成文档是否最新；不会写文件，也不会读取本地 Modrinth cache。
- `python tools/update_project_data.py projects`：只重新生成 `data/projects.json`。
- `python tools/update_project_data.py dependencies`：只重新生成 `data/dependencies.json`。
- `python tools/update_project_data.py docs`：只重新生成公开文档。
