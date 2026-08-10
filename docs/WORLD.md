# The world of the Hollow Veil

A dimension registered through the Script API has no world generator, so
every block here is placed by this addon. That constraint shapes the whole
design.

## Streaming terrain

The world is a disc of radius **1024** (~130x the old 90-block island at
512, and 4x that again at 1024). It is not built up front - that would be tens of thousands of
commands in a single tick and a hung client. Instead
`BP/scripts/world/terrain.js` builds it one **32x32 sector** at a time,
only within 3 sectors of a player, at most one sector per pass. Which
sectors are finished is persisted, so terrain survives relogs, never
rebuilds, and never overwrites anything a player has changed.

Within a sector, columns of equal height and biome are merged into strips
before being filled, which turns ~1024 potential commands into a few dozen.

## Biomes

`BP/scripts/world/biomes.js` decides which biome owns a position from two
independent value-noise fields, so territories are large irregular blobs
that interleave at the edges rather than four fixed pie slices. Measured
coverage is roughly even:

| Biome | Share | Ground | Signature mobs |
|---|---|---|---|
| The Grave Moors | ~24% | podzol, headstones, dead trees | Wraith, Banshee, Shade, Poltergeist |
| The Ashlands | ~25% | blackstone, magma, ember vents | Hellhound, Imp, Ashen Whelp, Bastion Sentinel |
| The Boneyard Marsh | ~22% | veil mud, pools, glimmershrooms | Bonehide Elk, Glimmershroom Toad, Marrow Crawler, Ashwing Bat |
| The Sunken Ruins | ~29% | deepslate tile, rubble | City Wraithguard, Ashwing Bat, Shade, Fallen Knight |

A neutral hub (**The Misty Reach**) covers the first 40 blocks around
spawn, where Hollow Hamlet and the three Warden altars sit.

Height varies over roughly a 28-block range and flattens toward the hub so
the village is always buildable; the rim falls away into the void.

**Graveyard read**: the moors are the heartland of it, but every biome also
gets a thin scatter of headstones, grave mounds and bone litter, so the
whole dimension keeps a burial-ground feel rather than confining it to one
quarter of the map.

## Landmarks

`BP/scripts/world/sites.js` rolls a catalogue of **206 sites** across the
map, each filtered to the biomes it belongs in and spaced at least 46
blocks apart. They range from ~170 to ~985 blocks from spawn, so there is
always something further out. Each is built the first time a player comes
within 48 blocks of it.

| Site | Biome | Count |
|---|---|---|
| Graveyard (fenced plot, headstone rows) | Moors | 34 |
| Mausoleum | Moors | 16 |
| Ruined watchtower | Moors, Ruins | 22 |
| Ember bastion | Ashlands | 14 |
| Smouldering camp | Ashlands | 22 |
| Bone nest | Marsh | 24 |
| Abandoned hut | Marsh | 14 |
| Drowned city | Ruins | 12 |
| Broken arch | Ruins | 28 |
| Crypt (stairs down to a buried loot room) | Moors, Ruins | 20 |

Placement comes from the same deterministic hash as the terrain, so the
site list is stable: leave and come back and the crypt is still there.

## Darkness and fog

Each biome has its own fog definition in `RP/fogs/`, pushed onto the player
with the `/fog` command as they cross a border
(`BP/scripts/world/atmosphere.js`). All of them are dark and close - the
marsh closes to 34 blocks, the moors to 42 - which is what actually sells
the darkness. Natural light sources are deliberately rare: soul lanterns
scatter at well under 2% of feature rolls.

## Ore

Ore is scattered **per sector** rather than once per world, so every
territory you explore is minable. Hollowforged stays genuinely rare via an
extra roll on top of its already-low per-sector count.

## Creature surfacing

Every mob is assigned a surface material in `ENTITY_PATTERN`
(`tools/gen_assets.py`) which `boxuv.paint_cube` renders into its texture:
cloth folds for robed spirits, banded plate with rivets for armoured
mobs, rib striping for bone creatures, offset scale rows for dragons and
reptiles, broken strands for fur. Each face also gets a top-lit/bottom-
shadowed vertical gradient and a one-pixel rim highlight along its top
edge. Flat single-value faces were the main reason the old models read as
featureless blobs at any distance.
