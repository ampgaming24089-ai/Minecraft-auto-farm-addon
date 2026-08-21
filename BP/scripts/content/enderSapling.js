/**
 * Ender saplings, and the trees they become.
 *
 * Bedrock's random-tick plumbing for custom blocks is a moving target, so
 * growth is tracked in script instead: a placed sapling is written into a
 * world dynamic property with the tick it went in, and a slow pass grows the
 * ones whose time has come and whose chunk is loaded. Bone meal skips the
 * wait, as it does for every other sapling in the game.
 *
 * The tree it grows is authored here rather than reusing the worldgen feature,
 * because a feature cannot be invoked from script - and because a planted tree
 * wants to be a little smaller than a wild one, so a grove a player builds
 * does not swallow whatever they built it next to.
 */

import { BlockPermutation, EquipmentSlot, system, world } from "@minecraft/server";
import { Rng } from "../lib/rng.js";
import { END_DIMENSION } from "../world/generator.js";

const SAPLING = "voidbound:ender_sapling";
const LOG = "voidbound:ender_log";
const LEAVES = "voidbound:ender_leaves";
const BUSH = "voidbound:ender_bush";

const PENDING_KEY = "voidbound.saplings";

/** How often the growth pass runs, and how long a sapling waits. */
const SWEEP_INTERVAL = 200;
const GROW_TICKS = 1200;

/** Beyond this the list is doing no useful work, so the oldest drops off. */
const MAX_PENDING = 64;

/** What a sapling may grow through - anything else blocks the trunk. */
const PASSABLE = new Set([
  "minecraft:air",
  SAPLING,
  LEAVES,
  BUSH,
  "voidbound:voidbloom",
]);

function readPending() {
  try {
    const raw = world.getDynamicProperty(PENDING_KEY);
    if (typeof raw !== "string" || raw.length === 0) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writePending(list) {
  try {
    world.setDynamicProperty(PENDING_KEY, JSON.stringify(list));
  } catch {
    // Over budget or shutting down; the sapling simply stays a sapling.
  }
}

function remember(location) {
  const list = readPending();
  const x = Math.floor(location.x);
  const y = Math.floor(location.y);
  const z = Math.floor(location.z);
  if (list.some((entry) => entry.x === x && entry.y === y && entry.z === z)) return;
  list.push({ x, y, z, t: system.currentTick });
  while (list.length > MAX_PENDING) list.shift();
  writePending(list);
}

function forget(location) {
  const x = Math.floor(location.x);
  const y = Math.floor(location.y);
  const z = Math.floor(location.z);
  const list = readPending();
  const kept = list.filter((entry) => !(entry.x === x && entry.y === y && entry.z === z));
  if (kept.length !== list.length) writePending(kept);
}

function setBlock(dimension, x, y, z, id) {
  try {
    const block = dimension.getBlock({ x, y, z });
    if (!block) return false;
    if (!PASSABLE.has(block.typeId)) return false;
    block.setPermutation(BlockPermutation.resolve(id));
    return true;
  } catch {
    return false;
  }
}

function isPassable(dimension, x, y, z) {
  try {
    const block = dimension.getBlock({ x, y, z });
    if (!block) return false;
    return PASSABLE.has(block.typeId);
  } catch {
    return false;
  }
}

/**
 * Grow one tree from a base block.
 *
 * Returns false when the spot cannot hold a tree, so the caller can leave the
 * sapling in place rather than deleting it into nothing.
 */
export function growTree(dimension, base, rng) {
  const height = rng.int(5, 8);

  // Headroom first. A tree that grows into a ceiling looks like a bug.
  for (let dy = 1; dy <= height; dy++) {
    if (!isPassable(dimension, base.x, base.y + dy, base.z)) return false;
  }

  // Trunk, with a single lean so a grove is not a row of posts.
  const leanAt = rng.int(2, Math.max(2, height - 2));
  const leanX = rng.chance(0.5) ? (rng.chance(0.5) ? 1 : -1) : 0;
  const leanZ = leanX === 0 ? (rng.chance(0.5) ? 1 : -1) : 0;

  let tipX = base.x;
  let tipZ = base.z;
  for (let dy = 0; dy < height; dy++) {
    if (dy === leanAt) {
      // Bridge the step, or the trunk breaks into a floating diagonal.
      setBlock(dimension, tipX, base.y + dy, tipZ, LOG);
      tipX += leanX;
      tipZ += leanZ;
    }
    setBlock(dimension, tipX, base.y + dy, tipZ, LOG);
  }

  // Canopy: three stacked discs, narrowing upwards, thinned at the corners.
  const top = base.y + height;
  const discs = [
    { dy: -1, radius: 2.6 },
    { dy: 0, radius: 2.2 },
    { dy: 1, radius: 1.4 },
  ];
  for (const disc of discs) {
    const r = Math.ceil(disc.radius);
    for (let dx = -r; dx <= r; dx++) {
      for (let dz = -r; dz <= r; dz++) {
        const distance = Math.hypot(dx, dz);
        if (distance > disc.radius) continue;
        // Corners drop out at random so the canopy is not a cylinder.
        if (distance > disc.radius - 0.8 && rng.chance(0.45)) continue;
        setBlock(dimension, tipX + dx, top + disc.dy, tipZ + dz, LEAVES);
      }
    }
  }
  setBlock(dimension, tipX, top + 2, tipZ, LEAVES);

  try {
    dimension.spawnParticle("voidbound:grove_spores", {
      x: tipX + 0.5,
      y: top,
      z: tipZ + 0.5,
    });
  } catch {
    // Decoration only.
  }
  return true;
}

function tryGrow(dimension, entry, rng) {
  try {
    if (!dimension.isChunkLoaded({ x: entry.x, y: entry.y, z: entry.z })) return false;
    const block = dimension.getBlock({ x: entry.x, y: entry.y, z: entry.z });
    if (!block) return false;
    // Broken or replaced since it was planted: drop it from the list.
    if (block.typeId !== SAPLING) return true;
    return growTree(dimension, { x: entry.x, y: entry.y, z: entry.z }, rng);
  } catch {
    return false;
  }
}

function sweep() {
  const list = readPending();
  if (list.length === 0) return;

  let dimension;
  try {
    dimension = world.getDimension(END_DIMENSION);
  } catch {
    return;
  }

  const now = system.currentTick;
  const kept = [];
  let changed = false;
  for (const entry of list) {
    if (now - entry.t < GROW_TICKS) {
      kept.push(entry);
      continue;
    }
    const rng = new Rng(((entry.x * 73856093) ^ (entry.z * 19349663) ^ now) >>> 0);
    if (tryGrow(dimension, entry, rng)) {
      changed = true;
      continue; // Grown, or gone - either way it leaves the list.
    }
    // Blocked by something overhead. Reset the clock and look again later.
    kept.push({ ...entry, t: now });
    changed = true;
  }
  if (changed || kept.length !== list.length) writePending(kept);
}

export function startEnderSapling() {
  system.runInterval(sweep, SWEEP_INTERVAL);

  world.afterEvents.playerPlaceBlock.subscribe((event) => {
    if (event.block?.typeId !== SAPLING) return;
    remember(event.block.location);
  });

  world.afterEvents.playerBreakBlock.subscribe((event) => {
    if (event.brokenBlockPermutation?.type?.id !== SAPLING) return;
    forget(event.block.location);
  });

  // Bone meal, as it works on every other sapling in the game.
  world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
    if (event.block?.typeId !== SAPLING) return;
    if (event.itemStack?.typeId !== "minecraft:bone_meal") return;
    event.cancel = true;

    const player = event.player;
    const location = event.block.location;
    const dimension = event.block.dimension;

    system.run(() => {
      const rng = new Rng(((location.x * 73856093) ^ (location.z * 19349663) ^ system.currentTick) >>> 0);
      if (!growTree(dimension, location, rng)) {
        try {
          player?.onScreenDisplay?.setActionBar("§7There is no room for it to grow.");
        } catch {
          // Cosmetic.
        }
        return;
      }
      forget(location);
      if (!player?.isValid) return;
      // The enum has been spelled both ways across versions, so compare loosely.
      let creative = false;
      try {
        creative = String(player.getGameMode()).toLowerCase() === "creative";
      } catch {
        creative = false;
      }
      if (creative) return;
      try {
        const equipment = player.getComponent("minecraft:equippable");
        const held = equipment?.getEquipment(EquipmentSlot.Mainhand);
        if (held && held.amount > 1) {
          held.amount -= 1;
          equipment.setEquipment(EquipmentSlot.Mainhand, held);
        } else if (held) {
          equipment.setEquipment(EquipmentSlot.Mainhand, undefined);
        }
      } catch {
        // Could not spend it; growing a tree free is a small mercy.
      }
    });
  });
}
