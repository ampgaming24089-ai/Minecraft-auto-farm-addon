# Aurora

Three resource packs for **Minecraft Bedrock 26.40** (`1.26.40`) that together
restyle how the game looks, how its menus feel, and how everything in it moves:

| Pack | What it changes |
| --- | --- |
| **Aurora Visuals** | The shader layer — sun and moon, sky scattering, water, colour grading, soft shadows |
| **Aurora Interface** | One dark-slate-and-cyan style shared by every screen |
| **Aurora Animations** | Reanimated player and mobs — 83 animation overrides |

They are independent. Enable one, two, or all three.

## Install

Download or build `dist/Aurora.mcaddon` and open it — Minecraft imports all
three packs at once. Then enable them per world under
**Settings → Global Resources**, or per world in **Edit World → Resource Packs**.

To install just one pack, use the matching `dist/*.mcpack`.

> **Aurora Visuals needs Vibrant Visuals turned on.**
> Set **Settings → Video → Graphics Mode** to *Vibrant Visuals*. That mode is what
> runs Bedrock's deferred renderer; with it off, the lighting and water files in
> this pack are ignored and only the other two packs do anything.

## Aurora Visuals

Bedrock shaders are not GLSL. Since the Vibrant Visuals renderer shipped, the
look of the world is driven by JSON that the engine compiles into its deferred
pipeline, and a resource pack changes the look by replacing those files.

Aurora Visuals replaces **all 47 of them** — so every biome is restyled, not
just the default — and adds a shadow-settings file that vanilla does not ship:

- **Lighting** (15 files) — noon runs brighter than vanilla (130 vs 100 lux) and
  the falloff into evening is stretched between 0.18 and 0.29 of the day cycle,
  which is what produces the long golden hour. Moonlight is raised from 0.4 to
  0.9 so nights stay readable and cast real directional shadows. Ambient light
  is kept low and tinted by time of day — blue at night, warm at dusk — so
  shadows have colour instead of going flat grey.
- **Atmospherics** (17 files) — deeper Rayleigh scattering for a richer blue
  zenith, and forward Mie scattering more than doubled (1.6 vs vanilla's 0.75)
  but only inside the golden hours, so a low sun blooms without washing out
  midday. The Nether, the End and each Nether biome keep their own fixed skies.
- **Colour grading** (14 files) — a filmic pass with `hable` tone mapping: cool
  desaturated shadows against warm highlights, mild contrast, per-biome
  temperature from 5200K in the badlands to 7900K over ice spikes.
- **Water** — waves and caustics enabled, with chlorophyll and CDOM
  concentrations set so water reads as deep teal and darkens with depth.
- **Shadows** — `soft_shadows` at texel size 16.

Blocks are left alone on purpose: vanilla already ships 1206 PBR texture sets
with per-pixel metalness/emissive/roughness maps, so overriding them with flat
values would lose detail rather than add it.

### Tuning it

Everything is generated from one file, `tools/gen_visuals.py`, which holds the
master day/night curves at the top and a per-biome table of tints and multipliers
below. Change a number, re-run it, rebuild:

```bash
python3 tools/gen_visuals.py && ./build.sh
```

To get a punchier, higher-contrast image, change the grading `operator` default
from `hable` to `aces`.

## Aurora Interface

Bedrock draws nearly every screen from one small shared pool of textures. Aurora
replaces 61 of them, which is why the inventory, chests, crafting, furnaces,
tooltips, the pause menu and settings all change together.

That is also deliberate restraint. JSON UI is unversioned and breaks when Mojang
edits vanilla layouts, so this pack ships **no copied screen layouts** — only
textures plus a 41-key colour override in `ui/_global_variables.json`. Since
vanilla resolves its labels through those variables (the inventory title is
`$title_text_color`, not a hardcoded colour), overriding them recolours text
everywhere at once. Those flips are load-bearing: vanilla's "light" button text
is dark grey because vanilla buttons are pale, and Aurora's are dark slate.

Textures are drawn at 4x resolution wherever a texture declares a `base_size`,
and at native size where it does not. All detail is kept inside the fixed
nine-slice border so that stretched panels never smear.

Palette: `#0A0C11` wells, `#12151D` panels, `#1A1F2B` buttons, `#4DE3D0` accent.
Edit `tools/gen_ui_textures.py` and re-run to change it.

## Aurora Animations

Bedrock overrides animations **by identifier, not by file path**, and the
override is absolute for that one identifier. So this pack defines only the 83
animations it wants to change; everything else stays vanilla, and no Mojang
files are copied.

**Player** — arm and leg swings widen when sprinting, arms swing slightly across
the body, and the torso leans and bounces with each footfall (all scaled by
`query.modified_move_speed`, so nothing moves while standing still). Attacks get
a heavier windup, a body twist, a forward lunge and counter-swing on the off
arm. Sneaking sits lower, the swim kick is stronger, and gliding finally uses a
real swept-back wingsuit pose instead of running in mid-air.

**Mobs** — around 60 identities, either individually or through the shared bases
they inherit:

- *Shared bases* — `animation.humanoid.move` gains a torso sway, and
  `animation.quadruped.walk` gains diagonal leg phasing plus a body bounce, so
  every humanoid and every farm animal walks better.
- *Undead* — zombies reach with an uneven, drifting shamble; skeletons hold a
  tighter, rattling aim; wither skeletons are stiffer and wider; drowned sway.
- *Hostiles* — spiders get a proper alternating-tetrapod gait, creepers a subtle
  waddle, blazes counter-rotate their rods at three different speeds, ghasts
  ripple their tentacles in a travelling wave, phantoms and vexes and bats beat
  their wings with delayed wingtips, silverfish and endermites ripple
  segment-by-segment, wardens lumber, creakings sway when idle.
- *Passives* — cats and ocelots walk and sprint differently, wolves have a
  wagging tail, rabbits hop rather than walk, bees and allays hover with fast
  wingbeats, axolotls and dolphins and fish undulate from body to tail, camels
  and sniffers and armadillos each get their own gait, horses (and donkeys,
  mules, skeleton and zombie horses) share a rebuilt canter.

Mobs whose walk comes from a shared base — zombies and skeletons both use
`animation.humanoid.move` — are differentiated through the animations they *do*
own, such as their attack poses.

## Development

```bash
python3 tools/gen_visuals.py        # shader JSON
python3 tools/gen_ui_textures.py    # UI textures  (needs Pillow)
python3 tools/gen_pack_icons.py     # pack icons   (needs Pillow)
python3 tools/validate.py           # checks
./build.sh                          # dist/Aurora.mcaddon + per-pack .mcpack
```

### Validation

`tools/validate.py` parses every shipped file as strict JSON, checks manifest
UUIDs are unique and engine versions are high enough, and range-checks the
Vibrant Visuals settings against the documented limits.

Given a vanilla checkout it also catches the two ways an override fails
silently:

- **Dead overrides** — an animation identifier, UI texture, or UI variable that
  vanilla does not have, which would simply never apply.
- **Dropped bones** — a bone the vanilla animation moved but ours does not.
  Because overriding is absolute, that motion would vanish with no error. This
  check caught three real cases during development: strider bristles, camel ears
  and the axolotl's head.

```bash
git clone --depth 1 https://github.com/Mojang/bedrock-samples.git
BEDROCK_SAMPLES=./bedrock-samples python3 tools/validate.py
```

## Compatibility

- Built and validated against vanilla `1.26.40.5`.
- `min_engine_version` is `1.21.120`, the first version with Vibrant Visuals
  resource pack support, so the packs also load on releases between that and
  26.40.
- Other packs that replace the same `textures/ui/` files or the same animation
  identifiers will conflict; whichever sits higher in the pack list wins.
- No behaviour pack, no scripts, and no gameplay changes — these are
  client-side visuals only, so they are safe on servers and do not affect
  achievements.
