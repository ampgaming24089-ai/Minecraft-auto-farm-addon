import { world, system, BlockVolume } from "@minecraft/server";
import { HOLLOW_VEIL, HUB_CLEAR } from "./build.js";
import {
  BIOMES, SECTOR, WORLD_RADIUS, BEDROCK_Y, STONE_TOP_Y,
  biomeAt, heightAt, featureRoll, isWithinWorld,
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
// not uniform - measured across the world it averages ~110 native fills but
// runs to 200 where several biomes and a lot of height variation meet - so a
// fixed "N sectors per pass" is either wasteful on easy ground or a visible
// hitch on hard ground. A budget bounds the actual work either way.
//
// A sector is only STARTED if budget remains, and once started it is always
// finished: a half-built sector that got marked done is how the old builder
// left permanent holes.
const WRITE_BUDGET = 640;
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

/** Builds one SECTOR x SECTOR column of world. Returns false if it could not. */
function buildSector(dim, sx, sz) {
  const x0 = sx * SECTOR;
  const z0 = sz * SECTOR;

  // Sample height and biome once per column; everything below reads the cache
  // rather than re-running the noise.
  const height = new Int16Array(SECTOR * SECTOR);
  const biome = new Array(SECTOR * SECTOR);
  let minH = Infinity;
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
      const h = heightAt(x, z);
      height[i] = h;
      biome[i] = biomeAt(x, z);
      if (h < minH) minH = h;
      any = true;
    }
  }
  if (!any) return true;                       // wholly outside the world: nothing owed
  const base = Math.max(BEDROCK_Y + 1, Math.min(minH, STONE_TOP_Y));

  // 1. Floor and deep stone, merged on biome alone so they cost a handful of
  //    fills for the whole sector.
  let ok = false;
  for (const r of rectangles((lx, lz) => {
    const i = lz * SECTOR + lx;
    return height[i] < 0 ? null : biome[i].id;
  })) {
    const b = biome[r.lz * SECTOR + r.lx];
    const xa = x0 + r.lx;
    const za = z0 + r.lz;
    const xb = xa + r.w - 1;
    const zb = za + r.h - 1;
    if (fill(dim, xa, BEDROCK_Y, za, xb, BEDROCK_Y, zb, "minecraft:bedrock")) ok = true;
    fill(dim, xa, BEDROCK_Y + 1, za, xb, base - 1, zb, b.filler);
  }
  // If not one fill landed the chunk went away mid-build; leave the sector
  // unmarked so a later pass rebuilds it properly.
  if (!ok) return false;

  // 2. The shaped top, merged on height AND biome.
  for (const r of rectangles((lx, lz) => {
    const i = lz * SECTOR + lx;
    return height[i] < 0 ? null : `${height[i]}:${biome[i].id}`;
  })) {
    const i = r.lz * SECTOR + r.lx;
    const h = height[i];
    const b = biome[i];
    const xa = x0 + r.lx;
    const za = z0 + r.lz;
    const xb = xa + r.w - 1;
    const zb = za + r.h - 1;
    if (h > base) fill(dim, xa, base, za, xb, h - 1, zb, b.filler);
    fill(dim, xa, h, za, xb, h, zb, b.surface);
  }

  decorateSector(dim, x0, z0);
  return true;
}

/** Scatters this biome's features across the sector. Everything is driven by
 * featureRoll(), so a sector always decorates the same way. */
function decorateSector(dim, x0, z0) {
  for (let i = 0; i < 26; i++) {
    const x = x0 + Math.floor(featureRoll(x0 + i, z0, 11) * SECTOR);
    const z = z0 + Math.floor(featureRoll(x0, z0 + i, 23) * SECTOR);
    if (!isWithinWorld({ x, z })) continue;
    // The hub is built by world/build.js and holds the altars, the village
    // and the arrival point. Decoration must not litter it.
    if (Math.hypot(x, z) < HUB_CLEAR + 4) continue;
    const b = biomeAt(x, z);
    const y = heightAt(x, z);
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

/** Ore is scattered per sector rather than per world, so it exists
 * everywhere you explore instead of only in one starting island. */
function scatterOre(dim, x0, z0) {
  const veins = [
    { block: "hollowveil:wraithsteel_ore", n: 5, lo: BEDROCK_Y + 2, hi: STONE_TOP_Y, salt: 101 },
    { block: "hollowveil:ember_coal_ore", n: 4, lo: STONE_TOP_Y - 6, hi: STONE_TOP_Y, salt: 103 },
    { block: "hollowveil:veilsteel_ore", n: 2, lo: BEDROCK_Y + 2, hi: BEDROCK_Y + 9, salt: 107 },
    { block: "hollowveil:hollowforged_ore", n: 1, lo: BEDROCK_Y + 1, hi: BEDROCK_Y + 3, salt: 109 },
  ];
  for (const v of veins) {
    for (let i = 0; i < v.n; i++) {
      const rx = featureRoll(x0 + i * 3, z0, v.salt);
      const rz = featureRoll(x0, z0 + i * 3, v.salt + 1);
      const ry = featureRoll(x0 + i, z0 + i, v.salt + 2);
      // hollowforged stays genuinely rare even though it is now per-sector
      if (v.block.includes("hollowforged") && ry > 0.22) continue;
      const x = x0 + Math.floor(rx * SECTOR);
      const z = z0 + Math.floor(rz * SECTOR);
      if (!isWithinWorld({ x, z })) continue;
      const y = Math.floor(v.lo + ry * (v.hi - v.lo));
      fill(dim, x, y, z, x + 1, y, z, v.block);
    }
  }
}

export { BIOMES };
