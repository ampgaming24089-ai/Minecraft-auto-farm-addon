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
import { TREES } from "../world/trees.js";

const BUSH = "voidbound:ender_bush";

/**
 * Every sapling in the pack, keyed by block id.
 *
 * The original tree is folded in here as one more species rather than kept as
 * a special case, so there is one growth path: a sapling knows its own log,
 * leaves, height range and crown shape, and nothing downstream has to ask
 * which kind of tree this is.
 */
const SPECIES = new Map();
SPECIES.set("voidbound:ender_sapling", {
  log: "voidbound:ender_log",
  leaves: "voidbound:ender_leaves",
  canopy: "dome",
  height: [5, 8],
});
for (const tree of Object.values(TREES)) SPECIES.set(tree.sapling, tree);

const PENDING_KEY = "voidbound.saplings";

/** How often the growth pass runs, and how long a sapling waits. */
const SWEEP_INTERVAL = 200;
const GROW_TICKS = 1200;

/** Beyond this the list is doing no useful work, so the oldest drops off. */
const MAX_PENDING = 64;

/** What a sapling may grow through - anything else blocks the trunk. Every
 *  species' own sapling and leaves are in here, so a tree can grow up through
 *  a neighbour's canopy instead of stopping dead under it. */
const PASSABLE = new Set([
  "minecraft:air",
  BUSH,
  "voidbound:voidbloom",
  ...SPECIES.keys(),
  ...[...SPECIES.values()].map((tree) => tree.leaves),
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
 * The crowns.
 *
 * Colour alone does not distinguish a species - a violet canopy and a green
 * one are the same tree tinted, and from any distance that is exactly what
 * they look like. The silhouette is what tells them apart, so each species
 * names one of these and they are deliberately different shapes rather than
 * different radii of the same shape.
 *
 * Each returns a list of {dy, radius, ragged} discs relative to the trunk top.
 */
const CROWNS = {
  // Rounded, widest in the middle: an ordinary tree.
  dome: () => [
    { dy: -2, radius: 2.2, ragged: 0.35 },
    { dy: -1, radius: 2.8, ragged: 0.45 },
    { dy: 0, radius: 2.4, ragged: 0.45 },
    { dy: 1, radius: 1.5, ragged: 0.3 },
    { dy: 2, radius: 0.8, ragged: 0.0 },
  ],
  // A narrow cone. Tall and thin, so a spire forest reads as a spire forest.
  spire: () => [
    { dy: -4, radius: 2.0, ragged: 0.3 },
    { dy: -3, radius: 1.9, ragged: 0.3 },
    { dy: -2, radius: 1.7, ragged: 0.25 },
    { dy: -1, radius: 1.4, ragged: 0.25 },
    { dy: 0, radius: 1.2, ragged: 0.2 },
    { dy: 1, radius: 0.9, ragged: 0.0 },
    { dy: 2, radius: 0.6, ragged: 0.0 },
  ],
  // A flat plate on a bare trunk - a mushroom, essentially.
  parasol: () => [
    { dy: 0, radius: 3.6, ragged: 0.2 },
    { dy: 1, radius: 2.6, ragged: 0.35 },
  ],
  // Loose blobs hung off the top, with gaps between them.
  cluster: () => [
    { dy: -2, radius: 1.6, ragged: 0.6 },
    { dy: 0, radius: 2.4, ragged: 0.55 },
    { dy: 2, radius: 1.8, ragged: 0.6 },
  ],
  // A crown that hangs down past where the branches are.
  weeping: () => [
    { dy: -4, radius: 1.4, ragged: 0.7 },
    { dy: -3, radius: 2.0, ragged: 0.6 },
    { dy: -2, radius: 2.6, ragged: 0.4 },
    { dy: -1, radius: 3.0, ragged: 0.3 },
    { dy: 0, radius: 2.6, ragged: 0.3 },
    { dy: 1, radius: 1.4, ragged: 0.2 },
  ],
  // Short, wide and gnarled.
  scrub: () => [
    { dy: -1, radius: 3.0, ragged: 0.55 },
    { dy: 0, radius: 3.2, ragged: 0.5 },
    { dy: 1, radius: 1.8, ragged: 0.5 },
  ],
};

/**
 * Grow one tree from a base block.
 *
 * Returns false when the spot cannot hold a tree, so the caller can leave the
 * sapling in place rather than deleting it into nothing.
 */
export function growTree(dimension, base, rng, species) {
  const tree = species ?? SPECIES.get("voidbound:ender_sapling");
  const LOG = tree.log;
  const LEAVES = tree.leaves;
  const height = rng.int(tree.height[0], tree.height[1]);

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

  // Canopy: the species' own crown, laid as discs around the trunk top.
  const top = base.y + height;
  for (const disc of (CROWNS[tree.canopy] ?? CROWNS.dome)()) {
    const r = Math.ceil(disc.radius);
    for (let dx = -r; dx <= r; dx++) {
      for (let dz = -r; dz <= r; dz++) {
        const distance = Math.hypot(dx, dz);
        if (distance > disc.radius) continue;
        // Corners drop out at random so the canopy is not a cylinder.
        if (distance > disc.radius - 0.9 && rng.next() < disc.ragged) continue;
        setBlock(dimension, tipX + dx, top + disc.dy, tipZ + dz, LEAVES);
      }
    }
  }

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
    const species = SPECIES.get(block.typeId);
    if (!species) return true;
    return growTree(dimension, { x: entry.x, y: entry.y, z: entry.z }, rng,
                    species);
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
    if (!SPECIES.has(event.block?.typeId)) return;
    remember(event.block.location);
  });

  world.afterEvents.playerBreakBlock.subscribe((event) => {
    if (!SPECIES.has(event.brokenBlockPermutation?.type?.id)) return;
    forget(event.block.location);
  });

  // Bone meal, as it works on every other sapling in the game.
  world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
    const species = SPECIES.get(event.block?.typeId);
    if (!species) return;
    if (event.itemStack?.typeId !== "minecraft:bone_meal") return;
    event.cancel = true;

    const player = event.player;
    const location = event.block.location;
    const dimension = event.block.dimension;

    system.run(() => {
      const rng = new Rng(((location.x * 73856093) ^ (location.z * 19349663) ^ system.currentTick) >>> 0);
      if (!growTree(dimension, location, rng, species)) {
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
