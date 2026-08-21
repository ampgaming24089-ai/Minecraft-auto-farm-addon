/**
 * Saplings, and the trees they become.
 *
 * Bedrock's random-tick plumbing for custom blocks is a moving target, so
 * growth is tracked in script instead: a placed sapling is written into a
 * world dynamic property with the tick it went in, and a slow pass grows the
 * ones whose time has come and whose chunk is loaded. Bone meal skips the
 * wait, as it does for every other sapling in the game.
 *
 * There are seven species now, one per region, and every one of them is
 * handled here: the sapling block a player placed identifies its species, and
 * the shared table in `lib/tree.js` says what that species grows into. That
 * table is the same one the painter and the sky islands build wild trees from,
 * so a Bonewood you plant is a Bonewood you would have found.
 */

import { EquipmentSlot, system, world } from "@minecraft/server";
import { Rng } from "../lib/rng.js";
import { BY_SAPLING, growTree } from "../lib/tree.js";
import { END_DIMENSION } from "../world/generator.js";

const PENDING_KEY = "voidbound.saplings";

/** How often the growth pass runs, and how long a sapling waits. */
const SWEEP_INTERVAL = 200;
const GROW_TICKS = 1200;

/** Beyond this the list is doing no useful work, so the oldest drops off. */
const MAX_PENDING = 96;

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

function remember(location, species) {
  const list = readPending();
  const x = Math.floor(location.x);
  const y = Math.floor(location.y);
  const z = Math.floor(location.z);
  if (list.some((entry) => entry.x === x && entry.y === y && entry.z === z)) return;
  list.push({ x, y, z, k: species.key, t: system.currentTick });
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

function speciesAt(dimension, location) {
  try {
    const block = dimension.getBlock(location);
    return block ? BY_SAPLING[block.typeId] : undefined;
  } catch {
    return undefined;
  }
}

/** Grow the tree, and mark the moment with the region's own particle. */
function grow(dimension, location, species, rng) {
  if (!growTree(dimension, location, species, rng)) return false;
  try {
    dimension.spawnParticle("voidbound:grove_spores", {
      x: location.x + 0.5,
      y: location.y + 2,
      z: location.z + 0.5,
    });
  } catch {
    // Decoration only.
  }
  return true;
}

function tryGrow(dimension, entry, rng) {
  try {
    const location = { x: entry.x, y: entry.y, z: entry.z };
    if (!dimension.isChunkLoaded(location)) return false;
    const species = speciesAt(dimension, location);
    // Broken or replaced since it was planted: drop it from the list.
    if (!species) return true;
    return grow(dimension, location, species, rng);
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

function spendOne(player) {
  let creative = false;
  try {
    // The enum has been spelled both ways across versions, so compare loosely.
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
}

export function startSaplings() {
  system.runInterval(sweep, SWEEP_INTERVAL);

  world.afterEvents.playerPlaceBlock.subscribe((event) => {
    const species = BY_SAPLING[event.block?.typeId];
    if (!species) return;
    remember(event.block.location, species);
  });

  world.afterEvents.playerBreakBlock.subscribe((event) => {
    const broken = event.brokenBlockPermutation?.type?.id;
    if (!broken || !BY_SAPLING[broken]) return;
    forget(event.block.location);
  });

  // Bone meal, as it works on every other sapling in the game.
  world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
    const species = BY_SAPLING[event.block?.typeId];
    if (!species) return;
    if (event.itemStack?.typeId !== "minecraft:bone_meal") return;
    event.cancel = true;

    const player = event.player;
    const location = event.block.location;
    const dimension = event.block.dimension;

    system.run(() => {
      const seed = ((location.x * 73856093) ^ (location.z * 19349663)
                    ^ system.currentTick) >>> 0;
      if (!grow(dimension, location, species, new Rng(seed))) {
        try {
          player?.onScreenDisplay?.setActionBar("§7There is no room for it to grow.");
        } catch {
          // Cosmetic.
        }
        return;
      }
      forget(location);
      if (player?.isValid) spendOne(player);
    });
  });
}
