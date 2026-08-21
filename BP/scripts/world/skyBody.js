/**
 * The planet in the End's sky.
 *
 * The skybox cannot hold it. That texture is tiled across all six faces of a
 * cube, so anything the size of a planet in it appears dozens of times over,
 * and Bedrock draws no sun or moon in the End at all - `moon_phases.png` is an
 * Overworld texture that never renders here. An entity is the only way to put
 * one large object in this sky.
 *
 * So there is a flat plate held at a fixed offset from the player and turned
 * to face them every tick. Because the offset is fixed rather than the
 * position, it never falls behind, and it has no parallax: walking towards it
 * does not bring it closer, which is exactly how something that far away
 * should behave.
 *
 * The compromise, stated plainly: entities are shared, so in multiplayer each
 * player's plate is visible to everyone. Players standing together see one
 * planet; players a long way apart see each other's low on the horizon. There
 * is no per-player rendering in the Bedrock script API, so this is the price
 * of having a planet at all.
 */

import { system, world } from "@minecraft/server";
import { END_DIMENSION } from "./generator.js";

const MOON = "voidbound:void_moon";

/** Where the planet sits relative to the player who owns it.
 *
 *  52 blocks, not 80. Entity render distance is tied to simulation distance,
 *  and the default on a phone is four chunks - a plate parked past that is
 *  simply not drawn, which is a planet that exists only on a desktop. The
 *  apparent size is set by the entity's scale against this distance, so
 *  bringing it closer and shrinking it keeps the same planet in the sky and
 *  puts it inside everyone's draw range. */
const DISTANCE = 52;
const ELEVATION = 0.55;      // sine of the angle above the horizon
const BEARING = 2.2;         // radians, so it is not always due north

/** Which player a plate belongs to. */
const OWNER = "voidbound.moon_owner";

const UPDATE_TICKS = 4;

/**
 * Entity render distance is finite, and a plate parked beyond it simply is not
 * drawn. 78 blocks is inside the default on every platform; further out looks
 * better on a PC with the distance turned up and vanishes on a phone.
 */
function anchorFor(player) {
  const at = player.location;
  const flat = Math.sqrt(Math.max(0, 1 - ELEVATION * ELEVATION));
  return {
    x: at.x + Math.cos(BEARING) * flat * DISTANCE,
    y: at.y + ELEVATION * DISTANCE,
    z: at.z + Math.sin(BEARING) * flat * DISTANCE,
  };
}

/** The plate's own plane faces -Z, so this is the yaw that turns it around. */
function facing(from, to) {
  const dx = to.x - from.x;
  const dz = to.z - from.z;
  const yaw = (Math.atan2(dz, dx) * 180) / Math.PI - 90;
  const dy = to.y - from.y;
  const flat = Math.hypot(dx, dz);
  const pitch = (-Math.atan2(dy, flat) * 180) / Math.PI;
  return { x: pitch, y: yaw };
}

function findMoon(dimension, player) {
  let candidates;
  try {
    candidates = dimension.getEntities({ type: MOON });
  } catch {
    return undefined;
  }
  for (const moon of candidates) {
    try {
      if (moon.getDynamicProperty(OWNER) === player.id) return moon;
    } catch {
      // Unloaded mid-scan.
    }
  }
  return undefined;
}

/** Plates whose player has left the End, or the game. */
function sweepOrphans(dimension, owners) {
  let all;
  try {
    all = dimension.getEntities({ type: MOON });
  } catch {
    return;
  }
  for (const moon of all) {
    try {
      const owner = moon.getDynamicProperty(OWNER);
      if (typeof owner === "string" && owners.has(owner)) continue;
      moon.remove();
    } catch {
      // Already gone.
    }
  }
}

function tick() {
  let dimension;
  try {
    dimension = world.getDimension(END_DIMENSION);
  } catch {
    return;
  }

  const owners = new Set();
  for (const player of world.getAllPlayers()) {
    if (player.dimension.id !== END_DIMENSION) continue;
    owners.add(player.id);

    const anchor = anchorFor(player);
    let moon = findMoon(dimension, player);
    if (!moon) {
      try {
        moon = dimension.spawnEntity(MOON, anchor);
        moon.setDynamicProperty(OWNER, player.id);
      } catch {
        continue; // Chunk not ready; try again next pass.
      }
    }
    try {
      moon.teleport(anchor, {
        dimension,
        rotation: facing(anchor, player.location),
      });
    } catch {
      // It will be re-placed on the next pass.
    }
  }

  sweepOrphans(dimension, owners);
}

export function startSkyBody() {
  system.runInterval(tick, UPDATE_TICKS);
}
