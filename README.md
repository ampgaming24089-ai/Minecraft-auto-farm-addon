# Auto Farm Addon (Minecraft Bedrock)

Instant, stackable auto farms for Minecraft Bedrock / Pocket Edition. Right-click
a block with the **Structure Build Tool**, pick a farm from a menu, preview
its footprint as a particle outline, then confirm to have it built instantly.

Includes three farms:

- **Stackable Iron Farm** — an open villager hall (beds + composters, not
  sealed pods — see below for why that matters), a caged zombie for spawn
  urgency, an open-top lit spawn platform, and a magma-block kill trench
  that funnels iron/poppy drops into hoppers. Build 1-4 levels, stacked
  vertically and deliberately close together.
- **Auto Crop Farm** — two farmer villagers, each with their own
  composter-on-water plot, separated from a caged collector villager by a
  hopper-minecart barrier that catches food they try (and fail) to share
  across it. Build 1-4 of these as fully separate, independent farms on
  the ground, 10 blocks apart from each other.
- **Passive Mob Farm** — a lit, open grass platform where cows/pigs/sheep/
  chickens spawn and graze, a water funnel pushes them into a fall + magma
  kill zone, and an auto-smoker cooks the drops before a hopper stores them
  in a chest. Build 1-4 of these too, same ground-level layout as the crop
  farm.

## Important: what "stackable" actually means for the iron farm

Bedrock's real requirement for iron golems to spawn at all is **20 beds and
10 villagers, with 75% of them having reached and used a workstation in the
last in-game day** — much bigger than most people assume, and far bigger
than earlier versions of this addon used (which is why golems never spawned
and "water doesn't push them" was moot — there was nothing to push). Each
level here has **20 beds + 20 composters** in two open rows of 10.

The golem population cap is **1 golem per 10 villagers in a village**. An
earlier version of this addon tried to give every floor its own
*independent* cap by spacing levels far enough apart (80+ blocks) that
Bedrock wouldn't merge them into one village. That turned out to be a
mistake, based on a mechanic I'd missed:

**A village only spawns golems while a player is standing inside its
"activation region"** — the village's bounds expanded outward by roughly
32-48 blocks depending on your simulation distance setting. The distance
needed to keep two villages from merging is *larger* than that (~64+ blocks
beyond each village's own bounds). Since the separation-to-avoid-merging is
always bigger than the activation range, **there is no single spot you can
stand that keeps two truly separate villages both active at once** — you'd
only ever activate whichever one you're currently near, and the others sit
idle. That's true whether the farms are stacked vertically or spread out
horizontally on the ground — spreading them out doesn't fix it, it just
changes which axis the wasted distance is on.

So this farm does the opposite: **levels are built close together on
purpose so they merge into one combined village.** More levels = more total
villagers = a higher population cap, and because it's one village with one
activation region, every floor can spawn golems simultaneously from a
single AFK spot at the base:

- **4 levels = 80 villagers in one village = a population cap of 8**
  concurrent golems, all reachable from one spot.
- **Height is back to normal** — a 4-level build is about 45 blocks tall,
  not 250.
- **Collection is shared again** — one external hopper shaft down to one
  base chest, since the levels are close enough together that this is
  fast, not the minutes-long chain a spread-out design would need.
- **1-3 levels may not reliably spawn golems at all** if you don't fill
  every level's beds. This farm is only guaranteed to work with every
  built level fully populated (20/20 beds per level).
- **Build it away from any existing village** (100+ blocks is a commonly
  cited safe distance) — a nearby real village can merge with yours and
  throw off the cap.

Two more fixes worth calling out explicitly, both found from real in-game
testing feedback:

- **The water current wasn't pushing golems anywhere.** The earlier design
  ringed all 4 edges of the spawn platform with water flowing inward. That
  looks reasonable on paper, but water only flows about 7 blocks from a
  source before stopping, and two currents flowing head-on into each other
  from opposite edges create a dead/ambiguous push exactly where they
  meet — which was exactly the center drain, the one place the push needed
  to be strongest. The fix drops the north/south edges entirely and only
  uses a full-depth water column on the west wall (flowing east) and one on
  the east wall (flowing west). Every tile on the platform now has exactly
  one clear push direction toward the drain, never two fighting each other.
- **No more roof.** Each level used to be a fully sealed box. That's gone —
  every level is now open at the top. An enclosed room's darkness used to
  be what (accidentally) kept hostile mobs out; with the roof gone, that
  job is done instead by lighting the place heavily (sea lanterns lining
  both walls at hall height and platform height on every level), which
  keeps light levels high enough that nothing hostile spawns despite the
  open top.

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
3. In your world settings, add **both** **Homestead Works [Behavior]**
   *and* **Homestead Works [Resources]** — under their respective
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
4. Pick how many to build (1-4 — stacked levels for the iron farm, or
   separate ground-level units 10 blocks apart for the crop and mob farms)
   and whether to show the outline preview.
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
Levels are spaced close together (12 blocks) on purpose so every built
level merges into one combined village instead of staying separate — see
"what stackable actually means" above for why deliberately merging beats
trying to keep floors independent. A caged zombie on each level is
visible/near enough to raise that village's "under attack" state, which
vanilla uses to increase golem spawn urgency. Golems spawn on the open-top,
heavily-lit platform above each level (inside the village bounds), get
walked into a 2-wide center drain by a one-axis water current (west wall
flows east, east wall flows west, nothing on north/south — see the
water-current fix above for why), fall down the shaft onto a magma-block
trench, and take real damage-over-time until they die. A water current in
the trench sweeps the drops into a hopper feeding the shared collection
shaft. Magma, not lava, is deliberate: lava sets dropped items on fire and
destroys them — magma damages the golem without touching the loot.

**Crop Farm** — Two farmer villagers, each in their own 8x8 plot (farmers
won't work land more than ~4 blocks from their composter, so a wider plot
just wastes space). Each plot's center tile is a water source with a
composter placed directly on top of it — hydrates the whole plot and
serves as that farmer's job site in one tile — with glowstone above for
light. A collector villager is caged in a narrow pen between the two
plots so it can never wander off. The boundary between each plot and the
pen is a hopper + rail + parked hopper-minecart (walkable — farmers step
right up to any tile of it) with an open trapdoor one block above blocking
actual crossing. Farmers still approach and try to share surplus food with
the caged collector across the gap; that attempt drops food onto whichever
minecart they're standing at, which the hopper underneath catches. This is
a documented, real Bedrock design, not an invented one — but it's still
real (and therefore somewhat unpredictable) villager AI, so give it real
time before judging it broken. Unlike the iron farm, this one isn't
stacked — each of the 1-4 you build is a complete, independent farm on the
ground, 10 blocks from the next one, so there's nothing to merge or share
between them except the final collection chest.

**Passive Mob Farm** — An open, heavily-lit grass platform where cows,
pigs, sheep, and chickens naturally spawn and graze over time (no
breeding required, though feeding them speeds it up) inside a 2-block-high
fence barrier that keeps them from wandering off the edge early. The same
one-axis water convergence used to fix the iron farm's platform pushes
grown animals into a 2-wide center drain, which drops them 14 blocks — far
enough to kill cows/pigs/sheep outright with fall damage alone. Chickens
take no fall damage in vanilla, so the landing zone is also lined with
magma blocks (safe for item drops, unlike lava) as a guaranteed finisher.
A water current sweeps the raw drops into a hopper that feeds a smoker's
input slot from directly above — standard vanilla hopper-into-furnace
behavior, no scripting needed for the cooking itself. The smoker's fuel
slot is pre-loaded with a stack of coal at build time (good for 512
smelts), and a second hopper underneath automatically pulls the cooked
output into the final chest.

All three farms funnel their output into one shared external hopper chain
ending in a double chest — not buried, so it's immediately visible without
digging, and there's only ever one chest to check per farm type regardless
of how many levels/units you built.

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
- **Building 4 of the crop or mob farm** means the farthest unit's items
  travel through a long shared hopper chain (up to ~120 blocks) to reach
  the one collection chest. This is normal vanilla hopper transfer speed,
  not a bug — expect a real but bounded delay (each hop is 8 game ticks),
  not data loss (hoppers buffer 5 stacks each). If you'd rather have faster,
  fully independent collection per unit at the cost of more chests to
  check, that's a one-line change in the farm's `plan()` — see "Adding your
  own farm" below.
- **Passive Mob Farm fall shaft goes ~15 blocks below where you build.** If
  you build on ground very close to the world's minimum build height, the
  kill zone/smoker/chest can clip below it. Build on typical Overworld
  terrain and this isn't a concern.
- **Build site**: the tool clears a generous interior volume before
  building, but doesn't touch anything outside the farm's own footprint.
  Build on relatively flat ground, away from any existing village (see
  above). Clearance needed: the iron farm is roughly 45 blocks tall at 4
  levels (15x15 footprint); the crop and mob farms are only ~6-7 blocks
  tall each but stretch to ~120 blocks wide at 4 units (23x10 and 15x15
  footprints per unit, 10 blocks apart) since they're built side by side on
  the ground rather than stacked.
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
    farms/mobFarm.js              Passive mob farm layout + mechanics
RP/                      Resource pack (icon, item texture, lang)
  manifest.json             Includes metadata.product_type: "addon"
build_addon.sh            Packages BP/ + RP/ into dist/AutoFarmAddon.mcaddon
```

## Adding your own farm

Each farm module exports an object with `id`, `name`, `shortDescription`,
`size`, `levelSpacing`, `maxLevels`, and a `plan({ levels, facing })` method
returning `{ placements, spawns, fills? }` in local space (see `ironFarm.js`
for a fully worked example of vertical stacking, or `cropFarm.js`/
`mobFarm.js` for side-by-side ground units). Register it in `FARMS` in
`scripts/main.js` and it shows up in the menu automatically.

A few optional properties change how the generic build flow treats a farm:

- `stackAxis: "x"` (or `"z"`) — repeat levels sideways in local space
  instead of stacking them in `y`. Defaults to `"y"` if omitted.
- `levelLabel` — override the slider's label text in the level-count menu
  (defaults to `"Stack height (levels)"`).
- `unitNoun` — override the word used for "N of these" in menus/messages
  (defaults to `"Level"`).
- `fills` — a list of `{x, y, z, slot, itemId, amount}` to pre-load into an
  already-placed container's inventory slot after building (e.g. fuel into
  a smoker), applied after `placements` but before `spawns`.
