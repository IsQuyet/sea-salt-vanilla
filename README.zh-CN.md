# Sea Salt Vanilla

[English](README.md) | [简体中文](README.zh-CN.md)

海盐香草（Sea Salt Vanilla）是一个以客户端体验为核心的 Fabric 整合包，面向单人游玩与多人联机，改善日常 Minecraft 客户端体验。

目标很简单：**尽量保留原版体验的辨识度**，然后在画面、音效、交互、氛围和生活质量上偷偷加点料。就像给香草冰淇淋撒上一小撮海盐：还是香草，但你会怀疑它是不是偷偷升级了配方。

## 项目状态

- Loader：**Fabric**
- Minecraft：**1.21.1**
- 定位：**以客户端为主**
- 维护格式：**packwiz**（TOML 元数据，不直接提交 Mod jar）
- 版本控制：Git/GitHub

## 发布方式

- 发布版本会导出为 Modrinth `.mrpack` 包
- 必要时提供 CurseForge 包
- 版本更新说明发布在 GitHub Releases 与 Modrinth 版本页面

## 项目文档

- [模组](docs/mods.zh-CN.md)
- [资源包](docs/resourcepacks.zh-CN.md)
- [光影包](docs/shaderpacks.zh-CN.md)
- [数据包](docs/datapacks.zh-CN.md)
- [工具使用手册](tools/README.zh-CN.md)

## 数据与工具工作流

公开项目矩阵的唯一真相源是 `docs/config/`。`data/` 下的注册表和 `docs/*.md` 下的公开文档都是生成产物，不建议手动编辑。

推荐命令：

```bash
python tools/update_project_data.py generate
python tools/update_project_data.py check
```

- `generate` 会更新项目注册表、依赖数据和公开文档。
- `check` 会验证生成文件、docs config、packwiz 元数据、依赖数据和项目唯一性，并且不写入生成产物。

当前生成数据的语义：

- `data/projects.json`：由 `docs/config/**/matrix/*.json` 声明的默认项目生成。
- `data/optional.json`：由 `docs/config/**/optional.json` 和矩阵 alternatives 声明的可选/替代项目生成。
- `data/dependencies.json`：packwiz 已安装、但不作为公开功能项展示的 dependency-only 项目。

packwiz 元数据代表实际安装事实，用于一致性检查。如果文档与 packwiz 不一致，优先修正 `docs/config/`，然后运行检查，再根据检查结果补装或移除 packwiz 项目。

## 目录约定

```text
sea-salt-vanilla/
|-- mods/                 # Mod 的 packwiz 元数据
|-- resourcepacks/        # 资源包的 packwiz 元数据
|-- shaderpacks/          # 光影包的 packwiz 元数据
|-- datapacks/            # 数据包内容与 packwiz 元数据
|-- config/               # 随包分发的游戏配置
|-- defaultconfigs/       # 创建新世界时复制的默认配置
|-- docs/
|   |-- config/
|   |   `-- <category>/                # mods、resourcepacks、shaderpacks 等
|   |       |-- meta.json              # 生成文档的元数据
|   |       |-- matrix/*.json          # 文档可见项目矩阵
|   |       `-- optional.json          # 已记录的可选项目
|   `-- *.md                           # 自动生成的公开文档
|-- data/
|   |-- projects.json                  # 自动生成的可见项目注册表
|   |-- optional.json                  # 自动生成的可选/替代项目注册表
|   `-- dependencies.json              # 自动生成的 dependency-only 注册表
`-- tools/                             # 生成和检查脚本
```

## 致谢

海盐香草（Sea Salt Vanilla）之所以能够存在，不仅因为 Minecraft 本身提供了一个值得被反复游玩的世界，也因为像 Sodium、Iris 这样的开源项目，以及许多长期近乎无偿投入时间、技术和维护工作的开发者，让这个世界变得更流畅、更漂亮、更易用。它们并不只是方便下载的文件；它们背后是真实的人、真实的劳动，以及很多时候并不轻松的坚持。

如果这个整合包让你更享受 Minecraft，也希望你能花一点时间了解它所使用的项目，在合适的地方留下善意反馈，负责任地报告问题，并在能力范围内支持原作者。哪怕只是多一点关注和感谢，也能让这个社区变得更健康一点。

## 许可证说明

本仓库计划仅包含整合包配置、元数据、文档，以及为本整合包制作的自定义脚本/资源。第三方 Mod、资源包、光影、数据包和其他外部内容的版权归其原作者所有，并遵循各自许可证。
