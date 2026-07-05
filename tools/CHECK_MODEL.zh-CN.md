# CI 检查模型与数据流说明

本文档说明项目数据脚本在 CI 中应该回答哪些问题、读取哪些输入，以及哪些步骤不应该依赖 Modrinth API 或本地 Modrinth cache。

## 核心边界

CI 的 `python tools/update_project_data.py check` 应该是一组只读检查：

- 不调用 Modrinth API。
- 不读取 `cache/modrinth/*.json` 作为必需输入。
- 不写入 `data/`、`docs/` 或 `cache/` 中的产物。
- 只检查已经提交到仓库里的 docs config、generated data、docs markdown 和 packwiz 元数据是否互相解释得通。

需要 Modrinth metadata 的步骤应该放在显式刷新/生成流程中：

```bash
python tools/refresh_modrinth_cache.py
python tools/update_project_data.py generate
```

换句话说，cache 的作用是帮助生成 `data/dependencies.json` 和补全项目元数据，不应该成为普通 CI check 的隐式前提。

## 为什么之前的 check 还依赖 Modrinth cache

之前 `check_project_data.py --check` 会计算这些内容：

- installed project 的 `required_by` 关系；
- 当前 packwiz 是否缺少某个 Modrinth required dependency；
- dependency cache/project cache 是否有错误；
- 某些 packwiz 目录和 Modrinth version loader 是否不匹配。

这些问题都需要读取 Modrinth version/project metadata，所以会间接依赖：

- `cache/modrinth/modrinth-version-dependencies.json`
- `cache/modrinth/modrinth-projects.json`

它们适合放在本地 refresh/generate 或额外诊断里，不适合成为 CI 基础检查的必要条件。

## CI check 当前应该运行的阶段

| 阶段 | 是否属于默认 CI | 是否需要 Modrinth cache/API | 回答的问题 |
| --- | --- | --- | --- |
| `check_project_data.py` | 是，属于核心 check | 不需要 | packwiz、docs config、`data/*.json` 之间的归类和集合关系是否成立 |
| `check_generated_docs.py` | 是，属于 docs 防手改 guard | 不需要 | 生成 Markdown 是否被人工直接改过；脚本只比较内存渲染结果，不写文件 |
| `generate_project_registry.py` | 否，属于 generate | 需要 project snapshot 才能补全 enriched data | 生成 `data/projects.json` / `data/optional.json` |
| `generate_project_dependencies.py` | 否，属于 generate | 需要 version/project snapshot | 生成 `data/dependencies.json` |

如果需要确认生成是否会带来变化，应在本地运行生成命令后查看 diff：

```bash
python tools/update_project_data.py generate
git diff
```

## 检查项表格

| 检查项 | 输入 | 是否依赖 cache/API | 示例 | 失败时说明 |
| --- | --- | --- | --- | --- |
| docs markdown 是否最新 | `docs/config/`、`data/projects.json`、`data/optional.json`、`docs/*.md` | 否 | 修改了矩阵标题但没重新生成 `docs/mods.md` | 需要运行 docs 生成 |
| 默认项目是否安装 | `docs/config/`、`data/projects.json`、packwiz `*.pw.toml` | 否 | docs 里声明 Sodium 是默认项目，但 `mods/sodium.pw.toml` 不存在 | packwiz 缺默认项目，或 docs/data stale |
| 可选/替代项目是否意外安装 | `docs/config/`、`data/optional.json`、packwiz `*.pw.toml` | 否 | 某项目在 optional group 里，但默认包安装了它 | 应移出默认包，或改成默认项目 |
| generated data 集合是否互斥 | `data/projects.json`、`data/optional.json`、`data/dependencies.json` | 否 | 同一个 slug 同时出现在 projects 和 dependencies | 项目归类冲突 |
| packwiz 项目是否全部被解释 | `data/projects.json`、`data/dependencies.json`、packwiz `*.pw.toml` | 否 | packwiz 装了一个项目，但它既不是默认项目，也不在 dependencies | 需要补文档、补 dependency 生成结果，或移除多余安装 |
| 缺失 Modrinth required dependency | packwiz `*.pw.toml`、Modrinth version metadata | 是 | 已安装的某个 mod 声明 require Cloth Config，但 packwiz 没安装 | 应在 refresh/generate 或额外诊断中检查，不放入无缓存 CI |
| Modrinth version loader 是否匹配目录 | packwiz `*.pw.toml`、Modrinth version metadata | 是 | datapack 目录里的条目对应 version 没有 datapack loader | 需要 cache，不放入无缓存 CI |
| cache 健康度 | `cache/modrinth/*.json` | 是 | cache 中有 API error entry | 属于 refresh 质量问题，不属于基础 CI check |

## 例子

### 例 1：文档默认项目缺安装

docs config 中写了：

```json
{
  "selected": "sodium"
}
```

但 packwiz 没有对应的 `mods/sodium.pw.toml`。

CI check 应该失败，因为它回答的是：

> 文档声明的默认项目是否真实安装？

这个问题不需要 Modrinth cache。

### 例 2：packwiz 出现未解释项目

packwiz 有：

```text
mods/example-library.pw.toml
```

但这个项目既没有在 `data/projects.json`，也没有在 `data/dependencies.json`。

CI check 应该失败，因为它回答的是：

> 默认包里安装的项目是否都有身份归类？

这个检查只看仓库内已经提交的数据，不重新请求 Modrinth。

### 例 3：dependency 需要更新

某个已安装 mod 的新版新增了 required dependency。这个事实需要 Modrinth version metadata 才能知道。

这不应该由普通 CI check 临时推导。正确流程是：

```bash
python tools/refresh_modrinth_cache.py
python tools/update_project_data.py generate
python tools/update_project_data.py check
```

这样 `data/dependencies.json` 会作为已提交生成产物参与 CI，而不是 CI 每次依赖本地 cache 重新推导。

## 依赖语义待确认项

`data/dependencies.json` 如果继续从 packwiz + Modrinth dependency metadata 生成，那么它更像：

> packwiz-derived dependency-only classification report

也就是“当前默认包里安装的项目中，哪些不是文档默认项目，但能被 required dependency 关系解释”。

此时这条关系：

```text
data/projects.json + data/dependencies.json == packwiz installed set
```

应该命名为“已安装项目归类覆盖检查”，而不是“期望安装集检查”。它检查的是 packwiz 里的项目是否都能被解释，而不是拿 packwiz 生成一个列表再证明 packwiz 等于自己。
