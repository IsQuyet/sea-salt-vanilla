# Immersive Vanilla

[English](README.md) | [简体中文](README.zh-CN.md)

沉浸式香草（Immersive Vanilla）是一个以客户端体验为主的 Fabric 整合包，用于增强原版 Minecraft 体验，而不要求服务器添加新的玩法内容。

目标很简单：**尽量保留原版体验的辨识度**，然后在画面、音效、交互、氛围和生活质量上偷偷加点料。就像往香草冰淇淋里撒一小撮海盐：还是香草，但你会怀疑它是不是偷偷升级了配方。

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

## 目录约定

```text
mods/            # Mod，packwiz 元数据或本地文件
config/          # 随包分发的客户端/通用配置
defaultconfigs/  # 创建新世界时复制的默认配置
resourcepacks/   # 资源包，packwiz 元数据或本地文件
shaderpacks/     # 光影包，packwiz 元数据或本地文件
dist/            # 本地导出产物，不提交
```

## 许可证说明

本仓库计划仅包含整合包配置、元数据、文档，以及为本整合包制作的自定义脚本/资源。第三方 Mod、资源包、光影、数据包和其他外部内容的版权归其原作者所有，并遵循各自许可证。
