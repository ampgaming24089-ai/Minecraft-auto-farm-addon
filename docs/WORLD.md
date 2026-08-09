# The island: regions, structures, spawners

Expands on `docs/DIMENSION.md` — since the Hollow Veil is a script-registered
void dimension with no real world generator, "biomes" and "structures" here
are entirely script-built. This file covers the layer added on top of the
base island (terrain + Hollow Hamlet + the 3 boss altars from the original
build): four themed regions, two landmark structures, and the spawner
blocks that guard them.

## Regions (`BP/scripts/world/build.js` → `regionAt`)

The island is split by quadrant around a neutral core:

| Region | Where | Ground | Ambient mobs |
|---|---|---|---|
| Misty Reach | center, radius 26 | bonestone (default) | wraith, banshee, poltergeist, shade, fallen knight, soul wisp |
| Bastion | +x, −z | blackstone | hellhound, imp, ashen whelp (roaming, not the Sentinel guards) |
| Ashlands | +x, +z | blackstone + magma accents | hellhound, imp, ashen whelp |
| Boneyard Marsh | −x, +z | veil mud + glimmershroom light | bonehide elk, glimmershroom toad, poltergeist |
| Sunken Ruins | −x, −z | deepslate tiles | ashwing bat, marrow crawler, shade, wraith |

This is a script-side classification only — there's no Bedrock biome under
any of it (see `docs/DIMENSION.md` for why) — but it drives both the ground
palette laid down in `paintRegions()` and which mobs
`BP/scripts/mobs/spawner.js` picks from near each player, so it reads as
distinct territory in practice.

## Structures

Built once, during the same `ensureWorldBuilt()` pass as the rest of the
island (see `docs/STRUCTURES.md` for why everything here is code, not a
shipped `.mcstructure`):

- **Ember Bastion** (bastion quadrant) — a walled blackstone/bastion-brick
  fortress with four corner towers, a molten-floor courtyard, a loot chest
  (sentinel cores, ember coal, veilsteel scrap), and two Sentinel Spawners.
- **Sunken City** (ruins quadrant) — a five-tower ruined skyline around a
  plaza, a vault chest (veilsteel plating, spectral dust, a small chance of
  a dragon egg) under the tallest tower, two Wraithguard Spawners, and a
  Crawler Spawner in the undercroft.

## Spawner blocks (`BP/scripts/world/spawners.js`)

`hollowveil:wraith_spawner` / `hellhound_spawner` / `sentinel_spawner` /
`wraithguard_spawner` / `crawler_spawner` are placed directly by the
structure builders above at known coordinates (recorded in a world dynamic
property, not discovered by scanning). A lightweight interval script checks
each one every ~3s: if a player is within 20 blocks and fewer than 4 of
that spawner's mob are already nearby, it spawns one and goes on a ~10s
cooldown — the same shape as a vanilla monster spawner, without needing one.
Per-spawner cooldowns live in memory only; a world restart just makes every
spawner immediately available again, which is a cheaper problem than
keeping a growing position→cooldown map in sync on every fire.

## Extending this

Both structure builders and `paintRegions()` are ordinary `/fill`/`setblock`
sequences — adding a third landmark structure or a fifth region is a matter
of writing another builder function and (for a new spawner-guarded
structure) pushing entries onto the `spawnerPositions` array before it's
saved.
