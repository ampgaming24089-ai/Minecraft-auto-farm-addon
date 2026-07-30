# Auto Farm Addon (Minecraft Bedrock)

Instant, stackable auto farms for Minecraft Bedrock / Pocket Edition,
delivered as **craftable beacon items** — no menus, no scripting, no
commands typed by the player.

Includes two farms, both quad-stackable:

- **Stackable Iron Farm** — a real 4-villager village (claimed beds), a
  caged zombie for spawn urgency, a walled spawn platform, and a
  magma-block kill trench that funnels iron/poppy drops into hoppers.
- **Stackable Auto Crop Farm** — four farmland plots worked by farmer
  villagers, a center villager they periodically try to share surplus food
  with, and a hopper-minecart collection pen that catches the dropped food.

## Why this version exists (achievement compatibility)

The first version of this addon used the `@minecraft/server` Script API to
build farms dynamically from a menu. In testing, activating that pack
immediately showed Minecraft's own **"You can't earn achievements"**
dialog, listing *"An external behavior pack was activated"* as the reason —
before any code even ran. That ruled out Script API entirely: on current
Bedrock, a behavior pack that declares a `"type": "script"` module appears
to disable achievements unconditionally, regardless of what the script
does or whether cheats/experiments are on.

This version has **no `scripts/` folder and no script module in the
manifest at all** — it's 100% data-driven (items, recipes, and vanilla
`.mcfunction` command files, the same mechanism `/function` and command
blocks use). Each of the 8 beacon items below directly triggers one
`.mcfunction` file through a plain item-use event; nothing here requires
cheats, experiments, or the Script API.

**Please treat this as unverified until you've tested it.** I can't run a
Bedrock client myself, and the exact schema for "item triggers a command on
use" (the `minecraft:on_use` component below) is the one piece I couldn't
cross-check against a live game. If the beacon doesn't fire when used,
that's almost certainly a small fix to that one component in
`BP/items/*.json` — the actual farm layouts (everything the `.mcfunction`
files do) were validated independently and don't depend on that part being
right.

## Install

1. Run `./build_addon.sh` (requires `zip`) to produce `dist/AutoFarmAddon.mcaddon`,
   or zip the `BP/` and `RP/` folders together yourself.
2. Send that `.mcaddon` file to your device and open it — Minecraft will
   import both packs.
3. In your world settings, add both **Instant Auto Farms [Behavior]** and
   **Instant Auto Farms [Resources]** under Behavior Packs / Resource Packs.
4. Leave everything under **Experiments** off and cheats off — nothing here
   needs them.

## Using it in-game

Each farm/level combination is its own craftable item (8 total), since
there's no menu to pick from anymore:

| Item | Recipe (shapeless) |
|---|---|
| Iron Farm Beacon (1-4 Levels) | 1 iron block + *N* emeralds + 1 stick |
| Crop Farm Beacon (1-4 Levels) | 1 hay block + *N* emeralds + 1 stick |

(*N* = the level count, so a 3-level beacon costs 3 emeralds.) All 8 are
also in the Creative inventory under Equipment.

To build: stand where you want the **northwest floor corner** of the farm,
then use (right-click) the beacon. The structure always builds extending
east (+X) and south (+Z) from that spot — orientation is fixed rather than
based on which way you're facing, which keeps the placement commands
simple and reliable. You'll get a chat message when it starts and when
it's done.

**Building on the same spot twice will duplicate villagers/zombies** (the
blocks just get overwritten, but each use spawns a fresh set of mobs) — move
to a new location for each beacon use rather than reusing one spot.

## How the mechanics actually work

Nothing here is scripted loot or fake spawns — every drop comes from real
vanilla AI and physics:

**Iron Farm** — Four sealed bedrooms, each with one claimed bed, make the
level a valid village. A caged zombie is visible/near enough to raise the
village's "under attack" state, which vanilla uses to increase golem spawn
urgency. Golems spawn on the walled platform above (inside the village
bounds), get walked into a center drain by a real inward water current, fall
down a shaft onto a magma-block trench, and take real damage-over-time until
they die. A water current in the trench sweeps the drops into a hopper.

**Crop Farm** — Four hydrated farmland plots each have a composter, which
turns a spawned villager into a real Farmer (vanilla profession AI handles
planting/harvesting). A fenced corridor connects each plot to a shared pen
holding one more villager. Real vanilla farmer behavior periodically shares
surplus food with nearby villagers, dropping items on the ground; the pen
floor is hopper blocks topped with rails holding parked hopper minecarts, so
anything dropped there is collected immediately and drained into hoppers
below.

Both farms funnel every level's output into one shared external hopper
shaft on the outside of the tower, ending in a double chest at the base.

## Known limitations / tuning tips

- **The item-use trigger is the one unverified piece.** See the
  achievement-compatibility section above.
- **Fixed orientation.** No facing detection (that required the Script
  API), so every build extends the same direction (+X/+Z). Plan your
  approach position accordingly.
- **Bed and hopper orientation states** are hardcoded to one consistent
  layout; if a state value doesn't match your game version exactly, the
  bed/hopper still functions — worst case it's a cosmetic mismatch fixable
  by breaking and replacing that one block.
- **Villager profession race**: the crop farm's center villager could in
  rare cases claim a plot's composter before the intended farmer does. If a
  plot never seems to work, break/replace that composter to force a
  re-claim.
- **Very tall stacks (4 levels)** mean the bottom level's items travel
  through a long hopper chain to reach the base chest — normal vanilla
  transfer speed, not a bug.
- **Build site**: clear, relatively flat ground with headroom for a
  4-level stack (roughly 46 blocks for the iron farm, 34 for the crop farm)
  extending east and south of where you stand.
- `min_engine_version` in both manifests is set to a recent value; if your
  game complains on import, bump it in `BP/manifest.json` /
  `RP/manifest.json` to match your installed version.

## Project layout

```
BP/                      Behavior pack (100% data-driven, no scripts/)
  manifest.json
  items/*.json             8 beacon items (iron/crop x 1-4 levels)
  recipes/*.json            Matching shapeless crafting recipes
  functions/
    iron_farm/level[1-4].mcfunction    Generated command sequences
    crop_farm/level[1-4].mcfunction
RP/                      Resource pack (icons, item names)
tools/                   Dev-only generator (not shipped in the .mcaddon)
  cmdBuilder.js            fill/setblock/summon command formatting
  ironFarmLayout.js         Iron farm geometry -> command list
  cropFarmLayout.js          Crop farm geometry -> command list
  generate.js                Writes BP/functions/**/*.mcfunction
  generateItems.js            Writes BP/items/*.json + BP/recipes/*.json
  validateFunctions.js         Sanity-checks generated command syntax
build_addon.sh            Packages BP/ + RP/ into dist/AutoFarmAddon.mcaddon
```

## Regenerating the functions/items

The `.mcfunction` and item/recipe JSON files are generated, not hand-written.
After changing a layout in `tools/ironFarmLayout.js` or
`tools/cropFarmLayout.js`, regenerate and re-validate:

```
node tools/generate.js
node tools/generateItems.js
node tools/validateFunctions.js
```
