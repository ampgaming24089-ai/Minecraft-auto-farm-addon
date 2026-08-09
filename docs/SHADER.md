# "Custom shader for the world" — what this actually is on Bedrock

Bedrock add-ons cannot ship an arbitrary pixel/vertex shader the way Java's
OptiFine/Iris packs do — the closest first-party equivalent is **Vibrant
Visuals** (PBR textures + a deferred renderer), and its JSON contract is
still one of the least stable parts of the platform. Rather than ship a
`atmospherics/*.json` file built on a schema I can't verify against a live
client, the Hollow Veil's look is built entirely on the parts of the
rendering pipeline that have been stable for years and will load correctly
today:

- **`RP/fogs/hollow_veil_fog.json`** — a dedicated fog profile for the
  dimension: a close, heavy, violet-grey fog band (fog starts at 10 blocks,
  fully opaque by 55), so the Veil always reads as thick and close even in
  open areas. Schema verified against Mojang's own vanilla biome fog files
  (`basalt_deltas_fog_setting.json` etc. in `bedrock-samples`).
- **`RP/biomes_client.json`** — ties that fog profile to whatever biome the
  dimension actually reports. Because Hollow Veil is a **script-registered
  custom dimension** (see `docs/DIMENSION.md`) it has no biome of its own
  to key off; this currently guesses `minecraft:the_void`, the standard
  Bedrock void biome, since that's the most likely default for an empty
  custom dimension. If that guess is wrong for a given game version, the
  fog file itself still loads fine (valid schema either way) — the only
  effect is the color grading not visually kicking in, not an error.
- **Particle ambience** — `hollow_king_pulse_particle`, `soul_wisp_particle`,
  `banshee_scream_particle`, `ember_particle`, `shade_teleport_particle` and
  `portal_particle` (`RP/particles/`, sprites in
  `RP/textures/particle/`) carry the moment-to-moment atmosphere: drifting
  wisp light, screen-filling scream pulses, embers around Malacoda.
- **Palette discipline** — every custom block/entity texture in the pack
  pulls from the same desaturated grey-violet-bone palette (see
  `tools/gen_assets.py`'s `PAL` table), with Malacoda's Cinder Bastion the
  one deliberate break into saturated red/orange (see `docs/STORY.md`'s
  tone notes for why).

If you want to push further into full PBR/Vibrant Visuals materials later,
the palette and fog color values here are the source of truth to carry
over — add `_normal`/`_mer` texture variants per block/entity and an
`atmospherics/hollow_veil.json` once you can verify the current schema
in-game.
