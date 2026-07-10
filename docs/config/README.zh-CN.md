# 文档配置

这个目录是公开项目表格的人工维护源。仓库目前只面向 `pack.toml` 声明的
Minecraft 版本，因此每一行直接使用 `selected` 和 `alternatives`，不再维护
版本映射。

## 项目引用

项目引用保持紧凑：

```json
{ "source": "modrinth", "slug": "fabric-api" }
```

- `source` 只能是 `modrinth` 或 `curseforge`。
- `selected` 始终是列表，包含一个功能的全部默认实现。
- `alternatives` 使用相同结构表示可选替代。
- 不要把显示名称复制进矩阵引用；应刷新项目元数据。

规范身份是“平台 + 平台项目 ID”。slug 只用于查询和展示，不是身份。同一
平台项目不能重复声明；工具也不会猜测两个平台上的项目是否等价。

## Inventory 契约

维护 inventory 在内存中推导四个集合：

- **P**：非 optional 矩阵选择的默认项目。
- **O**：可选选择与 alternatives。
- **D**：从 P 可达的 required dependency-only Modrinth 项目。
- **A**：packwiz 安装的全部项目。

检查要求 P、O、D 两两不相交，并满足 `A = P union D`。因此，移除默认项目
后遗留在 packwiz 中、且不再被其他项目需要的依赖会被识别出来。

依赖分析有意限定为 Modrinth-only。具有外部依赖的 Mod 应优先使用
Modrinth。CurseForge 仍可用于直接项目和自包含资源，但默认 CurseForge Mod
会被标记为依赖闭包未验证。

## 目录结构

每个包含 `meta.json` 的分类目录会渲染为 `docs/<分类名>.md` 和
`docs/<分类名>.zh-CN.md`。

- `meta.json`：双语标题和介绍。
- `matrix/*.json`：按顺序渲染的默认功能组。
- `optional.json`：不默认分发的可选功能。

持久化辅助数据一份文件只负责一种事实：

- `data/project-metadata.json`：受跟踪的规范 slug、名称和项目页面。
- `data/modrinth-dependencies.json`：普通离线检查使用的 required 边。
- `cache/modrinth/versions.json`：忽略提交的本地平台版本事实。

P、O、D、A 这些 inventory 分类不会再写成独立注册表。

## 命令

```bash
python tools/maintain.py status
python tools/maintain.py check
python tools/maintain.py refresh --dry-run
python tools/maintain.py refresh
python tools/maintain.py generate
python tools/maintain.py index
```

- `status` 只读展示资源类型、平台和状态数量。
- `check` 是普通的离线、无缓存一致性检查。
- `check --deep` 额外比较受跟踪依赖快照和本地版本池。
- `refresh` 查询平台元数据；可按需使用 `--provider`、`--scope`、`--force` 或 `--dry-run`。
- `generate` 写入依赖快照和公开 Markdown。
- `index` 规范化 LF 行尾并刷新 packwiz 索引。
- `sync` 依次执行 refresh、generate、index 和深度检查。

所有报告命令都支持 `--json` 机器可读输出。
