# Mod feature matrix

[English](mod-matrix.md) | [简体中文](mod-matrix.zh-CN.md)

This page tracks which mod provides each feature in released Minecraft versions. Sections group related features, rows describe specific features, and version columns name the mod used for that version.

## Core foundation

These entries provide the runtime, rendering, performance, and configuration base for the pack.

### Runtime and APIs

These entries provide loader-level APIs and language runtimes used by other mods.

| Feature | 1.21.1 |
| --- | --- |
| Fabric API support | Fabric API |
| Kotlin runtime | Fabric Language Kotlin |

### Rendering base

These entries replace vanilla rendering or keep Fabric rendering features compatible.

| Feature | 1.21.1 |
| --- | --- |
| Rendering engine | Sodium |
| Fabric Rendering API compatibility | Indium |

### Performance

These entries improve frame pacing, memory use, lighting, networking, and rendering cost.

| Feature | 1.21.1 |
| --- | --- |
| Game logic optimization | Lithium |
| Startup and memory fixes | ModernFix |
| Immediate rendering optimization | ImmediatelyFast |
| Network stack optimization | Krypton |
| Light engine optimization | ScalableLux |
| Entity render culling | Entity Culling |
| General render culling | More Culling |
| Block entity rendering optimization | Enhanced Block Entities |
| Leaf rendering culling | Cull Leaves |
| Particle performance | AsyncParticles |

### Pack management

These entries help discover, load, or manage resource packs and global packs.

| Feature | 1.21.1 |
| --- | --- |
| Resource pack discovery | Resourcify |
| Global pack loading | Global Packs |

### Mod management and configuration

These entries provide mod lists, in-game config screens, and config frameworks used by other mods.

| Feature | 1.21.1 |
| --- | --- |
| Mod list and config entry | Mod Menu |
| In-game configuration screens | Configured |
| YACL configuration framework | YetAnotherConfigLib |
| Cloth Config framework | Cloth Config |
| Forge config compatibility | Forge Config API Port |

## Visual and audio enhancements

These entries improve immersion through visuals, audio, animation, and presentation.

### OptiFine feature parity

These entries provide OptiFine-style visual and resource-pack features through Fabric-friendly mods.

| Feature | 1.21.1 |
| --- | --- |
| Shader loader | Iris |
| Sodium video option extensions | Sodium Extra |
| Complementary shader extensions | Euphoria Patcher |
| Custom entity models | Entity Model Features |
| Custom entity textures | Entity Texture Features |
| Custom item textures | CIT Resewn |
| Connected textures | Continuity |
| Custom GUI resource pack support | OptiGUI |

### View distance and world presentation

These entries make the world feel larger or more continuous from the client side.

| Feature | 1.21.1 |
| --- | --- |
| Distant terrain renderer | Distant Horizons |

### Visual effects

These entries add client-side ambience, particles, and small visual feedback effects.

| Feature | 1.21.1 |
| --- | --- |
| Ambient particles | Visuality |
| Subtle visual effects | Subtle Effects |
| Additional particle effects | Particle Effects |
| Particle interactions | EG Particle Interactions |
| Bubble pop effects | Make Bubbles Pop |
| Falling leaf particles | Falling Leaves |
| Explosion effects | Explosive Enhancement |
| Mining visual feedback | Mining Quakes |
| Immersive visual effects | Perception |

### Audio

These entries add ambience and improve how sound events feel in play.

| Feature | 1.21.1 |
| --- | --- |
| Ambient soundscapes | AmbientSounds |
| Footstep sounds | Presence Footsteps |
| Sound event improvements | Sounds |

### Animation and movement

These entries improve first-person, third-person, item, block, and movement presentation.

| Feature | 1.21.1 |
| --- | --- |
| Player animations | Not Enough Animations |
| Eating animations | Eating Animation |
| Item drop physics | ItemPhysic Lite |
| Block placement animations | A Good Place |
| First-person item animations | Hold My Items |
| Held item display | YDM's Weapon Master |
| Camera motion | Camera Overhaul |
| Elytra flight controls | Do a Barrel Roll |

### Interface polish

These entries adjust menus, UI motion, text rendering, and screen layout.

| Feature | 1.21.1 |
| --- | --- |
| Player paper doll | Paper Doll |
| Status effect folding | Mini Effects |
| Inventory item animations | Tiny Item Animations |
| HUD positioning | Raised |
| UI background blur | Blur |
| Smooth scrolling | Smooth Scroll |
| Smooth GUI animation | Smooth GUI |
| Modern UI framework and text rendering | Modern UI |
| Immersive UI interactions | Immersive UI |

### Chat and social UI

These entries improve chat readability and presentation without requiring server-side gameplay content.

| Feature | 1.21.1 |
| --- | --- |
| Chat avatars | Chat Heads |
| Chat message animation | Chat Animation |

### Skin and cosmetics

These entries improve player skin, cape, and cosmetic display.

| Feature | 1.21.1 |
| --- | --- |
| 3D skin layers | 3D Skin Layers |
| Cape physics | WaveyCapes |
| Cape provider support | Capes |
| Custom skin loading | CustomSkinLoader |

## Utility features

These entries make information, navigation, controls, multiplayer use, and creative workflows easier.

### Lookup, inventory, and controls

These entries improve item lookup, inventory interaction, controls, and input handling.

| Feature | 1.21.1 |
| --- | --- |
| Item and recipe browser | Roughly Enough Items |
| Block and entity overlay | Jade |
| Food value display | AppleSkin |
| Shulker box preview | Shulker Box Tooltip |
| Inventory profiles and sorting | Inventory Profiles Next |
| Mouse inventory actions | Mouse Tweaks |
| Inventory movement | InvMove |
| Keybinding search and conflicts | Controlling |
| Input method conflict handling | IMBlocker |
| Zoom controls | Zoomify |

### HUD information and client convenience

These entries surface gameplay information or remove small interface friction.

| Feature | 1.21.1 |
| --- | --- |
| Advanced HUD overlays | MiniHUD |
| Inventory HUD overlay | Inventory HUD+ |
| Mount HUD improvements | Better Mount HUD |
| Statistics screen improvements | Better Stats |
| Armor detail display | Detail Armor Bar |
| Dynamic crosshair | Dynamic Crosshair |
| Draggable resource pack lists | Draggable Lists |
| Custom world warning suppression | Disable Custom Worlds Advice |

### Map and navigation

These entries provide client-side map, minimap, and location presentation tools.

| Feature | 1.21.1 |
| --- | --- |
| Minimap | Xaero's Minimap |
| World map | Xaero's World Map |
| Location title cards | Traveler's Titles |

### Optional multiplayer features

These entries add features that work best on compatible multiplayer servers.

| Feature | 1.21.1 |
| --- | --- |
| Proximity voice chat | Simple Voice Chat |
| Server resource-pack unpacking | Server Unpacker |
| Multiplayer client enhancements | Noxesium |

### Creative tools and diagnostics

These entries are useful for building, testing, profiling, or personal creative workflows.

| Feature | 1.21.1 |
| --- | --- |
| Performance profiler | Spark |
| World editing | WorldEdit |
| Creative builder tools | LotTweaks |
