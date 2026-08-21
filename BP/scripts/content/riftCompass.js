/**
 * The Rift Compass.
 *
 * A vanilla compass is useless in the End. This one reads the same seed-derived
 * map the generator uses, so it can name and point at a structure that has not
 * been built yet - which is what makes flying out into empty void feel like
 * travel rather than a gamble.
 */

import { system, world } from "@minecraft/server";
import { discoveryCount } from "../world/discovery.js";
import { END_DIMENSION } from "../world/generator.js";
import { distanceTo, sitesNear } from "../world/sites.js";

const ITEM_ID = "voidbound:rift_compass";

/** How far out the needle can read, in cells (272 blocks each). */
const SEARCH_CELLS = 3;

/** Ticks a player must wait between readings. */
const COOLDOWN_TICKS = 20;

const lastUsed = new Map();

const BEARINGS = [
  "north", "north-east", "east", "south-east",
  "south", "south-west", "west", "north-west",
];

/** Bedrock: -z is north, +x is east. Exported so tools/smoketest.mjs can check it. */
export function bearingFrom(dx, dz) {
  const angle = Math.atan2(dx, -dz); // 0 = north, increasing clockwise
  const index = Math.round(((angle + Math.PI * 2) % (Math.PI * 2)) / (Math.PI / 4)) % 8;
  return BEARINGS[index];
}

function survey(player) {
  const position = player.location;

  if (player.dimension.id !== END_DIMENSION) {
    player.sendMessage("§8The needle spins without settling. It only reads the End.");
    player.playSound("note.bass", { volume: 0.5, pitch: 0.7 });
    return;
  }

  const sites = sitesNear(position.x, position.z, SEARCH_CELLS);
  if (sites.length === 0) {
    player.sendMessage("§8Nothing within reach. Travel further out.");
    player.playSound("note.bass", { volume: 0.5, pitch: 0.7 });
    return;
  }

  const nearest = sites[0];
  const distance = Math.round(distanceTo(nearest, position));
  const bearing = bearingFrom(nearest.x - position.x, nearest.z - position.z);

  player.sendMessage(
    `§5${nearest.blueprint.name} §7- §f${distance}§7 blocks to the §f${bearing}§7.`
  );

  // Name the runner-up too, so the compass supports choosing a route.
  if (sites.length > 1) {
    const second = sites[1];
    player.sendMessage(
      `§8then ${second.blueprint.name}, ${Math.round(distanceTo(second, position))} blocks ` +
        `to the ${bearingFrom(second.x - position.x, second.z - position.z)}.`
    );
  }

  const found = discoveryCount(player);
  if (found > 0) player.onScreenDisplay.setActionBar(`§7Structures found: §f${found}`);

  // A trail of particles toward the reading, so it reads on mobile too.
  const length = Math.hypot(nearest.x - position.x, nearest.z - position.z) || 1;
  const stepX = ((nearest.x - position.x) / length) * 1.5;
  const stepZ = ((nearest.z - position.z) / length) * 1.5;
  for (let step = 1; step <= 6; step++) {
    try {
      player.dimension.spawnParticle("minecraft:endrod", {
        x: position.x + stepX * step,
        y: position.y + 1.2,
        z: position.z + stepZ * step,
      });
    } catch {
      // Particles are decoration; a blocked spawn is not an error.
    }
  }
  player.playSound("random.orb", { volume: 0.6, pitch: 1.6 });
}

export function startRiftCompass() {
  world.afterEvents.itemUse.subscribe((event) => {
    const { source: player, itemStack } = event;
    if (itemStack.typeId !== ITEM_ID) return;

    const now = system.currentTick;
    if (now - (lastUsed.get(player.id) ?? -Infinity) < COOLDOWN_TICKS) return;
    lastUsed.set(player.id, now);

    try {
      survey(player);
    } catch (error) {
      console.warn(`[End Unbound] compass survey failed: ${error}`);
    }
  });

  world.afterEvents.playerLeave.subscribe((event) => {
    lastUsed.delete(event.playerId);
  });
}
