# Sea Salt Vanilla 工具使用手册

[English](README.md) | [简体中文](README.zh-CN.md)

本目录下的脚本用于维护整合包的生成项目数据和公开文档。所有命令都建议从仓库根目录运行。

## 真相源模型

- `docs/config/` 是公开项目矩阵和分类意图的来源。
- `packwiz` 元数据代表实际安装事实，用于一致性检查。
- `cache/modrinth/` 保存由 `tools/refresh_modrinth_cache.py` 生成的本地 Modrinth 元数据缓存；这些文件被 git 忽略，不是人工维护的真相源。
- `data/*.json` 和 `docs/*.md` 是生成产物，不是真相源。

除非正在调试生成器本身，否则不要手动编辑生成文件。

## 推荐命令

编辑 `docs/config/` 或 packwiz 元数据后，生成所有产物：

```bash
python tools/refresh_modrinth_cache.py
python tools/update_project_data.py generate
```

提交前检查所有产物与一致性：

```bash
python tools/update_project_data.py check
```

`check` 命令会验证仓库内一致性不变量，并且不会写入生成产物、缓存或检查报告。它不会重新生成 `data/*.json` 或 `docs/*.md`。默认 CI check 不读取 Modrinth cache，也不会调用 Modrinth API；需要 Modrinth metadata 的重新生成/诊断步骤应在本地显式运行。

更详细的检查边界、表格和示例见 [`CHECK_MODEL.zh-CN.md`](CHECK_MODEL.zh-CN.md)。

## 生成数据语义

- `data/projects.json`：由 docs config 矩阵文件声明的默认项目。
- `data/optional.json`：由 docs config 声明的可选项目和替代项目。
- `data/dependencies.json`：由显式依赖生成步骤维护的 dependency-only 项目清单。默认 CI check 把它作为已提交的生成数据参与归类覆盖检查，不在 CI 中重新读取 Modrinth cache 推导。

检查器要求这些集合彼此不重叠，并验证：

- `projects.json + optional.json = docs/config project refs`
- `projects.json`、`optional.json`、`dependencies.json` 彼此不重叠
- `projects.json + dependencies.json = packwiz 默认安装项目 refs`，语义是“已安装项目归类覆盖”，不是“CI 临时重新推导依赖”
- 目标版本的 docs config 中不存在重复项目引用

## 脚本说明

### `update_project_data.py`

日常使用的主入口。

```bash
python tools/update_project_data.py generate
python tools/update_project_data.py check
```

也可以单独运行某个阶段：

```bash
python tools/update_project_data.py projects
python tools/update_project_data.py dependencies
python tools/update_project_data.py docs
```

单步命令会生成对应产物。普通 `generate` 只运行 `projects`、`dependencies` 和 `docs`。如果想确认生成是否带来变化，请运行生成命令后查看 `git diff`。

### `refresh_modrinth_cache.py`

刷新供生成和额外诊断使用的 Modrinth 元数据快照。

```bash
python tools/refresh_modrinth_cache.py
```

这个脚本是项目数据工具链中明确允许联网的入口。它会扫描 packwiz 元数据和 docs config 引用，刷新：

- `cache/modrinth/modrinth-version-dependencies.json`
- `cache/modrinth/modrinth-projects.json`
- `cache/modrinth/manifest.json`

如果 Modrinth 查询失败，脚本会失败并保留现有缓存文件不变。临时 API 错误不会被写入本地缓存；需要先重新刷新成功，再运行依赖缓存的生成或诊断。

常用模式：

```bash
# 只补齐缺失的快照数据。
python tools/refresh_modrinth_cache.py

# 重新拉取所有必需的 Modrinth version/project 条目。
python tools/refresh_modrinth_cache.py --force

# 只重建项目元数据，适合修改 project cache 字段后使用。
python tools/refresh_modrinth_cache.py --only-projects --force --verbose

# 只查看刷新范围，不联网也不写文件。
python tools/refresh_modrinth_cache.py --dry-run --verbose
```

这些缓存文件是生成产物，用于生成 `data/dependencies.json` 和补全项目元数据。它们是本地文件，被 git 忽略，也可以随时删除重建。默认 CI check 不依赖它们；需要更新时运行刷新脚本，不要手动编辑。

`modrinth-version-dependencies.json` 以 Modrinth version id 为 key，保存检查使用的锁定版本字段：project id、version number、loaders、files 和 version dependencies。`modrinth-projects.json` 使用规范化结构，避免重复保存项目对象：

```json
{
  "schema_version": 2,
  "projects": {
    "5faXoLqX": { "id": "5faXoLqX", "slug": "iceberg", "title": "Iceberg" }
  },
  "aliases": {
    "iceberg": "5faXoLqX"
  },
  "errors": {}
}
```

manifest 里的计数字段含义：

- `installed_projects`：从受支持项目目录扫描到的 packwiz 项目文件数量。
- `version_refs`：packwiz 元数据中唯一的已安装 Modrinth version id 数量。
- `version_cache_entries`：当前 `modrinth-version-dependencies.json` 中保存的条目数。
- `project_refs`：docs config、optional 条目、矩阵 alternatives、已安装锁定项目和 required dependency closure 共同需要的唯一项目查询引用数。
- `project_refs_to_fetch`：本次运行中缺失、错误或因 force 而需要重新拉取的项目查询引用数。
- `project_cache_projects`：`projects` 下保存的唯一项目元数据对象数量。
- `project_cache_aliases`：映射到 project id 的别名查询 key 数量，例如 slug。

### `generate_project_registry.py`

生成：

- `data/projects.json`
- `data/optional.json`

输入：

- `docs/config/**/matrix/*.json`
- `docs/config/**/optional.json`
- 本地 Modrinth 项目快照，用于补全项目元数据

这个脚本不需要实时网络访问。

### `generate_project_dependencies.py`

生成：

- `data/dependencies.json`

输入：

- `mods/`、`resourcepacks/`、`shaderpacks/`、`datapacks/` 等受支持项目目录中的 packwiz 元数据
- docs config 默认根项目、optional 分组和矩阵里的 alternatives
- Modrinth 版本依赖快照

生成不会联网或写入缓存；缺少必要快照数据时会提示先运行 `python tools/refresh_modrinth_cache.py`。默认 CI check 不运行 cache-backed 依赖重新生成。

### `generate_project_docs.py`

生成双语公开文档：

- `docs/mods.md`
- `docs/mods.zh-CN.md`
- `docs/resourcepacks.md`
- `docs/resourcepacks.zh-CN.md`
- `docs/shaderpacks.md`
- `docs/shaderpacks.zh-CN.md`
- `docs/datapacks.md`
- `docs/datapacks.zh-CN.md`

输入：

- `docs/config/**/meta.json`
- `docs/config/**/matrix/*.json`
- `docs/config/**/optional.json`
- 已生成的项目注册表

### `check_project_data.py`

检查生成数据、docs config、packwiz 元数据和项目唯一性。这个脚本只检查：不写文件、不读取 Modrinth cache，也不会访问 Modrinth API。

### `check_generated_docs.py`

检查生成 Markdown 文档，但不写文件。它会在内存中渲染预期 docs，并和已提交的 `docs/*.md` 文件对比。

`python tools/update_project_data.py check` 会运行两个检查脚本：仓库一致性检查和生成 docs 新鲜度检查。两个检查脚本都是只读的。

重要摘要字段：

- `unexplained`：packwiz 已安装，但未被 docs 或依赖数据解释的项目。
- `cache_errors`：尚未解决的 Modrinth 缓存/API 错误。
- `generated_data_invariants`：生成数据集合等式或互斥规则被破坏。
- `missing_defaults`：docs 默认项目没有安装进 packwiz。
- `unexpected_installed`：可选或替代项目被安装进默认包。
- `unknown_refs`：docs 引用没有进入生成注册表。
- `duplicate_refs`：同一个项目在目标版本 docs config 中出现多次。

### 共享 helper 模块

- `project_data_common.py`：共享文件系统、packwiz、Modrinth、依赖和 Markdown helper。
- `project_data_identity.py`：共享项目 identity 和引用解析 helper。
- `project_data_invariants.py`：生成数据集合不变量检查。

这些 helper 模块不应该直接运行。

## 推荐工作流

1. 优先编辑 `docs/config/`。
2. 如果新增或更新了 Modrinth 项目/version，运行 `python tools/refresh_modrinth_cache.py`。
3. 运行 `python tools/update_project_data.py generate`。
4. 如果检查器报告缺失或意外的 packwiz 项目，根据结果更新 packwiz 元数据。
5. 必要时再次刷新 Modrinth 快照并运行 `python tools/update_project_data.py generate`。
6. 提交前运行 `python tools/update_project_data.py check`。
