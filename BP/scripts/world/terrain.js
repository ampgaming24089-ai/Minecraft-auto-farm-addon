import { world, system } from "@minecraft/server";
import { HOLLOW_VEIL } from "./build.js";
import {
  BIOMES, SECTOR, WORLD_RADIUS, BEDROCK_Y, STONE_TOP_Y,
  biomeAt, heightAt, featureRoll, isWithinWorld,
} from "./biomes.js";
import { commandRunner } from "../lib/cmd.js";

// Streaming terrain.
//
// The old world was a single 90-block island raised in one burst the first
// time anyone arrived. That does not scale: a 512-radius world is ~130x the
// area, and building it up front would mean tens of thousands of commands in
// one tick and a hung client.
//
// Instead terrain is built one SECTOR at a time, only near a player, and
// only once - which sectors are done is persisted, so a world keeps its
// terrain across sessions and never rebuilds (and so never overwrites
// anything a player has since changed).

const BUILD_RADIUS = 3;      // sectors around a player kept generated
const SECTORS_PER_TICK = 1;  // hard cap on work per pass
const TICK_INTERVAL = 10;

// Which sectors are already built is NOT persisted. At radius 10000 there
// are ~307,000 sectors, and a list of the visited ones would grow into
// megabytes of dynamic property - far past the budget - for a world that is
// otherwise entirely deterministic. Instead a sector is probed: terrain lays
// a bedrock floor at BEDROCK_Y, so if that block is already bedrock the
// sector has been built before. That is O(1), needs no storage, survives
// relogs for free, and still never rebuilds over a player's changes.
const sessionBuilt = new Set(); // in-memory only, avoids re-probing each pass
let queue = [];
const queued = new Set();

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
    // chunk not loaded - treat as unbuilt; the build itself will no-op safely
  }
  return false;
}

export function startTerrainStreaming() {
  system.runInterval(() => {
    const dim = veil();
    if (!dim) return;
    enqueueNearPlayers(dim);
    drainQueue(dim);
  }, TICK_INTERVAL);
}

function veil() {
  try {
    return world.getDimension(HOLLOW_VEIL);
  } catch {
    return null;
  }
}

function enqueueNearPlayers(dim) {
  for (const p of world.getAllPlayers()) {
    if (p.dimension.id !== HOLLOW_VEIL) continue;
    const psx = Math.floor(p.location.x / SECTOR);
    const psz = Math.floor(p.location.z / SECTOR);
    for (let dx = -BUILD_RADIUS; dx <= BUILD_RADIUS; dx++) {
      for (let dz = -BUILD_RADIUS; dz <= BUILD_RADIUS; dz++) {
        const sx = psx + dx;
        const sz = psz + dz;
        const key = `${sx},${sz}`;
        if (queued.has(key) || sessionBuilt.has(key)) continue;
        const cx = sx * SECTOR + SECTOR / 2;
        const cz = sz * SECTOR + SECTOR / 2;
        if (Math.hypot(cx, cz) > WORLD_RADIUS + SECTOR) continue;
        queued.add(key);
        queue.push({ sx, sz, key, d: dx * dx + dz * dz });
      }
    }
  }
  // nearest first, so ground appears under the player before the horizon
  queue.sort((a, b) => a.d - b.d);
  // a player sprinting across the world can outrun the builder; cap the
  // backlog so it never grows without bound
  if (queue.length > 256) {
    for (const job of queue.splice(256)) queued.delete(job.key);
  }
}

function drainQueue(dim) {
  for (let i = 0; i < SECTORS_PER_TICK && queue.length; i++) {
    const job = queue.shift();
    queued.delete(job.key);
    if (sectorIsBuilt(dim, job.sx, job.sz)) continue;
    try {
      buildSector(dim, job.sx, job.sz);
      sessionBuilt.add(job.key);
    } catch {
      // chunk not loaded yet: drop it, the next pass re-queues it
    }
  }
}

/** Builds one SECTOR x SECTOR column of world. */
function buildSector(dim, sx, sz) {
  const x0 = sx * SECTOR;
  const z0 = sz * SECTOR;
  const run = commandRunner(dim);

  // Terrain is built as columns of constant height. Rather than one fill per
  // block column (1024 commands), adjacent columns of equal height and biome
  // are merged into strips, which typically cuts it to a few dozen.
  for (let lz = 0; lz < SECTOR; lz++) {
    const z = z0 + lz;
    let runStart = null;
    let runH = null;
    let runBiome = null;
    for (let lx = 0; lx <= SECTOR; lx++) {
      const x = x0 + lx;
      const inside = lx < SECTOR && isWithinWorld({ x, z });
      const h = inside ? heightAt(x, z) : null;
      const b = inside ? biomeAt(x, z) : null;
      if (runStart !== null && (!inside || h !== runH || b !== runBiome)) {
        emitStrip(run, runStart, z, x - 1, runH, runBiome);
        runStart = null;
      }
      if (inside && runStart === null) {
        runStart = x;
        runH = h;
        runBiome = b;
      }
    }
  }
  decorateSector(run, dim, x0, z0);
}

function emitStrip(run, xa, z, xb, h, biome) {
  run(`fill ${xa} ${BEDROCK_Y} ${z} ${xb} ${BEDROCK_Y} ${z} minecraft:bedrock`);
  run(`fill ${xa} ${BEDROCK_Y + 1} ${z} ${xb} ${h - 1} ${z} ${biome.filler}`);
  run(`fill ${xa} ${h} ${z} ${xb} ${h} ${z} ${biome.surface}`);
}

/** Scatters this biome's features across the sector. Everything is driven by
 * featureRoll(), so a sector always decorates the same way. */
function decorateSector(run, dim, x0, z0) {
  for (let i = 0; i < 26; i++) {
    const x = x0 + Math.floor(featureRoll(x0 + i, z0, 11) * SECTOR);
    const z = z0 + Math.floor(featureRoll(x0, z0 + i, 23) * SECTOR);
    if (!isWithinWorld({ x, z })) continue;
    const b = biomeAt(x, z);
    const y = heightAt(x, z);
    const r = featureRoll(x, z, 47);

    if (b.accents && r < 0.30) {
      const acc = b.accents[Math.floor(featureRoll(x, z, 51) * b.accents.length)];
      run(`fill ${x} ${y} ${z} ${x + 1} ${y} ${z + 1} ${acc}`);
    }
    if (b.graves && r > 0.30 && r < 0.44) placeGrave(run, x, y, z);
    if (b.deadTrees && r > 0.44 && r < 0.52) placeDeadTree(run, x, y, z);
    if (b.emberVents && r > 0.30 && r < 0.38) {
      run(`setblock ${x} ${y} ${z} minecraft:magma_block`);
      run(`setblock ${x} ${y + 1} ${z} minecraft:fire`);
    }
    if (b.pools && r > 0.30 && r < 0.40) {
      run(`fill ${x - 1} ${y} ${z - 1} ${x + 1} ${y} ${z + 1} minecraft:water`);
    }
    if (b.shrooms && r > 0.40 && r < 0.48) {
      run(`setblock ${x} ${y + 1} ${z} hollowveil:glimmershroom`);
    }
    if (b.rubble && r > 0.30 && r < 0.44) placeRubble(run, x, y, z, featureRoll(x, z, 61));

    // The graveyard read is meant to carry across the whole dimension, not
    // just the moors, so every biome gets a thin scatter of graves and bone
    // litter on top of its own features. The moors stay the heartland of it
    // (their own `graves` pass above is much denser).
    if (!b.graves && r > 0.88 && r < 0.93) placeGrave(run, x, y, z);
    if (r > 0.93 && r < 0.955) {
      run(`setblock ${x} ${y + 1} ${z} minecraft:bone_block`);
    }

    // soul lanterns are the only real light out here, and they are rare -
    // the dimension is meant to stay dark
    if (r > 0.985) run(`setblock ${x} ${y + 1} ${z} hollowveil:soul_lantern`);
  }
  scatterOre(run, x0, z0);
}

/** A headstone, sometimes with a mound and a wither-rose. */
function placeGrave(run, x, y, z) {
  const kind = featureRoll(x, z, 71);
  run(`setblock ${x} ${y + 1} ${z} minecraft:cobblestone_wall`);
  if (kind > 0.6) {
    run(`setblock ${x} ${y + 2} ${z} minecraft:stone_brick_slab`);
  }
  if (kind > 0.85) {
    run(`setblock ${x} ${y + 1} ${z + 1} minecraft:wither_rose`);
  }
  run(`fill ${x - 1} ${y} ${z} ${x + 1} ${y} ${z} minecraft:coarse_dirt`);
}

function placeDeadTree(run, x, y, z) {
  const h = 3 + Math.floor(featureRoll(x, z, 83) * 4);
  run(`fill ${x} ${y + 1} ${z} ${x} ${y + h} ${z} minecraft:stripped_dark_oak_log`);
  run(`setblock ${x + 1} ${y + h} ${z} minecraft:stripped_dark_oak_log`);
  run(`setblock ${x - 1} ${y + h - 1} ${z} minecraft:stripped_dark_oak_log`);
}

function placeRubble(run, x, y, z, r) {
  const h = 1 + Math.floor(r * 4);
  run(`fill ${x} ${y + 1} ${z} ${x} ${y + h} ${z} hollowveil:sunken_bricks`);
  if (r > 0.7) run(`setblock ${x + 1} ${y + 1} ${z} minecraft:cracked_deepslate_bricks`);
}

/** Ore is scattered per sector rather than per world, so it exists
 * everywhere you explore instead of only in one starting island. */
function scatterOre(run, x0, z0) {
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
      run(`fill ${x} ${y} ${z} ${x + 1} ${y} ${z} ${v.block}`);
    }
  }
}

export { BIOMES };
