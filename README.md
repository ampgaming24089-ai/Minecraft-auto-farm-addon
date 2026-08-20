# Riftborne — an End overhaul for Minecraft Bedrock

The End has been one biome, one sky and two structures since 1.9. Riftborne
rebuilds it for Bedrock **26.4** (internal `1.26.40`, current hotfix `26.44`):
a new sky and lighting model, volumetric fog that changes with where you are,
four kinds of seed-derived structure scattered across the outer islands, two
new mobs, an ore, flora, and a compass that works out there.

Everything runs on documented, non-experimental APIs. No experiments toggle,
no world conversion, no commands typed by the player.

```
./build_addon.sh --check      # validate everything, then build dist/Riftborne.mcaddon
```

Import the `.mcaddon`, enable both packs on a world, and turn **Vibrant
Visuals** on in video settings for the full lighting treatment. The pack still
works with Vibrant Visuals off — you get the new fog, sky colour and all the
content, just not the PBR lighting.

---

## What changes

### The sky and the light

The End's built-in look is a flat purple void: two constant white directional
lights, a near-black sky, no depth. Riftborne replaces the whole Vibrant
Visuals stack for `minecraft:the_end`.

| File | What it does |
|---|---|
| `RP/lighting/end.json` | Pink-white sun, cool moon, and a vivid magenta End flash at 18 lx against vanilla's 3 |
| `RP/atmospherics/end.json` | Deep violet zenith under a magenta horizon, with Rayleigh scattering turned up so the glow carries to the horizon |
| `RP/color_grading/end.json` | ACES tone mapping, crushed cool shadows, magenta highlights, 8200 K balance |
| `RP/pbr/global.json` | Fallback MER values so untextured surfaces still light correctly |
| `RP/local_lighting/local_lighting.json` | Coloured point lights — end rods go violet, lumen bulbs teal |
| `RP/biomes/the_end.client_biome.json` | Binds all of the above to the End biome |

Since 1.21.90 the vanilla pack's per-biome settings beat any global file a
custom pack ships, so these are bound through the client biome rather than
through `lighting/global.json`. That is the part most End packs get wrong.

### Fog that knows where you are

Bedrock exposes exactly one End biome, so a biome-bound fog can only ever be
one mood. Riftborne ships four fog definitions and pushes the right one onto
each player's fog stack — the layer that sits above biome fog:

- **`fog_end_open`** — the default, bound to the biome. Thin violet haze that
  thickens toward the void below.
- **`fog_void_deep`** — below y=0. Draw distance collapses, forward scattering
  drops, everything goes black-violet.
- **`fog_luminous_grove`** — inside a grove. Bright, wide, teal, strong forward
  scattering so the canopies throw god rays.
- **`fog_rift`** — near a spire or anchor. Hot magenta, uniform density, short.

Each carries volumetric density, media coefficients and a Henyey–Greenstein
term, so under Vibrant Visuals these are real light shafts rather than a
coloured screen tint. The swap costs one command per boundary crossing.

### Structures worth flying to

Four blueprints, procedurally varied, generated on a 272-block grid across the
outer islands. Cells within 1100 blocks of the origin stay empty so the main
island, the obsidian pillars and the gateway are untouched.

- **Void Spire** — a 22–34 block crystal needle on a shattered plinth, with
  echo ore in the cracks and a sealed vault underneath.
- **Shattered Sanctum** — a purpur and end-brick hall, built complete and then
  eroded from a random corner, so no two are collapsed the same way.
- **Luminous Grove** — verdant crust, crystal trees with glowing canopies,
  bulbs and blooms. The one safe place out there.
- **Rift Anchor** — an obsidian frame holding a crystal tear open, ringed by
  broken pillars and guarded by rift stalkers.

Chest contents scale with distance from the origin: the rare pool goes from a
6% chance near the island to 28% around 30,000 blocks out.

### The Rift Sovereign

The End's second boss, holding open the tear at the centre of every Rift
Anchor. 400 health, a boss bar, and a fight that escalates in three phases
rather than repeating one attack:

| | Phase 1 | Phase 2 (below 66%) | Phase 3 (below 33%) |
|---|---|---|---|
| Rift lance | yes | faster | faster still |
| Shockwave | — | 9-block ring, knockback | — |
| Blink | — | repositions behind you | — |
| Summons | 3 rift stalkers | 3 rift stalkers | 2 echo sentinels |
| Cooldowns | full | −20% | −33% |

Its shells counter-rotate and its shard ring orbits faster as its health
drops, driven from the model's own Molang rather than a second animation, so
the escalation is visible before the attack pattern changes. Five custom
particle effects carry the fight — a standing aura, the lance bolt, the burst,
the ground shockwave, and a slow collapse on death that deliberately reads
differently from every attack that preceded it.

Drops 12–20 void crystals and 16–28 echo shards — roughly a full armour set
in one kill — plus a rift compass and two rolls of a rarer pool.

### The sky

`RP/textures/environment/end_sky.png` replaces the End's skybox. This is
deliberately *not* a Vibrant Visuals cubemap: Mojang restricts cubemap
customisation to the Overworld, and the End keeps its built-in one.
Overriding the vanilla texture works either way, so the sky changes whether or
not Vibrant Visuals is switched on.

The hard constraint is tiling. The game repeats this 128px tile many times
across every face, so anything with large features or strong contrast becomes
visible wallpaper — the first attempt at a magenta nebula did exactly that.
Vanilla's own End sky is nearly black for the same reason. The current one is
a very dark base with dust variation held under about 8% brightness, and stars
doing all the visible work: points small and sparse enough that the eye reads
a starfield instead of a repeat, and no cross flares, which repeat
conspicuously at that tile count.

### Mobs, ore and flora

- **Lumen Wisp** — passive, floating, shy. Drops lumen berries and the odd echo
  shard.
- **Rift Stalker** — hostile quadruped that spawns in the dark and guards
  anchors. Drops echo shards, void crystals, sometimes a pearl.
- **Echo Ore** — generated through End islands, drops 2–4 echo shards.
- **Voidbloom** and **Lumen Bulb** — glowing flora in scattered patches.
- **Shattered End Stone**, **Verdant End Stone**, **Void Crystal Block**,
  **Void Glass**, **Rift Lantern** — building blocks, all craftable.
- **Void Moth** — passive, four-winged, drifts between islands. Drops lumen
  berries and phantom membrane.
- **Echo Sentinel** — a 3-block masonry guardian with an echo core in its
  chest. 60 health, 9 damage, near-immune to knockback. Drops void crystals.
- **Chorus Hopper** — passive grazer that bolts from anything hostile. Drops
  chorus fruit.
- **Crystal Crawler** — low, fast six-legged swarmer armoured in echo crystal.
- **Shard Wraith** — a hollow flying shroud that ignores terrain.
- **Rift Sovereign** — the boss, above.
- **Rift Compass** — points at the nearest structure by name, distance and
  bearing, and names the runner-up so you can pick a route.

### Riftborne armour

The endgame set, a clear step past netherite:

| | Helm | Cuirass | Greaves | Sabatons | Set |
|---|---|---|---|---|---|
| Riftborne protection | 4 | 9 | 7 | 4 | **24** |
| Netherite protection | 3 | 8 | 6 | 3 | 20 |
| Riftborne durability | 561 | 816 | 765 | 663 | |
| Netherite durability | 407 | 592 | 555 | 481 | |

Each piece is banded the way vanilla armour is — pauldron caps, a belt line, a
knee band, a boot cuff, gold trim — because a flat wash of one colour over the
whole body renders as paint rather than plate, which is how the first pass
looked in game.

Enchantability is 18 against netherite's 15, and pieces repair with void
crystals. Crafted from void crystals alone — 24 for the full set, which is 12
crafts of the crystal recipe, so it is a genuine grind rather than an upgrade
stone.

Raw numbers would only make it a slightly better netherite, so the set carries
a bonus: **wearing all four pieces in the End grants Slow Falling and
Resistance I**, which is what actually changes how the dimension plays — the
gaps between islands stop being lethal. Remove a piece or leave the End and it
lapses within two seconds.

Recipes are in `BP/recipes/`. The chain is: mine echo ore → echo shards →
void crystals (with an ender pearl) → crystal blocks, glass, lanterns, and the
compass (with a vanilla compass).

---

## How it works, and why

Bedrock add-ons cannot add biomes to the End, cannot add structures to the
chunk generator, and cannot ship custom shaders. Three constraints, three
answers:

**Biomes → the fog stack.** Covered above: one biome, four moods, swapped by
proximity.

**Structures → generate ahead of the player.** Siting is a pure function of
`(world seed, cell x, cell z)` — a hash decides whether a cell holds a
structure, which kind, where in the cell, and which way it faces. Nothing is
written to disk. A scan every two seconds finds sited structures within 128
blocks of a player in the End and builds them with `system.runJob`, spread
across ticks.

Two consequences fall out of siting being seed-derived rather than stored:

1. The rift compass can point at a structure that does not exist yet, because
   "where is the nearest spire" is answerable without generating anything.
2. If the built-sites cache evicts an old entry (it is FIFO-capped at 1500),
   the structure regenerates *identically*, because the same seed produces the
   same blueprint.

Before building, the generator samples the footprint and abandons the site if
it finds chests, beds, rails, torches or anything else that says somebody
lives there. It also only builds on natural End ground, which keeps end
cities, the obsidian pillars and existing structures intact.

**Shaders → Vibrant Visuals.** Custom render pipelines have been closed off
for years. The Vibrant Visuals data files are the supported replacement, and
they reach further than the old shader packs did: real volumetric scattering,
PBR materials, per-biome lighting.

### Textures are generated, not drawn

`tools/gen_art.py` produces every texture from code — albedo plus a matching
`_mer` map for metalness / emissive / roughness — using a small pure-Python
imaging toolkit in `tools/artlib.py`. No Pillow, no committed binary art you
cannot edit.

Emissive maps are derived from the albedo rather than painted separately: each
recipe names an anchor colour, and pixels near it glow in proportion. Change a
palette entry and the glow follows automatically.

```
python3 tools/gen_art.py       # regenerate every texture (deterministic)
python3 tools/preview.py       # dist/texture_preview.png, zoomed contact sheet
```

The six anchor colours live in `PALETTE` at the top of `tools/gen_art.py`.
Everything else is derived from them, so retinting the pack is a six-line edit.

---

## Checking it

Add-on JSON fails silently. A malformed file is skipped at load, the block
never appears, and the reason sits in a log nobody opens. So the pack ships
with four checks:

```
npm install       # dev-only: Mojang's schemas, id tables, and TypeScript
npm run check
```

| Check | What it catches |
|---|---|
| `check:ids` | Every `minecraft:` and `voidbound:` identifier in every JSON value and JS string, against Mojang's published id tables. This is what caught `minecraft:end_stone_bricks` — Bedrock calls that block `minecraft:end_bricks`. |
| `check:json` | Every JSON file against `@minecraft/bedrock-schemas` for the target version |
| `check:scripts` | Runs the siting, blueprint and loot code against a stub of `@minecraft/server` — 10,000+ assertions over 200 seeds per structure |
| `check:types` | TypeScript over the scripts against the real `@minecraft/server` 2.9.0 type definitions |

**On how much the schema check is worth.** The published schemas are a beta and
in places contradict Mojang's own documentation and the vanilla packs — they
type block `display_name` as an object when the docs call it a loc-string key,
type manifest versions as strings when every vanilla pack uses arrays, and
type geometry vectors as Molang strings when every `.geo.json` uses numbers.
Those are recorded as known defects in `tools/validate.mjs`, each with the
reason, and reported as warnings rather than failures. The schemas are also
uneven: entity definitions are checked against 394 components, items against
2. Mutation-testing the validator, it catches wrong types in entities, spawn
rules and blocks, and misses unknown component names, out-of-range values and
most item fields. Treat a clean run as "no known-bad JSON", not "provably
correct".

## What the in-game loads found

Two rounds of content-log errors on Bedrock 26.44 (iOS). Every one is a case
the published schemas and Mojang's own documentation both accept but the
engine rejects, so none could have been caught without running it.

**Round one:**

| Log error | Cause | Fix |
|---|---|---|
| `minecraft:flower_pottable` needs Upcoming Creator Features | Requires block format 1.21.120; the blocks declared 1.21.100 | Bumped to 1.21.120 |
| `child 'minecraft:instrument_sound' not valid here` | The engine rejects the object form the schema documents | Component dropped |
| `min_sides_must_attach` value 0 outside `[1, 4]` | 0 does not mean "no requirement" | Set to 1 |
| Recipe malformed, "is not a block" | Cascades from the blocks that failed to parse | Resolved by the above |

**Round two:**

| Log error | Cause | Fix |
|---|---|---|
| `random_offset -> x -> range: expected an object` | `range` takes `{min, max}`, not `[min, max]` — the schema allows the array form | Switched to the object form |
| `minecraft:wearable -> dispensable: not present in the Schema` | `dispensable` does not exist in this version | Removed from all four armour pieces |
| `cannot find atmosphere definition` | Still unresolved — see below | The binding removed so it stops taking the rest down |

### The atmosphere binding, and why it is currently off

`RP/atmospherics/end.json` will not register, and the log says only
`[Lighting] Expected keyframes`. The file has been rewritten twice — once as a
structural clone of the vanilla pack's own `end_atmospherics.json`, once with
every value keyframed — and neither took.

A client biome file is all-or-nothing: one unresolvable identifier makes the
engine discard the whole file. So that single failing binding was throwing away
the fog, sky colour, lighting and colour grading bindings with it, which is why
the End kept rendering as vanilla no matter what else changed. The
`minecraft:atmosphere_identifier` line is now removed from the client biome.
The other four bindings apply, and the atmospherics JSON stays in the pack,
unreferenced, until the cause is understood.

The sky is covered regardless by the `end_sky.png` override, which does not go
through Vibrant Visuals at all.

### Reading the log

Content-log errors carry the world path they came from. Two different worlds
appeared in the last report — one still running an older build of the pack, so
half those errors were already fixed. Check the path before chasing one:
`.../minecraftWorlds/<world id>/behavior_packs/pack`. The
`Syc's Force Creative` scripting error is a different add-on entirely.

### Still unverified

- Whether the Rift Sovereign fight reads well in play — phase timings, attack
  cadence and damage are tuned blind.
- Armour rendering on the player model, and whether the plate art lines up
  with vanilla's armour UV layout.
- Structure generation timing under elytra — `BUILD_RADIUS` in
  `BP/scripts/world/generator.js` may need raising.
- Mob spawn rates; the weights in `BP/spawn_rules/` are still first guesses.
- The mobs and the boss have no custom sounds; they are silent.

## Tuning

| What | Where |
|---|---|
| Palette / all texture colours | `PALETTE` in `tools/gen_art.py` |
| Sky, sun, flash, ambient | `RP/lighting/end.json` |
| Sky colours and scattering | `RP/atmospherics/end.json` |
| Fog density and colour | `RP/fogs/*.json` |
| Structure spacing and rarity | `CELL_SIZE`, `SITE_CHANCE`, `INNER_CLEARANCE` in `BP/scripts/world/sites.js` |
| Which structures, how often | `STRUCTURES` weights in `BP/scripts/structures/index.js` |
| Chest contents and rarity curve | `BP/scripts/content/loot.js` |
| Ore and flora density | `BP/feature_rules/*.json` |
| Mob spawn weights | `BP/spawn_rules/*.json` |
| Armour stats and set bonus | `BP/items/void_*.json`, `BP/scripts/content/armorSet.js` |

## Layout

```
BP/                     behavior pack
  blocks/ items/        8 blocks, 8 items (4 of them armour)
  entities/ spawn_rules/ loot_tables/
  features/ feature_rules/   ore, shattered stone and flora generation
  recipes/
  scripts/
    lib/                rng, vectors, blueprint placement
    structures/         the four blueprints
    world/              siting, generation, atmosphere, discovery, persistence
    content/            loot tables and the rift compass
RP/                     resource pack
  lighting/ atmospherics/ color_grading/ pbr/ local_lighting/ fogs/
  biomes/               client biome binding the above to the End
  textures/             generated art + texture sets
  models/ animations/ entity/ render_controllers/ attachables/
tools/                  art generation and the four checks
```

## Compatibility

Targets `min_engine_version` `[1, 26, 40]`, so it loads on 26.4 and its
hotfixes including 26.44. Uses `@minecraft/server` 2.9.0, the stable script API
shipped with that drop. The `pbr` capability requires 1.21.120 or newer, which
26.4 comfortably clears.

Achievements stay enabled — nothing here turns on cheats.
