/**
 * The bloomstalk: the End's crop.
 *
 * Bedrock's growth plumbing for custom blocks has moved between drops, so this
 * takes the same route the saplings do - planted stalks are remembered in a
 * world dynamic property with the tick they went in, and a slow pass advances
 * the ones whose time has come. The block itself only has to describe its four
 * looks and say which one it is showing.
 *
 * Harvesting is where the design is. Breaking a grown stalk gives pods *and*
 * seed and replants itself at stage zero, so a farm keeps producing without
 * being re-sown; breaking an unripe one gives the seed back and nothing else.
 * That is the whole loop, and it means a village crop plot is worth finding
 * even for a player who never trades.
 */

import { BlockPermutation, ItemStack, system, world } from "@minecraft/server";
import { Rng, hash } from "../lib/rng.js";
import { worldSeedHash } from "../world/sites.js";

const CROP = "voidbound:bloomstalk";
const STATE = "voidbound:growth";
const RIPE = 3;

const SEED = "voidbound:bloomstalk_seed";
const POD = "voidbound:bloom_pod";

const PROPERTY = "voidbound.bloomstalks";
const MAX_TRACKED = 256;

/** How often growth is checked, and how long one stage takes. */
const SWEEP_INTERVAL = 200;
const STAGE_TICKS = 900;

let cache;

function load() {
  if (cache) return cache;
  let raw = "";
  try {
    const stored = world.getDynamicProperty(PROPERTY);
    if (typeof stored === "string") raw = stored;
  } catch {
    raw = "";
  }
  cache = raw ? raw.split(";").filter(Boolean).map((entry) => {
    const [x, y, z, t] = entry.split(",").map(Number);
    return { x, y, z, t };
  }) : [];
  return cache;
}

function save(list) {
  cache = list;
  try {
    world.setDynamicProperty(PROPERTY, list.map((e) => `${e.x},${e.y},${e.z},${e.t}`).join(";"));
  } catch {
    // Over budget or shutting down; the stalk simply stops advancing.
  }
}

function track(location) {
  const x = Math.floor(location.x);
  const y = Math.floor(location.y);
  const z = Math.floor(location.z);
  const list = load().filter((e) => !(e.x === x && e.y === y && e.z === z));
  list.push({ x, y, z, t: system.currentTick });
  while (list.length > MAX_TRACKED) list.shift();
  save(list);
}

function untrack(location) {
  const x = Math.floor(location.x);
  const y = Math.floor(location.y);
  const z = Math.floor(location.z);
  const list = load();
  const kept = list.filter((e) => !(e.x === x && e.y === y && e.z === z));
  if (kept.length !== list.length) save(kept);
}

/**
 * Read the growth state off a permutation.
 *
 * `getState` is typed against `BlockStateSuperset`, which lists vanilla states
 * only - a custom state is a perfectly valid argument the type definitions
 * cannot know about, so the cast is the honest way to say so rather than
 * widening anything else.
 *
 * @param {{ getState: (name: string) => unknown } | undefined} permutation
 */
function growthOf(permutation) {
  try {
    const read = /** @type {{ getState: (name: string) => unknown }} */ (permutation);
    const value = read?.getState(STATE);
    return typeof value === "number" ? value : 0;
  } catch {
    return 0;
  }
}

function stageOf(block) {
  try {
    return growthOf(block.permutation);
  } catch {
    return 0;
  }
}

function setStage(block, stage) {
  try {
    block.setPermutation(BlockPermutation.resolve(CROP, { [STATE]: stage }));
    return true;
  } catch {
    return false;
  }
}

/**
 * Drop a harvest at the block, the way breaking any crop does.
 *
 * Deliberately not `/give`: that puts the items straight into some nearby
 * player's inventory, which is a different thing entirely - it ignores who
 * actually broke the block, ignores a full inventory, and gives no item to
 * pick up. A harvest should land on the ground.
 */
function drop(dimension, location, typeId, amount) {
  if (amount <= 0) return;
  try {
    dimension.spawnItem(new ItemStack(typeId, amount), {
      x: location.x + 0.5,
      y: location.y + 0.5,
      z: location.z + 0.5,
    });
  } catch {
    // Unloaded chunk, or the id is gone. The seed from the loot table stands.
  }
}

function sweep() {
  const list = load();
  if (list.length === 0) return;

  const now = system.currentTick;
  const kept = [];
  let changed = false;

  for (const entry of list) {
    let block;
    try {
      const dimension = world.getDimension("minecraft:the_end");
      if (!dimension.isChunkLoaded({ x: entry.x, y: entry.y, z: entry.z })) {
        kept.push(entry);
        continue;
      }
      block = dimension.getBlock({ x: entry.x, y: entry.y, z: entry.z });
    } catch {
      kept.push(entry);
      continue;
    }
    // Gone, or replaced with something else: stop tracking it.
    if (!block || block.typeId !== CROP) {
      changed = true;
      continue;
    }

    const stage = stageOf(block);
    if (stage >= RIPE) {
      changed = true;
      continue; // Ripe stalks need no further attention until harvested.
    }
    if (now - entry.t < STAGE_TICKS) {
      kept.push(entry);
      continue;
    }
    if (setStage(block, stage + 1)) {
      kept.push({ ...entry, t: now });
      changed = true;
    } else {
      kept.push(entry);
    }
  }
  if (changed || kept.length !== list.length) save(kept);
}

export function startBloomstalk() {
  system.runInterval(sweep, SWEEP_INTERVAL);

  world.afterEvents.playerPlaceBlock.subscribe((event) => {
    if (event.block?.typeId !== CROP) return;
    setStage(event.block, 0);
    track(event.block.location);
  });

  // Harvest. A ripe stalk pays out and replants itself; an unripe one just
  // gives the seed back, so pulling a crop early is a mistake and not a loss.
  world.afterEvents.playerBreakBlock.subscribe((event) => {
    const broken = event.brokenBlockPermutation;
    if (broken?.type?.id !== CROP) return;

    const location = event.block.location;
    untrack(location);

    const stage = growthOf(broken);
    if (stage < RIPE) return; // The loot table already returned the seed.

    const rng = new Rng(hash(worldSeedHash(), 0x81ac, location.x, location.z) ^ system.currentTick);
    const dimension = event.dimension ?? event.player?.dimension;
    if (!dimension) return;

    drop(dimension, location, POD, rng.int(1, 3));
    drop(dimension, location, SEED, rng.int(0, 1));

    // Replant, so a plot keeps running once it is established.
    try {
      const cell = dimension.getBlock(location);
      if (cell && cell.typeId === "minecraft:air") {
        if (setStage(cell, 0)) track(location);
      }
    } catch {
      // Could not replant; the player still has the seed.
    }
  });

  // Bone meal, as it works on every other crop in the game.
  world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
    if (event.block?.typeId !== CROP) return;
    if (event.itemStack?.typeId !== "minecraft:bone_meal") return;
    event.cancel = true;

    const block = event.block;
    system.run(() => {
      const stage = stageOf(block);
      if (stage >= RIPE) return;
      if (setStage(block, Math.min(RIPE, stage + 1))) track(block.location);
    });
  });
}
