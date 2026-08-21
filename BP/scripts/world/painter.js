/**
 * Painting the biomes onto the ground.
 *
 * The region system decides where a biome is; this is what makes it visible.
 * As a player moves, the patches of ground around them that have not been
 * painted yet get repainted in their region's palette - surface block, the
 * two layers under it, and whatever flora that biome grows.
 *
 * This is the one system in the pack that rewrites terrain a player might
 * care about, so it is deliberately timid:
 *
 *   - Only *natural* End ground is ever replaced. A block that is not in
 *     NATURAL is left exactly as it is, which covers every player build, every
 *     structure this pack places, end cities, the obsidian pillars, and the
 *     gateway.
 *   - Flora is only ever placed into air, directly on top of ground the
 *     painter itself just laid down.
 *   - The Voidfall Barrens have no surface block at all, so a quarter of the
 *     End is never touched by any of this.
 *   - Every patch is painted at most once, tracked in a bounded FIFO, so
 *     walking back and forth does not re-stamp over anything.
 *
 * Work is done in `system.runJob`, which yields between columns, because a
 * first arrival in a region is a few thousand block reads and doing that in
 * one tick is how you trip the watchdog.
 */

import { BlockPermutation, system, world } from "@minecraft/server";
import { Rng, hash } from "../lib/rng.js";
import { biomeAt } from "./biomes.js";
import { TREES } from "./trees.js";
import { growTree } from "../content/enderSapling.js";
import { END_DIMENSION } from "./generator.js";
import { worldSeedHash } from "./sites.js";

/** Patch size in blocks. Small enough that one job is short, big enough that
 *  the bookkeeping does not dwarf the work. */
const PATCH = 8;

/** How far around a player patches get painted. */
const PAINT_RADIUS = 56;

const SCAN_INTERVAL_TICKS = 40;

/** Patches queued per player per scan, so arriving somewhere new is gradual. */
const PATCHES_PER_SCAN = 3;

/** Painted-patch memory. Bounded: an evicted patch simply repaints the same
 *  way, because the biome and the RNG are both pure functions of the seed. */
const PROPERTY = "voidbound.painted";
const MAX_PATCHES = 4000;

/**
 * The only blocks the painter will ever replace.
 *
 * Every one of these is something *worldgen* placed - end stone and the three
 * variants this pack's features scatter through it. The biome surfaces the
 * painter itself lays down are deliberately absent, and that is what makes a
 * player's build safe: the only way glowspore soil exists in the world is that
 * the painter put it there (in which case the patch is already marked and will
 * not be visited again) or that a player placed it (in which case it must not
 * be touched). Leaving them out costs nothing and closes the gap.
 */
const NATURAL = new Set([
  "minecraft:end_stone",
  "voidbound:shattered_end_stone",
  "voidbound:verdant_end_stone",
  "voidbound:mossy_end_stone",
]);

/** Ground has to be inside this band to count as an island. */
const GROUND_MIN_Y = 4;
const GROUND_MAX_Y = 128;

/** How often a column grows something off its underside, and how far it hangs. */
const UNDERSIDE_CHANCE = 0.34;
const UNDERSIDE_LENGTH = 5;

/** How far down to look for the bottom of an island before giving up. */
const UNDERSIDE_SEARCH = 24;

let cache;
const inFlight = new Set();

function load() {
  if (cache) return cache;
  let raw = "";
  try {
    const stored = world.getDynamicProperty(PROPERTY);
    if (typeof stored === "string") raw = stored;
  } catch {
    raw = "";
  }
  cache = new Set(raw ? raw.split(",") : []);
  return cache;
}

function markPainted(key) {
  const painted = load();
  painted.add(key);
  if (painted.size > MAX_PATCHES) {
    // Sets keep insertion order, so the first key out is the oldest.
    painted.delete(painted.values().next().value);
  }
  try {
    world.setDynamicProperty(PROPERTY, [...painted].join(","));
  } catch (error) {
    console.warn(`[End Everlasting] could not persist painted patches: ${error}`);
  }
}

function permutation(id) {
  try {
    return BlockPermutation.resolve(id);
  } catch {
    return undefined;
  }
}

/** Cache permutations - resolving the same id thousands of times is waste. */
const permutations = new Map();
function cachedPermutation(id) {
  if (!permutations.has(id)) permutations.set(id, permutation(id));
  return permutations.get(id);
}

/**
 * The lowest solid block of the island under this column, or undefined.
 *
 * Walks down from the surface until it finds air with solid ground above it.
 * Bounded, because a column over the void has no bottom and this must not
 * search the whole world to discover that.
 */
function bottomOf(dimension, x, z, fromY) {
  let solid = fromY;
  for (let y = fromY - 1; y >= fromY - UNDERSIDE_SEARCH; y--) {
    let block;
    try {
      block = dimension.getBlock({ x, y, z });
    } catch {
      return undefined;
    }
    if (!block) return undefined;
    if (block.typeId === "minecraft:air") return solid;
    solid = y;
  }
  // Still solid after the whole search: this is a thick column, not an island
  // edge, and hanging growth off the middle of one would float.
  return undefined;
}

/** Weighted pick from a biome's flora list. */
function pickFlora(biome, rng) {
  const total = biome.flora.reduce((sum, entry) => sum + entry.weight, 0);
  if (total <= 0) return undefined;
  let roll = rng.float(0, total);
  for (const entry of biome.flora) {
    roll -= entry.weight;
    if (roll <= 0) return entry;
  }
  return biome.flora[biome.flora.length - 1];
}

/**
 * Paint one patch.
 *
 * A generator, so the caller can hand it to runJob and let it yield between
 * columns. Every block read is guarded: block handles are lazy, and reading
 * typeId on one from an unloaded chunk throws.
 */
function* paintPatch(dimension, patchX, patchZ, report) {
  const originX = patchX * PATCH;
  const originZ = patchZ * PATCH;

  for (let dx = 0; dx < PATCH; dx++) {
    for (let dz = 0; dz < PATCH; dz++) {
      const x = originX + dx;
      const z = originZ + dz;
      const biome = biomeAt(x, z);
      // The Barrens paint nothing, which is what keeps them the Barrens.
      if (!biome.surface) {
        yield;
        continue;
      }

      let top;
      try {
        if (!dimension.isChunkLoaded({ x, y: GROUND_MIN_Y, z })) {
          // Not painted, and not paintable *yet*. Say so, or the patch gets
          // marked done and this column stays unpainted for ever.
          report.complete = false;
          yield;
          continue;
        }
        top = dimension.getTopmostBlock({ x, z });
        if (!top) {
          report.complete = false;
          yield;
          continue;
        }
        if (top.y < GROUND_MIN_Y || top.y > GROUND_MAX_Y) {
          yield;
          continue;
        }
        if (!NATURAL.has(top.typeId)) {
          // Somebody's block, or already painted. Either way, done with it.
          yield;
          continue;
        }
      } catch {
        report.complete = false;
        yield;
        continue;
      }

      // Per-column RNG, so the same column always grows the same thing even
      // if its patch is evicted from memory and painted again later.
      const rng = new Rng(hash(worldSeedHash(), 0x9e11, x, z));

      const surface = cachedPermutation(biome.surface);
      if (surface) {
        try {
          top.setPermutation(surface);
        } catch {
          report.complete = false;
          yield;
          continue;
        }
      }

      // Two layers of filler under the surface, so a cliff face shows the
      // biome rather than a one-block skin over plain end stone.
      const filler = cachedPermutation(biome.filler ?? biome.surface);
      if (filler) {
        for (let depth = 1; depth <= 2; depth++) {
          try {
            const below = dimension.getBlock({ x, y: top.y - depth, z });
            if (below && NATURAL.has(below.typeId)) below.setPermutation(filler);
          } catch {
            break;
          }
        }
      }

      // The underside. An End island stopping dead at its own bottom face is
      // the single biggest tell that it was generated rather than grown, so
      // whatever that biome hangs gets hung from it.
      if (biome.hanging && rng.next() < UNDERSIDE_CHANCE) {
        const growth = cachedPermutation(biome.hanging);
        if (growth) {
          const floor = bottomOf(dimension, x, z, top.y);
          if (floor !== undefined) {
            const length = rng.int(1, UNDERSIDE_LENGTH);
            for (let down = 1; down <= length; down++) {
              try {
                const cell = dimension.getBlock({ x, y: floor - down, z });
                if (!cell || cell.typeId !== "minecraft:air") break;
                cell.setPermutation(growth);
              } catch {
                break;
              }
            }
          }
        }
      }

      // Trees, before the ground cover: a trunk wants the column it is going
      // into to be empty, and a flower placed there first would stop it.
      //
      // Spaced on a lattice rather than rolled per block. A pure per-column
      // roll at this rate puts trunks two apart as often as ten, and a wood
      // where every trunk is touching its neighbour reads as a wall, not a
      // wood.
      if (biome.tree && ((x * 31 + z * 17) & 3) === 0
          && rng.next() < (biome.treeChance ?? 0) * 4) {
        const species = TREES[biome.tree];
        if (species) {
          try {
            growTree(dimension, { x, y: top.y + 1, z }, rng, species);
          } catch {
            // No room, or the chunk went away. The ground is still painted.
          }
        }
      }

      if (rng.next() < (biome.floraChance ?? 0)) {
        const entry = pickFlora(biome, rng);
        const plant = entry && cachedPermutation(entry.id);
        if (plant) {
          const height = entry.pillar ? rng.int(1, entry.pillar) : 1;
          for (let up = 1; up <= height; up++) {
            try {
              const cell = dimension.getBlock({ x, y: top.y + up, z });
              // Air only. Never overwrite anything, not even other flora.
              if (!cell || cell.typeId !== "minecraft:air") break;
              cell.setPermutation(plant);
            } catch {
              break;
            }
          }
        }
      }
      yield;
    }
  }
}

/** Queue the nearest unpainted patches around one player. */
function scanFor(player) {
  const { x, z } = player.location;
  const painted = load();
  const centreX = Math.floor(x / PATCH);
  const centreZ = Math.floor(z / PATCH);
  const reach = Math.ceil(PAINT_RADIUS / PATCH);

  const candidates = [];
  for (let dx = -reach; dx <= reach; dx++) {
    for (let dz = -reach; dz <= reach; dz++) {
      const patchX = centreX + dx;
      const patchZ = centreZ + dz;
      const key = `${patchX}.${patchZ}`;
      if (painted.has(key) || inFlight.has(key)) continue;
      const distance = Math.hypot(dx, dz);
      if (distance > reach) continue;
      // Skip patches whose whole area is Barrens - there is nothing to do and
      // marking them painted would waste the FIFO on empty work.
      if (!biomeAt(patchX * PATCH + PATCH / 2, patchZ * PATCH + PATCH / 2).surface) continue;
      candidates.push({ key, patchX, patchZ, distance });
    }
  }
  // Nearest first, so the ground under the player changes before the horizon.
  candidates.sort((a, b) => a.distance - b.distance);
  return candidates.slice(0, PATCHES_PER_SCAN);
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
    let queued;
    try {
      queued = scanFor(player);
    } catch {
      continue;
    }
    for (const patch of queued) {
      inFlight.add(patch.key);
      try {
        system.runJob(finish(dimension, patch));
      } catch {
        inFlight.delete(patch.key);
      }
    }
  }
}

/**
 * Wrap the paint job so the patch is released however it ends, and marked
 * only if it actually finished.
 *
 * A patch whose chunks were not loaded has not been painted, and marking it
 * done would leave that ground plain for the rest of the world's life. So it
 * stays unmarked and gets picked up again on a later scan, when the player is
 * closer and the chunks are there.
 */
function* finish(dimension, patch) {
  const report = { complete: true };
  try {
    yield* paintPatch(dimension, patch.patchX, patch.patchZ, report);
    if (report.complete) markPainted(patch.key);
  } catch (error) {
    console.warn(`[End Everlasting] painting ${patch.key} failed: ${error}`);
  } finally {
    inFlight.delete(patch.key);
  }
}

export function startPainter() {
  system.runInterval(scan, SCAN_INTERVAL_TICKS);
}
