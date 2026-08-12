import { world, system, BlockVolume } from "@minecraft/server";
import { HOLLOW_VEIL, HUB_CLEAR } from "./build.js";
import {
  BIOMES, SECTOR, WORLD_RADIUS, BEDROCK_Y, SEA_LEVEL,
  biomeAt, heightAt, caveFloorAt, crustAt, featureRoll, isWithinWorld,
} from "./biomes.js";
import { sectorCandidates, headingFrom } from "./frontier.js";

// Streaming terrain.
//
// A script-registered dimension has no world generator - `registerCustomDimension`
// takes a type id and nothing else, there is no generator hook in the 2.9.0
// bindings - so every block out here is placed by this file. The world is
// 100,000 blocks in every direction, which is far past anything that could be
// built up front, so it is built around players as they move and never stored:
// terrain is a pure function of coordinates, and "has this sector been built"
// is answered by probing for its bedrock floor rather than by a list.
//
// The previous version left a visible edge you could fall off, for two
// reasons, and both are fixed here:
//
//  1. It built a radius of 3 sectors - 96 blocks - around each player. Bedrock
//     renders 128 to 256 blocks on most devices, so the frontier was always
//     inside what you could see. The radius is now 10 sectors (320 blocks),
//     comfortably past any render distance, so the edge is never on screen.
//     tools/test_terrain.js holds that property against a sprinting player.
//
//  2. It was far too slow to keep up. Every strip of ground went through the
//     command parser as a `/fill` string - roughly a hundred commands per
//     sector, two sectors a second. Walking outran it immediately. Terrain is
//     now placed with `Dimension.fillBlocks`, a direct native call, and the
//     columns are merged into 2D rectangles first, so a sector costs a few
//     dozen native fills instead of a few hundred parsed commands.
//
// Blocks can only be written to loaded chunks, so a sector outside the
// player's loaded set is skipped and reconsidered on a later pass rather than
// being marked done - the old code marked a sector built whether or not any
// of its fills had actually landed, which permanently pocked the world with
// holes wherever a chunk had not loaded in time.

// Build radius and look-ahead live in ./frontier.js, which has no engine
// imports so tools/test_terrain.js can sprint a player across the world and
// prove the frontier stays outside view distance.
const TICK_INTERVAL = 2;

// Work is budgeted in block writes per pass, not in sectors. Sector cost is
// not uniform - tools/bench_terrain.mjs measures ~208 native fills for an
// average sector and 473 for the worst sampled - so a fixed "N sectors per
// pass" is either wasteful on easy ground or a visible hitch on hard ground.
// A budget bounds the actual work either way.
//
// A sector is only STARTED if budget remains, and once started it is always
// finished: a half-built sector that got marked done is how the old builder
// left permanent holes.
const WRITE_BUDGET = 900;
let budget = 0;

const sessionBuilt = new Set();   // in-memory only; the bedrock probe is the truth

/** Where each player was last pass, to work out which way they are heading. */
const lastSeen = new Map();

function sectorIsBuilt(dim, sx, sz) {
  const key = `${sx},${sz}`;
  if (sessionBuilt.has(key)) return true;
  const x = sx * SECTOR + (SECTOR >> 1);
  const z = sz * SECTOR + (SECTOR >> 1);
  try {
    if (dim.getBlock({ x, y: BEDROCK_Y, z })?.typeId === "minecraft:bedrock") {
      sessionBuilt.add(key);
      return true;
    }
  } catch {
    // chunk not loaded - not built as far as we can tell, and buildSector
    // will decline it anyway
  }
  return false;
}

export function startTerrainStreaming() {
  system.runInterval(() => {
    const dim = veil();
    if (!dim) return;
    budget = WRITE_BUDGET;
    for (const p of world.getAllPlayers()) {
      if (p.dimension.id !== HOLLOW_VEIL) continue;
      if (budget <= 0) break;
      buildAround(dim, p);
    }
  }, TICK_INTERVAL);
}

function veil() {
  try {
    return world.getDimension(HOLLOW_VEIL);
  } catch {
    return null;
  }
}

/**
 * Picks this pass's sectors: nearest first, biased along the direction of
 * travel so ground is already down by the time you reach it rather than
 * appearing under your feet.
 */
function buildAround(dim, player) {
  const loc = player.location;
  const prev = lastSeen.get(player.id);
  lastSeen.set(player.id, { x: loc.x, z: loc.z });

  const candidates = sectorCandidates(loc.x, loc.z, headingFrom(prev, loc), {
    worldRadius: WORLD_RADIUS,
    isBuilt: (sx, sz) => sessionBuilt.has(`${sx},${sz}`),
  });

  for (const c of candidates) {
    if (budget <= 0) break;
    // Only loaded chunks accept blocks. An unloaded sector is left alone -
    // NOT marked built - so it is picked up again once it loads.
    if (!chunkLoaded(dim, c.sx, c.sz)) continue;
    if (sectorIsBuilt(dim, c.sx, c.sz)) continue;
    if (buildSector(dim, c.sx, c.sz)) sessionBuilt.add(`${c.sx},${c.sz}`);
  }
}

function chunkLoaded(dim, sx, sz) {
  // A sector is 32x32, which straddles four 16x16 chunks; both far corners
  // have to be loaded for its fills to land.
  const x = sx * SECTOR;
  const z = sz * SECTOR;
  try {
    return dim.isChunkLoaded({ x, y: BEDROCK_Y, z }) &&
           dim.isChunkLoaded({ x: x + SECTOR - 1, y: BEDROCK_Y, z: z + SECTOR - 1 });
  } catch {
    return false;
  }
}

// ------------------------------------------------------------- placing ----
// Native block writes. `fillBlocks` and `setBlockType` are both on the 2.9.0
// Dimension bindings and neither goes through the command parser, which is
// what makes a build radius this large affordable at all.

function fill(dim, x0, y0, z0, x1, y1, z1, type) {
  if (y1 < y0) return false;
  budget -= 1;
  try {
    dim.fillBlocks(new BlockVolume({ x: x0, y: y0, z: z0 }, { x: x1, y: y1, z: z1 }), type);
    return true;
  } catch {
    return false;
  }
}

function setBlock(dim, x, y, z, type) {
  budget -= 1;
  try {
    dim.setBlockType({ x, y, z }, type);
    return true;
  } catch {
    return false;
  }
}

/**
 * Greedy 2D rectangle decomposition of a 32x32 grid of keys.
 *
 * Terrain height moves slowly (value noise at a 70-block cell over an
 * 11-block range), so a sector holds only a handful of distinct heights and
 * they lie in broad contiguous bands. Merging those into rectangles turns
 * ~1000 per-column fills into a few dozen - the difference between a sector
 * costing a visible hitch and costing nothing anyone notices.
 */
function rectangles(keyAt) {
  const used = new Uint8Array(SECTOR * SECTOR);
  const out = [];
  for (let lz = 0; lz < SECTOR; lz++) {
    for (let lx = 0; lx < SECTOR; lx++) {
      const i = lz * SECTOR + lx;
      if (used[i]) continue;
      const k = keyAt(lx, lz);
      if (k === null) {
        used[i] = 1;
        continue;
      }
      let w = 1;
      while (lx + w < SECTOR && !used[i + w] && keyAt(lx + w, lz) === k) w += 1;
      let h = 1;
      grow: while (lz + h < SECTOR) {
        for (let dx = 0; dx < w; dx++) {
          const j = (lz + h) * SECTOR + lx + dx;
          if (used[j] || keyAt(lx + dx, lz + h) !== k) break grow;
        }
        h += 1;
      }
      for (let dz = 0; dz < h; dz++) {
        for (let dx = 0; dx < w; dx++) used[(lz + dz) * SECTOR + lx + dx] = 1;
      }
      out.push({ lx, lz, w, h, k });
    }
  }
  return out;
}

/**
 * Builds one SECTOR x SECTOR column of world. Returns false if it could not.
 *
 * Three merged passes rather than one, because the world now has three
 * separate surfaces at different heights:
 *
 *   A  bedrock floor + the underground landscape sitting on it
 *   B  the crust hanging under the surface, and the surface itself
 *   C  water, wherever the surface fell below sea level
 *
 * The cavern between A and B is never written at all. A script-registered
 * dimension starts as void, so open space is the default state and "carving"
 * a cave system out of it costs nothing - which is why a world with 87 blocks
 * of relief and a continuous cave system underneath it is barely more
 * expensive than the 12-block slab this replaced.
 */
function buildSector(dim, sx, sz) {
  const x0 = sx * SECTOR;
  const z0 = sz * SECTOR;

  // Sample every column once; the passes below read the cache rather than
  // re-running four bands of noise per block.
  const height = new Int16Array(SECTOR * SECTOR);
  const floor = new Int16Array(SECTOR * SECTOR);
  const crust = new Int16Array(SECTOR * SECTOR);
  const biome = new Array(SECTOR * SECTOR);
  let any = false;
  for (let lz = 0; lz < SECTOR; lz++) {
    for (let lx = 0; lx < SECTOR; lx++) {
      const i = lz * SECTOR + lx;
      const x = x0 + lx;
      const z = z0 + lz;
      if (!isWithinWorld({ x, z })) {
        height[i] = -1;
        continue;
      }
      const b = biomeAt(x, z);
      biome[i] = b;
      height[i] = heightAt(x, z, b);
      floor[i] = caveFloorAt(x, z);
      crust[i] = crustAt(x, z);
      any = true;
    }
  }
  if (!any) return true;                       // wholly outside the world: nothing owed

  const rect = (r) => ({
    i: r.lz * SECTOR + r.lx,
    xa: x0 + r.lx, za: z0 + r.lz,
    xb: x0 + r.lx + r.w - 1, zb: z0 + r.lz + r.h - 1,
  });

  // --- A. bedrock floor and the underground landscape ---------------------
  let ok = false;
  for (const r of rectangles((lx, lz) => {
    const i = lz * SECTOR + lx;
    return height[i] < 0 ? null : `${floor[i]}:${biome[i].id}`;
  })) {
    const { i, xa, za, xb, zb } = rect(r);
    const b = biome[i];
    const cf = floor[i];
    if (fill(dim, xa, BEDROCK_Y, za, xb, BEDROCK_Y, zb, "minecraft:bedrock")) ok = true;
    fill(dim, xa, BEDROCK_Y + 1, za, xb, cf - 1, zb, b.filler);
    fill(dim, xa, cf, za, xb, cf, zb, b.cave ?? b.filler);
  }
  // If not one fill landed the chunk went away mid-build; leave the sector
  // unmarked so a later pass rebuilds it properly.
  if (!ok) return false;

  // --- B. the crust, and the surface on top of it -------------------------
  for (const r of rectangles((lx, lz) => {
    const i = lz * SECTOR + lx;
    return height[i] < 0 ? null : `${height[i]}:${crust[i]}:${biome[i].id}`;
  })) {
    const { i, xa, za, xb, zb } = rect(r);
    const b = biome[i];
    const h = height[i];
    // Never let the crust reach down into the cave floor, or the cavern
    // closes up and the underground disappears.
    const bottom = Math.max(floor[i] + 2, h - crust[i]);
    fill(dim, xa, bottom, za, xb, h - 1, zb, b.filler);
    fill(dim, xa, h, za, xb, h, zb, b.surface);
  }

  // --- C. seas and lakes --------------------------------------------------
  // Everything below sea level floods. This is what turns the marsh into
  // actual wetland and puts coastlines on the other biomes.
  for (const r of rectangles((lx, lz) => {
    const i = lz * SECTOR + lx;
    return height[i] < 0 || height[i] >= SEA_LEVEL ? null : "sea";
  })) {
    const { i, xa, za, xb, zb } = rect(r);
    fill(dim, xa, height[i] + 1, za, xb, SEA_LEVEL, zb, "minecraft:water");
  }

  cavePillars(dim, x0, z0, height, floor, crust, biome);
  caveMouths(dim, x0, z0, height, floor, crust, biome);
  decorateSector(dim, x0, z0);
  return true;
}

/**
 * Sinkholes: shafts opened from the surface down into the cavern.
 *
 * The caves were there in the last build and the owner never saw one, which is
 * the whole problem with a cave system that has no doors - the crust is solid
 * everywhere, so the only way in was to already know it was there and dig. A
 * cave you cannot find is not content.
 *
 * Roughly one sinkhole every few sectors, widening as it descends so it reads
 * as collapsed ground rather than a drilled hole, with a lip of rubble around
 * the mouth so it is visible from across the valley.
 */
function caveMouths(dim, x0, z0, height, floor, crust, biome) {
  // Measured before tuning: at 0.34 this was one sinkhole every ~56 blocks,
  // which is not a cave system, it is Swiss cheese. At 0.09 it is roughly one
  // every 110 blocks - findable while exploring, rare enough to be a find.
  if (featureRoll(x0, z0, 151) > 0.09) return;
  const lx = 6 + Math.floor(featureRoll(x0, z0, 157) * (SECTOR - 12));
  const lz = 6 + Math.floor(featureRoll(x0 + 1, z0 + 1, 163) * (SECTOR - 12));
  const i = lz * SECTOR + lx;
  if (height[i] < 0) return;

  const x = x0 + lx;
  const z = z0 + lz;
  const top = height[i];
  const bottom = Math.max(floor[i] + 1, top - crust[i]);
  if (top - bottom < 8) return;                     // crust too thin to be a shaft

  const b = biome[i];
  // A rubble lip, so the hole announces itself instead of being a trap.
  fill(dim, x - 4, top, z - 4, x + 4, top, z + 4, b.filler);
  // The shaft, widening downward.
  const steps = 4;
  for (let s = 0; s < steps; s++) {
    const ya = top - Math.round(((top - bottom) * s) / steps);
    const yb = top - Math.round(((top - bottom) * (s + 1)) / steps) + 1;
    const r = 2 + s;
    fill(dim, x - r, yb, z - r, x + r, ya, z + r, "minecraft:air");
  }
  // A lantern on the rim: the one concession to being findable in the dark.
  setBlock(dim, x + 5, top + 1, z, "hollowveil:soul_lantern");
}

/**
 * Columns joining the cave floor to the underside of the crust.
 *
 * A cavern with a flat floor and a flat ceiling is a corridor, not a cave.
 * A handful of pillars per sector breaks the sightlines and gives the
 * underground somewhere to hide things - and at four per sector they cost
 * almost nothing.
 */
function cavePillars(dim, x0, z0, height, floor, crust, biome) {
  for (let n = 0; n < 4; n++) {
    const lx = Math.floor(featureRoll(x0 + n * 5, z0, 131) * SECTOR);
    const lz = Math.floor(featureRoll(x0, z0 + n * 5, 137) * SECTOR);
    const i = lz * SECTOR + lx;
    if (height[i] < 0) continue;
    const top = Math.max(floor[i] + 2, height[i] - crust[i]);
    if (top - floor[i] < 6) continue;          // too short to read as a pillar
    const w = featureRoll(x0 + n, z0 + n, 139) > 0.6 ? 1 : 0;
    const x = x0 + lx;
    const z = z0 + lz;
    fill(dim, x - w, floor[i] + 1, z - w, x + w, top - 1, z + w, biome[i].filler);
  }
}

/**
 * Surface variety.
 *
 * "Biomes have no leaves or structures or grass types" and "very little block
 * variation" - and both were true: every column of a biome was the same single
 * surface block, so a hillside was one flat colour to the horizon.
 *
 * Blending is done as patches rather than per column on purpose. Mixing the
 * material into the column data would put it in the key the surface rectangles
 * merge on, which is what shatters a sector into hundreds of fills; laying
 * blobs on top afterwards costs a dozen fills and reads better anyway, because
 * real ground varies in patches rather than per block.
 */
function blendSurface(dim, x0, z0) {
  for (let i = 0; i < 10; i++) {
    const x = x0 + Math.floor(featureRoll(x0 + i * 7, z0, 171) * SECTOR);
    const z = z0 + Math.floor(featureRoll(x0, z0 + i * 7, 173) * SECTOR);
    if (!isWithinWorld({ x, z })) continue;
    const b = biomeAt(x, z);
    const blends = b.blend;
    if (!blends?.length) continue;
    const pick = blends[Math.floor(featureRoll(x, z, 177) * blends.length)];
    const r = 1 + Math.floor(featureRoll(x, z, 179) * 2);
    // One fill per row rather than one write per block: a patch follows the
    // slope along z (where it matters most, since that is the direction the
    // rectangle merge runs) at a fifth of the cost. Filling every block
    // individually would have cost more than the entire sector build.
    for (let dz = -r; dz <= r; dz++) {
      const bz = z + dz;
      if (!isWithinWorld({ x, z: bz })) continue;
      const y = heightAt(x, bz, biomeAt(x, bz));
      fill(dim, x - r, y, bz, x + r, y, bz, pick);
    }
  }
}

/**
 * Flora: the thing whose absence made every biome read as a car park.
 *
 * Each biome gets its own planting list and its own density, so the marsh is
 * thick with fungus and roots, the moors carry dead groves and grave weeds,
 * the Ashlands sprout charred spires, and the ruins push up through cracked
 * paving. Everything is featureRoll-driven, so a place always grows the same
 * way however many times you walk back to it.
 */
function plantFlora(dim, x0, z0) {
  for (let i = 0; i < 34; i++) {
    const x = x0 + Math.floor(featureRoll(x0 + i * 3, z0 + i, 181) * SECTOR);
    const z = z0 + Math.floor(featureRoll(x0 + i, z0 + i * 3, 191) * SECTOR);
    if (!isWithinWorld({ x, z })) continue;
    if (Math.hypot(x, z) < HUB_CLEAR + 4) continue;
    const b = biomeAt(x, z);
    const flora = b.flora;
    if (!flora?.length) continue;
    const r = featureRoll(x, z, 193);
    if (r > (b.floraDensity ?? 0.4)) continue;
    const y = heightAt(x, z, b);
    const kind = flora[Math.floor(featureRoll(x, z, 197) * flora.length)];
    plant(dim, x, y, z, kind, featureRoll(x, z, 199));
  }
}

function plant(dim, x, y, z, kind, r) {
  switch (kind) {
    case "dead_grove": {
      // A cluster, not a lone trunk - single trees on an empty plain read as
      // fence posts, which is exactly how the old scatter looked.
      const n = 2 + Math.floor(r * 3);
      for (let i = 0; i < n; i++) {
        const ox = Math.round((featureRoll(x + i, z, 211) - 0.5) * 7);
        const oz = Math.round((featureRoll(x, z + i, 223) - 0.5) * 7);
        placeDeadTree(dim, x + ox, y, z + oz);
      }
      break;
    }
    case "fungus": {
      const h = 2 + Math.floor(r * 3);
      fill(dim, x, y + 1, z, x, y + h, z, "minecraft:mushroom_stem");
      fill(dim, x - 1, y + h, z - 1, x + 1, y + h + 1, z + 1, "hollowveil:glimmershroom");
      break;
    }
    case "shroom_patch":
      for (let i = 0; i < 4; i++) {
        const ox = Math.round((featureRoll(x + i, z, 227) - 0.5) * 5);
        const oz = Math.round((featureRoll(x, z + i, 229) - 0.5) * 5);
        setBlock(dim, x + ox, y + 1, z + oz, "hollowveil:glimmershroom");
      }
      break;
    case "roots":
      fill(dim, x, y + 1, z, x, y + 1 + Math.floor(r * 3), z, "minecraft:hanging_roots");
      break;
    case "ash_spire": {
      const h = 4 + Math.floor(r * 7);
      fill(dim, x, y + 1, z, x, y + h, z, "minecraft:basalt");
      if (r > 0.6) fill(dim, x + 1, y + 1, z, x + 1, y + Math.max(1, h - 3), z, "minecraft:basalt");
      setBlock(dim, x, y + h + 1, z, "minecraft:magma_block");
      break;
    }
    case "bone_pile":
      fill(dim, x - 1, y + 1, z - 1, x + 1, y + 1, z + 1, "minecraft:bone_block");
      setBlock(dim, x, y + 2, z, "minecraft:bone_block");
      break;
    case "grave_weeds":
      for (let i = 0; i < 5; i++) {
        const ox = Math.round((featureRoll(x + i, z, 233) - 0.5) * 6);
        const oz = Math.round((featureRoll(x, z + i, 239) - 0.5) * 6);
        setBlock(dim, x + ox, y + 1, z + oz,
                 featureRoll(x + i, z + i, 241) > 0.7 ? "minecraft:wither_rose" : "minecraft:deadbush");
      }
      break;
    case "broken_column": {
      const h = 3 + Math.floor(r * 5);
      fill(dim, x, y + 1, z, x, y + h, z, "hollowveil:sunken_bricks");
      setBlock(dim, x, y + h + 1, z, "minecraft:cracked_deepslate_bricks");
      break;
    }
    case "ruined_wall": {
      const len = 3 + Math.floor(r * 5);
      const along = featureRoll(x, z, 243) > 0.5;
      const h = 2 + Math.floor(r * 3);
      if (along) fill(dim, x, y + 1, z, x + len, y + h, z, "hollowveil:sunken_bricks");
      else fill(dim, x, y + 1, z, x, y + h, z + len, "hollowveil:sunken_bricks");
      break;
    }
    case "tar_pit":
      fill(dim, x - 2, y, z - 2, x + 2, y, z + 2, "minecraft:obsidian");
      fill(dim, x - 1, y, z - 1, x + 1, y, z + 1, "minecraft:lava");
      break;
    case "crystal": {
      // A dark spire with a single lit tip. An all-lantern column was the
      // first version and there were 2,700 of them per square kilometre -
      // enough to light the Veil like a car park, which is the opposite of
      // the point.
      const h = 2 + Math.floor(r * 4);
      fill(dim, x, y + 1, z, x, y + h, z, "hollowveil:soulforged_obsidian");
      setBlock(dim, x, y + h + 1, z, "hollowveil:soul_lantern");
      break;
    }
    default:
      break;
  }
}

/** Scatters this biome's features across the sector. Everything is driven by
 * featureRoll(), so a sector always decorates the same way. */
function decorateSector(dim, x0, z0) {
  blendSurface(dim, x0, z0);
  plantFlora(dim, x0, z0);
  for (let i = 0; i < 26; i++) {
    const x = x0 + Math.floor(featureRoll(x0 + i, z0, 11) * SECTOR);
    const z = z0 + Math.floor(featureRoll(x0, z0 + i, 23) * SECTOR);
    if (!isWithinWorld({ x, z })) continue;
    // The hub is built by world/build.js and holds the altars, the village
    // and the arrival point. Decoration must not litter it.
    if (Math.hypot(x, z) < HUB_CLEAR + 4) continue;
    const b = biomeAt(x, z);
    const y = heightAt(x, z, b);
    const r = featureRoll(x, z, 47);

    if (b.accents && r < 0.30) {
      const acc = b.accents[Math.floor(featureRoll(x, z, 51) * b.accents.length)];
      fill(dim, x, y, z, x + 1, y, z + 1, acc);
    }
    if (b.graves && r > 0.30 && r < 0.44) placeGrave(dim, x, y, z);
    if (b.deadTrees && r > 0.44 && r < 0.52) placeDeadTree(dim, x, y, z);
    if (b.emberVents && r > 0.30 && r < 0.38) {
      setBlock(dim, x, y, z, "minecraft:magma_block");
      setBlock(dim, x, y + 1, z, "minecraft:fire");
    }
    if (b.pools && r > 0.30 && r < 0.40) {
      fill(dim, x - 1, y, z - 1, x + 1, y, z + 1, "minecraft:water");
    }
    if (b.shrooms && r > 0.40 && r < 0.48) {
      setBlock(dim, x, y + 1, z, "hollowveil:glimmershroom");
    }
    if (b.rubble && r > 0.30 && r < 0.44) placeRubble(dim, x, y, z, featureRoll(x, z, 61));

    // The graveyard read is meant to carry across the whole dimension, not
    // just the moors, so every biome gets a thin scatter of graves and bone
    // litter on top of its own features. The moors stay the heartland of it
    // (their own `graves` pass above is much denser).
    if (!b.graves && r > 0.88 && r < 0.93) placeGrave(dim, x, y, z);
    if (r > 0.93 && r < 0.955) setBlock(dim, x, y + 1, z, "minecraft:bone_block");

    // soul lanterns are the only real light out here, and they are rare -
    // the dimension is meant to stay dark
    if (r > 0.985) setBlock(dim, x, y + 1, z, "hollowveil:soul_lantern");
  }
  scatterOre(dim, x0, z0);
}

/** A headstone, sometimes with a mound and a wither-rose. */
function placeGrave(dim, x, y, z) {
  const kind = featureRoll(x, z, 71);
  fill(dim, x - 1, y, z, x + 1, y, z, "minecraft:coarse_dirt");
  setBlock(dim, x, y + 1, z, "minecraft:cobblestone_wall");
  if (kind > 0.6) setBlock(dim, x, y + 2, z, "minecraft:stone_brick_slab");
  if (kind > 0.85) setBlock(dim, x, y + 1, z + 1, "minecraft:wither_rose");
}

function placeDeadTree(dim, x, y, z) {
  const h = 3 + Math.floor(featureRoll(x, z, 83) * 4);
  fill(dim, x, y + 1, z, x, y + h, z, "minecraft:stripped_dark_oak_log");
  setBlock(dim, x + 1, y + h, z, "minecraft:stripped_dark_oak_log");
  setBlock(dim, x - 1, y + h - 1, z, "minecraft:stripped_dark_oak_log");
}

function placeRubble(dim, x, y, z, r) {
  const h = 1 + Math.floor(r * 4);
  fill(dim, x, y + 1, z, x, y + h, z, "hollowveil:sunken_bricks");
  if (r > 0.7) setBlock(dim, x + 1, y + 1, z, "minecraft:cracked_deepslate_bricks");
}

/**
 * Ore, placed against the world's real surfaces.
 *
 * The old table used fixed absolute heights, which made sense when the whole
 * world was a 12-block slab and made none once the surface ranges from 40 to
 * 127. A vein at "y = 54" would be deep underground beneath a mountain and
 * floating in the sky over the marsh.
 *
 * Every vein is now positioned RELATIVE to something the player can actually
 * find: `crust` sits just under the surface where you dig down, and `cave`
 * sits on the floor of the cavern system where you go looking for it. That
 * also gives the tiers a real progression - the good stuff is only in the
 * caves, so the caves are worth the trip.
 */
function scatterOre(dim, x0, z0) {
  const veins = [
    { block: "hollowveil:wraithsteel_ore", n: 5, where: "crust", salt: 101 },
    { block: "hollowveil:ember_coal_ore", n: 4, where: "crust", salt: 103 },
    { block: "hollowveil:veilsteel_ore", n: 3, where: "cave", salt: 107 },
    { block: "hollowveil:hollowforged_ore", n: 2, where: "cave", salt: 109, rare: 0.22 },
  ];
  for (const v of veins) {
    for (let i = 0; i < v.n; i++) {
      const rx = featureRoll(x0 + i * 3, z0, v.salt);
      const rz = featureRoll(x0, z0 + i * 3, v.salt + 1);
      const ry = featureRoll(x0 + i, z0 + i, v.salt + 2);
      if (v.rare && ry > v.rare) continue;      // hollowforged stays genuinely rare
      const x = x0 + Math.floor(rx * SECTOR);
      const z = z0 + Math.floor(rz * SECTOR);
      if (!isWithinWorld({ x, z })) continue;
      const b = biomeAt(x, z);
      let y;
      if (v.where === "crust") {
        const h = heightAt(x, z, b);
        y = h - 2 - Math.floor(ry * Math.max(1, crustAt(x, z) - 2));
      } else {
        y = caveFloorAt(x, z) + (ry > 0.5 ? 1 : 0);
      }
      if (y <= BEDROCK_Y) continue;
      fill(dim, x, y, z, x + 1, y, z, v.block);
    }
  }
}

export { BIOMES };
