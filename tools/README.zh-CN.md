# Sea Salt Vanilla 工具使用手册

[English](README.md) | [简体中文](README.zh-CN.md)

本目录下的脚本用于维护整合包的生成项目数据和公开文档。所有命令都建议从仓库根目录运行。

## 真相源模型

- `docs/config/` 是公开项目矩阵的唯一真相源。
- `packwiz` 元数据代表实际安装事实，用于一致性检查。
- `data/*.json` 和 `docs/*.md` 是生成产物。

除非正在调试生成器本身，否则不要手动编辑生成文件。

## 推荐命令

编辑 `docs/config/` 或 packwiz 元数据后，生成所有产物：

```bash
python tools/update_project_data.py generate
```

提交前检查所有产物与一致性：

```bash
python tools/update_project_data.py check
```

`check` 命令会验证生成文件和一致性不变量，并且不会写入生成产物、缓存或检查报告。

## 生成数据语义

- `data/projects.json`：由 docs config 矩阵文件声明的默认项目。
- `data/optional.json`：由 docs config 声明的可选项目和替代项目。
- `data/dependencies.json`：packwiz 已安装、但不作为公开功能项展示的 dependency-only 项目。

检查器要求这些集合彼此不重叠，并验证：

- `projects.json + optional.json = docs/config project refs`
- `projects.json + dependencies.json = packwiz installed project refs`
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
python tools/update_project_data.py report
```

给单个阶段加上 `--check` 可以只检查该阶段是否最新，而不写入对应生成产物。

### `generate_project_registry.py`

生成：

- `data/projects.json`
- `data/optional.json`

输入：

- `docs/config/**/matrix/*.json`
- `docs/config/**/optional.json`
- 本地 Modrinth 项目缓存，用于补全项目元数据

这个脚本不需要实时网络访问。

### `generate_project_dependencies.py`

生成：

- `data/dependencies.json`

输入：

- `mods/`、`resourcepacks/`、`shaderpacks/`、`datapacks/` 等受支持项目目录中的 packwiz 元数据
- 已生成的项目注册表
- Modrinth 版本依赖缓存/API 数据

在生成模式下，这个脚本可能刷新本地依赖缓存。在检查模式下，它不会写入缓存。

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

检查生成数据、docs config、packwiz 元数据、依赖关系、缓存健康度和项目唯一性。

生成模式会写入供人工阅读的报告：

```text
reference/modrinth-collections/project-data-check.zh-CN.md
```

检查模式会打印同样的摘要，但不会写入报告或缓存文件。

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
2. 运行 `python tools/update_project_data.py generate`。
3. 如果检查器报告缺失或意外的 packwiz 项目，根据结果更新 packwiz 元数据。
4. 再次运行 `python tools/update_project_data.py generate`。
5. 提交前运行 `python tools/update_project_data.py check`。
