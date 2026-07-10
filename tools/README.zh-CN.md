# Sea Salt Vanilla 工具使用手册

[返回 README](../README.zh-CN.md)

所有命令都从仓库根目录运行。本手册只保留日常维护会用到的核心流程。

## 改动应该放在哪里

| 路径 | 作用 | 是否手动维护 |
| --- | --- | --- |
| `docs/config/` | 公开分类：功能行、可选项目、替代项目和展示顺序 | 是 |
| `mods/`、`resourcepacks/`、`shaderpacks/`、`datapacks/`、`plugins/` | 默认 packwiz 项目。这些目录里的 `.pw.toml` 表示项目会默认分发 | 是 |
| `cache/modrinth/`、`cache/curseforge/` | 生成步骤使用的本地平台元数据缓存 | 否。刷新即可，不要提交 |
| `data/projects.json` | 生成的默认分发项目目录 | 否 |
| `data/optional.json` | 生成的可选项目和替代项目目录 | 否 |
| `data/dependencies.json` | 生成的仅依赖项目目录 | 否 |
| `data/project-catalog.json` | 生成的全版本文档项目元数据目录 | 否 |
| `data/modrinth-locks.json` | 生成的当前 packwiz Modrinth 锁定版本最小 required 依赖图 | 否 |
| `docs/*.md` | 生成的公开文档 | 否 |

## 元数据归属与缓存模型

每类来源只负责一件事：

- `docs/config/` 声明项目意图：功能定位、默认或可选状态，以及替代项目。
- packwiz `.pw.toml` 声明安装事实：平台项目 ID，以及锁定的版本或文件。
- 平台项目缓存提供规范的 `id`、`slug`、`name`、`type` 元数据。
- Modrinth version cache 只提供锁定版本的 loader 与依赖关系。

不同来源发生矛盾时会直接报错，不通过隐含优先级静默选择某一边。

Modrinth 与 CurseForge 缓存仍分别存放在各自的平台目录，但项目条目使用相同的最小结构：

```json
{
  "id": "417768",
  "slug": "lottweaks",
  "name": "LotTweaks",
  "type": "mod"
}
```

Modrinth version cache 只保留 `project_id`、`loaders`、`dependencies`；每项依赖只保留 `project_id` 和 `dependency_type`。它是 packwiz 当前锁定 release 的本地快照。生成步骤会把 required 边投影到受版本控制的 `data/modrinth-locks.json`，因此普通检查不需要平台缓存或网络，也能重新计算依赖闭包。两个刷新命令仍写入各自的 manifest 文件，但 summary 结构一致。

项目刷新计划只由全部文档项目和全部 packwiz 已安装项目控制，依赖关系不会再扩大项目查询根。已知的 ID 与 slug 坐标会在平台内归并为逻辑项目，并优先使用平台 ID。项目缓存是这些查询根的快照，不再额外持久化可推导的 alias 表。

## 项目数据契约

生成数据包含四个语义集合。集合比较使用“平台 + 平台项目 ID”，而不是本地 packwiz 文件名：

- **P**：目标版本非 optional 矩阵中的默认项目，存放在 `data/projects.json`。
- **O**：目标版本 optional 选择与 alternatives，存放在 `data/optional.json`。
- **D**：从 P 和具体 packwiz Modrinth 版本锁推导出的 required dependency-only 闭包，存放在 `data/dependencies.json`。
- **A**：packwiz 当前安装的全部项目。

检查器强制以下规则：

```text
P 与 O 不相交
P 与 D 不相交
O 与 D 不相交
A = P ∪ D
```

这正是遗留依赖检测的基础：移除一个默认项目后，如果它留下的依赖不再被其他默认项目需要，该项目就会落在 `P ∪ D` 之外，并被报告为 `unexplained`。

`data/project-catalog.json` 有意与 P/O 分离。它保存所有被渲染 Minecraft 版本引用的规范项目元数据，因此历史版本文档仍然完整，而 P/O 只描述当前目标版本。

依赖分析有意限定为 Modrinth-only。项目同时存在于两个平台时，尤其是具有依赖的 Mod，优先使用 Modrinth 来源。CurseForge 仍支持直接项目和自包含资源，但在不使用 CurseForge API 的前提下，检查器无法证明它们的依赖闭包。如果必须使用 CurseForge 来源，优先选择没有已知外部 Mod 依赖的资源。平台专属依赖 ID 不会被视为跨平台项目身份。

## 添加默认 Modrinth 项目

当一个项目应该进入默认整合包，并且需要写进矩阵时，使用这个流程。

```bash
packwiz modrinth install <slug> --yes
python tools/refresh_modrinth_cache.py
# 编辑 docs/config/**/matrix/*.json
python tools/update_project_data.py generate
python tools/refresh_packwiz.py
python tools/update_project_data.py check
git diff --check
```

顺序很重要：

- 先安装，让 packwiz 记录项目和锁定版本。
- 生成前刷新 Modrinth 缓存，让依赖数据可用。
- 先改矩阵再运行 `generate`，让公开文档说明项目为什么默认分发。
- 最后运行 `python tools/refresh_packwiz.py` 和 `check`，更新索引并验证一致性。

## 添加默认 CurseForge 项目

当项目只在 CurseForge 提供时，使用这个流程。

```bash
packwiz curseforge add <slug-or-url> --yes
# 编辑 docs/config/**/matrix/*.json
python tools/refresh_curseforge_cache.py
python tools/update_project_data.py generate
python tools/refresh_packwiz.py
python tools/update_project_data.py check
git diff --check
```

CurseForge 刷新默认使用无需密钥的 CFWidget 元数据接口。如果配置了
`CURSEFORGE_API_KEY` 或 `CF_API_KEY`，则改用 CurseForge 官方 API。按 slug
查询时会保留矩阵中的项目类型，使模组、资源包、光影包、数据包和插件使用
正确的 CurseForge 分类路径。

## 把默认项目移到可选

当一个项目仍然被整合包认可，但不应该默认分发时，使用这个流程。

```bash
# 从 docs/config/**/matrix/*.json 移除项目
# 添加到 docs/config/**/optional.json
git rm <packwiz-project-file>.pw.toml
python tools/update_project_data.py generate
python tools/refresh_packwiz.py
python tools/update_project_data.py check
git diff --check
```

删除默认 `.pw.toml`；否则项目仍会默认分发。

## 只调整文档分类

如果没有改变实际安装的项目版本，只改分类或矩阵说明，使用这个流程。

```bash
# 编辑 docs/config/**/*.json
python tools/update_project_data.py generate
python tools/update_project_data.py check
git diff --check
```

只有当生成命令提示缺少 Modrinth cache 条目时，才需要先运行 `python tools/refresh_modrinth_cache.py`。

## 修改 packwiz 或随包分发配置

修改 packwiz metadata 或通过 packwiz 分发的配置文件后，使用这个流程。

```bash
python tools/refresh_packwiz.py
python tools/update_project_data.py check
git diff --check
```

如果新增或更新了 Modrinth 项目版本，还需要刷新 Modrinth cache 并重新生成数据和文档：

```bash
python tools/refresh_modrinth_cache.py
python tools/update_project_data.py generate
python tools/refresh_packwiz.py
python tools/update_project_data.py check
git diff --check
```

## 命令速查

| 命令 | 用途 | 是否写文件 |
| --- | --- | --- |
| `python tools/update_project_data.py generate` | 重新生成 `data/*.json` 和公开文档 | 是 |
| `python tools/update_project_data.py projects` | 重新生成 P、O 和全版本项目目录 | 是 |
| `python tools/update_project_data.py locks` | 从本地版本缓存重新生成受跟踪的 Modrinth 锁图 | 是 |
| `python tools/update_project_data.py dependencies` | 根据 P 和受跟踪的 Modrinth 锁图重新计算 D | 是 |
| `python tools/update_project_data.py docs` | 根据全版本项目目录重新生成公开 Markdown | 是 |
| `python tools/update_project_data.py check` | 检查 docs config、生成数据、packwiz 元数据和生成文档 | 否 |
| `python tools/refresh_modrinth_cache.py` | 新增或更新 Modrinth 项目版本后刷新本地元数据；生成命令提示缺缓存时也运行 | 是，仅缓存 |
| `python tools/refresh_curseforge_cache.py` | 通过 CFWidget 刷新本地 CurseForge 项目元数据；配置密钥时改用官方 API | 是，仅缓存 |
| `python tools/normalize_line_endings.py` | 在 hash 敏感操作前，把 Git 管理为 `eol=lf` 的文件规范化为 LF | 是，仅行尾 |
| `python tools/normalize_line_endings.py --check` | 检查工作区里需要行尾规范化的 `eol=lf` 文件 | 否 |
| `python tools/refresh_packwiz.py` | 先规范化 LF-managed 文件，再刷新 `index.toml` 和 `pack.toml` 里的 index hash | 是 |

辅助脚本：

- `generate_project_registry.py`：写出 `data/projects.json`、`data/optional.json` 和 `data/project-catalog.json`
- `generate_modrinth_locks.py`：根据本地 Modrinth version cache 写出 `data/modrinth-locks.json`
- `generate_project_dependencies.py`：写出 `data/dependencies.json`
- `generate_project_docs.py`：写出公开 Markdown 文档
- `refresh_curseforge_cache.py`：缓存规范化的 CurseForge 项目 ID、slug、名称和类型，不下载项目文件
- `check_project_data.py`：检查 docs config、生成数据和 packwiz 元数据
- `check_generated_docs.py`：检查生成 Markdown 是否新鲜

## 常见检查失败

- `missing_defaults`：默认矩阵声明了项目，但 packwiz 没有安装。
- `unexpected_installed`：可选或替代项目被安装进默认包。
- `unexplained`：packwiz 安装了项目，但它既不是默认文档项目，也不是 dependency-only 项目。
- `generated_data_invariants`：P、O、D、A 违反了不相交、身份、目录或 `A = P ∪ D` 规则。
- `modrinth_lock_conflicts`：受跟踪的 Modrinth 锁图已过期，或与当前 packwiz 版本锁不一致。
- `dependency_closure_conflicts`：`data/dependencies.json` 与从 P 重新计算的 required Modrinth 闭包不一致。
- `unknown_refs`：docs config 引用了没有进入生成注册表的项目。
- `duplicate_refs`：同一个项目在目标版本 docs config 中出现多次。
- `installed_identity_conflicts`：packwiz 文件重复声明平台 ID 或 slug，或者同一文件同时声明两个平台。

提交前检查 diff，只提交真实内容改动。Windows 换行提示不等于实际 diff；以 `git diff` 是否有 patch 为准。
