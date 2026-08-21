/**
 * Using the height of the world.
 *
 * The End generates one band of islands around y=60 and then nearly two
 * hundred blocks of nothing above it. That is most of the dimension unused,
 * and it is why the End reads as flat however wide it is: everything is at eye
 * level, so there is never anything to climb toward.
 *
 * So this hangs more land through the whole column - above the natural band
 * and below it - sited from the seed exactly the way structures are, and built
 * from the biome underneath, so a Glowspore Basin gets magenta islands
 * overhead and an Ashen Waste gets charcoal ones. Looking up in a region tells
 * you which region you are in.
 *
 * What was wrong with the first version of this, and why it never appeared:
 *
 *   - Nothing generated within 900 blocks of the origin. That is the entire
 *     area a player arriving through the portal actually plays in, so the
 *     feature was invisible unless you first flew a thousand blocks in a
 *     straight line. The clearance now only covers vanilla's island, its
 *     pillars and the gateway ring.
 *   - One island per 96-block cell, at one random height, 36% of the time. A
 *     single rock every couple of hundred blocks is not an upper layer; it is
 *     litter. Islands are now sited per *tier*, several tiers deep, so the
 *     column above a region has land at four or five different heights.
 *   - One island built every three seconds, within 132 blocks. A player flying
 *     at End speed outran it permanently. The scan is three times as often,
 *     reaches further, and starts several builds at once.
 *   - Whether a site was already built was answered out of a 1,500-entry FIFO
 *     shared with every structure in the pack, which sky islands alone would
 *     churn through in a few minutes of flying - so islands were re-tested
 *     forever and the structure memory was destroyed as a side effect. It now
 *     asks the world instead: if the island's core block is already there, it
 *     is built. That is O(1), needs no storage, and is correct across
 *     restarts.
 *
 * Two rules keep this from wrecking anything, and both are unchanged:
 *
 *   - An island is only ever built into *air*. Every block of its footprint is
 *     checked first, and one non-air block anywhere in it abandons the site.
 *     Nothing this places can ever overwrite terrain, a structure or a build.
 *   - Nothing generates near the origin, so the main island, the pillars, the
 *     gateway and the fight arena are all untouched.
 */

import { BlockPermutation, system, world } from "@minecraft/server";
import { Rng, hash } from "../lib/rng.js";
import { SPECIES, growTree } from "../lib/tree.js";
import { biomeAt } from "./biomes.js";
import { END_DIMENSION } from "./generator.js";
import { worldSeedHash } from "./sites.js";

/** Siting grid. One roll per tier per cell. */
const CELL = 72;

/**
 * The bands islands hang in.
 *
 * `chance` is per cell, so the expected number of islands in a cell is the sum
 * of these - a little over two. The natural End band is roughly y=40..70 and
 * is deliberately skipped: this adds layers above and below it rather than
 * crowding the one that already exists.
 */
const TIERS = [
  { min: 16, max: 34, chance: 0.30, radius: [4.0, 8.0] },   // below the band
  { min: 86, max: 112, chance: 0.52, radius: [5.0, 12.0] },
  { min: 122, max: 152, chance: 0.48, radius: [5.0, 13.0] },
  { min: 162, max: 196, chance: 0.42, radius: [4.5, 11.0] },
  { min: 204, max: 238, chance: 0.34, radius: [4.0, 9.0] },
];

/** Keep clear of vanilla's island, the pillars and the gateway ring. */
const INNER_CLEARANCE = 220;

/** How far ahead of a player islands are built, and how often we look. */
const BUILD_RADIUS = 176;
const SCAN_INTERVAL_TICKS = 20;
const BUILDS_PER_SCAN = 3;

/** Ceiling on jobs in flight, so a player flying fast cannot queue hundreds. */
const MAX_CONCURRENT = 6;

const building = new Set();
/** Sites resolved this session: built by us, or occupied by something else. */
const settled = new Set();

/**
 * Every island sited in a cell. Pure in (seed, cellX, cellZ).
 *
 * @returns {{key:string, x:number, y:number, z:number, radius:number,
 *            seed:number, tier:number}[]}
 */
export function islandsInCell(cellX, cellZ) {
  const found = [];
  for (let tier = 0; tier < TIERS.length; tier++) {
    const band = TIERS[tier];
    const seed = hash(worldSeedHash(), 0x5c1a + tier, cellX, cellZ);
    const rng = new Rng(seed);
    if (rng.next() > band.chance) continue;

    const x = cellX * CELL + rng.int(6, CELL - 6);
    const z = cellZ * CELL + rng.int(6, CELL - 6);
    if (Math.hypot(x, z) < INNER_CLEARANCE) continue;

    found.push({
      key: `sky.${tier}.${cellX}.${cellZ}`,
      x,
      z,
      y: rng.int(band.min, band.max),
      radius: rng.float(band.radius[0], band.radius[1]),
      seed,
      tier,
    });
  }
  return found;
}

/** Every sited island within a few cells of a point. */
export function islandsNear(x, z, cellRadius = 3) {
  const centreX = Math.floor(x / CELL);
  const centreZ = Math.floor(z / CELL);
  const found = [];
  for (let dx = -cellRadius; dx <= cellRadius; dx++) {
    for (let dz = -cellRadius; dz <= cellRadius; dz++) {
      found.push(...islandsInCell(centreX + dx, centreZ + dz));
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
 * tapering to a keel underneath, which is the profile a floating rock reads
 * as. Returned as offsets so the caller can test the space before filling it.
 */
function* shape(island, rng) {
  const r = Math.ceil(island.radius);
  const depth = Math.ceil(island.radius * 0.85);
  for (let dx = -r; dx <= r; dx++) {
    for (let dz = -r; dz <= r; dz++) {
      const flat = Math.hypot(dx, dz);
      if (flat > island.radius) continue;
      // Edges wobble, so the outline is not a circle from above.
      const wobble = 1.0 + (rng.next() - 0.5) * 0.3;
      if (flat > island.radius * wobble) continue;

      const rim = 1.0 - flat / island.radius;
      const below = Math.max(1, Math.round(depth * rim * rim));
      // A gentle crown, so the top is not a table.
      const above = flat < island.radius * 0.45
        ? (rng.chance(0.55) ? 1 : 0)
        : 0;
      for (let dy = -below; dy <= above; dy++) {
        yield { dx, dy, dz, surface: dy === above, flat };
      }
    }
  }
}

/**
 * Has this island already been built?
 *
 * Asks the world rather than a ledger: the block at the island's centre is
 * either its own surface (built), air (not built), or something else
 * (somebody's, and off limits). One read, no storage, and it survives a
 * restart, which is what the FIFO this replaced could not do.
 *
 * @returns "built" | "clear" | "taken" | "unknown"
 */
function centreState(dimension, island, surfaceId, fillerId) {
  const at = { x: island.x, y: island.y, z: island.z };
  try {
    if (!dimension.isChunkLoaded(at)) return "unknown";
    const block = dimension.getBlock(at);
    if (!block) return "unknown";
    if (block.typeId === "minecraft:air") return "clear";
    if (block.typeId === surfaceId || block.typeId === fillerId) return "built";
    return "taken";
  } catch {
    return "unknown";
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

    const state = centreState(dimension, island, surfaceId, fillerId);
    if (state === "unknown") return;      // try again when it is loaded
    if (state !== "clear") {
      settled.add(island.key);
      return;
    }

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
      if (++checked % 96 === 0) yield;
    }
    if (!clear) {
      settled.add(island.key);
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
      if (++placed % 96 === 0) yield;
    }

    yield* dress(dimension, island, biome, cells, rng);
    settled.add(island.key);
  } catch (error) {
    console.warn(`[End Everlasting] sky island ${island.key} failed: ${error}`);
  } finally {
    building.delete(island.key);
  }
}

/**
 * Everything that turns a lump of rock into somewhere.
 *
 * Trees first, because they need the most headroom and the most room around
 * them; then flora in what is left; then whatever the region hangs off the
 * underside, which is what stops an island edge simply stopping.
 */
function* dress(dimension, island, biome, cells, rng) {
  const surfaces = cells.filter((cell) => cell.surface);

  // Trees. An island wide enough to stand a tree on gets one or two, planted
  // in from the rim so the canopy is over the island rather than over the void.
  const species = biome.tree && SPECIES[biome.tree];
  if (species && island.radius >= 5.5) {
    const wanted = island.radius >= 9 ? rng.int(1, 3) : 1;
    const inner = surfaces.filter((cell) => cell.flat < island.radius - 2.2);
    for (let i = 0; i < wanted && inner.length > 0; i++) {
      const cell = inner[rng.int(0, inner.length - 1)];
      growTree(
        dimension,
        { x: island.x + cell.dx, y: island.y + cell.dy + 1, z: island.z + cell.dz },
        species,
        rng
      );
      yield;
    }
  }

  // Ground cover.
  let grown = 0;
  for (const cell of surfaces) {
    if (rng.next() >= (biome.floraChance ?? 0.1) * 1.8) continue;
    const flora = pickFlora(biome, rng);
    const plant = flora && cachedPermutation(flora.id);
    if (!plant) continue;
    const height = flora.pillar ? rng.int(1, flora.pillar) : 1;
    for (let up = 1; up <= height; up++) {
      try {
        const block = dimension.getBlock({
          x: island.x + cell.dx,
          y: island.y + cell.dy + up,
          z: island.z + cell.dz,
        });
        if (!block || block.typeId !== "minecraft:air") break;
        block.setPermutation(plant);
      } catch {
        break;
      }
    }
    if (++grown % 24 === 0) yield;
  }

  // The underside. Hung from the rim, where the island is thin, so the growth
  // reaches down into open air instead of starting inside the rock.
  const hanging = biome.hanging && cachedPermutation(biome.hanging);
  if (!hanging) return;
  let hung = 0;
  for (const cell of cells) {
    if (!cell.surface) continue;
    if (cell.flat < island.radius * 0.35) continue;
    if (!rng.chance(0.34)) continue;
    const x = island.x + cell.dx;
    const z = island.z + cell.dz;
    const floor = bottomOf(dimension, island, x, z);
    if (floor === undefined) continue;
    const length = rng.int(2, 7);
    for (let down = 1; down <= length; down++) {
      try {
        const block = dimension.getBlock({ x, y: floor - down, z });
        if (!block || block.typeId !== "minecraft:air") break;
        block.setPermutation(hanging);
      } catch {
        break;
      }
    }
    if (++hung % 16 === 0) yield;
  }
}

/** The lowest solid block of this island's column, or undefined. */
function bottomOf(dimension, island, x, z) {
  const depth = Math.ceil(island.radius) + 4;
  let solid;
  for (let y = island.y + 2; y >= island.y - depth; y--) {
    try {
      const block = dimension.getBlock({ x, y, z });
      if (!block) return undefined;
      if (block.typeId === "minecraft:air") {
        if (solid !== undefined) return solid;
        continue;
      }
      solid = y;
    } catch {
      return undefined;
    }
  }
  return solid;
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

/**
 * The highest block this dimension will accept, resolved once.
 *
 * The top tier sits close to the End's ceiling, and a `getBlock` above it
 * throws rather than returning nothing - so the ceiling is read from the
 * dimension instead of assumed, and an island that would not fit under it is
 * never sited in the first place.
 */
let ceiling;
function ceilingOf(dimension) {
  if (ceiling === undefined) {
    ceiling = 255;
    try {
      const range = dimension.heightRange;
      if (typeof range?.max === "number") ceiling = range.max;
    } catch {
      // Older runtime without heightRange; the default is the End's own.
    }
  }
  return ceiling;
}

function scan() {
  let dimension;
  try {
    dimension = world.getDimension(END_DIMENSION);
  } catch {
    return;
  }
  const roof = ceilingOf(dimension);

  for (const player of world.getAllPlayers()) {
    if (player.dimension.id !== END_DIMENSION) continue;
    if (building.size >= MAX_CONCURRENT) return;
    const { x, z } = player.location;

    // Nearest first, so the sky fills in around the player rather than at the
    // edge of their render distance.
    const candidates = islandsNear(x, z, 3)
      .filter((island) => !building.has(island.key) && !settled.has(island.key))
      .filter((island) => island.y + Math.ceil(island.radius) + 3 <= roof)
      .map((island) => ({ island, distance: Math.hypot(island.x - x, island.z - z) }))
      .filter((entry) => entry.distance <= BUILD_RADIUS)
      .sort((a, b) => a.distance - b.distance);

    let started = 0;
    for (const { island } of candidates) {
      if (started >= BUILDS_PER_SCAN || building.size >= MAX_CONCURRENT) break;
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
