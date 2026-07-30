# Auto Farm Addon (Minecraft Bedrock)

Instant, stackable, achievement-friendly auto farms for Minecraft Bedrock /
Pocket Edition. Right-click a block with the **Structure Build Tool**, pick a
farm from a menu, preview its footprint as a particle outline, then confirm
to have it built instantly.

Includes two farms, both quad-stackable:

- **Stackable Iron Farm** — a real 4-villager village (claimed beds), a
  caged zombie for spawn urgency, a walled spawn platform, and a
  magma-block kill trench that funnels iron/poppy drops into hoppers.
- **Stackable Auto Crop Farm** — four farmland plots worked by farmer
  villagers, a center villager they periodically try to share surplus food
  with, and a hopper-minecart collection pen that catches the dropped food.

## Why it's achievement-friendly

Bedrock disables achievements for a world if cheats are turned on **or** if
any experimental toggle (including "Beta APIs"/Holiday Creator Features) is
enabled — even if you never use it. This addon avoids both:

- Every block placed and every entity spawned goes through the
  `@minecraft/server` Script API (`block.setPermutation`, `dimension.spawnEntity`)
  — never `/give`, `/fill`, `/structure`, or any other slash command, so
  cheats never need to be turned on.
- `BP/manifest.json` depends on the **stable** release of `@minecraft/server`
  and `@minecraft/server-ui` (plain version numbers, no `-beta` suffix).
  Stable Script API modules run on a normal world with no experimental
  toggles at all — do **not** turn on "Beta APIs"/Holiday Creator Features;
  that toggle disables achievements by itself and this addon doesn't need it.
- The Structure Build Tool is also obtainable through a normal crafting
  recipe (see below), so a legitimate survival world never needs cheats or
  experiments enabled at any point.

## Install

1. Run `./build_addon.sh` (requires `zip`) to produce `dist/AutoFarmAddon.mcaddon`,
   or simply zip the `BP/` and `RP/` folders together yourself.
2. Send that `.mcaddon` file to your device and open it — Minecraft will
   import both packs automatically.
3. In your world settings, add both **Instant Auto Farms [Behavior]** and
   **Instant Auto Farms [Resources]** under Behavior Packs / Resource Packs.
4. Leave every toggle under **Experiments** off. Nothing in this addon needs
   them, and turning any of them on disables achievements regardless of
   what the addon itself does.

If Minecraft complains about a script API version mismatch on load, it means
your game version's stable module numbers have moved on — open
`BP/manifest.json` and bump the `@minecraft/server` / `@minecraft/server-ui`
module versions (and `min_engine_version`) to whatever the current **stable**
(non-beta) versions are per Mojang's Script API documentation. Avoid `-beta`
suffixed versions — those require the experimental toggle and will cost you
achievements.

## Using it in-game

1. Craft a **Structure Build Tool**: iron ingot / emerald / iron ingot on
   the top and bottom-middle row, stick in the bottom-middle — see the
   recipe book, or `BP/recipes/build_tool.json`. (It's also in the Creative
   inventory under Equipment.)
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

- **Bed and hopper orientation** are set programmatically and rotated to
  match the direction you built in; if a state value mapping doesn't match
  your game version exactly, the bed/hopper still functions — worst case
  it's a purely cosmetic mismatch you can fix by breaking and replacing
  that one block.
- **Villager profession race**: the crop farm's center villager could in
  rare cases claim a plot's composter before the intended farmer does. If a
  plot never seems to work, walk over, note which villager has no farmer
  job, and give it a moment — or break/replace that composter to force a
  re-claim.
- **Very tall stacks (4 levels)** mean the bottom level's items travel
  through a long hopper chain to reach the base chest. This is normal
  vanilla hopper transfer speed, not a bug — expect a short delay, not data
  loss (hoppers buffer 5 stacks each).
- **Build site**: the tool clears a generous interior volume before
  building, but doesn't touch anything outside the farm's own footprint.
  Build on relatively flat ground with clearance above for a 4-level stack
  (roughly 48 blocks for the iron farm, 36 for the crop farm).
- Module/engine versions in `BP/manifest.json` are set to reasonably recent
  values; if your Minecraft version is newer, update them per Mojang's
  Script API changelog.

## Project layout

```
BP/                      Behavior pack
  manifest.json
  items/structure_tool.json
  recipes/build_tool.json
  scripts/
    main.js               Item-use handler, menus, build orchestration
    lib/geometry.js        Facing + rotation math
    lib/builder.js          Block/entity placement generators (system.runJob-safe)
    lib/outline.js           Particle bounding-box preview
    farms/ironFarm.js         Iron farm layout + mechanics
    farms/cropFarm.js          Crop farm layout + mechanics
RP/                      Resource pack (icon, item texture, lang)
build_addon.sh            Packages BP/ + RP/ into dist/AutoFarmAddon.mcaddon
```

## Adding your own farm

Each farm module exports an object with `id`, `name`, `shortDescription`,
`size`, `levelSpacing`, `maxLevels`, and a `plan({ levels, facing })` method
returning `{ placements, spawns }` in local space (see `ironFarm.js` for a
fully worked example). Register it in `FARMS` in `scripts/main.js` and it
shows up in the menu automatically.
