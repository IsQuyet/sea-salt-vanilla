# Sea Salt Vanilla 工具使用手册

[返回 README](../README.zh-CN.md)

所有命令都从仓库根目录通过同一个入口运行：

```bash
python tools/maintain.py <command>
```

## 数据模型

每个持久化来源只负责一种事实：

| 路径 | 用途 | 是否提交 |
| --- | --- | --- |
| `docs/config/` | 默认、可选和替代项目意图 | 是 |
| Packwiz `.pw.toml` 文件 | 已安装项目和平台锁定信息 | 是 |
| `data/project-metadata.json` | Modrinth 与 CurseForge 项目名称、slug 和页面 | 是 |
| `cache/modrinth/versions.json` | 可重建的 Modrinth 版本 owner、loaders 和 required 边 | 否 |
| `data/modrinth-dependencies.json` | 普通离线检查使用的最小 required 边 | 是 |
| `docs/*.md` | 自动生成的公开项目文档 | 是 |

项目元数据查询列表是全部文档项目与全部已安装项目的并集。依赖不会额外扩大查询根，因为已安装依赖已经出现在 Packwiz 中。

版本查询列表只包含 Packwiz 锁定的具体 Modrinth version ID。工具不分析 CurseForge 依赖，因此不维护 CurseForge 版本池。

inventory 在内存中推导 `default`、`optional`、`dependency`、`installed` 和 `unexplained`。规范身份是“平台 + 平台项目 ID”；这些分类不会写成独立注册表。

## 一致性规则

对于 `pack.toml` 声明的 Minecraft 版本：

- **P**：公开文档中的默认项目
- **O**：可选项目和 alternatives
- **D**：从 P 可达的 required dependency-only Modrinth 项目
- **A**：Packwiz 安装的全部项目

检查要求 P、O、D 两两不相交，并满足 `A = P union D`。这会识别缺失的默认项目、已安装的可选项目和孤立依赖。

依赖分析仅支持 Modrinth。具有依赖关系的 Mod 应优先使用 Modrinth。默认 CurseForge Mod 会产生 warning，因为工具无法验证其依赖闭包。

## 命令

| 命令 | 用途 | 写入 |
| --- | --- | --- |
| `python tools/maintain.py status` | 展示资源、平台、状态和健康数量 | 不写入 |
| `python tools/maintain.py check` | 执行离线一致性和文档检查 | 不写入 |
| `python tools/maintain.py check --deep` | 比较受跟踪依赖边与本地版本池 | 不写入 |
| `python tools/maintain.py refresh --scope projects` | 刷新 Modrinth 与 CurseForge 项目元数据 | `data/project-metadata.json` |
| `python tools/maintain.py refresh --scope versions` | 刷新已安装 Modrinth 版本事实 | `cache/modrinth/versions.json` |
| `python tools/maintain.py refresh` | 执行两个刷新范围 | 上述两个文件 |
| `python tools/maintain.py generate` | 重新生成依赖数据和公开文档 | `data/modrinth-dependencies.json`、`docs/*.md` |
| `python tools/maintain.py index` | 规范化 LF 行尾并执行 `packwiz refresh` | 发生变化的 LF 文件、`index.toml`、`pack.toml` |
| `python tools/maintain.py sync` | 执行 refresh、generate、index 和深度检查 | 上述全部输出 |

可使用 `--provider modrinth|curseforge|all`、`--scope projects|versions|all`、`--force` 或 `--dry-run` 控制刷新。报告命令支持 `--json`。

## 维护流程

| 改动 | 运行 |
| --- | --- |
| 只调整文档分类 | `generate`，然后 `check` |
| 修改 Packwiz 元数据或随包文件 | `index`，然后 `check` |
| 添加或更新 Modrinth 项目 | `refresh --provider modrinth`、`generate`、`index`，然后 `check --deep` |
| 添加 CurseForge 项目 | `refresh --provider curseforge --scope projects`、`generate`、`index`，然后 `check` |

CurseForge 项目刷新默认使用 CFWidget。设置 `CURSEFORGE_API_KEY` 或 `CF_API_KEY` 后会使用官方 API。

提交前运行：

```bash
python tools/maintain.py generate
python tools/maintain.py index
python tools/maintain.py check
python tools/maintain.py check --deep
git diff --check
```

## 模块边界

- `maintain.py`：CLI 和报告
- `inventory.py`：inventory 和一致性规则
- `dependencies.py`：纯 required 依赖分析
- `project_metadata.py`：项目元数据和平台查询
- `modrinth_versions.py`：本地 Modrinth 版本池
- `documents.py`：Markdown 生成与新鲜度检查
- `packwiz.py`：仓库路径、Packwiz 事实、行尾和索引刷新
