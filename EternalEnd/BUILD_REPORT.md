# BUILD REPORT — Eternal End

All 20 mobs in `design/mobs.json` were built and checked. This report says what
was produced, what was verified and how, and where the implementation had to
choose the nearest Bedrock-native answer rather than the literal one.

## The roster

Every mob uses the exact identifier from `specs/mobs.json`, under the
`eternal_end:` namespace, with its own geometry, its own texture, its own
client entity and its own behaviour entity. No identifier is reused and no
texture is shared between two mobs.

| # | Identifier | Category | Geometry | Texture | Spawn rules | Loot |
| --- | --- | --- | --- | --- | --- | --- |
| 01 | `eternal_end:void_dragon` | boss | 256² | 256² | seated at Void Spires | Void Scale, Dragon's Breath, Void Heart |
| 02 | `eternal_end:ender_overlord` | boss | 256² | 256² | seated at Rift Anchors | Void Scale, Ender Pearls, Overlord Eye |
| 03 | `eternal_end:end_king` | boss | 256² | 256² | seated at Shattered Sanctums | Void Scale, Gold, Crown Shard |
| 04 | `eternal_end:void_stalker` | hostile | 128² | 128² | yes | Void Scale, Ender Pearl |
| 05 | `eternal_end:endermite_hive` | hostile | 128² | 128² | yes | Ender Pearls, Void Scale |
| 06 | `eternal_end:purpur_golem` | hostile | 128² | 128² | yes | Purpur, Void Scale |
| 07 | `eternal_end:shulker_beast` | hostile | 128² | 128² | yes | Shulker Shell, Void Scale |
| 08 | `eternal_end:void_wisp` | hostile | 64² | 64² | yes | Void Ember |
| 09 | `eternal_end:end_spider` | hostile | 128² | 128² | yes | String, Void Scale |
| 10 | `eternal_end:corrupted_enderman` | hostile | 128² | 128² | yes | Ender Pearls, Void Scale |
| 11 | `eternal_end:chorus_fiend` | hostile | 128² | 128² | yes | Chorus Fruit, Void Scale |
| 12 | `eternal_end:void_slime` | hostile | 64² | 64² | yes | Slimeball, Void Ember |
| 13 | `eternal_end:teleporter` | hostile | 128² | 128² | yes | Ender Pearls, Void Ember |
| 14 | `eternal_end:end_crab` | hostile | 128² | 128² | yes | Void Chitin Plate, Void Scale |
| 15 | `eternal_end:obsidian_beast` | hostile | 256² | 256² | yes | Obsidian, Void Scale |
| 16 | `eternal_end:ender_deer` | passive/tame | 128² | 128² | yes | Raw Ender Venison |
| 17 | `eternal_end:chorus_cow` | passive/tame | 128² | 128² | yes | Raw Chorus Beef, Leather |
| 18 | `eternal_end:void_hog` | passive/tame | 128² | 128² | yes | Raw Void Pork |
| 19 | `eternal_end:sky_ray` | passive/tame | 256² | 256² | yes | Raw Ray Meat |
| 20 | `eternal_end:ender_bird` | passive/tame | 128² | 128² | yes | Raw Ender Poultry, Feather |

Ender Ghost was **not** added, per the correction in `README_FOR_CLAUDE.md`.
The roster is 3 bosses + 12 hostile + 5 passive/tameable = 20.

## What each mob got

- **Geometry** — hand-designed bone and cube layout per mob in
  `tools/mobgen/roster.py`, emitted as a `1.12.0` geometry file. Blocky,
  axis-aligned, Minecraft-native; no smoothed or generic 3D shapes.
- **Texture** — a final UV texture painted against the packed atlas, not the
  design PNG. The reference sheets were sampled for palette only, exactly as
  the implementation rules require. Nearest-neighbour pixel art throughout; no
  blurring, no smoothing, no placeholder.
- **Client entity** — materials, texture and geometry bindings, five animation
  slots and a spawn egg coloured from the mob's own palette.
- **Behaviour entity** — stats, locomotion, target acquisition and attack AI.
- **Animations** — 80 looping clips (idle, move, alert, death) and 40 one-shots
  (attack, hurt), plus a shared state controller. Attack and hurt are played
  from `mobActions.js` through `/playanimation`, matching how the pack's
  original mobs work.
- **Loot table** — every entry resolves to an item this pack or vanilla
  defines.
- **Spawn rules** — all 17 non-boss mobs. The bosses are seated at structures
  instead, which is what makes finding one mean something.

## Supporting content added for the roster

- **4 projectiles** — `void_breath`, `void_lance`, `royal_bolt`, `wisp_flame`,
  each a real entity with its own texture, fired through `minecraft:shooter`.
- **5 raw meats and 5 cooked**, with furnace, smoker and campfire recipes.
- **Lumen Feed**, the taming and breeding item, craftable from Chorus Fruit,
  Lumen Berries and a Bloom Pod.
- **6 boss and hostile drop materials** — Void Scale, Void Ember, Void Chitin
  Plate, Void Heart, Overlord Eye, Crown Shard.
- **Language strings** for every mob, spawn egg, projectile and item.

## Emissive treatment

Glow is carried in the alpha channel of each mob's texture: a texel at alpha
254 is emissive, 255 is not, and nothing is ever written at alpha 0. The client
entities use `entity_emissive_alpha`, so the violet crystals, glowing eyes and
lit cores light themselves with no second geometry layer, no second texture and
no render controller branch. The same mask is written out again as the emissive
channel of a MER map with a `texture_set.json` beside it, so the mobs also
light correctly under Vibrant Visuals.

## Verification

`tools/validate.py` resolves, across **both** packs:

- every geometry, texture, animation, animation controller and render
  controller a client entity names
- every bone an animation moves, against the geometry it is played on
- behaviour ↔ client entity pairing in both directions
- every loot table, trade table and spawn rule a behaviour entity names
- every item, block and entity identifier named by a loot table, recipe,
  tameable, breedable, ageable, tempt, shooter or summon component
- every component group an event adds or removes, against the groups declared
- every texture shortname an item or block asks for, in both atlases, and
  every path those atlases point at
- every identifier the behaviour scripts name in a string literal, and every
  animation they play
- manifest UUID uniqueness and the behaviour → resource dependency

Result: **no broken references.** 45 behaviour entities, 46 client entities, 40
geometries, 258 animation clips, 5 controllers, 45 items, 68 blocks, 327
textures.

The check was itself checked: renaming one bone in one animation makes it fail,
and restoring it makes it pass.

Beyond static checking:

- All 36 behaviour scripts import and evaluate against a stand-in
  `@minecraft/server`, and `main.js` starts every system without throwing.
- The sky-island and painter generators were run against a fake dimension.
  43 islands built spanning y=11 to y=240; region trees grew on the ground in
  both a painted region and the unpainted Barrens; a second pass over the same
  ground changed nothing.
- `tools/mobgen/preview.py` renders the assembled roster - bone transforms,
  z-buffer, real texture sampling - so every model was looked at rather than
  inferred from JSON. Several were reworked on the strength of it: the Void
  Dragon's wings, the End Spider's legs, the End Crab's claws.

## Limitations

Stated plainly, per rule 12.

1. **Nothing has been run in Minecraft itself.** Every check above is static
   analysis or simulation against a stand-in API. It cannot catch a component
   whose schema changed in a Bedrock version this environment has no copy of.
   The component sets are modelled on the ones already shipping in this pack
   and working in the author's world, which is the best available proxy.
2. **Mob armour is a damage multiplier.** Bedrock has no armour stat for mobs,
   so the Purpur Golem, End Crab and Obsidian Beast take a fraction of what
   they are hit for via `minecraft:damage_sensor`. Only `cause` and
   `damage_multiplier` are set - the two fields of that component that have
   been stable across versions.
3. **The Sky Ray is flown from script.** `minecraft:rideable` and
   `behavior.player_ride_tamed` seat the rider; `content/skyRay.js` turns their
   view direction into flight. On a runtime without `player.inputInfo` the
   mount still flies, just always forward rather than on the rider's throttle.
4. **Boss attacks are Bedrock-native, not bespoke.** Each boss has a unique
   projectile, a much larger scale, a boss bar and heavily raised stats, and
   the End King summons Corrupted Endermen. Multi-phase scripted fights of the
   kind `riftSovereign.js` and `voidTitan.js` implement for the original roster
   were not written for these three; they fight through the component system.
5. **The design sheets are palettes, not pixels.** Rule 6 forbids treating the
   reference PNGs as UV maps, so each mob's silhouette is a reading of its
   sheet, not a trace of it. The Chorus Cow's tan face flash, the End King's
   gold crown and cape, the Sky Ray's cyan spine, the Ender Deer's antlers -
   the identifying features are there, but a mob is a reinterpretation.
6. **Existing worlds fill in as you travel.** The stacked islands and the
   region trees are placed ahead of the player, not by the chunk generator, so
   they appear where you go rather than everywhere at once. Ground you have
   already fully explored and built on will not be rewritten - by design.
