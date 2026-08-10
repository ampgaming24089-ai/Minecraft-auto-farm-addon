# The world of the Hollow Veil

A dimension registered through the Script API has no world generator, so
every block here is placed by this addon. That constraint shapes the whole
design.

## Streaming terrain

The world is a disc of radius **512** (~130x the area of the old 90-block
island). It is not built up front - that would be tens of thousands of
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

`BP/scripts/world/sites.js` rolls a catalogue of **76 sites** across the
map, each filtered to the biomes it belongs in and spaced at least 46
blocks apart. They range from ~120 to ~470 blocks from spawn, so there is
always something further out. Each is built the first time a player comes
within 48 blocks of it.

| Site | Biome | Count |
|---|---|---|
| Graveyard (fenced plot, headstone rows) | Moors | 14 |
| Mausoleum | Moors | 6 |
| Ruined watchtower | Moors, Ruins | 8 |
| Ember bastion | Ashlands | 5 |
| Smouldering camp | Ashlands | 8 |
| Bone nest | Marsh | 9 |
| Abandoned hut | Marsh | 5 |
| Drowned city | Ruins | 4 |
| Broken arch | Ruins | 10 |
| Crypt (stairs down to a buried loot room) | Moors, Ruins | 7 |

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
