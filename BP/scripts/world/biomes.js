// Deterministic value noise + biome layout for the Hollow Veil.
//
// A script-registered dimension has no world generator, so there is no real
// Bedrock biome under any of this - the "biome" a position belongs to is
// decided here and then drives terrain palette, feature scatter, mob
// spawning and fog. Doing it with noise rather than the old fixed quadrants
// means biome borders are irregular and every world lays out differently,
// so exploring actually turns up something new instead of the same four
// pie slices in the same four places.

export const WORLD_RADIUS = 100000; // 90 -> 512 -> 1024 -> 10000 -> 50000 -> 100000
// 100,000 blocks in every direction: a 200,000-block-wide disc, comfortably
// inside Bedrock's +/-30,000,000 world limit. Nothing about this number is
// stored anywhere - see world/terrain.js for why the generator holds no
// per-sector state at all - so widening the world costs no memory and no
// dynamic-property budget. It only changes where the rim is.
export const SECTOR = 32; // terrain is built one sector at a time, near players
export const SURFACE_Y = 64;
export const BEDROCK_Y = SURFACE_Y - 12;
export const STONE_TOP_Y = SURFACE_Y - 2;

/** 32-bit integer hash. Same input always gives the same output, across
 * sessions and devices - no Math.random() anywhere in world layout. */
function hash2(x, z, seed) {
  // Math.imul throughout: plain `*` on large constants overflows JS's
  // 53-bit safe integer range and silently loses the low bits, which
  // collapses the hash to a near-constant and makes every noise lookup
  // return roughly the same value.
  let h = Math.imul(x | 0, 374761393) ^ Math.imul(z | 0, 668265263) ^ Math.imul(seed | 0, 1274126177);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967295;
}

function smooth(t) {
  return t * t * (3 - 2 * t);
}

/** Smoothed 2D value noise in [0,1] at the given cell size. */
export function noise2(x, z, cell, seed) {
  const fx = x / cell;
  const fz = z / cell;
  const x0 = Math.floor(fx);
  const z0 = Math.floor(fz);
  const tx = smooth(fx - x0);
  const tz = smooth(fz - z0);
  const n00 = hash2(x0, z0, seed);
  const n10 = hash2(x0 + 1, z0, seed);
  const n01 = hash2(x0, z0 + 1, seed);
  const n11 = hash2(x0 + 1, z0 + 1, seed);
  return (n00 * (1 - tx) + n10 * tx) * (1 - tz) + (n01 * (1 - tx) + n11 * tx) * tz;
}

/** Two octaves, so borders wobble at both large and small scale. */
function fbm(x, z, cell, seed) {
  return noise2(x, z, cell, seed) * 0.7 + noise2(x, z, cell / 3, seed + 991) * 0.3;
}

// --- the four biomes + the hub ------------------------------------------
// Each is a full recipe: what the ground is made of, what grows on it, and
// which mobs belong there. `weight` biases how much of the map it claims.
export const BIOMES = {
  hub: {
    id: "hub",
    name: "The Misty Reach",
    surface: "hollowveil:bonestone",
    filler: "minecraft:deepslate",
    fog: [0.28, 0.26, 0.34],
    mobs: [],
  },
  moors: {
    id: "moors",
    name: "The Grave Moors",
    surface: "minecraft:podzol",
    filler: "minecraft:deepslate",
    accents: ["minecraft:coarse_dirt", "hollowveil:bonestone"],
    fog: [0.13, 0.13, 0.17],
    mobs: ["hollowveil:wraith", "hollowveil:banshee", "hollowveil:shade", "hollowveil:poltergeist"],
    // the graveyard identity of the dimension lives here
    graves: true,
    deadTrees: true,
  },
  ashlands: {
    id: "ashlands",
    name: "The Ashlands",
    surface: "minecraft:blackstone",
    filler: "minecraft:basalt",
    accents: ["minecraft:magma_block", "minecraft:polished_blackstone"],
    fog: [0.22, 0.09, 0.06],
    mobs: ["hollowveil:hellhound", "hollowveil:imp", "hollowveil:ashen_whelp", "hollowveil:bastion_sentinel"],
    emberVents: true,
  },
  marsh: {
    id: "marsh",
    name: "The Boneyard Marsh",
    surface: "hollowveil:veil_mud",
    filler: "minecraft:deepslate",
    accents: ["minecraft:mud", "minecraft:moss_block"],
    fog: [0.12, 0.18, 0.14],
    mobs: ["hollowveil:bonehide_elk", "hollowveil:glimmershroom_toad", "hollowveil:marrow_crawler", "hollowveil:ashwing_bat"],
    pools: true,
    shrooms: true,
  },
  ruins: {
    id: "ruins",
    name: "The Sunken Ruins",
    surface: "minecraft:deepslate_tiles",
    filler: "minecraft:deepslate",
    accents: ["minecraft:cracked_deepslate_tiles", "hollowveil:sunken_bricks"],
    fog: [0.10, 0.14, 0.20],
    mobs: ["hollowveil:city_wraithguard", "hollowveil:ashwing_bat", "hollowveil:shade", "hollowveil:fallen_knight"],
    rubble: true,
  },
};

const HUB_RADIUS = 40;

/** World layout seed. Fixed per pack (not per world) so a given coordinate
 * is always the same biome for everyone playing this addon - which keeps
 * the docs/maps honest - while still being irregular rather than gridded. */
const LAYOUT_SEED = 20260810;

// Territory size. Tuned by sampling the real distribution across the whole
// 50,000-block radius rather than guessed - see tools/biome_stats.js.
const BIOME_CELL = 1500;
const BIOME_WARP_CELL = 700;
const BIOME_WARP = 850;

/** Which biome owns this position. */
export function biomeAt(x, z) {
  const dist = Math.hypot(x, z);
  if (dist < HUB_RADIUS) return BIOMES.hub;
  // A "which biome" field plus a warp field, so the four territories form
  // large irregular blobs instead of quadrants, and interleave at the edges.
  // Biome scale grows with the world. At the old 190-block cell a 100,000
  // wide map would be roughly 500 territories across - a patchwork you cross
  // three of on a short walk. At ~900 the four territories read as continents
  // you travel through for a thousand blocks at a time, which is the point of
  // making the world this big.
  const wx = x + (noise2(x, z, BIOME_WARP_CELL, LAYOUT_SEED + 7) - 0.5) * BIOME_WARP;
  const wz = z + (noise2(x, z, BIOME_WARP_CELL, LAYOUT_SEED + 13) - 0.5) * BIOME_WARP;
  // Two independent fields rather than one bucketed field. fbm's output is
  // bell-shaped around 0.5, so slicing a single field into four equal
  // ranges hands the two middle slices most of the map (measured: 50%/37%
  // vs 4%). Splitting on two fields gives four genuinely comparable
  // territories, and the thresholds below are tuned against the measured
  // distribution - MOORS_CUT is deliberately generous because the
  // graveyard moors are the dimension's signature look.
  const a = fbm(wx, wz, BIOME_CELL, LAYOUT_SEED);
  const b = fbm(wx + 4096, wz - 4096, BIOME_CELL * 0.79, LAYOUT_SEED + 77);
  const MOORS_CUT = 0.54;
  const SPLIT = 0.5;
  if (a < MOORS_CUT) return b < SPLIT ? BIOMES.moors : BIOMES.ashlands;
  return b < SPLIT ? BIOMES.marsh : BIOMES.ruins;
}

/** Ground height at a position. Gently rolling, flattened toward the hub so
 * the arrival area and the village are always buildable, and falling away
 * to a cliff edge at the world rim. */
export function heightAt(x, z) {
  const dist = Math.hypot(x, z);
  const rolling = (fbm(x, z, 70, LAYOUT_SEED + 31) - 0.5) * 11;
  const hubFlatten = Math.min(1, Math.max(0, (dist - 18) / 34));
  let y = SURFACE_Y + rolling * hubFlatten;
  const edge = WORLD_RADIUS - dist;
  if (edge < 48) y -= (48 - edge) * 0.6; // rim drops into the void
  return Math.round(y);
}

export function isWithinWorld(pos) {
  return Math.hypot(pos.x, pos.z) < WORLD_RADIUS - 2;
}

/** Stable per-position randomness for feature scatter. */
export function featureRoll(x, z, salt) {
  return hash2(x, z, LAYOUT_SEED + salt);
}
