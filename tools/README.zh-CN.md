# Sea Salt Vanilla 工具使用手册

[返回 README](../README.zh-CN.md)

所有命令都从仓库根目录运行。本手册只保留日常维护会用到的核心流程。

## 改动应该放在哪里

| 路径 | 作用 | 是否手动维护 |
| --- | --- | --- |
| `docs/config/` | 公开分类：功能行、可选项目、替代项目和展示顺序 | 是 |
| `mods/`、`resourcepacks/`、`shaderpacks/`、`datapacks/` | 默认 packwiz 项目。这些目录里的 `.pw.toml` 表示项目会默认分发 | 是 |
| `cache/modrinth/`、`cache/curseforge/` | 生成步骤使用的本地平台元数据缓存 | 否。刷新即可，不要提交 |
| `data/projects.json` | 生成的默认分发项目目录 | 否 |
| `data/optional.json` | 生成的可选项目和替代项目目录 | 否 |
| `data/dependencies.json` | 生成的仅依赖项目目录 | 否 |
| `docs/*.md` | 生成的公开文档 | 否 |

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
| `python tools/update_project_data.py check` | 检查 docs config、生成数据、packwiz 元数据和生成文档 | 否 |
| `python tools/refresh_modrinth_cache.py` | 新增或更新 Modrinth 项目版本后刷新本地元数据；生成命令提示缺缓存时也运行 | 是，仅缓存 |
| `python tools/refresh_curseforge_cache.py` | 通过 CFWidget 刷新本地 CurseForge 项目元数据；配置密钥时改用官方 API | 是，仅缓存 |
| `python tools/normalize_line_endings.py` | 在 hash 敏感操作前，把 Git 管理为 `eol=lf` 的文件规范化为 LF | 是，仅行尾 |
| `python tools/normalize_line_endings.py --check` | 检查工作区里需要行尾规范化的 `eol=lf` 文件 | 否 |
| `python tools/refresh_packwiz.py` | 先规范化 LF-managed 文件，再刷新 `index.toml` 和 `pack.toml` 里的 index hash | 是 |

辅助脚本：

- `generate_project_registry.py`：写出 `data/projects.json` 和 `data/optional.json`
- `generate_project_dependencies.py`：写出 `data/dependencies.json`
- `generate_project_docs.py`：写出公开 Markdown 文档
- `refresh_curseforge_cache.py`：缓存 CurseForge 项目名称、ID、slug 和链接，不下载项目文件
- `check_project_data.py`：检查 docs config、生成数据和 packwiz 元数据
- `check_generated_docs.py`：检查生成 Markdown 是否新鲜

## 常见检查失败

- `missing_defaults`：默认矩阵声明了项目，但 packwiz 没有安装。
- `unexpected_installed`：可选或替代项目被安装进默认包。
- `unexplained`：packwiz 安装了项目，但它既不是默认文档项目，也不是 dependency-only 项目。
- `unknown_refs`：docs config 引用了没有进入生成注册表的项目。
- `duplicate_refs`：同一个项目在目标版本 docs config 中出现多次。

提交前检查 diff，只提交真实内容改动。Windows 换行提示不等于实际 diff；以 `git diff` 是否有 patch 为准。
