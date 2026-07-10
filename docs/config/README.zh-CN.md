# 文档配置

这个目录包含人工维护的源配置，用于生成公开项目文档和项目数据。

工具链把每个被记录的条目都建模为平台无关的*项目（project）*，而不仅仅是 Mod。它会扫描 `mods/`、`resourcepacks/`、`shaderpacks/`、`datapacks/`、`plugins/` 目录下的 packwiz `*.pw.toml` 元文件。文档分类提供预期的项目 `type`（`mod`、`resourcepack`、`shader` 等），本地 Modrinth 与 CurseForge 缓存则提供规范的 ID、slug 和名称。

项目引用通过 `source` 选择平台，通常只写紧凑的 `slug`。`selected` 始终是列表，并包含该功能的所有默认实现；`alternatives` 使用相同的引用结构表示可选替代。不要为了补偿缓存缺失而额外写显示名称；应刷新对应的平台缓存。

生成目录仍以便于阅读的 slug 作为 key，但身份检查会带上平台。同一平台的同一项目不能在目标版本的多个位置重复出现，不同平台身份也不能静默占用同一个生成目录 key。

## 项目数据契约

当前目标版本由四个集合描述：

- **P**：目标版本矩阵中非 optional 的 selected 项目。
- **O**：目标版本矩阵中的 optional selections 与 alternatives。
- **D**：从 P 和具体 packwiz 版本锁推导出的 required dependency-only Modrinth 项目。
- **A**：packwiz 安装的全部项目。

检查按“平台 + 项目 ID”比较身份，要求 P、O、D 两两不相交，并满足 `A = P ∪ D`。因此，一个已安装项目如果既没有被直接记录，也无法从 P 沿 required Modrinth 依赖到达，就会成为无效的遗留项目。

自动依赖分析有意限定为 Modrinth-only。具有依赖关系的 Mod 应优先使用 Modrinth 来源。必须使用 CurseForge 时，优先选择直接项目或自包含资源；在没有 CurseForge API 的情况下，其依赖闭包只会报告为“未验证”，不会被猜测。

## 目录结构

每个包含 `meta.json` 的子目录都是一个*文档分类*。每个分类渲染为 `docs/<分类名>.md` 和 `docs/<分类名>.zh-CN.md`。

分类目录包含：

- `meta.json`：文档标题、支持的 Minecraft 版本和介绍文本。
- `matrix/*.json`：默认功能矩阵。表格行可以通过 slug 引用任意类型的项目；分类只决定矩阵渲染进哪份文档，不限制它能引用什么。每个矩阵文件都必须包含 `order` 数字；数字越小，渲染顺序越靠前。
- `optional.json`（可选文件）：可选能力矩阵。这里的条目会被记录为可选项，不应安装进默认整合包。

生成的机器可读产物包括：

- `data/projects.json`：当前目标版本的 P。
- `data/optional.json`：当前目标版本的 O。
- `data/dependencies.json`：当前目标版本的 D。
- `data/project-catalog.json`：所有被渲染版本引用的规范项目元数据。
- `data/modrinth-locks.json`：当前 packwiz Modrinth 版本锁的最小 required 边，供离线检查使用。

不要手动编辑这些生成文件。

## 命令

- `python tools/update_project_data.py` 或 `python tools/update_project_data.py generate`：重新生成项目元数据、依赖元数据和公开文档。
- `python tools/update_project_data.py check`：只读检查仓库一致性和生成文档是否最新；不会写文件，也不会发起网络请求。
- `python tools/update_project_data.py projects`：重新生成 P、O 和全版本项目目录。
- `python tools/update_project_data.py locks`：根据本地版本缓存重新生成受跟踪的 Modrinth 锁图。
- `python tools/update_project_data.py dependencies`：只重新生成 `data/dependencies.json`。
- `python tools/update_project_data.py docs`：只重新生成公开文档。
