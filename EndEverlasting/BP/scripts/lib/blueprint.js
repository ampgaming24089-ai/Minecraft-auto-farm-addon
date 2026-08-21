/**
 * Blueprint authoring and placement.
 *
 * A structure is authored once in local space (+x right, +y up, +z forward)
 * as a flat list of placements, then rotated onto one of four facings and
 * written into the world by a generator that yields, so a large build spreads
 * over many ticks instead of tripping the server watchdog.
 */

import { BlockPermutation } from "@minecraft/server";
import { rotate } from "./vec.js";

/** @typedef {{x:number,y:number,z:number,id:string,states?:Record<string,unknown>}} Placement */

const permutations = new Map();

function permutationFor(id, states) {
  const key = states ? `${id}|${JSON.stringify(states)}` : id;
  let permutation = permutations.get(key);
  if (permutation === undefined) {
    permutation = BlockPermutation.resolve(id, states);
    permutations.set(key, permutation);
  }
  return permutation;
}

/** Rectangular fill, inclusive of both corners. */
export function box(from, to, id, states) {
  const out = [];
  const [x1, y1, z1] = from;
  const [x2, y2, z2] = to;
  for (let x = Math.min(x1, x2); x <= Math.max(x1, x2); x++) {
    for (let y = Math.min(y1, y2); y <= Math.max(y1, y2); y++) {
      for (let z = Math.min(z1, z2); z <= Math.max(z1, z2); z++) {
        out.push({ x, y, z, id, states });
      }
    }
  }
  return out;
}

/** Hollow shell of a box - walls, floor and ceiling, no interior. */
export function shell(from, to, id, states) {
  const [x1, y1, z1] = from;
  const [x2, y2, z2] = to;
  const minX = Math.min(x1, x2), maxX = Math.max(x1, x2);
  const minY = Math.min(y1, y2), maxY = Math.max(y1, y2);
  const minZ = Math.min(z1, z2), maxZ = Math.max(z1, z2);
  const out = [];
  for (let x = minX; x <= maxX; x++) {
    for (let y = minY; y <= maxY; y++) {
      for (let z = minZ; z <= maxZ; z++) {
        const onEdge =
          x === minX || x === maxX || y === minY || y === maxY || z === minZ || z === maxZ;
        if (onEdge) out.push({ x, y, z, id, states });
      }
    }
  }
  return out;
}

/** Single placement, returned as an array so it composes inside merge(). */
export function at(x, y, z, id, states) {
  return [{ x, y, z, id, states }];
}

/** Solid sphere/ellipsoid, useful for crystal blobs and island caps. */
export function blob(cx, cy, cz, radius, id, states, squash = 1) {
  const out = [];
  const r = Math.ceil(radius);
  for (let x = -r; x <= r; x++) {
    for (let y = -r; y <= r; y++) {
      for (let z = -r; z <= r; z++) {
        const dy = y / squash;
        if (x * x + dy * dy + z * z <= radius * radius) {
          out.push({ x: cx + x, y: cy + y, z: cz + z, id, states });
        }
      }
    }
  }
  return out;
}

/**
 * Merge placement lists; later entries win at the same coordinate. Callers lay
 * down bulk shapes first and then punch doorways and detail through them.
 */
export function merge(...lists) {
  const byCoordinate = new Map();
  for (const list of lists) {
    for (const placement of list) {
      byCoordinate.set(`${placement.x},${placement.y},${placement.z}`, placement);
    }
  }
  return [...byCoordinate.values()];
}

/** Blocks that mean "somebody lives here" - never build over these. */
const PLAYER_MARKERS = [
  "chest", "barrel", "shulker", "furnace", "smoker", "blast_furnace", "crafting",
  "bed", "torch", "lantern", "sign", "door", "anvil", "enchant", "brewing",
  "hopper", "dispenser", "dropper", "piston", "rail", "beacon", "respawn_anchor",
  "spawner", "banner", "item_frame", "lectern", "campfire", "loom", "grindstone",
];

function looksPlayerBuilt(typeId) {
  if (typeId.startsWith("voidbound:")) return false;
  const bare = typeId.replace("minecraft:", "");
  return PLAYER_MARKERS.some((marker) => bare.includes(marker));
}

/**
 * Sample the footprint before building. Generation is meant to feel like it
 * was always there, which it will not if it eats somebody's base, so a site
 * that shows signs of habitation is abandoned rather than overwritten.
 */
export function siteIsClear(dimension, origin, radius = 10, height = 14) {
  for (let x = -radius; x <= radius; x += 3) {
    for (let z = -radius; z <= radius; z += 3) {
      for (let y = -3; y <= height; y += 3) {
        // Reading typeId is what throws on an unloaded chunk, not getBlock, so
        // the whole read has to sit inside the guard.
        try {
          const block = dimension.getBlock({
            x: origin.x + x,
            y: origin.y + y,
            z: origin.z + z,
          });
          if (!block) return false;
          if (looksPlayerBuilt(block.typeId)) return false;
        } catch {
          return false; // Unloaded chunk - try again on a later pass.
        }
      }
    }
  }
  return true;
}

/**
 * Write a blueprint into the world.
 *
 * Yields every `throttle` blocks so the caller can drive it with
 * system.runJob. Placements that land in an unloaded chunk are skipped rather
 * than aborting the build - the structure's own chunk is loaded by definition,
 * and edges can trail off the loaded area.
 */
export function* place(dimension, origin, placements, facing, throttle = 128) {
  let written = 0;
  for (const placement of placements) {
    const offset = rotate(placement, facing);
    const target = {
      x: origin.x + offset.x,
      y: origin.y + offset.y,
      z: origin.z + offset.z,
    };
    try {
      const block = dimension.getBlock(target);
      if (block) block.setPermutation(permutationFor(placement.id, placement.states));
    } catch {
      // Outside the world height range or in an unloaded chunk.
    }
    written += 1;
    if (written % throttle === 0) yield;
  }
}

/** Stock a container that a blueprint has already placed. */
export function fillContainer(dimension, location, items) {
  try {
    const block = dimension.getBlock(location);
    const inventory = block?.getComponent("minecraft:inventory");
    if (!inventory) return false;
    for (const { slot, stack } of items) inventory.container.setItem(slot, stack);
    return true;
  } catch {
    return false;
  }
}
