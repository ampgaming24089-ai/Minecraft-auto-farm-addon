/**
 * Turning sites into actual structures.
 *
 * Bedrock add-ons cannot add structures to the chunk generator itself, so
 * Voidbound generates them just ahead of the player instead: a scan every two
 * seconds finds sited structures the player is approaching, checks that the
 * ground under them is untouched natural End, and builds them over a handful
 * of ticks with system.runJob.
 *
 * Because siting is seed-derived, a structure built this way sits exactly
 * where the rift compass said it would, whether the player walked there or
 * flew in from 20,000 blocks away.
 */

import { system, world } from "@minecraft/server";
import { fillContainer, place, siteIsClear } from "../lib/blueprint.js";
import { Rng } from "../lib/rng.js";
import { rollChest } from "../content/loot.js";
import { rotate } from "../lib/vec.js";
import { isBuilt, markBuilt } from "./memory.js";
import { distanceTo, sitesNear } from "./sites.js";

export const END_DIMENSION = "minecraft:the_end";

/** How close a player must be before a structure is committed to the world. */
const BUILD_RADIUS = 128;

const SCAN_INTERVAL_TICKS = 40;

/** End islands sit in this band; anything outside it is not real ground. */
const GROUND_MIN_Y = 8;
const GROUND_MAX_Y = 120;

/** Only natural End ground is built on, which keeps end cities and the
 *  obsidian pillars intact and stops structures stacking on each other. */
const NATURAL_GROUND = new Set([
  "minecraft:end_stone",
  "voidbound:shattered_end_stone",
  "voidbound:verdant_end_stone",
  "voidbound:echo_ore",
]);

const building = new Set();
/** Sites rejected this session (occupied ground, no island, player base). */
const rejected = new Set();

/**
 * Find the surface to stand the structure on.
 * @returns {number | undefined} y of the topmost natural ground block
 */
function groundHeight(dimension, x, z) {
  let block;
  try {
    block = dimension.getTopmostBlock({ x, z });
  } catch {
    return undefined; // Chunk not loaded yet - try again next scan.
  }
  if (!block) return undefined;
  if (block.y < GROUND_MIN_Y || block.y > GROUND_MAX_Y) return undefined;
  if (!NATURAL_GROUND.has(block.typeId)) return undefined;
  return block.y;
}

function* buildJob(dimension, site, origin) {
  try {
    const rng = new Rng((site.seed ^ 0x5bf03635) >>> 0);
    const plan = site.blueprint.build(rng);

    yield* place(dimension, origin, plan.placements, site.facing);

    const distance = Math.sqrt(site.x * site.x + site.z * site.z);
    for (const chest of plan.chests ?? []) {
      const offset = rotate(chest, site.facing);
      fillContainer(
        dimension,
        { x: origin.x + offset.x, y: origin.y + offset.y, z: origin.z + offset.z },
        rollChest(rng, distance)
      );
      yield;
    }

    for (let i = 0; i < (plan.guards ?? 0); i++) {
      const angle = rng.float(0, Math.PI * 2);
      const reach = rng.float(4, site.blueprint.radius);
      try {
        dimension.spawnEntity("voidbound:rift_stalker", {
          x: origin.x + Math.cos(angle) * reach,
          y: origin.y + 2,
          z: origin.z + Math.sin(angle) * reach,
        });
      } catch {
        // A blocked spawn point is not worth failing the build over.
      }
      yield;
    }

    markBuilt(site.key);
  } catch (error) {
    console.warn(`[Voidbound] build failed at ${site.key}: ${error}`);
    rejected.add(site.key);
  } finally {
    building.delete(site.key);
  }
}

function considerSite(dimension, site) {
  if (building.has(site.key) || rejected.has(site.key) || isBuilt(site.key)) return;

  const y = groundHeight(dimension, site.x, site.z);
  if (y === undefined) return; // No island here, or the chunk is still loading.

  const origin = { x: site.x, y, z: site.z };
  if (!siteIsClear(dimension, origin, Math.min(12, site.blueprint.radius))) {
    rejected.add(site.key);
    return;
  }

  building.add(site.key);
  system.runJob(buildJob(dimension, site, origin));
}

function scan() {
  let players;
  try {
    players = world.getAllPlayers();
  } catch {
    return;
  }
  for (const player of players) {
    if (player.dimension.id !== END_DIMENSION) continue;
    const position = player.location;
    for (const site of sitesNear(position.x, position.z, 1)) {
      if (distanceTo(site, position) > BUILD_RADIUS) continue;
      considerSite(player.dimension, site);
    }
  }
}

export function startGenerator() {
  system.runInterval(scan, SCAN_INTERVAL_TICKS);
}
