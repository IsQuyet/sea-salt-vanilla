# Mod feature matrix

[English](mod-matrix.md) | [简体中文](mod-matrix.zh-CN.md)

This page tracks which mod provides each feature in released Minecraft versions. Sections group related features, rows describe specific features, and version columns name the mod used for that version.

## Core foundation

These entries provide the runtime, performance, pack management, and configuration base for the pack.

### Runtime and APIs

These entries provide loader-level APIs and language runtimes used by other mods.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Fabric API support | Fabric API | Added |
| Kotlin runtime | Fabric Language Kotlin | Added |

### Performance

These entries improve frame pacing, memory use, lighting, networking, and rendering cost.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Rendering engine optimization | Sodium | Added |
| Game logic optimization | Lithium | Added |
| Startup and memory fixes | ModernFix | Added |
| Immediate rendering optimization | ImmediatelyFast | Added |
| Network stack optimization | Krypton | Added |
| Light engine optimization | ScalableLux | Added |
| Entity render culling | Entity Culling | Added |
| General render culling | More Culling | Added |
| Block entity rendering optimization | Enhanced Block Entities | Added |
| Leaf rendering culling | Cull Leaves | Added |
| Particle performance | AsyncParticles | Added |

### Pack management and defaults

These entries help discover, load, or distribute pack-level resources and default client settings.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Resource pack discovery | Resourcify | Added |
| Global pack loading | Global Packs | Added |
| Default options and keybinds | Default Options | Added |

### Mod management and configuration frameworks

These entries provide mod lists, in-game config screens, and config frameworks used by other mods.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Mod list and config entry | Mod Menu | Added |
| In-game configuration screens | Configured | Added |
| YACL configuration framework | YetAnotherConfigLib | Added |
| Cloth Config framework | Cloth Config | Added |
| Forge config compatibility | Forge Config API Port | Added |

## Visual and audio enhancements

These entries improve immersion through visuals, audio, animation, and presentation.

### OptiFine feature parity

These entries provide OptiFine-style visual and resource-pack features through Fabric-friendly mods.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Shader loader | Iris | Added |
| Sodium video option extensions | Sodium Extra | Added |
| OptiFine alternatives integration | Puzzle | Added |
| Custom entity models | Entity Model Features | Added |
| Custom entity textures | Entity Texture Features | Added |
| Custom item textures | CIT Resewn | Added |
| Connected textures | Continuity | Added |
| Custom GUI resource pack support | OptiGUI | Added |

### Visual effects

These entries add client-side ambience, distant terrain, shader enhancements, particles, and small visual feedback effects.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Distant terrain renderer | Distant Horizons | Added |
| Complementary shader visual extensions | Euphoria Patches | Added |
| Ambient particles | Visuality | Added |
| Subtle visual effects | Subtle Effects | Added |
| Additional particle effects | Particle Effects | Added |
| Particle interactions | EG Particle Interactions | Added |
| Bubble pop effects | Make Bubbles Pop | Added |
| Falling leaf particles | Falling Leaves | Added |
| Explosion effects | Explosive Enhancement | Added |
| Mining visual feedback | Mining & Placing Animations | Added |
| Immersive visual effects | Perception | Added |

### Audio

These entries add ambience and improve how sound events feel in play.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Ambient soundscapes | AmbientSounds | Added |
| Footstep sounds | Presence Footsteps | Added |
| Sound event improvements | Sounds | Added |

### Animation and movement

These entries improve first-person, third-person, item, block, and movement presentation.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Player animations | Not Enough Animations | Added |
| Eating animations | Eating Animation | Added |
| Item drop physics | ItemPhysic Lite | Added |
| Block placement animations | A Good Place | Added |
| First-person item animations | Hold My Items | Added |
| Held item display | YDM's Weapon Master | Added |
| Camera motion | Camera Overhaul | Added |
| Elytra flight controls | Do a Barrel Roll | Added |

### Interface polish

These entries adjust menus, UI motion, text rendering, and screen layout.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Player paper doll | Paper Doll | Added |
| Status effect folding | Mini Effects | Added |
| Inventory item animations | Tiny Item Animations | Added |
| HUD positioning | Raised | Added |
| UI background blur | Blur | Added |
| Smooth scrolling | Smooth Scroll | Added |
| Smooth GUI animation | Smooth GUI | Added |
| Modern UI framework and text rendering | Modern UI | Added |
| Immersive UI interactions | Immersive UI | Added |

### Chat and social UI

These entries improve chat readability and presentation without requiring server-side gameplay content.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Chat avatars | Chat Heads | Added |
| Chat message animation | Chat Animation | Added |

### Skin and cosmetics

These entries improve player skin, cape, and cosmetic display.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| 3D skin layers | 3D Skin Layers | Planned |
| Cape physics | WaveyCapes | Planned |
| Cape provider support | Capes | Planned |
| Custom skin loading | CustomSkinLoader | Planned |

## Utility features

These entries make information, navigation, controls, multiplayer use, and creative workflows easier.

### Lookup, inventory, and controls

These entries improve item lookup, inventory interaction, controls, and input handling.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Item and recipe browser | Roughly Enough Items | Planned |
| Block and entity overlay | Jade | Planned |
| Food value display | AppleSkin | Planned |
| Shulker box preview | Shulker Box Tooltip | Planned |
| Inventory profiles and sorting | Inventory Profiles Next | Planned |
| Mouse inventory actions | Mouse Tweaks | Planned |
| Inventory movement | InvMove | Planned |
| Keybinding search and conflicts | Controlling | Planned |
| Input method conflict handling | IMBlocker | Planned |
| Zoom controls | Zoomify | Planned |

### HUD information and client convenience

These entries surface gameplay information or remove small interface friction.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Advanced HUD overlays | MiniHUD | Planned |
| Inventory HUD overlay | Inventory HUD+ | Planned |
| Mount HUD improvements | Better Mount HUD | Planned |
| Statistics screen improvements | Better Stats | Planned |
| Armor detail display | Detail Armor Bar | Planned |
| Dynamic crosshair | Dynamic Crosshair | Planned |
| Draggable resource pack lists | Draggable Lists | Planned |
| Resource pack warning suppression | No Resource Pack Warnings | Planned |
| Custom world warning suppression | Disable Custom Worlds Advice | Planned |

### Map and navigation

These entries provide client-side map, minimap, and location presentation tools.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Minimap | Xaero's Minimap | Planned |
| World map | Xaero's World Map | Planned |
| Location title cards | Traveler's Titles | Planned |

### Creative tools and diagnostics

These entries are useful for building, testing, profiling, or personal creative workflows.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Performance profiler | Spark | Planned |
| World editing | WorldEdit | Planned |
| Creative builder tools | LotTweaks | Planned |

### Optional multiplayer features

These entries add features that work best on compatible multiplayer servers.

| Feature | 1.21.1 | Pack status |
| --- | --- | --- |
| Proximity voice chat | Simple Voice Chat | Skipped |
| Server resource-pack unpacking | Server Unpacker | Skipped |
| Multiplayer client enhancements | Noxesium | Skipped |
