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

// The shape of the world, top to bottom.
//
// The old profile was a 12-block-thick slab: bedrock at 52, surface at 64,
// and roughly five blocks of roll across the whole map. That is why it read
// as "all bedrock and not properly generated" - it was, functionally, a
// textured plane.
//
// Bedrock's engine will not generate a script-registered dimension for us.
// `registerCustomDimension` takes a type id and nothing else, and the
// data-driven `BP/dimensions/*.json` file only overrides the height limits of
// the three dimensions that already exist - the generator type there is not
// mutable. So the only way to get a world that feels generated is to generate
// one, and that is what the numbers below are for.
//
// The profile now has four parts:
//
//   BEDROCK_Y ........ a true floor at the bottom of the world
//   cave floor ....... a rolling underground landscape just above it
//   (open cavern) .... free: a script dimension starts as void, so the space
//                      between the cave floor and the underside of the crust
//                      costs nothing to "carve" - it is simply never filled
//   crust ............ the few metres of rock hanging under the surface
//   surface .......... mountains, valleys, coastlines
//
// That gives a surface world with 60+ blocks of relief AND a continuous cave
// system under all of it, for barely more block writes than the old slab.
export const BEDROCK_Y = 0;
export const SEA_LEVEL = 58;
export const SURFACE_Y = 64;      // nominal height; the hub is flattened to it
export const SURFACE_MIN = 34;
export const SURFACE_MAX = 132;
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
    blend: ["hollowveil:bonestone"],
    flora: [],
    floraDensity: 0,
    base: 0, swell: 0, relief: 0, mountains: 0, cave: "minecraft:deepslate",
    name: "The Misty Reach",
    surface: "hollowveil:bonestone",
    filler: "minecraft:deepslate",
    fog: [0.28, 0.26, 0.34],
    mobs: [],
  },
  moors: {
    id: "moors",
    blend: ["minecraft:coarse_dirt", "minecraft:rooted_dirt", "hollowveil:bonestone", "minecraft:gravel"],
    flora: ["dead_grove", "grave_weeds", "bone_pile", "grave_weeds", "dead_grove"],
    floraDensity: 0.55,
    base: 2, swell: 1.0, relief: 1.0, mountains: 0.15, cave: "minecraft:deepslate",
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
    blend: ["minecraft:basalt", "minecraft:polished_blackstone", "minecraft:magma_block", "minecraft:gravel"],
    flora: ["ash_spire", "tar_pit", "ash_spire", "bone_pile"],
    floraDensity: 0.5,
    base: 6, swell: 1.1, relief: 1.35, mountains: 1.0, cave: "minecraft:basalt",
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
    blend: ["minecraft:mud", "minecraft:moss_block", "minecraft:clay", "minecraft:muddy_mangrove_roots"],
    flora: ["fungus", "shroom_patch", "roots", "fungus", "shroom_patch", "bone_pile"],
    floraDensity: 0.7,
    base: -9, swell: 0.6, relief: 0.45, mountains: 0.0, cave: "hollowveil:veil_mud",
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
    blend: ["minecraft:cracked_deepslate_tiles", "hollowveil:sunken_bricks", "minecraft:deepslate_bricks", "minecraft:gravel"],
    flora: ["broken_column", "ruined_wall", "crystal", "broken_column", "bone_pile"],
    floraDensity: 0.5,
    base: 0, swell: 0.9, relief: 0.8, mountains: 0.45, cave: "minecraft:deepslate_tiles",
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

/** Ridged noise: the standard way to get mountain SPINES rather than blobs.
 * Folding value noise about its midpoint turns smooth hills into creases, and
 * squaring sharpens the crease into a ridge. */
function ridged(x, z, cell, seed) {
  const n = 1 - Math.abs(noise2(x, z, cell, seed) * 2 - 1);
  return n * n;
}

/**
 * Surface height.
 *
 * Four bands of noise, the way a real generator layers them:
 *
 *   continents  cell 900   the slow swell that decides sea from highland
 *   hills       cell 150   the shape you actually walk over
 *   detail      cell 40    the roughness that keeps slopes from looking milled
 *   ridges      cell 320   mountain spines, gated by a separate mask so ranges
 *                          occur in places rather than everywhere
 *
 * `biome` is passed in rather than looked up: the caller has already decided
 * it, and biomeAt is four noise lookups that would otherwise run twice per
 * column. Each biome scales the bands differently, so the marsh is genuinely
 * low and wet and the Ashlands are genuinely jagged, instead of every region
 * being the same terrain in a different colour.
 */
export function heightAt(x, z, biome) {
  const b = biome || biomeAt(x, z);
  const dist = Math.hypot(x, z);

  const continents = (fbm(x, z, 900, LAYOUT_SEED + 3) - 0.5) * 34;
  const hills = (fbm(x, z, 150, LAYOUT_SEED + 31) - 0.5) * 26;
  const detail = (noise2(x, z, 40, LAYOUT_SEED + 41) - 0.5) * 5;

  // Ranges only where the mask is high, so mountains are somewhere you travel
  // to rather than a uniform crumple over the whole map.
  const mask = Math.max(0, fbm(x, z, 640, LAYOUT_SEED + 57) - 0.5) / 0.5;
  const ridges = ridged(x, z, 320, LAYOUT_SEED + 71) * 52 * mask;

  let y = SURFACE_Y + (b.base ?? 0)
        + continents * (b.swell ?? 1)
        + hills * (b.relief ?? 1)
        + detail
        + ridges * (b.mountains ?? 0);

  // The hub has to stay buildable: the arrival point, the altars and Hollow
  // Hamlet all sit at SURFACE_Y and none of them want a mountain through them.
  const hubFlatten = Math.min(1, Math.max(0, (dist - 24) / 90));
  y = SURFACE_Y + (y - SURFACE_Y) * hubFlatten;

  const edge = WORLD_RADIUS - dist;
  if (edge < 48) y -= (48 - edge) * 0.6; // rim drops into the void
  return Math.max(SURFACE_MIN, Math.min(SURFACE_MAX, Math.round(y)));
}

/**
 * The floor of the cave system, well below the surface.
 *
 * Quantised to 3-block steps on purpose. Terrain is written as merged
 * rectangles, and a cave floor that moves one block at a time would shatter
 * every rectangle into slivers - the quantisation costs nothing visually
 * underground and keeps the sector affordable.
 */
export function caveFloorAt(x, z) {
  const n = fbm(x, z, 260, LAYOUT_SEED + 91);
  return BEDROCK_Y + 3 + Math.round((n * 14) / 3) * 3;
}

/** How much rock hangs beneath the surface before the cavern opens up.
 *
 * Quantised to three thicknesses for the same reason the cave floor is
 * quantised: this value is part of the key the surface rectangles merge on,
 * and letting it vary block by block shattered a mountain sector into 450
 * separate fills. Three steps is invisible from above - you only ever see the
 * crust in cross-section at a cliff or a cave mouth - and it roughly halves
 * the cost of exactly the sectors that were most expensive. */
export function crustAt(x, z) {
  // Rendering a cross-section of the first attempt showed the mistake: a flat
  // 5-11 block crust made the whole world a thin skin stretched over one
  // continuous abyss. Digging anywhere dropped you forty blocks, and nothing
  // read as "cave" because there was nothing else for a cave to be inside of.
  //
  // The thickness now swings from 8 to 28 blocks on a broad noise field, so
  // most digging hits ordinary rock and the cave system opens up where the
  // field runs thin - which is what a cave is: a hole in something.
  const n = fbm(x, z, 380, LAYOUT_SEED + 97);
  return 8 + Math.round((n * 20) / 4) * 4;
}

export function isWithinWorld(pos) {
  return Math.hypot(pos.x, pos.z) < WORLD_RADIUS - 2;
}

/** Stable per-position randomness for feature scatter. */
export function featureRoll(x, z, salt) {
  return hash2(x, z, LAYOUT_SEED + salt);
}
