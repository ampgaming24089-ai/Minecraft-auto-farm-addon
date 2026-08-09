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
  dimension: a close, heavy, violet-grey fog band (fog starts at 12 blocks,
  fully opaque by 55) plus a volumetric density layer, so the Veil always
  reads as thick and close even in open areas.
- **`RP/biomes_client.json`** — ties that fog profile to the
  `hollowveil:hollow_veil` biome and gives its water a murky violet tint
  distinct from Overworld water.
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
