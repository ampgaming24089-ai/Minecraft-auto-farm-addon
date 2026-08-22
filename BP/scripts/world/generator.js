/**
 * Turning sites into actual structures.
 *
 * Bedrock add-ons cannot add structures to the chunk generator itself, so
 * Endrealm generates them just ahead of the player instead: a scan every two
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
 *
 * The whole body is guarded, not just the lookup. A Block handle is lazy:
 * getTopmostBlock can hand one back and then throw LocationInUnloadedChunk the
 * moment you read typeId off it, which is exactly what happened in play - the
 * scan hit a sited structure at the edge of the loaded area and threw twice a
 * second, forever, because nothing about the site changed between scans.
 *
 * @returns {number | undefined} y of the topmost natural ground block
 */
function groundHeight(dimension, x, z) {
  try {
    // Cheap pre-check so the common "player is nowhere near it yet" case
    // never reaches the throwing path at all.
    if (!dimension.isChunkLoaded({ x, y: GROUND_MIN_Y, z })) return undefined;
    const block = dimension.getTopmostBlock({ x, z });
    if (!block) return undefined;
    const y = block.y;
    if (y < GROUND_MIN_Y || y > GROUND_MAX_Y) return undefined;
    if (!NATURAL_GROUND.has(block.typeId)) return undefined;
    return y;
  } catch {
    return undefined; // Chunk went away mid-read; try again next scan.
  }
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

    if (plan.warden) {
      try {
        dimension.spawnEntity("voidbound:echo_warden", {
          x: origin.x, y: origin.y + 3, z: origin.z,
        });
      } catch (error) {
        console.warn(`[Endrealm] could not place the Warden at ${site.key}: ${error}`);
      }
      yield;
    }

    if (plan.boss) {
      try {
        dimension.spawnEntity("voidbound:rift_sovereign", {
          x: origin.x,
          y: origin.y + 6,
          z: origin.z,
        });
      } catch (error) {
        console.warn(`[Endrealm] could not place the Sovereign at ${site.key}: ${error}`);
      }
      yield;
    }

    for (let i = 0; i < (plan.villagers ?? 0); i++) {
      const angle = rng.float(0, Math.PI * 2);
      const reach = rng.float(3, 9);
      try {
        dimension.spawnEntity("voidbound:end_villager", {
          x: origin.x + Math.cos(angle) * reach,
          y: origin.y + 2,
          z: origin.z + Math.sin(angle) * reach,
        });
      } catch {
        // No room there; the village simply has one fewer resident.
      }
      yield;
    }

    if (plan.titan) {
      const offset = rotate(plan.titan, site.facing);
      try {
        dimension.spawnEntity("voidbound:void_titan", {
          x: origin.x + offset.x,
          y: origin.y + plan.titan.y,
          z: origin.z + offset.z,
        });
      } catch (error) {
        console.warn(`[Endrealm] could not place the Titan at ${site.key}: ${error}`);
      }
      yield;
    }

    for (let i = 0; i < (plan.guards ?? 0); i++) {
      const angle = rng.float(0, Math.PI * 2);
      const reach = rng.float(4, site.blueprint.radius);
      try {
        dimension.spawnEntity("voidbound:void_stalker", {
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
    console.warn(`[Endrealm] build failed at ${site.key}: ${error}`);
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
