# Eternal End

A Minecraft Bedrock add-on that turns the End into somewhere worth living.

Seven regions with their own ground, weather, light, wood and wildlife; land
stacked through the whole world height instead of one flat band at eye level;
forty-one mobs including five bosses, tameable herds and a flying mount; End
villages with traders; and a full set of tools, armour, food and travel gear
built out of what the End itself grows.

## Installing

```
./build.sh          # writes ../dist/EternalEnd.mcaddon
```

Open the `.mcaddon` on a device with Minecraft Bedrock installed, or drop it
into the game's `behavior_packs` and `resource_packs` folders. Both packs must
be active on the world - the behaviour pack lists the resource pack as a
dependency, so enabling one usually pulls in the other.

**If you already have the earlier "End Everlasting" build installed:** this
ships under new manifest UUIDs, so it imports as a separate pack rather than
colliding with it. Nothing was renamed *inside* the pack - every block, item
and mob keeps the identifier it had - so you can swap the new pack into an
existing world and everything already placed there keeps working. Enable one
or the other, not both.

New terrain features - the stacked islands, the region trees - appear as you
travel, so an existing world fills in around you rather than all at once.

## What is in it

### The map

Bedrock gives the End exactly one biome and no way to add another, so the
regions are drawn in script: `world/biomes.js` assigns a region to every point
as a pure function of the world seed, and everything a player can perceive
follows from it - the ground under them, the fog, the lighting, the particles,
the trees, and what spawns.

| Region | Ground | Wood | Character |
| --- | --- | --- | --- |
| Voidfall Barrens | *unpainted* | Voidwood | The End you already know, with the odd dead tree |
| Glowspore Basin | Glowspore soil | Sporewood | Magenta fungal caps, drifting spores |
| Bonespire Reach | Bonespire stone | Bonewood | Pale spires, falling frost |
| Crystalline Expanse | Crystalline end stone | Shardwood | Violet crystal, glinting air |
| Verdant Canopy | Verdant end stone | Ender | The one place in the End that is green |
| Ashen Wastes | Ashen end stone | Cinderwood | Charcoal ground, rising embers |
| Aurora Shelf | Aurora stone | Auralwood | Cyan light, shimmer overhead |

Islands hang at five separate heights from y=16 to y=238, built from the
region underneath them, so looking up in a region tells you which one you are
in. Around forty are in range of a player at any time.

### The mobs

Twenty of them are the Eternal End roster, built from the design pack in
`design/`:

**Bosses** — Void Dragon, Ender Overlord, The End King. Each seats itself at a
different structure: the Dragon roosts on a Void Spire, the King holds court in
a Shattered Sanctum, the Overlord comes through a Rift Anchor.

**Hostile** — Void Stalker, Endermite Hive, Purpur Golem, Shulker Beast, Void
Wisp, End Spider, Corrupted Enderman, Chorus Fiend, Void Slime, Teleporter, End
Crab, Obsidian Beast.

**Passive and tameable** — Ender Deer, Chorus Cow, Void Hog, Sky Ray, Ender
Bird. Tame with Lumen Feed, breed them, and they are a renewable meat supply.
The Chorus Cow milks. The Sky Ray can be ridden, and flies.

The other twenty-one are the original End Everlasting roster and are unchanged.

## Layout

```
BP/                 behaviour pack: entities, blocks, items, loot, spawn rules, scripts
RP/                 resource pack: models, textures, animations, fog, lighting, sky
design/             the Eternal End design sheets and the 20-mob spec
tools/mobgen/       generates the twenty mobs: geometry, art, entities, animations
tools/treegen/      generates the six new wood sets and BP/scripts/lib/tree.js
tools/skygen/       draws the sky texture
tools/icongen/      draws the pack icon
tools/validate.py   resolves every reference in both packs
build.sh            packages BP/ and RP/ into a .mcaddon
```

### Generated files

Everything under `tools/` writes into `BP/` and `RP/`. Those outputs are
checked in - the pack has to be buildable without Python - but they are
**generated**, and editing them by hand means the next build reverts it.
Change the generator instead:

```
python3 tools/mobgen/build.py      # the twenty mobs
python3 tools/mobgen/preview.py    # renders the roster so you can look at it
python3 tools/treegen/build.py     # the wood sets
python3 tools/skygen/build.py      # the sky
python3 tools/icongen/build.py     # the pack icon
python3 tools/validate.py          # check everything still resolves
```

`validate.py` is the one to run before shipping. Bedrock fails quietly - a
geometry that does not exist gives you an invisible mob and no error anywhere
a player can see - so it resolves every identifier, texture path, geometry,
animation, animated bone, loot table, spawn rule, recipe and atlas entry in
both packs, and every identifier the scripts name in a string literal.
