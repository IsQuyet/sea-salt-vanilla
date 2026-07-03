# Mod feature matrix

[Back to README](../README.md)

This page tracks which mod provides each feature in released Minecraft versions. Sections group related features, rows describe specific features, and version columns name the mod used for that version.

## Core foundation

These entries provide the runtime, performance, pack management, and configuration base for the pack.

### Runtime and APIs

These entries provide loader-level APIs and language runtimes used by other mods.

| Feature | 1.21.1 |
| --- | --- |
| Fabric API support | [Fabric API](https://modrinth.com/mod/fabric-api) |
| Kotlin runtime | [Fabric Language Kotlin](https://modrinth.com/mod/fabric-language-kotlin) |

### Performance

These entries improve frame pacing, memory use, lighting, networking, and rendering cost.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Rendering engine optimization | [Sodium](https://modrinth.com/mod/sodium) |  |
| Game logic optimization | [Lithium](https://modrinth.com/mod/lithium) |  |
| Startup and memory fixes | [ModernFix](https://modrinth.com/mod/modernfix) |  |
| Immediate rendering optimization | [ImmediatelyFast](https://modrinth.com/mod/immediatelyfast) |  |
| Network stack optimization | [Krypton](https://modrinth.com/mod/krypton) |  |
| Light engine optimization | [ScalableLux](https://modrinth.com/mod/scalablelux) |  |
| Entity render culling | [Entity Culling](https://modrinth.com/mod/entityculling) |  |
| General render culling | [More Culling](https://modrinth.com/mod/moreculling) |  |
| Block entity rendering optimization | [Enhanced Block Entities](https://modrinth.com/mod/ebe) | [Better Block Entities](https://modrinth.com/mod/better-block-entities) |
| Leaf rendering culling | [Cull Leaves](https://modrinth.com/mod/cull-leaves) |  |
| Particle performance | [AsyncParticles](https://modrinth.com/mod/asyncparticles) |  |
| Memory allocation optimization | [FerriteCore](https://modrinth.com/mod/ferrite-core) |  |
| Client performance tweaks | [BadOptimizations](https://modrinth.com/mod/badoptimizations) |  |
| Input event polling optimization | [Ixeris](https://modrinth.com/mod/ixeris) |  |

### Pack management and defaults

These entries help discover, load, or distribute pack-level resources and default client settings.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Resource pack discovery | [Resourcify](https://modrinth.com/mod/resourcify) |  |
| Global pack loading | [Global Packs](https://modrinth.com/mod/globalpacks) |  |
| Default options and keybinds | [Default Options](https://modrinth.com/mod/default-options) | [Your Options Shall Be Respected (YOSBR)](https://modrinth.com/mod/yosbr) |

### Mod management and configuration frameworks

These entries provide mod lists, in-game config screens, and config frameworks used by other mods.

| Feature | 1.21.1 |
| --- | --- |
| Mod list and config entry | [Mod Menu](https://modrinth.com/mod/modmenu) |
| In-game configuration screens | [Configured](https://modrinth.com/mod/configured) |
| YACL configuration framework | [YetAnotherConfigLib (YACL)](https://modrinth.com/mod/yacl) |
| Cloth Config framework | [Cloth Config API](https://modrinth.com/mod/cloth-config) |
| Forge config compatibility | [Forge Config API Port](https://modrinth.com/mod/forge-config-api-port) |

## Visual and audio enhancements

These entries improve immersion through visuals, audio, animation, and presentation.

### OptiFine feature parity

These entries provide OptiFine-style visual and resource-pack features through Fabric-friendly mods.

| Feature | 1.21.1 |
| --- | --- |
| Shader loader | [Iris Shaders](https://modrinth.com/mod/iris) |
| Sodium video option extensions | [Sodium Extra](https://modrinth.com/mod/sodium-extra) |
| OptiFine alternatives integration | [Puzzle](https://modrinth.com/mod/puzzle) |
| Custom entity models | [[EMF] Entity Model Features](https://modrinth.com/mod/entity-model-features) |
| Custom entity textures | [[ETF] Entity Texture Features](https://modrinth.com/mod/entitytexturefeatures) |
| Custom item textures | [CIT Resewn](https://modrinth.com/mod/cit-resewn) |
| Connected textures | [Continuity](https://modrinth.com/mod/continuity) |
| Custom GUI resource pack support | [OptiGUI](https://modrinth.com/mod/optigui) |

### Visual effects

These entries add client-side ambience, distant terrain, shader enhancements, particles, and small visual feedback effects.

| Feature | 1.21.1 |
| --- | --- |
| Distant terrain renderer | [Distant Horizons](https://modrinth.com/mod/distanthorizons) |
| Complementary shader visual extensions | [Euphoria Patches](https://modrinth.com/mod/euphoria-patches) |
| Ambient particles | [Visuality](https://modrinth.com/mod/visuality) |
| Cave dust ambience | [Cave Dust](https://modrinth.com/mod/cave-dust) |
| Boat item display | [Boat Item View](https://modrinth.com/mod/boat-item-view) |
| Connected block outlines | [Seamless](https://modrinth.com/mod/seamless) |
| Subtle visual effects | [Subtle Effects](https://modrinth.com/mod/subtle-effects) |
| Additional particle effects | [Particle Effects](https://modrinth.com/mod/particle-effects) |
| Inventory particle effects | [Inventory Particles](https://modrinth.com/mod/inventory-particles) |
| Ambient visual effects | [Mas Effects](https://modrinth.com/mod/mas-effects) |
| Particle interactions | [Particle Interactions](https://modrinth.com/mod/particle-interactions) |
| Bubble pop effects | [Make Bubbles Pop](https://modrinth.com/mod/make_bubbles_pop) |
| Falling leaf particles | [Falling Leaves](https://modrinth.com/mod/fallingleaves) |
| Explosion effects | [Explosive Enhancement](https://modrinth.com/mod/explosive-enhancement) |
| Projectile visual style | [2D Projectiles ➵](https://modrinth.com/mod/twod_projectiles) |
| Mining visual feedback | [Mining & Placing Animations](https://modrinth.com/mod/mining_and_placing_animations) |
| Immersive visual effects | [Perception](https://modrinth.com/mod/perception) |

### Audio

These entries add ambience and improve how sound events feel in play.

| Feature | 1.21.1 |
| --- | --- |
| Ambient soundscapes | [AmbientSounds](https://modrinth.com/mod/ambientsounds) |
| Footstep sounds | [Presence Footsteps](https://modrinth.com/mod/presence-footsteps) |
| Sound event improvements | [Sounds](https://modrinth.com/mod/sound) |

### Animation and movement

These entries improve first-person, third-person, item, block, and movement presentation.

| Feature | 1.21.1 |
| --- | --- |
| Player animations | [Not Enough Animations](https://modrinth.com/mod/not-enough-animations) |
| Eating animations | [Eating Animation](https://modrinth.com/mod/eating-animation) |
| Item drop physics | [ItemPhysic Lite](https://modrinth.com/mod/itemphysic-lite) |
| Falling block animations | [Vectorientation](https://modrinth.com/mod/vectorientation) |
| Block placement animations | [A Good Place](https://modrinth.com/mod/a-good-place) |
| First-person item animations | [Hold My Items](https://modrinth.com/mod/hold-my-items) |
| Held item display | [YDM's Weapon Master](https://modrinth.com/mod/weaponmaster) |
| Camera motion | [Camera Overhaul](https://modrinth.com/mod/cameraoverhaul) |
| Elytra flight controls | [Do a Barrel Roll](https://modrinth.com/mod/do-a-barrel-roll) |

### Interface polish

These entries adjust menus, UI motion, text rendering, and screen layout.

| Feature | 1.21.1 |
| --- | --- |
| Menu customization | [FancyMenu](https://modrinth.com/mod/fancymenu) |
| Player paper doll | [Paper Doll](https://modrinth.com/mod/paperdoll) |
| Head cosmetic disguises | [DisguiseHeads](https://modrinth.com/mod/disguiseheads) |
| Status effect folding | [Mini Effects](https://modrinth.com/mod/mini-effects) |
| Inventory item animations | [Tiny Item Animations](https://modrinth.com/mod/tiny-item-animations) |
| Inventory item swap animations | [Smooth Swapping](https://modrinth.com/mod/smooth-swapping) |
| HUD positioning | [Raised](https://modrinth.com/mod/raised) |
| UI background blur | [Blur+](https://modrinth.com/mod/blur-plus) |
| Smooth scrolling | [Smooth Scrolling](https://modrinth.com/mod/smooth-scroll) |
| Smooth GUI animation | [Smooth Gui](https://modrinth.com/mod/smooth-gui) |
| Modern UI framework and text rendering | [Modern UI](https://modrinth.com/mod/modern-ui) |
| Immersive UI interactions | [Immersive UI](https://modrinth.com/mod/immersive-ui) |

### Chat and social UI

These entries improve chat readability and presentation without requiring server-side gameplay content.

| Feature | 1.21.1 |
| --- | --- |
| Chat avatars | [Chat Heads](https://modrinth.com/mod/chat-heads) |
| Chat message animation | [Chat Animation [Smooth Chat]](https://modrinth.com/mod/chatanimation) |

### Skin and cosmetics

These entries improve player skin, cape, and cosmetic display.

| Feature | 1.21.1 |
| --- | --- |
| 3D skin layers | [3D Skin Layers](https://modrinth.com/mod/3dskinlayers) |
| Cape physics | [Wavey Capes](https://modrinth.com/mod/wavey-capes) |
| Cape provider support | [Capes](https://modrinth.com/mod/capes) |
| Custom skin loading | [CustomSkinLoader](https://modrinth.com/mod/customskinloader) |

## Utility features

These entries make information, navigation, controls, multiplayer use, and creative workflows easier.

### Lookup, inventory, and controls

These entries improve item lookup, inventory interaction, controls, and input handling.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Item and recipe browser | [Roughly Enough Items (REI)](https://modrinth.com/mod/rei) |  |
| Block and entity overlay | [Jade 🔍](https://modrinth.com/mod/jade) |  |
| Extra item and block hints | [Peek](https://modrinth.com/mod/peek) |  |
| Food value display | [AppleSkin](https://modrinth.com/mod/appleskin) |  |
| Shulker box preview | [Shulker Box Tooltip](https://modrinth.com/mod/shulkerboxtooltip) |  |
| Inventory profiles and sorting | [Inventory Profiles Next](https://modrinth.com/mod/inventory-profiles-next) |  |
| Mouse inventory actions | [Mouse Tweaks](https://modrinth.com/mod/mouse-tweaks) |  |
| Inventory movement | [InvMove](https://modrinth.com/mod/invmove) |  |
| Inventory movement compatibility | [InvMoveCompats](https://modrinth.com/mod/invmovecompats) |  |
| Keybinding search and conflicts | [Controlling](https://modrinth.com/mod/controlling) |  |
| Visual keybinding overview | [VisualKeys](https://modrinth.com/mod/visualkeys) |  |
| Attention flash notifications | [Flash](https://modrinth.com/mod/flash) |  |
| Inventory item highlighting | [Item Highlighter](https://modrinth.com/mod/item-highlighter) |  |
| Input method conflict handling | [IMBlocker](https://modrinth.com/mod/imblocker-original) |  |
| Chinese character search support | [JustEnoughCharacters](https://modrinth.com/mod/justenoughcharacters) |  |
| Zoom controls | [Zoomify (Zoom)](https://modrinth.com/mod/zoomify) | [Logical Zoom](https://modrinth.com/mod/logical-zoom), [Ok Zoomer - It's Zoom!](https://modrinth.com/mod/ok-zoomer) |

### HUD information and client convenience

These entries surface gameplay information or remove small interface friction.

| Feature | 1.21.1 |
| --- | --- |
| Advanced HUD overlays | [MiniHUD](https://modrinth.com/mod/minihud) |
| Inventory HUD overlay | [InventoryHUD+](https://modrinth.com/mod/inventoryhudplus) |
| Mount HUD improvements | [Better Mount HUD](https://modrinth.com/mod/better-mount-hud) |
| Statistics screen improvements | [Better Statistics Screen](https://modrinth.com/mod/better-stats) |
| Debug screen improvements | [BetterF3](https://modrinth.com/mod/betterf3) |
| World favorite management | [Cherished Worlds](https://modrinth.com/mod/cherished-worlds) |
| Advancement screen improvements | [Better Advancements](https://modrinth.com/mod/better-advancements) |
| Chat report friction removal | [No Chat Reports](https://modrinth.com/mod/no-chat-reports) |
| Chat interface convenience | [Chat Patches](https://modrinth.com/mod/chatpatches) |
| Server list ping optimization | [Fast IP Ping](https://modrinth.com/mod/fast-ip-ping) |
| Armor detail display | [Detail Armor Bar](https://modrinth.com/mod/detail-armor-bar) |
| Dynamic crosshair | [Dynamic Crosshair](https://modrinth.com/mod/dynamiccrosshair) |
| Draggable resource pack lists | [Draggable Lists](https://modrinth.com/mod/draggable-lists) |
| Resource pack warning suppression | [No Resource Pack Warnings](https://modrinth.com/mod/no-resource-pack-warnings) |
| Custom world warning suppression | [Disable Custom Worlds Advice](https://modrinth.com/mod/dcwa) |
| Screenshot viewer | [Screenshot Viewer](https://modrinth.com/mod/screenshot-viewer) |
| Hide interface for screenshots | [Better F1 Reborn](https://modrinth.com/mod/better-f1-reborn) |

### Map and navigation

These entries provide client-side map, minimap, and location presentation tools.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Minimap | [Xaero's Minimap](https://modrinth.com/mod/xaeros-minimap) |  |
| World map | [Xaero's World Map](https://modrinth.com/mod/xaeros-world-map) |  |
| Location title cards | [Traveler's Titles](https://modrinth.com/mod/travelers-titles) | [BiomeInfo](https://modrinth.com/mod/biomeinfo) |

### Creative tools and diagnostics

These entries are useful for building, testing, profiling, or personal creative workflows.

| Feature | 1.21.1 |
| --- | --- |
| Performance profiler | [spark](https://modrinth.com/mod/spark) |
| World editing | [WorldEdit](https://modrinth.com/mod/worldedit) |
| In-game notes | [Vanilla Notebook ](https://modrinth.com/mod/notebook) |
| Edge block placement | [Reacharound](https://modrinth.com/mod/reacharound) |

## Optional capabilities

These entries are useful extensions that are recognized by the pack, but are not part of the default distribution.

### Online play enhancements

These entries mainly improve the client-side experience when playing online or on compatible servers.

| Feature | 1.21.1 |
| --- | --- |
| Proximity voice chat | [Simple Voice Chat](https://modrinth.com/mod/simple-voice-chat) |
| Server resource-pack unpacking | [Server Unpacker](https://modrinth.com/mod/server-unpacker) |
| Multiplayer client enhancements | [Noxesium](https://modrinth.com/mod/noxesium) |
| Remote view-distance cache | [Bobby](https://modrinth.com/mod/bobby) |
| Client-side wearable rendering | [WearThat](https://modrinth.com/mod/wearthat) |
| Social client layer | [Essential Mod](https://modrinth.com/mod/essential) |
| Player emotes | [Emotecraft](https://modrinth.com/mod/emotecraft) |
| Voice chat bubbles | [TalkBubbles](https://modrinth.com/mod/talkbubbles) |
| Talking head indicators | [Talking Heads](https://modrinth.com/mod/talkingheads) |
| Chat image display | [ChatImage](https://modrinth.com/mod/chatimage) |
| Collectible heads | [REPO Heads](https://modrinth.com/mod/repo-heads) |
| Friendly interactions | [Headpat a Friend!](https://modrinth.com/mod/headpat) |

### Optional audiovisual ambience

These entries can strongly shape visual or audio ambience, so they are kept as opt-in choices.

| Feature | 1.21.1 |
| --- | --- |
| Dynamic lighting | [LambDynamicLights - Dynamic Lights](https://modrinth.com/mod/lambdynamiclights) |
| Sound physics | [Sound Physics Remastered](https://modrinth.com/mod/sound-physics-remastered) |
| Weather particle ambience | [Particle Rain](https://modrinth.com/mod/particle-rain) |

### Optional tools and workflows

These entries support specific creative, building, recording, or input workflows.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Orthographic screenshot tools | [OrthoCamera](https://modrinth.com/mod/orthocamera) | [Pixelshot](https://modrinth.com/mod/pixelshot) |
| Schematic building | [Litematica](https://modrinth.com/mod/litematica) |  |
| Creative builder tools | [LotTweaks](https://www.curseforge.com/minecraft/mc-mods/lottweaks) |  |
| Replay recording | [ReplayMod](https://modrinth.com/mod/replaymod) |  |
| Controller support | [Controlify (Controller support)](https://modrinth.com/mod/controlify) |  |
