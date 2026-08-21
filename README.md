# End Ascendant — an End overhaul for Minecraft Bedrock

The End has been one biome, one sky and two structures since 1.9. End
Ascendant rebuilds it for Bedrock **26.4** (internal `1.26.40`, current hotfix
`26.44`): a forest, three bosses, thirteen mobs, a full tool and armour tier, a
food chain, a waystone travel network, five structure types scattered across the
outer islands, and an atmosphere that moves.

Everything runs on documented, non-experimental APIs. No experiments toggle,
no world conversion, no commands typed by the player.

| | |
|---|---|
| Blocks | 23 |
| Items | 25 |
| Mobs | 16, three of them bosses |
| Recipes | 32 |
| Structures | 5 kinds, procedurally varied |
| Particle effects | 12 |
| Animations | 29 clips across 14 models |
| Textures | 142, all generated from code |

```
./build_addon.sh --check      # validate everything, then build the .mcaddon
```

Import the `.mcaddon`, enable both packs on a world, and turn **Vibrant
Visuals** on in video settings for the full lighting treatment. The pack still
works with it off — you get the sky, fog, particles and all the content, just
not the PBR lighting.

## What changes

### The sky and the light

The End's built-in look is a flat purple void: two constant white directional
lights, a near-black sky, no depth. End Ascendant replaces the whole Vibrant
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
one mood. End Ascendant ships four fog definitions and pushes the right one onto
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
  broken pillars. The Rift Sovereign holds it.
- **Voidwatch Tower** — the landmark. A 26–38 block shaft with a spiral stair
  cut into its inner wall, ringed galleries for landings, and the cache on an
  open deck at the top rather than in a vault at the bottom. The stair is
  carved as part of the shell, so the erosion pass can never leave it floating
  or bury it.

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

### The Void Titan

The third boss, and the opposite reading of the same threat. The Sovereign
fights in the air; the Titan never leaves the ground, and everything it does
travels along it. 550 health, 16 damage, immune to knockback and to fire, and
it guards the foot of every Voidwatch Tower.

| Attack | What it does | Counterplay |
|---|---|---|
| Slam | 8-block ring, damage falling off toward the edge | Be further out |
| Fissure | A crack that walks one block at a time toward one player | Step out of the line |
| Grab | Drags the *furthest* player back in | Do not fight it from a ledge |
| Quake | Below 40% health: 18 blocks, no safe distance | Be airborne when it lands |

The fissure is drawn on a timer rather than all at once, so it reads as
travelling and a player who moves escapes it. The quake checks `isOnGround`,
which makes "get off the floor" a real answer rather than a damage race. Below
40% every cooldown drops by 40% and the quake unlocks.

It drops a **Titan Core** — a one-of-a-kind item that hands you the Titan's own
footing for twelve seconds: Resistance III, Strength II, and its slam. It has a
75-second cooldown and is inert outside the End.

### The waystone network

The End is wide and mostly empty, and once you have found a grove, a sanctum
and a tower there is no reason to walk between them a second time. Waystones
close that loop.

Every Luminous Grove, Shattered Sanctum and Voidwatch Tower generates with one.
Stand at a waystone and interact: it attunes, joins the world's network, and
opens a menu of every *other* waystone you have personally stood at. Pick one
and you are there.

Two rules keep it from flattening the dimension:

- **Discovery is per-player.** The network is world-wide, but the menu only
  lists stones you have visited yourself, so the map still has to be earned
  once. Placing a waystone attunes it for the placer immediately.
- **It only reaches inside the End.** Interact with one anywhere else and it
  stays inert.

Arrival grants five seconds of Slow Falling, which covers the one case the
destination cannot: a stone that has since been undermined, leaving the arrival
point over open air. Waystones are craftable from ender bricks, an echo shard
and a voidsteel ingot, and the network is capped at 40 stones — past that the
menu stops being something anybody wants to read, so the oldest drops off.

### Ender saplings

Ender leaves drop saplings. Plant one on end stone and it grows into a tree on
its own in about a minute, or immediately with bone meal.

Bedrock's random-tick plumbing for custom blocks is a moving target, so growth
is not left to it: a placed sapling is written into a world dynamic property
with the tick it went in, and a slow pass grows the ones whose time has come
and whose chunk is loaded. The tree itself is authored in script rather than
reusing the worldgen feature — a feature cannot be invoked from script, and a
planted tree wants to be a little smaller than a wild one so a grove you build
does not swallow whatever you built it next to. Logs and leaves only replace
air, so a trunk that leans can never carve through something you built.

### The sky, and making it move

`RP/textures/environment/end_sky.png` replaces the End's skybox. This is
deliberately *not* a Vibrant Visuals cubemap: Mojang restricts cubemap
customisation to the Overworld, and the End keeps its built-in one.
Overriding the vanilla texture works either way.

Two constraints pull against each other. The game tiles this 128px texture
many times across every face, so large features or strong contrast read as
wallpaper — a first attempt at a magenta nebula did exactly that, and a second
attempt fixed it by going nearly black, which made the dimension feel dead.
The resolution is to keep the colour variation large but very low contrast, so
it never resolves into a repeating shape, and put all the high-frequency detail
into stars, which are small enough that repetition is invisible. The base sits
well off black so the sky glows on its own.

Bedrock gives a pack no way to animate a skybox. What it gives is particles,
and particles in front of a sky do most of the work a moving sky would.
`BP/scripts/world/ambience.js` spawns motes drifting up past the islands and
occasional streaks falling through the dark overhead, placed on a ring around
the player so they read as depth rather than as dust on the lens.

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
- **Chorus Hopper** — passive grazer that bolts from anything hostile. Breeds
  with chorus fruit, raises young, and drops haunches: the End's meat supply.
- **Crystal Crawler** — low, fast six-legged swarmer armoured in echo crystal.
- **Shard Wraith** — a hollow flying shroud that ignores terrain.
- **Void Serpent** — the End's apex flyer: six segments, each lagging the one
  ahead by a fixed phase, so one wave expression makes the whole body swim.
- **Glimmerfin** — a passive ray that drifts between islands in shoals and
  feeds on ender fruit.
- **End Stone Golem** — neutral. It ignores you entirely and hunts the End's
  monsters on sight, which makes a grove worth settling beside.
- **Astral Whale** — the biggest thing in the End's sky. Sixteen blocks of
  body drifting in slow arcs at a deliberately low animation frequency, because
  a whale is only convincing if it is slow. Drops astral shards.
- **Voidling** — a knee-high scavenger that follows ender fruit and flees
  anything with teeth. Drops fruit, crystals and the occasional pearl.
- **Ender Beetle** — a six-legged forager that walks a real tripod gait (legs
  0/3/4 swing together, 1/2/5 oppose them) and only fights back. Drops void
  chitin.
- **Rift Sovereign**, **Echo Warden**, **Void Titan** — the three bosses, below.
- **Rift Compass** — points at the nearest structure by name, distance and
  bearing, and names the runner-up so you can pick a route.

### End Ascendant armour

The endgame set, a clear step past netherite:

| | Helm | Cuirass | Greaves | Sabatons | Set |
|---|---|---|---|---|---|
| End Ascendant protection | 4 | 9 | 7 | 4 | **24** |
| Netherite protection | 3 | 8 | 6 | 3 | 20 |
| End Ascendant durability | 561 | 816 | 765 | 663 | |
| Netherite durability | 407 | 592 | 555 | 481 | |

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

A second chain runs off the new mobs: **void chitin** from ender beetles and
**astral shards** from astral whales combine with a void crystal into a
**voidsteel ingot**, which is what a waystone is built around. Chitin also
stacks into a block, and the End's stone now polishes and cracks — polished end
stone, cracked ender bricks, and a block of void chitin round out the building
set.

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
| `check:ids` | Every `minecraft:` and `voidbound:` identifier in every JSON value and JS string, against Mojang's published id tables. This is what caught `minecraft:end_stone_bricks` — Bedrock calls that block `minecraft:end_bricks`. It also checks that `local_lighting` only names blocks (it once named `end_crystal`, which is an entity), and scans the raw file text for whole-number fields written as floats — `"speed": 14.0` is a different literal from `"speed": 14` to the engine, and JSON parsing erases the difference, so this rule has to read the text. Client entities get their own pass: a geometry, animation, render controller or texture path that does not resolve renders the mob as a blank cube or as nothing at all, silently, so every one of those four cross-references is resolved against the files actually in the pack. |
| `check:json` | Every JSON file against `@minecraft/bedrock-schemas` for the target version |
| `check:scripts` | Runs the siting, blueprint and loot code against a stub of `@minecraft/server` — 12,000+ assertions over 200 seeds per structure. It also imports and *starts* every system, because a module that throws at load takes the whole script pack offline in game with nothing in the log pointing at the cause, and asserts `main.js` actually calls each one. |
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

- Whether the three boss fights read well in play — phase timings, attack
  cadence and damage are all tuned blind.
- Waystone menu behaviour on touch devices, and whether cancelling the form
  leaves anything stuck.
- Sapling growth timing; `GROW_TICKS` in `BP/scripts/content/enderSapling.js`
  is a first guess at one minute.
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
| Boss health, attacks and cooldowns | `BP/scripts/content/riftSovereign.js`, `voidTitan.js` |
| Waystone cap and network rules | `MAX_STONES` in `BP/scripts/content/waystones.js` |
| Sapling growth time | `GROW_TICKS` in `BP/scripts/content/enderSapling.js` |
| Flyer ceilings and leash lengths | `FLYERS` in `BP/scripts/world/flightControl.js` |

## Layout

```
BP/                     behavior pack
  blocks/ items/        23 blocks, 25 items (4 of them armour, 5 tools)
  entities/ spawn_rules/ loot_tables/
  features/ feature_rules/   ore, shattered stone and flora generation
  recipes/
  scripts/
    lib/                rng, vectors, blueprint placement
    structures/         the five blueprints
    world/              siting, generation, atmosphere, discovery, persistence
    content/            loot, compass, bosses, waystones, saplings, armour set
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
