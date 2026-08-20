/**
 * Keeping the flyers in play.
 *
 * Hover navigation tethers a mob to the ground beneath it, but the End is
 * mostly *not* ground: fly out past an island edge and there is nothing below
 * for hundreds of blocks, so the tether has nothing to hold on to and the mob
 * climbs or drifts off into the void until it despawns.
 *
 * Behaviour components have no answer for that, so this is the backstop: every
 * second, any of this pack's flyers that has climbed too far above the island
 * it belongs to gets pulled down, and any that has wandered out over open void
 * gets returned to the nearest player. It never touches a mob that is
 * behaving, so a normal flight path is unaffected.
 */

import { system, world } from "@minecraft/server";
import { END_DIMENSION } from "./generator.js";

const FLYERS = [
  "voidbound:lumen_wisp",
  "voidbound:void_moth",
  "voidbound:shard_wraith",
  "voidbound:echo_sentinel",
  "voidbound:rift_sovereign",
];

const CHECK_INTERVAL_TICKS = 20;

/** Blocks above the ground below it that a flyer may climb to. */
const MAX_ALTITUDE = 14;

/** How far a stranded flyer may be from a player before it is recalled. */
const RECALL_RANGE = 72;

/** Ground search band - End islands live here. */
const GROUND_MIN_Y = 4;
const GROUND_MAX_Y = 128;

function groundBelow(dimension, location) {
  try {
    const block = dimension.getTopmostBlock({ x: location.x, z: location.z });
    if (!block) return undefined;
    if (block.y < GROUND_MIN_Y || block.y > GROUND_MAX_Y) return undefined;
    if (block.y > location.y + 2) return undefined; // Ground is above it, not below.
    return block.y;
  } catch {
    return undefined;
  }
}

function nearestPlayer(dimension, location) {
  let best;
  let bestDistance = Infinity;
  for (const player of dimension.getPlayers()) {
    const dx = player.location.x - location.x;
    const dy = player.location.y - location.y;
    const dz = player.location.z - location.z;
    const distance = dx * dx + dy * dy + dz * dz;
    if (distance < bestDistance) {
      bestDistance = distance;
      best = player;
    }
  }
  return bestDistance <= RECALL_RANGE * RECALL_RANGE ? best : undefined;
}

function correct(entity) {
  const location = entity.location;
  const ground = groundBelow(entity.dimension, location);

  if (ground !== undefined) {
    const altitude = location.y - ground;
    if (altitude <= MAX_ALTITUDE) return;
    // Set it back down at a sensible hover height rather than shoving it, so
    // it does not immediately climb again fighting its own navigation.
    entity.teleport(
      { x: location.x, y: ground + 4, z: location.z },
      { dimension: entity.dimension }
    );
    return;
  }

  // Out over the void with nothing beneath it.
  const player = nearestPlayer(entity.dimension, location);
  if (!player) return; // Nobody to return it to; let it despawn naturally.
  const angle = Math.random() * Math.PI * 2;
  entity.teleport(
    {
      x: player.location.x + Math.cos(angle) * 6,
      y: player.location.y + 3,
      z: player.location.z + Math.sin(angle) * 6,
    },
    { dimension: entity.dimension }
  );
}

function tick() {
  let dimension;
  try {
    dimension = world.getDimension(END_DIMENSION);
  } catch {
    return;
  }
  for (const typeId of FLYERS) {
    let entities;
    try {
      entities = dimension.getEntities({ type: typeId });
    } catch {
      continue;
    }
    for (const entity of entities) {
      if (!entity.isValid) continue;
      try {
        correct(entity);
      } catch {
        // Entity died or unloaded mid-pass.
      }
    }
  }
}

export function startFlightControl() {
  system.runInterval(tick, CHECK_INTERVAL_TICKS);
}
