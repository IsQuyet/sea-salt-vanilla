# Mod 功能矩阵

[English](mod-matrix.md) | [简体中文](mod-matrix.zh-CN.md)

这页跟踪每个已发布 Minecraft 版本中，由哪个 Mod 提供对应功能。章节用于归类相关功能，表格行描述具体功能，版本列填写该版本使用的 Mod。

## 基础必备

这些条目提供整合包运行、渲染、性能和配置所需的基础能力。

### 运行时与 API

这些条目提供其他 Mod 需要的加载器 API 和语言运行时。


| 功能            | 1.21.1                 |
| ------------- | ---------------------- |
| Fabric API 支持 | Fabric API             |
| Kotlin 运行时    | Fabric Language Kotlin |


### 渲染基础

这些条目替换原版渲染，或保持 Fabric 渲染特性兼容。


| 功能                      | 1.21.1 |
| ----------------------- | ------ |
| 渲染引擎                    | Sodium |
| Fabric Rendering API 兼容 | Indium |


### 性能优化

这些条目改善帧率稳定性、内存使用、光照、网络和渲染开销。


| 功能       | 1.21.1                  |
| -------- | ----------------------- |
| 游戏逻辑优化   | Lithium                 |
| 启动与内存修复  | ModernFix               |
| 即时渲染优化   | ImmediatelyFast         |
| 网络栈优化    | Krypton                 |
| 光照引擎优化   | ScalableLux             |
| 实体渲染剔除   | Entity Culling          |
| 通用渲染剔除   | More Culling            |
| 方块实体渲染优化 | Enhanced Block Entities |
| 树叶渲染剔除   | Cull Leaves             |
| 粒子性能优化   | AsyncParticles          |


### 包管理

这些条目用于发现、加载或管理资源包和全局包。


| 功能    | 1.21.1       |
| ----- | ------------ |
| 资源包浏览 | Resourcify   |
| 全局包加载 | Global Packs |


### Mod 管理与配置

这些条目提供 Mod 列表、游戏内配置界面，以及其他 Mod 使用的配置框架。


| 功能                | 1.21.1                |
| ----------------- | --------------------- |
| Mod 列表与配置入口       | Mod Menu              |
| 游戏内配置界面           | Configured            |
| YACL 配置框架         | YetAnotherConfigLib   |
| Cloth Config 配置框架 | Cloth Config          |
| Forge 配置兼容        | Forge Config API Port |


## 视听美化

这些条目通过画面、声音、动画和呈现方式提升沉浸感。

### OptiFine 功能平替

这些条目通过 Fabric 友好的 Mod 提供类似 OptiFine 的视觉和资源包功能。


| 功能                 | 1.21.1                  |
| ------------------ | ----------------------- |
| 光影加载               | Iris                    |
| Sodium 视频选项扩展      | Sodium Extra            |
| Complementary 光影扩展 | Euphoria Patcher        |
| 自定义实体模型            | Entity Model Features   |
| 自定义实体纹理            | Entity Texture Features |
| 自定义物品纹理            | CIT Resewn              |
| 连接纹理               | Continuity              |
| 自定义 GUI 资源包支持      | OptiGUI                 |


### 视距与世界呈现

这些条目从客户端侧让世界显得更广阔或更连续。


| 功能     | 1.21.1           |
| ------ | ---------------- |
| 远景地形渲染 | Distant Horizons |


### 视觉效果

这些条目添加客户端氛围、粒子和细节视觉反馈。


| 功能      | 1.21.1                   |
| ------- | ------------------------ |
| 氛围粒子    | Visuality                |
| 细节视觉效果  | Subtle Effects           |
| 额外粒子效果  | Particle Effects         |
| 粒子交互    | EG Particle Interactions |
| 气泡破裂效果  | Make Bubbles Pop         |
| 落叶粒子    | Falling Leaves           |
| 爆炸效果    | Explosive Enhancement    |
| 挖掘视觉反馈  | Mining Quakes            |
| 沉浸式视觉效果 | Perception               |


### 音效

这些条目添加环境音，并改善游戏中的声音事件感受。


| 功能     | 1.21.1             |
| ------ | ------------------ |
| 环境音景   | AmbientSounds      |
| 脚步声    | Presence Footsteps |
| 声音事件改进 | Sounds             |


### 动画与移动

这些条目改善第一人称、第三人称、物品、方块和移动表现。


| 功能       | 1.21.1                |
| -------- | --------------------- |
| 玩家动画     | Not Enough Animations |
| 进食动画     | Eating Animation      |
| 物品掉落物理   | ItemPhysic Lite       |
| 方块放置动画   | A Good Place          |
| 第一人称物品动画 | Hold My Items         |
| 手持物品显示   | YDM's Weapon Master   |
| 镜头运动     | Camera Overhaul       |
| 鞘翅飞行控制   | Do a Barrel Roll      |


### 界面美化

这些条目调整菜单、UI 动效、文字渲染和界面布局。


| 功能            | 1.21.1               |
| ------------- | -------------------- |
| 纸娃娃显示         | Paper Doll           |
| 状态效果折叠        | Mini Effects         |
| 背包物品动画        | Tiny Item Animations |
| HUD 位置调整      | Raised               |
| UI 背景模糊       | Blur                 |
| 平滑滚动          | Smooth Scroll        |
| 平滑 GUI 动画     | Smooth GUI           |
| 现代 UI 框架与文字渲染 | Modern UI            |
| 沉浸式 UI 交互     | Immersive UI         |


### 聊天与社交 UI

这些条目改善聊天可读性和呈现方式，不要求服务器添加玩法内容。


| 功能     | 1.21.1         |
| ------ | -------------- |
| 聊天头像   | Chat Heads     |
| 聊天消息动画 | Chat Animation |


### 皮肤与外观

这些条目改善玩家皮肤、披风和外观显示。


| 功能      | 1.21.1           |
| ------- | ---------------- |
| 3D 皮肤层  | 3D Skin Layers   |
| 披风物理效果  | WaveyCapes       |
| 披风来源支持  | Capes            |
| 自定义皮肤加载 | CustomSkinLoader |


## 实用功能

这些条目让信息查询、导航、控制、多人体验和创造/诊断工作流更方便。

### 查询、背包与控制

这些条目改善物品查询、背包交互、控制和输入处理。


| 功能        | 1.21.1                  |
| --------- | ----------------------- |
| 物品与配方浏览   | Roughly Enough Items    |
| 方块与实体信息浮层 | Jade                    |
| 食物数值显示    | AppleSkin               |
| 潜影盒预览     | Shulker Box Tooltip     |
| 背包配置与整理   | Inventory Profiles Next |
| 鼠标背包操作    | Mouse Tweaks            |
| 打开背包时移动   | InvMove                 |
| 键位搜索与冲突提示 | Controlling             |
| 输入法冲突处理   | IMBlocker               |
| 缩放控制      | Zoomify                 |


### HUD 信息与客户端便利功能

这些条目展示游戏信息，或减少界面操作中的小摩擦。


| 功能        | 1.21.1                       |
| --------- | ---------------------------- |
| 高级 HUD 浮层 | MiniHUD                      |
| 背包 HUD 浮层 | Inventory HUD+               |
| 骑乘 HUD 改进 | Better Mount HUD             |
| 统计界面改进    | Better Stats                 |
| 盔甲细节显示    | Detail Armor Bar             |
| 动态准星      | Dynamic Crosshair            |
| 可拖动资源包列表  | Draggable Lists              |
| 自定义世界警告隐藏 | Disable Custom Worlds Advice |


### 地图与导航

这些条目提供客户端小地图、世界地图和位置呈现工具。


| 功能    | 1.21.1            |
| ----- | ----------------- |
| 小地图   | Xaero's Minimap   |
| 世界地图  | Xaero's World Map |
| 位置标题卡 | Traveler's Titles |


### 可选多人功能

这些条目在兼容的多人服务器上效果更完整。


| 功能         | 1.21.1            |
| ---------- | ----------------- |
| 近距离语音聊天    | Simple Voice Chat |
| 服务器资源包解包   | Server Unpacker   |
| 多人服务器客户端增强 | Noxesium          |


### 创造工具与诊断

这些条目用于建造、测试、性能分析或个人创造工作流。


| 功能       | 1.21.1    |
| -------- | --------- |
| 性能分析     | Spark     |
| 世界编辑     | WorldEdit |
| 创造模式建造工具 | LotTweaks |


