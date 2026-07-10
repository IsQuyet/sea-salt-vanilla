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
| Multiplayer client optimization | [Noxesium](https://modrinth.com/mod/noxesium) |  |
| Light engine optimization | [ScalableLux](https://modrinth.com/mod/scalablelux) |  |
| Entity render culling | [Entity Culling](https://modrinth.com/mod/entityculling) |  |
| General render culling | [More Culling](https://modrinth.com/mod/moreculling) |  |
| Block entity rendering optimization | [Enhanced Block Entities](https://modrinth.com/mod/ebe) | [Better Block Entities](https://modrinth.com/mod/better-block-entities) |
| Leaf rendering culling | [Cull Leaves](https://modrinth.com/mod/cull-leaves) |  |
| Particle performance | [Particle Core](https://modrinth.com/mod/particle-core) | [AsyncParticles](https://modrinth.com/mod/asyncparticles) |
| Memory allocation optimization | [FerriteCore](https://modrinth.com/mod/ferrite-core) |  |
| Client performance tweaks | [BadOptimizations](https://modrinth.com/mod/badoptimizations) |  |
| Input event polling optimization | [Ixeris](https://modrinth.com/mod/ixeris) |  |
| Thread scheduling optimization | [ThreadTweak](https://modrinth.com/mod/threadtweak) |  |

### Pack management and defaults

These entries help discover, load, or distribute pack-level resources and default client settings.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Resource pack discovery | [Resourcify](https://modrinth.com/mod/resourcify) |  |
| Global pack loading | [Global Packs](https://modrinth.com/mod/globalpacks) | [Open Loader](https://modrinth.com/mod/open-loader), [Paxi](https://modrinth.com/mod/paxi) |
| Packed pack management | [Packed Packs](https://modrinth.com/mod/packed-packs) |  |
| Default client options and config seeding | [Your Options Shall Be Respected (YOSBR)](https://modrinth.com/mod/yosbr) | [Default Options](https://modrinth.com/mod/default-options) |

### Mod management and configuration frameworks

These entries provide mod lists, in-game config screens, and config frameworks used by other mods.

| Feature | 1.21.1 |
| --- | --- |
| Mod list and config entry | [Mod Menu](https://modrinth.com/mod/modmenu) |
| In-game configuration screens | [Configured](https://www.curseforge.com/minecraft/mc-mods/configured) |
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

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Distant terrain renderer | [Distant Horizons](https://modrinth.com/mod/distanthorizons) | [Bobby](https://modrinth.com/mod/bobby), [voxy](https://modrinth.com/mod/voxy) |
| Complementary shader visual extensions | [Euphoria Patches](https://modrinth.com/mod/euphoria-patches) |  |
| Ambient particles | [Visuality](https://modrinth.com/mod/visuality) |  |
| Cave dust ambience | [Cave Dust](https://modrinth.com/mod/cave-dust) |  |
| Boat item display | [Boat Item View](https://modrinth.com/mod/boat-item-view) |  |
| Connected block outlines | [Seamless](https://modrinth.com/mod/seamless) |  |
| Subtle visual effects | [Subtle Effects](https://modrinth.com/mod/subtle-effects) |  |
| Additional particle effects | [Particle Effects](https://modrinth.com/mod/particle-effects) |  |
| Inventory particle effects | [Inventory Particles](https://modrinth.com/mod/inventory-particles), [Inventory Interactions](https://modrinth.com/mod/inventory-interactions) |  |
| Ambient visual effects | [Mas Effects](https://modrinth.com/mod/mas-effects) |  |
| Particle interactions | [Particle Interactions](https://modrinth.com/mod/particle-interactions) |  |
| Bubble pop effects | [Make Bubbles Pop](https://modrinth.com/mod/make_bubbles_pop) |  |
| Falling leaf particles | [Falling Leaves](https://modrinth.com/mod/fallingleaves) |  |
| Soft surface imprints | [Soft Imprints](https://modrinth.com/mod/snow-imprints) |  |
| Explosion effects | [Explosive Enhancement](https://modrinth.com/mod/explosive-enhancement) |  |
| Projectile visual style | [2D Projectiles ➵](https://modrinth.com/mod/twod_projectiles) |  |
| Mining visual feedback | [Mining & Placing Animations](https://modrinth.com/mod/mining_and_placing_animations) |  |
| Immersive visual effects | [Perception](https://modrinth.com/mod/perception) |  |
| Soul fire burn visuals | [Burn By Soul Fire](https://modrinth.com/mod/burn-by-soul-fire) |  |
| Elytra contrails | [Elytra Contrails Mod](https://modrinth.com/mod/elytra-contrails-mod) |  |

### Audio

These entries add ambience and improve how sound events feel in play.

| Feature | 1.21.1 |
| --- | --- |
| Ambient soundscapes | [AmbientSounds](https://modrinth.com/mod/ambientsounds) |
| Footstep sounds | [Presence Footsteps](https://modrinth.com/mod/presence-footsteps) |
| Sound event improvements | [Sounds](https://modrinth.com/mod/sound) |
| Dynamic rain sounds | [Cool Rain](https://modrinth.com/mod/coolrain) |

### Animation and movement

These entries improve first-person, third-person, item, block, and movement presentation.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Player animations | [Not Enough Animations](https://modrinth.com/mod/not-enough-animations) |  |
| Eating animations | [Eating Animation](https://modrinth.com/mod/eating-animation) |  |
| Item drop physics | [ItemPhysic Lite](https://modrinth.com/mod/itemphysic-lite) |  |
| Falling block animations | [Vectorientation](https://modrinth.com/mod/vectorientation) |  |
| Block placement animations | [A Good Place](https://modrinth.com/mod/a-good-place) |  |
| First-person item animations | [Hold My Items](https://modrinth.com/mod/hold-my-items) |  |
| Held item display | [YDM's Weapon Master](https://modrinth.com/mod/weaponmaster) |  |
| Camera motion | [Camera Overhaul](https://modrinth.com/mod/cameraoverhaul) |  |
| Third-person shoulder camera | [Shoulder Surfing Reloaded](https://modrinth.com/mod/shoulder-surfing-reloaded) | [Leawind's Third Person](https://modrinth.com/mod/leawind-third-person) |
| Elytra flight controls | [Do a Barrel Roll](https://modrinth.com/mod/do-a-barrel-roll) |  |
| World animation polish | [Fancy World Animations](https://modrinth.com/mod/fwa) |  |

### Interface polish

These entries adjust menus, UI motion, text rendering, and screen layout.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Menu customization | [FancyMenu](https://modrinth.com/mod/fancymenu) |  |
| Player paper doll | [Paper Doll](https://modrinth.com/mod/paperdoll) |  |
| Head cosmetic disguises | [DisguiseHeads](https://modrinth.com/mod/disguiseheads) |  |
| Status effect folding | [Mini Effects](https://modrinth.com/mod/mini-effects) |  |
| Inventory item animations | [Tiny Item Animations](https://modrinth.com/mod/tiny-item-animations) |  |
| Inventory item swap animations | [Smooth Swapping](https://modrinth.com/mod/smooth-swapping) |  |
| HUD positioning | [Raised](https://modrinth.com/mod/raised) |  |
| UI background blur | [Blur+](https://modrinth.com/mod/blur-plus) |  |
| Smooth scrolling | [Smooth Scrolling](https://modrinth.com/mod/smooth-scroll) | [Smooth Scrolling Refurbished](https://modrinth.com/mod/smooth-scrolling-refurbished) |
| Automatic GUI dark mode | [Mindful Darkness](https://modrinth.com/mod/mindful-darkness) |  |
| Smooth GUI animation | [Smooth Gui](https://modrinth.com/mod/smooth-gui) |  |
| Chat message animation | [Chat Animation [Smooth Chat]](https://modrinth.com/mod/chatanimation) |  |
| Toast notification polish | [Fancy Toasts \| Better Advancements](https://modrinth.com/mod/fancy-toasts) |  |
| Modern UI framework and text rendering | [Modern UI](https://modrinth.com/mod/modern-ui) |  |
| Immersive UI interactions | [Immersive UI](https://modrinth.com/mod/immersive-ui) |  |

### Chat and social UI

These entries improve chat readability and presentation without requiring server-side gameplay content.

| Feature | 1.21.1 |
| --- | --- |
| Chat avatars | [Chat Heads](https://modrinth.com/mod/chat-heads) |
| Proximity voice chat | [Simple Voice Chat](https://modrinth.com/mod/simple-voice-chat) |
| Chat image display | [ChatImage](https://modrinth.com/mod/chatimage) |
| Talking head indicators | [Talking Heads](https://modrinth.com/mod/talkingheads) |

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
| Enhanced tooltip details | [EnhancedTooltips](https://modrinth.com/mod/enhancedtooltips) |  |
| Food value display | [AppleSkin](https://modrinth.com/mod/appleskin) |  |
| Shulker box preview | [Shulker Box Tooltip](https://modrinth.com/mod/shulkerboxtooltip) |  |
| Inventory profiles and sorting | [Inventory Profiles Next](https://modrinth.com/mod/inventory-profiles-next) |  |
| Saved hotbar management | [Better Saved Hotbars](https://modrinth.com/mod/better-saved-hotbars) | [Better Saved Hotbars Forked](https://modrinth.com/mod/better-saved-hotbars-forked) |
| Mouse inventory actions | [Mouse Tweaks](https://modrinth.com/mod/mouse-tweaks) |  |
| Edge block placement | [Reacharound](https://modrinth.com/mod/reacharound) |  |
| Inventory movement | [InvMove](https://modrinth.com/mod/invmove), [InvMoveCompats](https://modrinth.com/mod/invmovecompats) |  |
| Keybinding search and conflicts | [Controlling](https://modrinth.com/mod/controlling) |  |
| Visual keybinding overview | [VisualKeys](https://modrinth.com/mod/visualkeys) |  |
| Attention flash notifications | [Flash](https://modrinth.com/mod/flash) |  |
| Inventory item highlighting | [Item Highlighter](https://modrinth.com/mod/item-highlighter) |  |
| Input method conflict handling | [IMBlocker](https://modrinth.com/mod/imblocker-original) |  |
| Chinese character search support | [JustEnoughCharacters](https://modrinth.com/mod/justenoughcharacters) |  |
| Sign and book text editing | [Scribble](https://modrinth.com/mod/scribble) |  |
| Zoom controls | [Zoomify (Zoom)](https://modrinth.com/mod/zoomify) | [Logical Zoom](https://modrinth.com/mod/logical-zoom), [Ok Zoomer - It's Zoom!](https://modrinth.com/mod/ok-zoomer) |

### HUD information and client convenience

These entries surface gameplay information or remove small interface friction.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Advanced HUD overlays | [MiniHUD](https://modrinth.com/mod/minihud) |  |
| Inventory HUD overlay | [InventoryHUD+](https://modrinth.com/mod/inventoryhudplus) |  |
| Immersive hotbar display | [Immersive Hotbar](https://modrinth.com/mod/immersive-hotbar) |  |
| Mount HUD improvements | [Leave My Bars Alone](https://modrinth.com/mod/leave-my-bars-alone) | [Better Mount HUD](https://modrinth.com/mod/better-mount-hud) |
| Status effect display | [Stylish Effects](https://modrinth.com/mod/stylish-effects) |  |
| Statistics screen improvements | [Better Statistics Screen](https://modrinth.com/mod/better-stats) |  |
| Debug screen improvements | [BetterF3](https://modrinth.com/mod/betterf3) |  |
| World favorite management | [Cherished Worlds](https://modrinth.com/mod/cherished-worlds) |  |
| Disconnect confirmation | [Confirm Disconnect](https://modrinth.com/mod/confirm-disconnect) |  |
| Advancement screen improvements | [Better Advancements](https://modrinth.com/mod/better-advancements) |  |
| Chat report friction removal | [No Chat Reports](https://modrinth.com/mod/no-chat-reports) |  |
| Insecure chat toast suppression | [Disable Insecure Chat Toast](https://modrinth.com/mod/disableinsecurechattoast) |  |
| Chat interface convenience | [Chat Patches](https://modrinth.com/mod/chatpatches) |  |
| Player pat interactions | [PatPat [Mod & Plugin]](https://modrinth.com/mod/patpat) |  |
| Server list ping optimization | [Fast IP Ping](https://modrinth.com/mod/fast-ip-ping) |  |
| Armor detail display | [Detail Armor Bar Reconstructed](https://modrinth.com/mod/detail-armor-bar-reconstructed) | [Detail Armor Bar](https://modrinth.com/mod/detail-armor-bar) |
| Client-side wearable rendering | [WearThat](https://modrinth.com/mod/wearthat) |  |
| In-game skin management | [Skin Shuffle](https://modrinth.com/mod/skinshuffle) | [Quick Skin](https://modrinth.com/mod/quick-skin) |
| Dynamic crosshair | [Dynamic Crosshair](https://modrinth.com/mod/dynamiccrosshair) |  |
| Centered crosshair | [Centered Crosshair](https://modrinth.com/mod/centered-crosshair) |  |
| Draggable resource pack lists | [Draggable Lists](https://modrinth.com/mod/draggable-lists) |  |
| Resource pack warning suppression | [No Resource Pack Warnings](https://modrinth.com/mod/no-resource-pack-warnings) |  |
| Custom world warning suppression | [Disable Custom Worlds Advice](https://modrinth.com/mod/dcwa) |  |
| Screenshot viewer | [Screenshot Viewer](https://modrinth.com/mod/screenshot-viewer) |  |
| Hide interface for screenshots | [Better F1 Reborn](https://modrinth.com/mod/better-f1-reborn) |  |
| Nametag visibility toggle | [Toggle Nametags](https://modrinth.com/mod/hidetags) |  |

### Map and navigation

These entries provide client-side map, minimap, and location presentation tools.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Minimap, world map, and waypoint navigation | [Xaero's Minimap](https://modrinth.com/mod/xaeros-minimap), [Xaero's World Map](https://modrinth.com/mod/xaeros-world-map) | [JourneyMap](https://modrinth.com/mod/journeymap), [VoxelMap-Updated](https://modrinth.com/mod/voxelmap-updated) |
| Location title cards | [Traveler's Titles](https://modrinth.com/mod/travelers-titles) | [BiomeInfo](https://modrinth.com/mod/biomeinfo) |

### Creative tools and diagnostics

These entries are useful for building, testing, profiling, or personal creative workflows.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Performance profiler | [spark](https://modrinth.com/mod/spark) |  |
| World editing | [WorldEdit](https://modrinth.com/mod/worldedit) |  |
| Orthographic screenshot tools | [OrthoCamera](https://modrinth.com/mod/orthocamera) | [Pixelshot](https://modrinth.com/mod/pixelshot) |
| Controller support | [Controlify (Controller support)](https://modrinth.com/mod/controlify) |  |

## Optional capabilities

These entries are useful extensions that are recognized by the pack, but are not part of the default distribution.

### Online play enhancements

These entries mainly improve the client-side experience when playing online or on compatible servers.

| Feature | 1.21.1 |
| --- | --- |
| Server resource-pack unpacking | [Server Unpacker](https://modrinth.com/mod/server-unpacker) |
| Social client layer | [Essential Mod](https://modrinth.com/mod/essential) |
| Player emotes | [Emotecraft](https://modrinth.com/mod/emotecraft) |
| Voice chat bubbles | [TalkBubbles](https://modrinth.com/mod/talkbubbles) |
| Friendly interactions | [Headpat a Friend!](https://modrinth.com/mod/headpat) |

### Optional client convenience

These entries add small client-side quality-of-life features that are useful but not part of the default distribution.

| Feature | 1.21.1 | Alternatives |
| --- | --- | --- |
| Enchantment tooltip descriptions | [Enchantment Descriptions](https://modrinth.com/mod/enchantment-descriptions) |  |
| Item pickup notifications | [Pick Up Notifier](https://modrinth.com/mod/pick-up-notifier) |  |
| Safe world deletion | [Delete Worlds To Trash](https://modrinth.com/mod/delete-worlds-to-trash) |  |
| Item swapping tools | [ItemSwapper](https://modrinth.com/mod/itemswapper) | [Slot Cycler](https://modrinth.com/mod/slot-cycler) |
| Completion tracking index | [Completionist's Index](https://modrinth.com/mod/completionists-index) |  |
| Health bar display | [Health Bars](https://modrinth.com/mod/new-health-bars) |  |
| Inventory tabs | [Inventory Tabs](https://modrinth.com/mod/inventory-tabs) |  |
| Collectible heads | [REPO Heads](https://modrinth.com/mod/repo-heads) |  |

### Optional pack management

These entries provide opt-in controls for resource packs, modpack resources, or pack-level behavior.

| Feature | 1.21.1 |
| --- | --- |
| Resource pack override control | [Resource Pack Overrides](https://modrinth.com/mod/resource-pack-overrides) |
| Recursive resource loading | [Recursive Resources](https://modrinth.com/mod/recursiveresources) |

### Optional audiovisual ambience

These entries can strongly shape visual or audio ambience, so they are kept as opt-in choices.

| Feature | 1.21.1 |
| --- | --- |
| Dynamic lighting | [LambDynamicLights - Dynamic Lights](https://modrinth.com/mod/lambdynamiclights) |
| Sound physics | [Sound Physics Remastered](https://modrinth.com/mod/sound-physics-remastered) |
| Weather particle ambience | [Particle Rain](https://modrinth.com/mod/particle-rain) |
| Realistic camera perspective | [Real Camera](https://modrinth.com/mod/real-camera) |
| Atmospheric visual ambience | [ATMOSPHERICS](https://modrinth.com/mod/atmospherics) |
| Better smoke effects | [Better Smoke](https://modrinth.com/mod/better-smoke) |
| Natural water rendering | [Natural Waters](https://modrinth.com/mod/natural-waters) |
| Enchantment glint outline | [Enchantment Glint Outline](https://modrinth.com/mod/enchantment-glint-outline) |

### Optional tools and workflows

These entries support specific creative, building, recording, or input workflows.

| Feature | 1.21.1 |
| --- | --- |
| Schematic building | [Litematica](https://modrinth.com/mod/litematica) |
| Creative builder tools | [Lottweaks](https://www.curseforge.com/minecraft/mc-mods/lottweaks) |
| Advanced creative building tools | [Axiom](https://modrinth.com/mod/axiom) |
| Replay recording | [ReplayMod](https://modrinth.com/mod/replaymod) |
| In-game notes | [Vanilla Notebook ](https://modrinth.com/mod/notebook) |
