/**
 * Biomes for a dimension that only has one.
 *
 * Bedrock gives the End exactly one biome and no way for an add-on to add
 * another. Every End pack that appears to have biomes is doing what this does:
 * dividing the dimension into regions in script, then changing everything a
 * player can actually perceive - the ground under them, the fog, the light,
 * the particles, what spawns - so the region reads as a place. The engine
 * still thinks it is all `minecraft:the_end`. Nobody flying over it does.
 *
 * Assignment is a pure function of the world seed and position, so it is the
 * same for every player on a seed, survives restarts, needs no storage, and
 * can be answered for somewhere nobody has been - which is what lets the
 * compass and the waystone menu talk about places that do not exist yet.
 *
 * The one thing a grid of cells gets wrong is *shape*: square biomes with
 * ruler-straight borders look exactly as generated as they are. So the lookup
 * warps its own input first, by an amount that itself comes from smooth noise.
 * The cells stay square; the borders between them stop being.
 */

import { hash } from "../lib/rng.js";
import { worldSeedHash } from "./sites.js";

/**
 * Biome cell pitch in blocks.
 *
 * Much bigger than a structure cell, on purpose. At 384 the map came out as a
 * busy patchwork - technically seven biomes, but nowhere you could stay. A
 * region has to be somewhere you fly across, notice the light change, and
 * still be in a minute later, which is what makes leaving it mean something.
 */
export const BIOME_CELL = 640;

/** Inside this radius the End stays vanilla - the island, pillars, gateway. */
const INNER_CLEARANCE = 900;

/** How far the border can wander from the true cell edge, in blocks. */
const WARP_STRENGTH = 168;

/** Period of the warp field. Long, so borders curve rather than wobble. */
const WARP_PERIOD = 352;

/**
 * The biome table.
 *
 * `weight` is relative frequency. `surface` is what the painter lays down and
 * `filler` what it puts underneath; `flora` is scattered on top by weight.
 * `hanging` is what grows on the underside of that biome's islands, which is
 * what stops an island edge simply stopping. `fog` and `particle` are
 * identifiers in the resource pack, `particleLift`
 * is how far above the player its emitters start - the difference between
 * weather and a ground effect, since frost has to fall from somewhere and
 * embers have to climb out of something. `mobs` is the roster the region-gated
 * spawner draws from, and `colour` is the section sign code the entry
 * announcement is drawn in.
 */
export const BIOMES = {
  barrens: {
    id: "barrens",
    name: "Voidfall Barrens",
    colour: "§7",
    weight: 26,
    // The default. Nothing is painted here - it is the End you already know,
    // and it is what makes the other six feel like somewhere else.
    surface: undefined,
    filler: undefined,
    flora: [],
    fog: "voidbound:fog_end_open",
    particle: undefined,
    mobs: ["voidbound:lumen_wisp", "voidbound:rift_stalker", "voidbound:crystal_crawler"],
  },
  glowspore: {
    id: "glowspore",
    name: "Glowspore Basin",
    colour: "§d",
    weight: 15,
    surface: "voidbound:glowspore_soil",
    filler: "voidbound:glowspore_soil",
    flora: [
      { id: "voidbound:sporelight_fungus", weight: 8 },
      { id: "voidbound:pale_shroom", weight: 3 },
      { id: "voidbound:sporelight_cap", weight: 1, pillar: 3 },
    ],
    floraChance: 0.16,
    hanging: "voidbound:spore_tendril",
    fog: "voidbound:fog_glowspore",
    particle: "voidbound:spore_drift",
    particleLift: -1,
    particleChance: 0.9,
    mobs: ["voidbound:void_moth", "voidbound:voidling", "voidbound:chorus_hopper"],
  },
  bonespire: {
    id: "bonespire",
    name: "Bonespire Reach",
    colour: "§f",
    weight: 13,
    surface: "voidbound:bonespire_stone",
    filler: "voidbound:bonespire_stone",
    flora: [
      { id: "voidbound:frost_bloom", weight: 6 },
      { id: "voidbound:bonespire_stone", weight: 2, pillar: 6 },
    ],
    floraChance: 0.10,
    hanging: "voidbound:frost_icicle",
    fog: "voidbound:fog_bonespire",
    particle: "voidbound:frost_fall",
    particleLift: 9,
    particleChance: 0.75,
    mobs: ["voidbound:shard_wraith", "voidbound:glimmerfin", "voidbound:echo_sentinel"],
  },
  crystalline: {
    id: "crystalline",
    name: "Crystalline Expanse",
    colour: "§5",
    weight: 12,
    surface: "voidbound:crystalline_end_stone",
    filler: "voidbound:crystalline_end_stone",
    flora: [
      { id: "voidbound:echo_cluster", weight: 7 },
      { id: "voidbound:void_crystal_block", weight: 2, pillar: 4 },
      { id: "voidbound:voidbloom", weight: 3 },
    ],
    floraChance: 0.13,
    hanging: "voidbound:crystal_dripstone",
    fog: "voidbound:fog_crystalline",
    particle: "voidbound:crystal_glint",
    particleLift: 0,
    particleChance: 0.7,
    mobs: ["voidbound:crystal_crawler", "voidbound:shard_wraith", "voidbound:lumen_wisp"],
  },
  verdant: {
    id: "verdant",
    name: "Verdant Canopy",
    colour: "§a",
    weight: 12,
    surface: "voidbound:verdant_end_stone",
    filler: "voidbound:mossy_end_stone",
    flora: [
      { id: "voidbound:ender_bush", weight: 6 },
      { id: "voidbound:pale_shroom", weight: 4 },
      { id: "voidbound:lumen_bulb", weight: 3 },
      { id: "voidbound:ender_sapling", weight: 2 },
    ],
    floraChance: 0.18,
    hanging: "voidbound:ender_vines",
    fog: "voidbound:fog_luminous_grove",
    particle: "voidbound:grove_spores",
    particleLift: 1,
    particleChance: 0.8,
    mobs: ["voidbound:chorus_hopper", "voidbound:glimmerfin", "voidbound:ender_beetle",
           "voidbound:endstone_golem"],
  },
  ashen: {
    id: "ashen",
    name: "Ashen Wastes",
    colour: "§6",
    weight: 11,
    surface: "voidbound:ashen_end_stone",
    filler: "voidbound:ashen_end_stone",
    flora: [
      { id: "voidbound:ember_vent", weight: 3 },
      { id: "voidbound:shattered_end_stone", weight: 4, pillar: 2 },
    ],
    floraChance: 0.07,
    hanging: "voidbound:ash_stalactite",
    fog: "voidbound:fog_ashen",
    particle: "voidbound:ember_rise",
    particleLift: -2,
    particleChance: 0.85,
    mobs: ["voidbound:rift_stalker", "voidbound:echo_sentinel", "voidbound:crystal_crawler"],
  },
  aurora: {
    id: "aurora",
    name: "Aurora Shelf",
    colour: "§b",
    weight: 11,
    surface: "voidbound:aurora_stone",
    filler: "voidbound:aurora_stone",
    flora: [
      { id: "voidbound:voidbloom", weight: 5 },
      { id: "voidbound:frost_bloom", weight: 3 },
      { id: "voidbound:lumen_bulb", weight: 2 },
    ],
    floraChance: 0.09,
    hanging: "voidbound:aurora_veil",
    fog: "voidbound:fog_aurora",
    particle: "voidbound:aurora_shimmer",
    particleLift: 22,
    particleChance: 0.6,
    mobs: ["voidbound:astral_whale", "voidbound:lumen_wisp", "voidbound:void_moth",
           "voidbound:glimmerfin"],
  },
};

/** Weighted pick order, built once. */
const ORDER = Object.values(BIOMES);
const TOTAL_WEIGHT = ORDER.reduce((sum, biome) => sum + biome.weight, 0);

/** Smooth value noise in [0,1] from the integer hash, bilinearly interpolated. */
function valueNoise(x, z, salt) {
  const gx = Math.floor(x / WARP_PERIOD);
  const gz = Math.floor(z / WARP_PERIOD);
  const fx = x / WARP_PERIOD - gx;
  const fz = z / WARP_PERIOD - gz;

  // Smoothstep, so the field has no visible creases at cell boundaries.
  const sx = fx * fx * (3 - 2 * fx);
  const sz = fz * fz * (3 - 2 * fz);

  const corner = (ix, iz) => (hash(worldSeedHash(), salt, ix, iz) >>> 8) / 0xffffff;
  const top = corner(gx, gz) * (1 - sx) + corner(gx + 1, gz) * sx;
  const bottom = corner(gx, gz + 1) * (1 - sx) + corner(gx + 1, gz + 1) * sx;
  return top * (1 - sz) + bottom * sz;
}

/** The biome id for a cell, before any warping. Pure in (seed, cell). */
function biomeForCell(cellX, cellZ) {
  const roll = ((hash(worldSeedHash(), 0x1f35d, cellX, cellZ) >>> 8) / 0xffffff) * TOTAL_WEIGHT;
  let running = 0;
  for (const biome of ORDER) {
    running += biome.weight;
    if (roll < running) return biome;
  }
  return ORDER[0];
}

/**
 * The biome at a world position.
 *
 * Pure function of the world seed and (x, z) - no state, no storage, and
 * answerable for anywhere, including chunks that have never been loaded.
 */
export function biomeAt(x, z) {
  if (Math.hypot(x, z) < INNER_CLEARANCE) return BIOMES.barrens;

  // Warp the sample point before it is quantised. Two offset fields so the
  // x and z displacement are independent, or borders shear along a diagonal.
  const wx = x + (valueNoise(x, z, 0x51ab) - 0.5) * 2 * WARP_STRENGTH;
  const wz = z + (valueNoise(x, z, 0x7c03) - 0.5) * 2 * WARP_STRENGTH;

  return biomeForCell(Math.floor(wx / BIOME_CELL), Math.floor(wz / BIOME_CELL));
}

/**
 * How far the position is from the nearest biome border, roughly, in blocks.
 *
 * Sampled rather than solved: the warp makes an exact answer expensive and an
 * approximate one is all any caller needs. Used to fade particle rates in near
 * a border so a biome does not switch on like a light.
 */
export function borderProximity(x, z, reach = 48) {
  const here = biomeAt(x, z).id;
  for (const [dx, dz] of [[reach, 0], [-reach, 0], [0, reach], [0, -reach]]) {
    if (biomeAt(x + dx, z + dz).id !== here) return 0;
  }
  return 1;
}
