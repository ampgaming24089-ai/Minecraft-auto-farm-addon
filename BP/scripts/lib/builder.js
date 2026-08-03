import { BlockPermutation, ItemStack } from "@minecraft/server";
import { toWorld } from "./geometry.js";

/**
 * A "placement" is one block to set, authored in local space.
 * @typedef {{x:number,y:number,z:number, id:string, states?:Record<string,any>}} Placement
 */

/**
 * A "spawn" is one entity to spawn, authored in local space.
 * @typedef {{x:number,y:number,z:number, typeId:string}} SpawnPoint
 */

const permutationCache = new Map();

/** Cached BlockPermutation.resolve to avoid re-resolving identical states every call. */
function resolvePermutation(id, states) {
  const key = id + JSON.stringify(states ?? {});
  let perm = permutationCache.get(key);
  if (!perm) {
    perm = BlockPermutation.resolve(id, states);
    permutationCache.set(key, perm);
  }
  return perm;
}

/**
 * Build a rectangular local-space region of placements filled with one block.
 * @param {[number,number,number]} from
 * @param {[number,number,number]} to (inclusive)
 * @param {string} id
 * @param {Record<string,any>} [states]
 * @param {{hollow?:boolean}} [opts]
 * @returns {Placement[]}
 */
export function box(from, to, id, states, opts = {}) {
  const [x1, y1, z1] = from;
  const [x2, y2, z2] = to;
  const minX = Math.min(x1, x2), maxX = Math.max(x1, x2);
  const minY = Math.min(y1, y2), maxY = Math.max(y1, y2);
  const minZ = Math.min(z1, z2), maxZ = Math.max(z1, z2);
  const out = [];
  for (let x = minX; x <= maxX; x++) {
    for (let y = minY; y <= maxY; y++) {
      for (let z = minZ; z <= maxZ; z++) {
        if (opts.hollow) {
          const onShell =
            x === minX || x === maxX || y === minY || y === maxY || z === minZ || z === maxZ;
          if (!onShell) continue;
        }
        out.push({ x, y, z, id, states });
      }
    }
  }
  return out;
}

/** Single-block placement shorthand. Returns a 1-element array so it composes with box() inside merge(). */
export function block(x, y, z, id, states) {
  return [{ x, y, z, id, states }];
}

/**
 * Merge placement lists in order; later entries overwrite earlier ones at the
 * same local coordinate (last write wins), so callers can lay a box() and
 * then punch details/openings into it.
 * @param {Placement[][]} lists
 * @returns {Placement[]}
 */
export function merge(...lists) {
  const map = new Map();
  for (const list of lists) {
    for (const p of list) {
      map.set(`${p.x},${p.y},${p.z}`, p);
    }
  }
  return [...map.values()];
}

/**
 * Generator that places every Placement into the world, rotated/translated
 * from local space into world space, yielding every `throttle` blocks so it
 * can be driven by system.runJob without tripping the watchdog.
 * @param {import("@minecraft/server").Dimension} dimension
 * @param {Vec3} origin
 * @param {Placement[]} placements
 * @param {keyof import("./geometry.js").FACINGS} facing
 * @param {number} [throttle]
 * @param {(done:number,total:number)=>void} [onProgress]
 */
export function* placeAll(dimension, origin, placements, facing, throttle = 60, onProgress) {
  let count = 0;
  for (const p of placements) {
    const world = toWorld(origin, p, facing);
    try {
      const b = dimension.getBlock(world);
      if (b) {
        b.setPermutation(resolvePermutation(p.id, p.states));
      }
    } catch {
      // Unloaded/out-of-bounds chunk edge case — skip rather than abort the whole build.
    }
    count++;
    if (count % throttle === 0) {
      if (onProgress) onProgress(count, placements.length);
      yield;
    }
  }
  if (onProgress) onProgress(placements.length, placements.length);
}

/**
 * A "fill" pre-loads one inventory slot of an already-placed container/fuel
 * block (e.g. coal into a smoker's fuel slot) so auto-cookers etc. work
 * immediately without the player having to supply fuel by hand first.
 * @typedef {{x:number,y:number,z:number, slot:number, itemId:string, amount?:number}} ContainerFill
 */

/**
 * Set inventory slots on already-placed blocks, rotated/translated into
 * world space like placeAll. Must run after placeAll so the target blocks
 * already exist.
 * @param {import("@minecraft/server").Dimension} dimension
 * @param {Vec3} origin
 * @param {ContainerFill[]} fills
 * @param {keyof import("./geometry.js").FACINGS} facing
 */
export function* fillContainers(dimension, origin, fills, facing) {
  for (const f of fills) {
    const world = toWorld(origin, f, facing);
    try {
      const b = dimension.getBlock(world);
      const inv = b?.getComponent("minecraft:inventory");
      if (inv) {
        inv.container.setItem(f.slot, new ItemStack(f.itemId, f.amount ?? 1));
      }
    } catch {
      // Unloaded chunk edge case — skip rather than abort the whole build.
    }
    yield;
  }
}

/**
 * Spawn a list of entities at local-space points, rotated/translated into
 * world space. Spread across ticks like placeAll.
 *
 * An optional `inventory` array on a spawn point ({slot, itemId, amount})
 * fills that entity's own inventory slots right after it spawns — used by
 * the giant crop farm to pre-load a farmer villager's carry slots with junk
 * items so it can never pick harvested crops back up (the real, documented
 * mechanic behind every "single villager + hopper floor" giant farm: a
 * farmer with a full inventory drops what it harvests on the ground instead
 * of holding it).
 * @param {import("@minecraft/server").Dimension} dimension
 * @param {Vec3} origin
 * @param {SpawnPoint[]} spawns
 * @param {keyof import("./geometry.js").FACINGS} facing
 */
export function* spawnAll(dimension, origin, spawns, facing) {
  for (const s of spawns) {
    const world = toWorld(origin, s, facing);
    try {
      const entity = dimension.spawnEntity(s.typeId, { x: world.x + 0.5, y: world.y, z: world.z + 0.5 });
      if (s.inventory && entity) {
        const inv = entity.getComponent("minecraft:inventory");
        if (inv) {
          for (const item of s.inventory) {
            inv.container.setItem(item.slot, new ItemStack(item.itemId, item.amount ?? 1));
          }
        }
      }
    } catch {
      // Best effort — a blocked spawn location shouldn't abort the whole build.
    }
    yield;
  }
}
