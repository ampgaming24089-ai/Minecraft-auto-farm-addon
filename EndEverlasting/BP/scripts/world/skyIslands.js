/**
 * Using the height of the world.
 *
 * The End generates one band of islands around y=60 and then a hundred and
 * fifty blocks of nothing above it. That is most of the dimension unused, and
 * it is why the End reads as flat however wide it is: everything is at eye
 * level, so there is never anything to climb toward.
 *
 * So this hangs more islands through the whole column. They are sited from the
 * seed exactly the way structures are - a pure function of (seed, cell) - and
 * built from the biome underneath them, so a Glowspore Basin gets magenta
 * islands overhead and an Ashen Waste gets charcoal ones. Looking up in a
 * region tells you which region you are in.
 *
 * Two rules keep this from wrecking anything:
 *
 *   - An island is only ever built into *air*. Every block of its footprint is
 *     checked first, and one non-air block anywhere in it abandons the site.
 *     Nothing this places can ever overwrite terrain, a structure or a build.
 *   - Nothing generates near the origin, so the main island, the pillars, the
 *     gateway and the fight arena are all untouched.
 */

import { BlockPermutation, system, world } from "@minecraft/server";
import { Rng, hash } from "../lib/rng.js";
import { biomeAt } from "./biomes.js";
import { END_DIMENSION } from "./generator.js";
import { isBuilt, markBuilt } from "./memory.js";
import { worldSeedHash } from "./sites.js";

/** Siting grid. Tighter than the structure grid - these are scenery, and the
 *  sky should have several in view rather than one every few minutes. */
const CELL = 96;

/** Fraction of cells that hold an island. */
const CHANCE = 0.36;

/** Keep clear of vanilla's island, the pillars and the gateway. */
const INNER_CLEARANCE = 900;

/** The band islands hang in. Deliberately above the natural terrain, so this
 *  adds a layer rather than crowding the one that already exists. */
const MIN_Y = 96;
const MAX_Y = 210;

/** How far ahead of a player islands are built, and how often we look. */
const BUILD_RADIUS = 132;
const SCAN_INTERVAL_TICKS = 60;
const BUILDS_PER_SCAN = 1;

const building = new Set();

/**
 * The island in a cell, or undefined. Pure in (seed, cellX, cellZ).
 *
 * @returns {{key:string, x:number, y:number, z:number, radius:number, seed:number}|undefined}
 */
export function islandInCell(cellX, cellZ) {
  const seed = hash(worldSeedHash(), 0x5c1a, cellX, cellZ);
  const rng = new Rng(seed);
  if (rng.next() > CHANCE) return undefined;

  const x = cellX * CELL + rng.int(8, CELL - 8);
  const z = cellZ * CELL + rng.int(8, CELL - 8);
  if (Math.hypot(x, z) < INNER_CLEARANCE) return undefined;

  return {
    key: `sky.${cellX}.${cellZ}`,
    x,
    y: rng.int(MIN_Y, MAX_Y),
    z,
    radius: rng.float(4.5, 11.0),
    seed,
  };
}

/** Every sited island within a few cells of a point. */
export function islandsNear(x, z, cellRadius = 2) {
  const centreX = Math.floor(x / CELL);
  const centreZ = Math.floor(z / CELL);
  const found = [];
  for (let dx = -cellRadius; dx <= cellRadius; dx++) {
    for (let dz = -cellRadius; dz <= cellRadius; dz++) {
      const island = islandInCell(centreX + dx, centreZ + dz);
      if (island) found.push(island);
    }
  }
  return found;
}

const permutations = new Map();
function cachedPermutation(id) {
  if (!permutations.has(id)) {
    try {
      permutations.set(id, BlockPermutation.resolve(id));
    } catch {
      permutations.set(id, undefined);
    }
  }
  return permutations.get(id);
}

/**
 * The shape of an island: a squashed ellipsoid, thicker in the middle and
 * tapering to nothing underneath, which is the profile a floating rock reads
 * as. Returned as offsets so the caller can test the space before filling it.
 */
function* shape(island, rng) {
  const r = Math.ceil(island.radius);
  const depth = Math.ceil(island.radius * 0.75);
  for (let dx = -r; dx <= r; dx++) {
    for (let dz = -r; dz <= r; dz++) {
      const flat = Math.hypot(dx, dz);
      if (flat > island.radius) continue;
      // Edges wobble, so the outline is not a circle from above.
      const wobble = 1.0 + (rng.next() - 0.5) * 0.28;
      if (flat > island.radius * wobble) continue;

      const rim = 1.0 - flat / island.radius;
      const below = Math.max(1, Math.round(depth * rim * rim));
      const above = flat < island.radius * 0.55 && rng.chance(0.4) ? 1 : 0;
      for (let dy = -below; dy <= above; dy++) {
        yield { dx, dy, dz, surface: dy === above };
      }
    }
  }
}

function* buildIsland(dimension, island) {
  try {
    const biome = biomeAt(island.x, island.z);
    const surfaceId = biome.surface ?? "minecraft:end_stone";
    const fillerId = biome.filler ?? surfaceId;
    const surface = cachedPermutation(surfaceId);
    const filler = cachedPermutation(fillerId);
    if (!surface || !filler) return;

    // Lay the shape out first, so the whole footprint can be tested before a
    // single block is placed. An island half-built into a player's tower is
    // worse than no island at all.
    const cells = [...shape(island, new Rng(island.seed ^ 0x2f1d))];

    let clear = true;
    let checked = 0;
    for (const cell of cells) {
      const at = { x: island.x + cell.dx, y: island.y + cell.dy, z: island.z + cell.dz };
      try {
        if (!dimension.isChunkLoaded(at)) return; // Come back when it is loaded.
        const block = dimension.getBlock(at);
        if (!block) return;
        if (block.typeId !== "minecraft:air") {
          clear = false;
          break;
        }
      } catch {
        return;
      }
      if (++checked % 64 === 0) yield;
    }
    if (!clear) {
      // Somebody or something is already there. Remember it so the site is
      // not re-tested every time a player flies past.
      markBuilt(island.key);
      return;
    }

    const rng = new Rng(island.seed ^ 0x77ab);
    let placed = 0;
    for (const cell of cells) {
      const at = { x: island.x + cell.dx, y: island.y + cell.dy, z: island.z + cell.dz };
      try {
        const block = dimension.getBlock(at);
        if (block) block.setPermutation(cell.surface ? surface : filler);
      } catch {
        // Chunk went away mid-build; the rest simply does not get placed.
      }
      if (++placed % 48 === 0) yield;
    }

    // Flora and hanging growth, so a sky island is not a bare lump of rock.
    for (const cell of cells) {
      if (!cell.surface) continue;
      const x = island.x + cell.dx;
      const z = island.z + cell.dz;
      if (rng.next() < (biome.floraChance ?? 0.1) * 1.6) {
        const flora = pickFlora(biome, rng);
        const plant = flora && cachedPermutation(flora.id);
        if (plant) {
          const height = flora.pillar ? rng.int(1, flora.pillar) : 1;
          for (let up = 1; up <= height; up++) {
            try {
              const cellBlock = dimension.getBlock({ x, y: island.y + cell.dy + up, z });
              if (!cellBlock || cellBlock.typeId !== "minecraft:air") break;
              cellBlock.setPermutation(plant);
            } catch {
              break;
            }
          }
        }
      }
      yield;
    }

    markBuilt(island.key);
  } catch (error) {
    console.warn(`[End Everlasting] sky island ${island.key} failed: ${error}`);
  } finally {
    building.delete(island.key);
  }
}

function pickFlora(biome, rng) {
  const flora = biome.flora ?? [];
  const total = flora.reduce((sum, entry) => sum + entry.weight, 0);
  if (total <= 0) return undefined;
  let roll = rng.float(0, total);
  for (const entry of flora) {
    roll -= entry.weight;
    if (roll <= 0) return entry;
  }
  return flora[flora.length - 1];
}

function scan() {
  let dimension;
  try {
    dimension = world.getDimension(END_DIMENSION);
  } catch {
    return;
  }

  for (const player of world.getAllPlayers()) {
    if (player.dimension.id !== END_DIMENSION) continue;
    const { x, z } = player.location;

    let started = 0;
    for (const island of islandsNear(x, z, 2)) {
      if (started >= BUILDS_PER_SCAN) break;
      if (building.has(island.key) || isBuilt(island.key)) continue;
      if (Math.hypot(island.x - x, island.z - z) > BUILD_RADIUS) continue;
      building.add(island.key);
      try {
        system.runJob(buildIsland(dimension, island));
        started += 1;
      } catch {
        building.delete(island.key);
      }
    }
  }
}

export function startSkyIslands() {
  system.runInterval(scan, SCAN_INTERVAL_TICKS);
}
