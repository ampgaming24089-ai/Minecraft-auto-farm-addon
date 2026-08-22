# Endrealm — an End overhaul for Minecraft Bedrock

The End has been one biome, one sky and two structures since 1.9. Endrealm
rebuilds it for Bedrock **26.4** (internal `1.26.40`, current hotfix `26.44`):
**seven biomes** in a dimension the engine says has one, floating
islands stacked through the whole world height, **End villages** with traders
who deal in three professions, crops, four breedable companions, **23 mobs**
built and animated from the ground up, a tree species for every region, a full
tool and armour tier, a waystone travel network, an animation pack for the
player and every mob in it, and an atmosphere that moves.

Everything runs on documented, non-experimental APIs. No experiments toggle,
no world conversion, no commands typed by the player.

| | |
|---|---|
| Biomes | 7, seed-derived, with their own terrain, fog, light and air |
| Blocks | 62 |
| Items | 28 |
| Mobs | 23 in the roster, four of them bosses, four breedable |
| Trees | 6 species, one per region, each a different crown |
| Recipes | 36 |
| Structures | 6 kinds, procedurally varied |
| Trades | 3 professions across 2 tiers each |
| Worldgen features | 15, across 9 placement rules |
| Fog definitions | 9, one per biome plus depth and structures |
| Particle effects | 27 |
| Animations | 224 clips, including a player animation pack |
| Textures | 141, all generated from code |

```
./build_addon.sh --check      # validate everything, then build the .mcaddon
```

Import the `.mcaddon`, enable both packs on a world, and turn **Vibrant
Visuals** on in video settings for the full lighting treatment. The pack still
works with it off — you get the sky, fog, particles and all the content, just
not the PBR lighting.

## What changes

### The sky and the light

The skybox is a starfield, and the reason it is not more than that is worth
stating: Bedrock tiles one texture across all six faces of the sky cube, many
times per face, and gives a pack no way to change that. There is no per-face
texture and no scale control. A single image stretched over the whole sky is
not possible - whatever is in that file repeats, in a grid.

A nebula was tried. It was seamless, in the sense that its edges met perfectly,
and it looked like a lattice of identical bright boxes marching off to each
face's vanishing point. What gives a tile away is not its seam, it is its
content: anything the eye can recognise twice is a grid. So the sky is a flat
base - identical on every face, no edge findable - carrying stars in three
tiers of brightness, a few with halos, four with diffraction spikes. Depth
comes from contrast between bright and faint rather than from any shape.


The End's built-in look is a flat purple void: two constant white directional
lights, a near-black sky, no depth. Endrealm replaces the whole Vibrant
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
one mood. Endrealm ships four fog definitions and pushes the right one onto
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

### Seven biomes, in a dimension that has one

Bedrock gives the End exactly one biome and no way for an add-on to add
another. Every End pack that appears to have biomes is doing what this does:
dividing the dimension into regions in script, then changing everything a
player can actually perceive — the ground under them, the fog, the light, the
particles, what spawns, and a name on screen when they cross a border. The
engine still thinks it is all `minecraft:the_end`. Nobody flying over it does.

| Biome | Ground | Air | Reads as |
|---|---|---|---|
| **Voidfall Barrens** | untouched End stone | the base haze | the End you already know — a quarter of the dimension, and what makes the other six feel like somewhere else |
| **Glowspore Basin** | magenta fungal soil, sporelight caps on stalks | thick, hot, close | a basin you are down inside rather than looking across |
| **Bonespire Reach** | pale striated bone, frost blooms | cold and very wide, almost no absorption | somewhere the haze carries to the horizon |
| **Crystalline Expanse** | violet-veined stone, echo clusters | thin and bright, hard glints | air that glitters rather than obscures |
| **Verdant Canopy** | verdant crust over moss, bushes and saplings | teal, strong forward scattering | the one safe-feeling place out there |
| **Ashen Wastes** | burnt charcoal stone, ember vents at light 14 | short draw, heavy absorption, warm | the only biome that hides things from you |
| **Aurora Shelf** | pale iridescent stone | nothing at eye level, everything up high | somewhere you look up |

**Where a biome is** is a pure function of the world seed and position — no
storage, identical for every player on a seed, and answerable for a place
nobody has ever been. A plain grid of cells would give square biomes with
ruler-straight borders, so the lookup **warps its own input** before quantising
it, by an amount that itself comes from smooth value noise. The cells stay
square; the borders stop being. Regions are 640 blocks across, which is big
enough that you fly into one, watch the light change, and are still in it a
minute later.

**Painting the ground** is `BP/scripts/world/painter.js`, and it is the one
system in the pack that rewrites terrain a player might care about, so it is
deliberately timid:

- Only *worldgen* ground is ever replaced — end stone and the three variants
  this pack's features scatter through it. The biome surfaces the painter
  itself lays down are **not** on that list, which is what makes a player's
  build safe: the only way glowspore soil exists is that the painter put it
  there (and that patch is already marked done) or that somebody placed it
  (and it must not be touched).
- Flora only ever goes into air, directly on top of ground the painter just
  laid.
- A patch whose chunks were not loaded stays **unmarked**, so it is picked up
  again later rather than being left plain for the rest of the world's life.
- Work runs in `system.runJob`, which the engine budgets against the frame's
  spare time.

It paints **surface first**. Each patch is two passes over the same columns:
the first lays nothing but the surface block, the second goes back for the
filler underneath, the growth hanging off the island's belly, the trees and
the flora. Done in one pass, all of that sat in front of the next column's
colour change and a patch only *looked* painted once every part of it was
finished. Split, the biome arrives immediately and fills in behind itself.

The first version was also far too timid about rate: three 8×8 patches every
two seconds inside a 56-block disc — a hundred seconds to convert ground the
player could take in at a glance, which is exactly why the End stayed plain
until you were standing on it. It is now a 128-block disc at roughly 1,300
columns a second, which fills in well under a minute, and the throttle that
matters is `MAX_IN_FLIGHT` rather than the queue rate: `runJob` already
self-limits, so the queue only has to be stopped from growing without bound.
The numbers are asserted in `npm run check:scripts` so they cannot drift back.

**Everything else follows the region.** Fog resolves in priority order: depth
beats everything, a structure beats its biome (a grove should feel like a grove
whichever region it sits in), and otherwise the biome decides. Particles come
from the biome table with their own vertical lift, because frost has to fall
from somewhere and embers have to climb out of something — and each emitter
re-checks its own footing, so nothing leaks across a border. Rates halve near
an edge, because a biome that switches its air on like a light gives away that
it is a script rather than a place.

Spawning is region-gated too, since spawn rules can only filter on the
*engine's* idea of biome. Each region's roster is topped up from script at a
rate low enough to supplement natural spawning rather than replace it —
vanilla endermen keep their share of the spawn budget, which was a specific
thing to protect.

### Using the height of the world

The End generates one band of islands around y=60 and then a hundred and fifty
blocks of nothing above it. That is most of the dimension unused, and it is why
the End reads as flat however wide it is — everything sits at eye level, so
there is never anything to climb toward.

`BP/scripts/world/skyIslands.js` hangs more land through the whole column,
between y=96 and y=210, sited from the seed exactly the way structures are.
Each one is built from **the biome underneath it**, so a Glowspore Basin gets
magenta islands overhead and an Ashen Waste gets charcoal ones: looking up in a
region tells you which region you are in.

Two rules keep it from wrecking anything. An island is only ever built into
air — the entire footprint is tested before a single block is placed, and one
non-air block anywhere in it abandons the site and remembers the refusal, so
nothing this places can overwrite terrain, a structure or a build. And nothing
generates within 900 blocks of the origin, so the main island, the pillars, the
gateway and the dragon arena are untouched.

### Undersides

An End island stopping dead at its own bottom face is the single biggest tell
that it was generated rather than grown, so every biome now hangs something off
it: spore tendrils, frost icicles, crystal dripstone, ender vines, ash
stalactites, and a fraying aurora veil that is a hanging sheet rather than
strands. The painter finds the lowest solid block of each column and grows down
from it — bounded, because a column over the void has no bottom and that must
not be discovered by searching the whole world.

### End villages

Every other structure in the pack is a ruin or a threat. This is the one that
is occupied, and everything about how it is built says so from a distance:
dressed stone that belongs to no biome, lantern posts along the paths, a well
at the centre with the huts on a ring facing inward, a market stall, and a crop
plot already planted.

The residents are **End villagers** — an enderman's proportions under a hooded
robe, which is the point: related to the things out there without being one.
Each picks a profession at spawn:

| Profession | Buys | Sells |
|---|---|---|
| **Void Merchant** | echo shards, void chitin, ender fruit | iron, emeralds, torches; at tier two, diamonds, ender pearls and a single elytra |
| **Shard Smith** | void crystals | voidsteel, and at tier two the pack's own swords, picks and armour |
| **Spore Herbalist** | bloom pods, lumen berries | bloomstalk seed, pies, cooked haunches, saplings, golden apples |

They all deal in **void sigils**, which are minted from voidsteel and crystal —
so a player who cannot find a village can still enter its economy, and one who
can has a reason to farm.

They flee rather than fight. A trader that brawls is a trader you lose, and
these are the only friendly faces out there.

### Farming, and something to keep

**Bloomstalk** is the End's crop: four growth stages, plantable on End stone or
any biome surface, bone-mealable. Breaking a ripe one drops pods *and* seed and
**replants itself at stage zero**, so an established plot keeps producing;
breaking an unripe one just gives the seed back, so pulling a crop early is a
mistake rather than a loss.

**Glowmites** are what the pods are really for. They tame on bloom pods, breed
on them, follow their owner, and gain health when tamed — the first thing in
this dimension you can keep rather than kill.

### The new mobs

- **Void Leviathan** — the colossus. Wide ribbed wings, a lit underside so it
  is still something rather than a black shape passing overhead, and a
  deliberately slow wingbeat because anything that size moving fast reads as
  weightless. Spawn weight 1: seeing one should be an event, not scenery.
- **Drift Jelly** — a bell that pulses and filaments that arrive late, which is
  the entire read of a jellyfish.
- **Cinder Stag** — charcoal hide with heat in its cracks and antlers that
  carry the fire. Grazes the Ashen Wastes on a long head-dip cycle; gores
  anything that starts something.
- **Glowmite** — small, round, warm, and it hops rather than walks: the body
  leaves the ground and the legs tuck off the same wave.

### The animation pack

Bedrock ships the player with about eighty animation clips and no way for an
add-on to add an eighty-first without taking ownership of the whole file. So
this pack copies Mojang's own `player.entity.json` verbatim and *adds* to it:
nothing vanilla is replaced, three extra animation controllers go into
`scripts.animate`, and every clip they play is an offset layered on top of
whatever vanilla already posed. That is the whole trick — the amplitudes are
small on purpose, because anything larger stops reading as a flourish and
starts reading as a broken skeleton the moment vanilla's own clip disagrees.

Eight of the clips are continuous and need no script at all, because Molang can
already see the state that triggers them:

| Clip | When | What it does |
|---|---|---|
| `idle_breathe` | standing still | Two breathing cycles at different rates, so it never resolves into an obvious loop |
| `sprint_lean` | sprinting on the ground | Leans into the run, counter-rotates the head so you still look where you are going |
| `sneak_prowl` | sneaking | Lower than vanilla's crouch, arms tucked, weight shifting foot to foot |
| `fall_brace` | falling faster than 4 m/s | Arms up, legs tucked — falling is the End's signature way to die |
| `glide_soar` | elytra gliding | Arms swept back along the wing, not spread |
| `swim_roll` | swimming | Body roll driven by distance moved, so it matches the stroke |
| `eat_relish` | using a food item | A fast nod under a slow tilt: chewing, without a jaw bone to chew with |
| `draw_steady` | drawing a bow, crossbow or trident | A tremor that **scales with `variable.item_use_normalized`** — a snap shot is steady, a long hold visibly costs you |

The other seven are one-shots that no query could predict, because they answer
events rather than states. Those fire from script through `/playanimation`,
which is the only route from the script API to a player's skeleton:

- **Victory** and **salute** on a boss dying — the player who landed the killing
  blow celebrates, everyone else within 40 blocks salutes.
- **Reach** when you attune a waystone or arrive through one.
- **Slam** when the Titan Core goes off, matching the shockwave it already made.
- **Savour** after eating anything the pack added.
- **Recoil** on taking a real hit in the End (6+ damage, so ordinary chip
  damage does not turn the dimension into a flinching contest).
- **Land absorb**, which is controller-driven rather than scripted: a knee bend
  on touching down, short enough never to fight whatever you do next.

Every `/playanimation` call passes a stop expression built from the clip's own
length. Without one the last keyframe holds and the player stands frozen in the
pose, which is a far worse failure than no animation at all.

### Mob actions

Every mob got idle and move clips in an earlier pass. This one gives all
sixteen an **attack**, a **hurt**, a **death** and an **alert** stance — 64
clips, generated rather than drawn.

They are generated because they are a rule and not an idea. An attack is a
wind-up and a follow-through, a hurt is a recoil, a death is a collapse; what
changes between creatures is which bones those map onto and how far they
travel. `tools/gen_mob_actions.py` holds that as a table of bones per mob plus
a single `scale` dial, because a whale that recoils as sharply as a beetle
looks weightless and a beetle that recoils as slowly as a whale looks broken.
The hand-authored idle and move clips stay in their own file, untouched.

Two of the four are pure client data. One shared animation controller reads
`query.has_target` for the alert stance and `query.is_alive` for the collapse,
and because every client entity maps the same two short names — `vb_alert`,
`vb_death` — to its own clips, **one controller drives all sixteen mobs**.

Attack and hurt cannot work that way: no Molang query can see a swing land, and
hooking `minecraft:behavior.delayed_attack` would mean retuning every mob's
combat just to get an animation out of it. So those fire from script on
`entityHitEntity` and `entityHurt`, again through `/playanimation`, which
reaches an entity's skeleton without touching its behaviour at all.

Death clips all run 0.95 s. Bedrock keeps a dead entity for about twenty ticks
and then removes it, so a longer collapse is one nobody ever sees the end of.

### Detail on the ground

Four things that make the End look inhabited by its own geology rather than
poured out of one bucket:

- **Ender vines** hang from the *undersides* of islands. The feature attaches
  to the block above rather than below, which is the bit that fixes the way End
  islands currently just stop at their own edge.
- **Echo clusters** grow on stone in loose scatters and drop echo shards — a
  surface deposit you spot from the air, so exploring competes with mining.
- **Pale shrooms** cover the forest floor, denser than the clusters.
- **Mossy end stone** replaces plain end stone the way an ore does, so it
  blends into the terrain instead of sitting on it as obvious blobs. Its moss
  follows its own noise field rather than the stone's, so the two patterns
  cross instead of tracing each other.

There is a fifth thing, and it is not decoration. Standing near a drop raises a
column of motes off the edge: four block samples every second, and if any of
them finds nothing below or a fall of 12+ blocks, the void gets an updraft. In
a dimension where the ground simply stops and the fall is fatal, an edge you
can see is worth more than any amount of sparkle.

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

### Endrealm armour

The endgame set, a clear step past netherite:

| | Helm | Cuirass | Greaves | Sabatons | Set |
|---|---|---|---|---|---|
| Endrealm protection | 4 | 9 | 7 | 4 | **24** |
| Netherite protection | 3 | 8 | 6 | 3 | 20 |
| Endrealm durability | 561 | 816 | 765 | 663 | |
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
answers — and in every case the answer is to stop trying to change what the
engine believes and change what the player perceives instead:

**Biomes → regions in script.** Covered above. Seed-derived, noise-warped
regions decide the ground, the fog, the air, the spawns and the name on screen.
The engine's answer to "what biome is this" never changes; everything a player
can see does. Fog is one part of that rather than the whole trick, and there
are nine definitions now rather than four.

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
| `check:ids` | Every `minecraft:` and `voidbound:` identifier in every JSON value and JS string, against Mojang's published id tables. This is what caught `minecraft:end_stone_bricks` — Bedrock calls that block `minecraft:end_bricks`. It also checks that `local_lighting` only names blocks (it once named `end_crystal`, which is an entity), and scans the raw file text for whole-number fields written as floats — `"speed": 14.0` is a different literal from `"speed": 14` to the engine, and JSON parsing erases the difference, so this rule has to read the text. Client entities get their own pass: a geometry, animation, render controller or texture path that does not resolve renders the mob as a blank cube or as nothing at all, silently, so every one of those four cross-references is resolved against the files actually in the pack — plus the short names each animation controller asks for, and whether anything reaches a declared clip at all. Animation identifiers named from *script* are checked too, which is why the emote and mob-action tables spell every one out in full: a name assembled at runtime is a name no validator can see. A `minecraft:*` client entity is recognised as an override of a vanilla one, so only the identifiers this pack actually owns are demanded of it. |
| `check:json` | Every JSON file against `@minecraft/bedrock-schemas` for the target version. Animation and animation-controller files have **no schema in the package**, so `check:ids` covers them instead: a vector that is not three components, a keyframe key that is not a time, keyframes out of order or landing past `animation_length`, a non-looping clip with no length at all (its last pose would hold for ever), and a script that stops a clip before the clip has finished. |
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

### Round three

One in-game load on 26.44 (iOS), four real bugs, and every one of them now has
a rule that catches it.

| Log line | Cause | Fix |
|---|---|---|
| `Missing referenced asset voidbound_titan_core` ×4 | `minecraft:icon` names a *key* in `item_texture.json`, not a file. The art was generated and the item registered; the atlas entry was never added, so four items existed, crafted, and rendered as nothing | Registered, plus a rule that resolves every icon and `material_instances` key through the atlases, every atlas entry to a file, and flags atlas entries nothing refers to |
| `polished_end_stone has the same ingredients as minecraft:end_bricks` | Four end stone in a square *is* the vanilla end-bricks recipe | Re-based on shattered end stone — a pack material, so it cannot collide. A rule now flags any recipe made entirely of vanilla ingredients, since that is exactly the set that can collide with a recipe this repo cannot see |
| The End looked grainy | 2358 stars in a 128px tile is **14% of every pixel**. At the distance a skybox is viewed that stops reading as stars and starts reading as film grain | Cut to 3.5% coverage, and the lost interest bought back with contrast rather than count: fewer stars, a real bright tier, halos on a handful |
| Light shafts read as hard beams with banding | `henyey_greenstein_g` at 0.82 concentrates nearly all scattering into a narrow forward lobe | 0.66 for the open End, and the fog distance band widened from 0.12 of render distance to 0.28 so the gradient has room to be a gradient |

The `Syc's Force Creative` scripting error in that log is a different add-on
entirely and has nothing to do with this one.

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
- Whether sky islands land at a density that reads as a layer rather than as
  clutter, and whether `BUILD_RADIUS` at 132 gets them built before a player
  flies into where one should have been.
- Whether villages generate on ground flat enough to sit on. The platform blob
  should handle it, but a village half-buried in a hillside is the failure mode.
- How the painter feels in play: whether the raised rate keeps up with a player
  on an elytra, and whether a first arrival reads as a wave of ground changing
  or as having always been there.
- Whether the biome fogs are too strong at their borders. Rates fade but the
  fog swap itself is a hard cut, because Bedrock's fog stack has no crossfade.
- Whether the player clips read as offsets or as fights with vanilla's own
  poses. The amplitudes are conservative for exactly this reason, but they are
  tuned blind and the sneak and fall poses are the two most likely to need
  pulling back.
- Whether `/playanimation` behaves the same on every platform for emotes; it is
  the standard technique but this pack has not run it on console.
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
| Fog density, colour and shaft hardness | `RP/fogs/*.json` — `henyey_greenstein_g` is the beam-width dial |
| Star density and sky colour | `end_sky()` in `tools/gen_art.py` — coverage above ~5% reads as grain |
| Sky island height band and rate | `MIN_Y`, `MAX_Y`, `CHANCE`, `CELL` in `BP/scripts/world/skyIslands.js` |
| Underside growth per biome | `hanging` in `BIOMES`, rate in `UNDERSIDE_CHANCE` in `painter.js` |
| Village layout and residents | `BP/scripts/structures/endVillage.js` |
| Trades | `BP/trading/*.json` |
| Crop growth speed | `STAGE_TICKS` in `BP/scripts/content/bloomstalk.js` |
| Biome mix, terrain, flora, rosters | `BIOMES` in `BP/scripts/world/biomes.js` |
| Biome size and border wander | `BIOME_CELL`, `WARP_STRENGTH`, `WARP_PERIOD` in `biomes.js` |
| What the painter may overwrite | `NATURAL` in `BP/scripts/world/painter.js` |
| Painting radius and rate | `PAINT_RADIUS`, `PATCHES_PER_SCAN` in `painter.js` |
| Region spawn cap and rate | `NEARBY_CAP`, `SPAWN_CHANCE` in `BP/scripts/world/biomeLife.js` |
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
| Player clip amplitudes | `RP/animations/voidbound.player.animation.json` |
| When each player clip plays | `RP/animation_controllers/voidbound.player.animation_controllers.json` |
| Mob action weight per creature | `MOBS` scale in `tools/gen_mob_actions.py` |
| Which events fire which emote | `BP/scripts/content/emotes.js` |
| Ambient particle rates and edge detection | `BP/scripts/world/ambience.js` |

## Layout

```
BP/                     behavior pack
  blocks/ items/        62 blocks, 28 items (4 of them armour, 5 tools)
  trading/              three villager professions
  entities/ spawn_rules/ loot_tables/
  features/ feature_rules/   ore, shattered stone and flora generation
  recipes/
  scripts/
    lib/                rng, vectors, blueprint placement
    structures/         the six blueprints
    world/              biomes, painter, siting, generation, atmosphere,
                        discovery, flight control, persistence
    content/            loot, compass, bosses, waystones, saplings, armour set
RP/                     resource pack
  lighting/ atmospherics/ color_grading/ pbr/ local_lighting/ fogs/
  biomes/               client biome binding the above to the End
  textures/             generated art + texture sets
  models/ animations/ animation_controllers/ entity/
  render_controllers/ attachables/
tools/                  art generation and the four checks
  artlib.py             dependency-free imaging: noise, blending, PNG io
  mobkit.py             model primitives - bones, cubes, muzzles, limbs, wings
  mobpaint.py           paints a texture *from* a model's own UV allocation
  render_mob.py         software rasteriser: see a model before the game does
  mobs/<name>.py        one builder and one painter per mob
  gen_entities.py       the roster table -> behaviour, spawn, loot, client, lang
  gen_mob_anims.py      clips generated from each rig's own bone names
  gen_trees.py          a tree species -> textures, blocks, atlas, script table
  sheet.py roster_sheet.py   labelled progress sheets of the models
```

### Why the models are generated

Six of the shipped mobs had a structural fault that only turned up when it was
possible to *look* at them: the End King's greatsword ran sixty blocks through
the floor, the whale's gold bands floated a block off a hull that tapered away
under them, the Corrupted Enderman's ten tatter chains all stacked in one place
on its shoulder, and three mobs stood six to eight pixels below the ground they
were on. None of that is visible in a JSON diff.

So `tools/render_mob.py` is a software rasteriser - bone tree, pivots, cube
rotations, inflate, mirroring, per-face UVs, a z-buffer, one key light and
emissive read from the MER map's green channel. It renders any model in the
pack to a PNG, with `--turnaround` for several angles and `--only` to isolate a
limb. Every model here was iterated against it, and every fault above was found
that way rather than in game.

## Two names, and why they differ

The pack has been renamed several times. Its *identifiers* never are: blocks,
items, entities and animations have all been `voidbound:` /
`animation.voidbound.` since the first version and will stay that way. Renaming
a block id breaks every world that already has one placed, so the display name
is the only thing allowed to move.

Renaming is **not** how a duplicate import is avoided, which took two rounds of
"duplicate pack detected" to learn. Bedrock identifies a pack by the UUIDs in
its manifests and replaces an installed one only when the incoming version is
strictly higher; at an equal version it cannot tell an update from a second
copy, so it asks, and whichever the player keeps, half the work is missing.
`build_addon.sh` therefore raises the patch number on every build, and the
UUIDs stay put - re-minting them to escape a prompt orphans the pack in every
world already using it. `tools/rename_pack.py` re-mints only when the pack is
genuinely being reissued under a new identity, as here.

Overriding `RP/entity/player.entity.json` has a cost worth stating plainly: the
copy here is Mojang's file from the 26.4 samples, so if a later drop adds a clip
to the player, this pack will hold the older version until it is refreshed.
`python3 tools/fetch_vanilla_refs.py` documents where the source lives.

## Compatibility

Targets `min_engine_version` `[1, 26, 40]`, so it loads on 26.4 and its
hotfixes including 26.44. Uses `@minecraft/server` 2.9.0, the stable script API
shipped with that drop. The `pbr` capability requires 1.21.120 or newer, which
26.4 comfortably clears.

Achievements stay enabled — nothing here turns on cheats.
