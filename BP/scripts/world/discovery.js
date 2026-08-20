/**
 * Discovery log.
 *
 * Exploration only reads as progress if arriving somewhere is acknowledged.
 * The first time a player reaches each structure they get a title card and a
 * running count; afterwards the place is theirs and stays quiet.
 */

import { system, world } from "@minecraft/server";
import { distanceTo, sitesNear } from "./sites.js";
import { END_DIMENSION } from "./generator.js";

const FOUND_PROPERTY = "voidbound.found";
const COUNT_PROPERTY = "voidbound.found_count";

/** How close counts as "arrived". */
const ARRIVAL_RADIUS = 22;

const CHECK_INTERVAL_TICKS = 20;

/** Per-player log cap - old entries fall off and can be re-discovered. */
const MAX_REMEMBERED = 300;

function loadFound(player) {
  try {
    const raw = player.getDynamicProperty(FOUND_PROPERTY);
    return typeof raw === "string" && raw ? raw.split(",") : [];
  } catch {
    return [];
  }
}

function recordFound(player, key) {
  const found = loadFound(player);
  found.push(key);
  while (found.length > MAX_REMEMBERED) found.shift();
  try {
    player.setDynamicProperty(FOUND_PROPERTY, found.join(","));
    const previous = player.getDynamicProperty(COUNT_PROPERTY);
    const total = (typeof previous === "number" ? previous : 0) + 1;
    player.setDynamicProperty(COUNT_PROPERTY, total);
    return total;
  } catch (error) {
    console.warn(`[Enderveil] could not record discovery: ${error}`);
    return undefined;
  }
}

/** How many structures this player has found. */
export function discoveryCount(player) {
  try {
    const total = player.getDynamicProperty(COUNT_PROPERTY);
    return typeof total === "number" ? total : 0;
  } catch {
    return 0;
  }
}

function check() {
  for (const player of world.getAllPlayers()) {
    if (player.dimension.id !== END_DIMENSION) continue;
    const position = player.location;
    const nearest = sitesNear(position.x, position.z, 1)[0];
    if (!nearest || distanceTo(nearest, position) > ARRIVAL_RADIUS) continue;

    const found = loadFound(player);
    if (found.includes(nearest.key)) continue;

    const total = recordFound(player, nearest.key);
    try {
      player.onScreenDisplay.setTitle(`§d${nearest.blueprint.name}`, {
        subtitle: total ? `§7Discovery ${total}` : "§7Discovered",
        fadeInDuration: 8,
        stayDuration: 45,
        fadeOutDuration: 16,
      });
      player.playSound("random.levelup", { volume: 0.5, pitch: 1.4 });
    } catch {
      // Cosmetic only.
    }
  }
}

export function startDiscovery() {
  system.runInterval(check, CHECK_INTERVAL_TICKS);
}
