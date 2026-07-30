# Auto Farm Addon (Minecraft Bedrock)

Instant, stackable auto farms for Minecraft Bedrock / Pocket Edition. Right-click
a block with the **Structure Build Tool**, pick a farm from a menu, preview
its footprint as a particle outline, then confirm to have it built instantly.

Includes two farms, both quad-stackable:

- **Stackable Iron Farm** — a real 4-villager village (claimed beds), a
  caged zombie for spawn urgency, a walled spawn platform, and a
  magma-block kill trench that funnels iron/poppy drops into hoppers.
- **Stackable Auto Crop Farm** — four farmland plots worked by farmer
  villagers, a center villager they periodically try to share surplus food
  with, and a hopper-minecart collection pen that catches the dropped food.

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
3. In your world settings, add **both** **CraftForge Instant Builds [Behavior]**
   *and* **CraftForge Instant Builds [Resources]** — under their respective
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

- **Two real bugs fixed after testing, both root-caused against current
  Bedrock docs/changelogs rather than guessed:**
  - The tool's icon and name were blank/unresolved because
    `@minecraft/server` removed the `itemUseOn` event entirely in its
    2.0.0 release — the manifest still pointed at the old 1.x module line,
    so the script's event handler silently never fired at all (this is
    also why the menu never opened). Updated the dependency versions in
    `BP/manifest.json` to `@minecraft/server` 2.0.0 / `@minecraft/server-ui`
    2.1.0, and switched the handler in `scripts/main.js` from
    `world.afterEvents.itemUseOn` to `world.afterEvents.playerInteractWithBlock`
    (the documented replacement).
  - To remove any remaining risk from custom texture/lang resolution, the
    tool's icon now points at the vanilla `book_enchanted` shortname
    (guaranteed to already exist in the base game) instead of a custom
    PNG, and its display name is a literal string instead of a
    translation key — so it doesn't depend on this pack's resource pack
    content loading correctly at all.
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
