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

/**
 * How far around a player patches get painted.
 *
 * 56 blocks was well inside render distance, which is exactly why the End
 * looked untouched until you were standing on it: everything past the disc was
 * plain end stone in plain sight. This reaches past what a phone loads on
 * purpose - a column in an unloaded chunk costs one `isChunkLoaded` and comes
 * back on a later scan, so asking for more than is loaded is nearly free and
 * paints the moment the chunk arrives.
 */
const PAINT_RADIUS = 128;

const SCAN_INTERVAL_TICKS = 10;

/**
 * Patches queued per player per scan, and the ceiling on jobs at once.
 *
 * The old three-per-two-seconds took a hundred seconds to fill even the small
 * disc, and that was the throttle, not the engine. `system.runJob` already
 * self-throttles - it spends the frame's spare time and no more - so the job
 * budget is the right limiter and this only has to stop the queue growing
 * without bound.
 */
const PATCHES_PER_SCAN = 10;
const MAX_IN_FLIGHT = 20;

/**
 * How many columns to do between yields.
 *
 * One yield per column meant 64 job slices to paint one patch, and the slice
 * overhead dwarfed the six block writes inside it.
 */
const SURFACE_YIELD_EVERY = 8;
const DETAIL_YIELD_EVERY = 4;

/**
 * Painted-patch memory.
 *
 * Repainting is idempotent - the biome is a pure function of position and each
 * column's RNG is seeded from its own coordinates, so a second visit makes the
 * same decisions, and flora only ever goes into air that is still air. So this
 * is an optimisation, not a correctness guard, and it is safe to hold far more
 * in memory than is written to disk.
 *
 * The written half is capped by *bytes*, not by count. A dynamic property
 * string has a hard ceiling, and the old 4000 keys of `x.z` ran past it - the
 * write threw, the catch logged, and nothing was ever persisted at all.
 */
const PROPERTY = "voidbound.painted";
const MAX_PATCHES = 50000;
const PERSIST_BUDGET_BYTES = 12000;

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

/**
 * What actually gets written to disk: the most recent keys, newest last.
 *
 * Kept as its own short list rather than derived from the full set. Reversing
 * and re-joining fifty thousand keys once a second to write twelve kilobytes
 * of them is the most expensive thing the painter would do, and all but the
 * tail of that work is thrown away.
 */
const recent = [];
let recentBytes = 0;

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
  // Seed the write-back list from what was on disk, so the first save after a
  // reload does not drop everything the last session painted.
  if (recent.length === 0 && raw) {
    for (const key of cache) {
      recent.push(key);
      recentBytes += key.length + 1;
    }
  }
  return cache;
}

/** Rebuilding the string on every patch is a string build per patch. */
let dirty = 0;
const PERSIST_EVERY = 24;

function persist(force) {
  if (!force && ++dirty < PERSIST_EVERY) return;
  dirty = 0;
  try {
    world.setDynamicProperty(PROPERTY, recent.join(","));
  } catch (error) {
    console.warn(`[Endrealm] could not persist painted patches: ${error}`);
  }
}

function markPainted(key) {
  const painted = load();
  if (painted.has(key)) return;
  painted.add(key);
  if (painted.size > MAX_PATCHES) {
    // Sets keep insertion order, so the first key out is the oldest.
    painted.delete(painted.values().next().value);
  }

  recent.push(key);
  recentBytes += key.length + 1;
  // Trim from the front: the ground a player is standing on is worth keeping,
  // wherever they were an hour ago is not.
  while (recentBytes > PERSIST_BUDGET_BYTES && recent.length > 1) {
    recentBytes -= recent.shift().length + 1;
  }
  persist(false);
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
 * Paint one patch, surface first.
 *
 * Two passes over the same columns, and the split is the whole point. The
 * first lays nothing but the surface block, so the ground under the player
 * changes colour as fast as the engine will let it. The second goes back over
 * the columns that took paint and does the slow half - the filler underneath,
 * the growth hanging off the island's belly, the trees, the flora.
 *
 * Done in one pass, every one of those was in front of the next column's
 * colour change, and a patch only *looked* painted once all of it was done.
 * Split, the biome arrives immediately and fills in behind itself.
 *
 * A generator, so the caller can hand it to runJob. Every block read is
 * guarded: block handles are lazy, and reading typeId on one from an unloaded
 * chunk throws.
 */
function* paintPatch(dimension, patchX, patchZ, report) {
  const originX = patchX * PATCH;
  const originZ = patchZ * PATCH;

  // --- pass one: the colour ------------------------------------------------
  const painted = [];
  let steps = 0;
  for (let dx = 0; dx < PATCH; dx++) {
    for (let dz = 0; dz < PATCH; dz++) {
      if (++steps % SURFACE_YIELD_EVERY === 0) yield;
      const x = originX + dx;
      const z = originZ + dz;
      const biome = biomeAt(x, z);
      // The Barrens paint nothing, which is what keeps them the Barrens.
      if (!biome.surface) continue;

      let top;
      try {
        if (!dimension.isChunkLoaded({ x, y: GROUND_MIN_Y, z })) {
          // Not painted, and not paintable *yet*. Say so, or the patch gets
          // marked done and this column stays unpainted for ever.
          report.complete = false;
          continue;
        }
        top = dimension.getTopmostBlock({ x, z });
        if (!top) {
          report.complete = false;
          continue;
        }
        if (top.y < GROUND_MIN_Y || top.y > GROUND_MAX_Y) continue;
        if (!NATURAL.has(top.typeId)) {
          // Somebody's block, or already painted. Either way, done with it.
          continue;
        }
        const surface = cachedPermutation(biome.surface);
        if (surface) top.setPermutation(surface);
      } catch {
        report.complete = false;
        continue;
      }
      painted.push({ x, z, y: top.y, biome });
    }
  }

  // --- pass two: everything that hangs off it ------------------------------
  steps = 0;
  for (const column of painted) {
    if (++steps % DETAIL_YIELD_EVERY === 0) yield;
    const { x, z, biome } = column;
    const top = { y: column.y };

    // Per-column RNG, so the same column always grows the same thing even
    // if its patch is evicted from memory and painted again later.
    const rng = new Rng(hash(worldSeedHash(), 0x9e11, x, z));

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
  }
}

/**
 * The offsets of a disc of patches, nearest first.
 *
 * Built once. It is the same ring of offsets around every player at every
 * scan, and at this radius rebuilding and re-sorting it four times a second is
 * a thousand `hypot` calls and a sort, per player, for an answer that never
 * changes.
 */
const DISC = (() => {
  const reach = Math.ceil(PAINT_RADIUS / PATCH);
  const offsets = [];
  for (let dx = -reach; dx <= reach; dx++) {
    for (let dz = -reach; dz <= reach; dz++) {
      const distance = Math.hypot(dx, dz);
      if (distance <= reach) offsets.push({ dx, dz, distance });
    }
  }
  offsets.sort((a, b) => a.distance - b.distance);
  return offsets;
})();

/** Queue the nearest unpainted patches around one player. */
function scanFor(player) {
  const { x, z } = player.location;
  const painted = load();
  const centreX = Math.floor(x / PATCH);
  const centreZ = Math.floor(z / PATCH);

  // Walk the disc nearest-first and stop at the first full handful, so the
  // ground under the player changes before the horizon does - and so the scan
  // costs a few dozen tests rather than the whole disc.
  //
  // The Barrens test is deliberately down here rather than in a filter over
  // every candidate: `biomeAt` is two noise samples, and running it across
  // eight hundred patches four times a second is a per-tick spike in an
  // interval the engine does not budget. Down here it runs a dozen times.
  const queued = [];
  for (const offset of DISC) {
    if (queued.length >= PATCHES_PER_SCAN) break;
    const patchX = centreX + offset.dx;
    const patchZ = centreZ + offset.dz;
    const key = `${patchX}.${patchZ}`;
    if (painted.has(key) || inFlight.has(key)) continue;
    // Patches whose middle is Barrens have nothing to do, and marking them
    // painted would spend the memory on empty work.
    if (!biomeAt(patchX * PATCH + PATCH / 2, patchZ * PATCH + PATCH / 2).surface) {
      continue;
    }
    queued.push({ key, patchX, patchZ, distance: offset.distance });
  }
  return queued;
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
      // The engine budgets runJob itself, but nothing budgets how many jobs
      // are *outstanding*. Without this the queue grows every scan while a
      // player runs through unpainted ground and never drains.
      if (inFlight.size >= MAX_IN_FLIGHT) break;
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
    console.warn(`[Endrealm] painting ${patch.key} failed: ${error}`);
  } finally {
    inFlight.delete(patch.key);
  }
}

export function startPainter() {
  system.runInterval(scan, SCAN_INTERVAL_TICKS);
  // Anything still unwritten when the world closes would be repainted on the
  // next visit - harmless, but free to avoid.
  try {
    world.beforeEvents.playerLeave.subscribe(() => persist(true));
  } catch {
    // Older runtimes without the event: the periodic write still covers it.
  }
}

/** The tuning, exported so the smoke test can hold it to account. */
export const TUNING = {
  PATCH,
  PAINT_RADIUS,
  SCAN_INTERVAL_TICKS,
  PATCHES_PER_SCAN,
  MAX_IN_FLIGHT,
  PERSIST_BUDGET_BYTES,
};
