# Auto Farm Addon (Minecraft Bedrock)

Instant, stackable auto farms for Minecraft Bedrock / Pocket Edition. Right-click
a block with the **Structure Build Tool**, pick a farm from a menu, preview
its footprint as a particle outline, then confirm to have it built instantly.

Includes two farms, both quad-stackable:

- **Stackable Iron Farm** — an open villager hall (beds + composters, not
  sealed pods — see below for why that matters), a caged zombie for spawn
  urgency, a walled spawn platform, and a magma-block kill trench that
  funnels iron/poppy drops into hoppers.
- **Stackable Auto Crop Farm** — two farmer villagers, each with their own
  composter-on-water plot, separated from a caged collector villager by a
  hopper-minecart barrier that catches food they try (and fail) to share
  across it.

## Important: what "stackable" actually means for the iron farm

Bedrock's real requirement for iron golems to spawn at all is **20 beds and
10 villagers, with 75% of them having reached and used a workstation in the
last in-game day** — much bigger than most people assume, and far bigger
than earlier versions of this addon used (which is why golems never spawned
and "water doesn't push them" was moot — there was nothing to push). Each
level here is a full village on its own: **20 beds + 20 composters** in two
open rows of 10, comfortably over the minimum by itself.

That raises a second, separate mechanic: **Bedrock merges two villages into
one if their bounds come within 64 blocks of each other**, and a merged
village shares a single golem population cap (**1 golem per 10 villagers**
— so a 20-villager village caps at 2 concurrent golems, no matter how big it
is). Stack levels close together and you don't get more golems by adding
more floors — you just get one bigger village still capped at 2. To make
every floor genuinely independent (its own village, its own 2-golem cap),
**levels here are spaced 80 blocks apart**, clearing the 64-block merge
threshold with real margin. That means:

- **4 levels = 4 independent villages = up to 8 concurrent golems**, not 2.
- **The trade-off is height.** A 4-level build is roughly **250 blocks
  tall.** There is no way to get real independent per-floor spawn caps
  without that vertical separation — it's a direct consequence of the
  mechanic, not a shortcut I could design around.
- **Collection is per-level, not shared.** A hopper shaft spanning 250
  blocks would take real minutes for a single item to reach the bottom, so
  each level drops into its own double chest right next to its own kill
  trench. Check every level's chest, not just the bottom one.
- **1-3 levels may not reliably spawn golems at all** if you don't fill
  every level's beds. This farm is only guaranteed to work with every
  built level fully populated (20/20 beds).
- **Build it away from any existing village** (100+ blocks is a commonly
  cited safe distance) — a nearby real village can merge with your bottom
  level and throw off its cap too.

## Achievement compatibility (read this first)

This took three tries to get right, so here's the real story:

1. **First version** used the Script API with no `metadata.product_type`
   field. Activating it immediately showed Minecraft's "You can't earn
   achievements" dialog — *"An external behavior pack was activated."*
2. **Second version** removed the Script API entirely and rebuilt
   everything as data-driven items triggering `.mcfunction` files via each
   item's `minecraft:on_use` component. This turned out to be a dead end:
   `run_command` (the action that actually invokes the function) requires
   the **Holiday Creator Features** experimental toggle to work at all —
   without it, the item silently does nothing, which is exactly what
   happened when tested. And experimental toggles disable achievements
   independently of everything else, so this path could never have worked
   for the stated goal even if the wiring had been correct.
3. **This version** goes back to the Script API (which doesn't need any
   experimental toggle — stable, non-beta `@minecraft/server` module
   versions like the ones this addon depends on never require Beta APIs or
   Holiday Creator Features) and adds the piece that was actually missing
   from the start:
   ```json
   "metadata": {
     "product_type": "addon"
   }
   ```
   in **both** `BP/manifest.json` and `RP/manifest.json`. Without this
   field, Bedrock treats any custom pack as a potential "cheat world" and
   blocks achievements regardless of what it contains — this is documented
   community knowledge and matches how other achievement-friendly
   community addons (e.g. Force Creative-style packs, which do far more
   invasive things than this one) stay compatible.

So: Script API + `product_type: addon`, no experiments, no cheats. This is
the version to test.

## Install

1. Run `./build_addon.sh` (requires `zip`) to produce `dist/AutoFarmAddon.mcaddon`,
   or zip the `BP/` and `RP/` folders together yourself.
2. Send that `.mcaddon` file to your device and open it — Minecraft will
   import both packs.
3. In your world settings, add **both** **Farmtopia [Behavior]**
   *and* **Farmtopia [Resources]** — under their respective
   Behavior Packs / Resource Packs tabs. Adding only one is a common
   mistake and shows up as items with no icon and a raw
   `item.autofarm:...name` name instead of proper text/art, since that
   text and icon live in the resource pack.
4. Leave everything under **Experiments** off, and leave cheats off.
   Nothing here needs them.

## Using it in-game

1. Craft a **Structure Build Tool**: iron ingot / emerald / iron ingot on
   the top row, stick in the bottom-middle row (see `BP/recipes/build_tool.json`,
   or check the recipe book). It's also in the Creative inventory under
   Equipment.
2. Stand where you want the farm's front-left corner and right-click the
   ground with the tool.
3. Pick a farm from the menu.
4. Pick a stack height (1-4 levels) and whether to show the outline preview.
5. If enabled, a particle box appears showing exactly where the structure
   will go. Confirm to build it instantly, or cancel — nothing is placed
   until you confirm.

The farm is built facing away from the direction you were looking when you
clicked, snapped to the nearest cardinal direction.

## How the mechanics actually work

Nothing here is scripted loot or fake spawns — every drop comes from real
vanilla AI and physics:

**Iron Farm** — Two open rows of 10 beds facing 10 composters each (20 of
each per level) let villagers freely path between sleeping and working,
which is what actually keeps them counted as valid village members
(sealing them in isolated pods, an earlier design, silently broke this).
Levels are spaced 80 blocks apart vertically — past Bedrock's 64-block
village-merge distance — so each level is its own independent village with
its own golem population cap, instead of every floor merging into one
shared-cap village. A caged zombie on each level is visible/near enough to
raise that village's "under attack" state, which vanilla uses to increase
golem spawn urgency. Golems spawn on the walled platform above (inside the
village bounds), get walked into a 2-wide center drain by a real inward
water current (a full perimeter ring of water sources, not a handful of
scattered points — that's what actually creates a connected current toward
the only low point instead of disconnected puddles), fall down the shaft
onto a magma-block trench, and take real damage-over-time until they die.
A water current in the trench sweeps the drops into a hopper feeding that
level's own chest. Magma, not lava, is deliberate: lava sets dropped items
on fire and destroys them — magma damages the golem without touching the
loot.

**Crop Farm** — Two farmer villagers, each in their own 8x8 plot (farmers
won't work land more than ~4 blocks from their composter, so a wider plot
just wastes space). Each plot's center tile is a water source with a
composter placed directly on top of it — hydrates the whole plot and
serves as that farmer's job site in one tile — with glowstone above for
light. A collector villager is caged in a narrow pen between the two
plots so it can never wander off. The boundary between each plot and the
pen is a hopper-block + rail + parked hopper-minecart (walkable — farmers
step right up to it) with an open trapdoor one block above blocking actual
crossing. Farmers still approach and try to share surplus food with the
caged collector across the gap; that attempt drops food right onto the
minecart row, which a hopper underneath continuously drains. This is a
documented, real Bedrock design, not an invented one — but it's still real
(and therefore somewhat unpredictable) villager AI, so give it real time
before judging it broken.

The crop farm funnels every level's output into one shared external hopper
shaft, ending in a double chest at ground level right next to the tower —
not buried, so it's immediately visible without digging. The iron farm is
different: because its levels are 80 blocks apart (see above), each level
gets its **own** double chest right next to its own kill trench instead of
one shared shaft — check every level, not just the bottom.

## Known limitations / tuning tips

- **Three real bugs found and fixed via testing + the in-game content
  log** (Settings → Creator → Content Log), not guesswork:
  1. `@minecraft/server` removed the `itemUseOn` event entirely in its
     2.0.0 release, and the manifest still pointed at the old 1.x module
     line — the script's event handler likely never loaded at all.
     Updated `BP/manifest.json` to `@minecraft/server` 2.0.0 /
     `@minecraft/server-ui` 2.1.0, and switched
     `scripts/main.js` from `world.afterEvents.itemUseOn` to
     `world.afterEvents.playerInteractWithBlock` (the documented
     replacement).
  2. **The actual cause of the persistent blank icon**, found via the
     content log's exact error text: `menu_category -> group: string
     must be prefixed with a namespace`. `BP/items/structure_tool.json`
     had `"group": "itemGroup.name.tool"` with no namespace, which made
     the *entire item* fail to parse — so no icon fix could ever have
     worked, because the item using that icon never successfully loaded
     in the first place. Fixed to `"minecraft:itemGroup.name.tool"`.
  3. The tool's icon points at a texture this pack ships itself
     (`RP/textures/items/build_tool_icon.png`) rather than trying to
     reference a vanilla texture by path without shipping it — that
     approach produced the same "missing icon" error reliably in
     testing, so item icons apparently require the file to be physically
     present in the resource pack that declares the shortname.
- **Bed and hopper orientation** are set programmatically and rotated to
  match the direction you built in; if a state value mapping doesn't match
  your game version exactly, the bed/hopper still functions — worst case
  it's a purely cosmetic mismatch you can fix by breaking and replacing
  that one block.
- **Crop farm collection is still the least deterministic mechanic here.**
  Each farmer plot has its own dedicated composter now (no more shared
  job-site race between villagers), but the actual food-sharing-across-the-
  barrier behavior is real, somewhat unpredictable vanilla AI. Give it real
  in-game time before concluding it isn't working.
- **Stay near the build site until you see "Build Complete!"** on screen.
  Building spreads block placement across many ticks to avoid freezing the
  game; a 4-level farm can take a while. If you wander far enough that
  chunks unload mid-build, later placements (including villager spawns,
  which happen last) can silently fail, leaving an incomplete structure. If
  that happens, just build again while staying put.
- **On leaves and golem spawning**: leaves aren't part of the vanilla iron
  golem spawn algorithm as far as I'm aware — spawning depends on village
  size/bed count, golem population cap, and a valid flat surface, not
  nearby foliage. If you have a specific source suggesting otherwise I'm
  happy to look into it, but I didn't want to add block placements based
  on a mechanic I can't verify is real.
- **Very tall crop farm stacks (4 levels)** mean the bottom level's items
  travel through a long hopper chain to reach the shared base chest. This
  is normal vanilla hopper transfer speed, not a bug — expect a short
  delay, not data loss (hoppers buffer 5 stacks each). The iron farm
  doesn't have this issue since each level collects into its own chest.
- **Build site**: the tool clears a generous interior volume before
  building, but doesn't touch anything outside the farm's own footprint.
  Build on relatively flat ground, away from any existing village (see
  above), with clearance above for a 4-level stack — the iron farm is
  roughly **250 blocks tall** at 4 levels (15x15 footprint; the height
  comes directly from the 80-block per-floor spacing needed for
  independent village golem caps, not padding), while the crop farm is
  34 blocks tall (23x10 footprint, since it's two 8x8 plots side by side
  rather than stacked around a center). Check your build height limit
  before attempting a 4-level iron farm.
- Module/engine versions in `BP/manifest.json` are set to reasonably recent
  values; if your Minecraft version is newer, update them per Mojang's
  Script API changelog.
- If a beacon/tool shows up with no icon and a raw translation key as its
  name, the resource pack isn't active for that world — see step 3 under
  Install.

## Project layout

```
BP/                      Behavior pack
  manifest.json            Includes metadata.product_type: "addon"
  items/structure_tool.json
  recipes/build_tool.json
  scripts/
    main.js               Item-use handler, menus, build orchestration
    lib/geometry.js         Facing + rotation math
    lib/builder.js            Block/entity placement generators (system.runJob-safe)
    lib/outline.js             Particle bounding-box preview
    farms/ironFarm.js           Iron farm layout + mechanics
    farms/cropFarm.js            Crop farm layout + mechanics
RP/                      Resource pack (icon, item texture, lang)
  manifest.json             Includes metadata.product_type: "addon"
build_addon.sh            Packages BP/ + RP/ into dist/AutoFarmAddon.mcaddon
```

## Adding your own farm

Each farm module exports an object with `id`, `name`, `shortDescription`,
`size`, `levelSpacing`, `maxLevels`, and a `plan({ levels, facing })` method
returning `{ placements, spawns }` in local space (see `ironFarm.js` for a
fully worked example). Register it in `FARMS` in `scripts/main.js` and it
shows up in the menu automatically.
