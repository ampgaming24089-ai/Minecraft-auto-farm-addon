/**
 * Keeping the flyers in play.
 *
 * Hover navigation tethers a mob to the ground beneath it, but the End is
 * mostly *not* ground: fly out past an island edge and there is nothing below
 * for hundreds of blocks, so the tether has nothing to hold and the mob climbs
 * or drifts until it despawns. Behaviour components have no answer for that.
 *
 * So each flyer gets a home. The first time one is seen standing over solid
 * ground, that spot is written to its own dynamic property, and from then on
 * this pass keeps it inside a radius of that spot and under a ceiling above
 * it. Bosses get a much tighter radius than wandering mobs, because a boss
 * that leaves its arena has effectively ended the fight.
 *
 * Nothing happens to a mob that is behaving, so ordinary flight is untouched.
 */

import { system, world } from "@minecraft/server";
import { END_DIMENSION } from "./generator.js";
import { FLIGHT_TRAILS } from "../content/mobActions.js";

/** typeId -> { ceiling, leash } in blocks. */
const FLYERS = new Map([
  ["voidbound:void_wisp", { ceiling: 8, leash: 26 }],
  ["voidbound:ender_ghost", { ceiling: 7, leash: 22 }],
  ["voidbound:ender_bird", { ceiling: 12, leash: 40 }],
  ["voidbound:sky_ray", { ceiling: 13, leash: 46 }],
  ["voidbound:echo_warden", { ceiling: 6, leash: 16 }],
  ["voidbound:rift_sovereign", { ceiling: 9, leash: 20 }],
  ["voidbound:ender_overlord", { ceiling: 11, leash: 26 }],
  // The whale is the biggest thing in the sky, so it gets the longest
  // rope - but a higher ceiling would put it out of render range.
  ["voidbound:astral_whale", { ceiling: 14, leash: 44 }],
  // The dragon gets the most rope of anything, because it is meant to be
  // seen crossing the sky - but the ceiling is what stops it becoming a dot.
  ["voidbound:void_dragon", { ceiling: 18, leash: 60 }],
]);

const CHECK_INTERVAL_TICKS = 10;

const HOME_X = "voidbound.home_x";
const HOME_Y = "voidbound.home_y";
const HOME_Z = "voidbound.home_z";

/** Ground search band - End islands live here. */
const GROUND_MIN_Y = 4;
const GROUND_MAX_Y = 128;

function groundBelow(dimension, location) {
  try {
    if (!dimension.isChunkLoaded({ x: location.x, y: GROUND_MIN_Y, z: location.z })) {
      return undefined;
    }
    const block = dimension.getTopmostBlock({ x: location.x, z: location.z });
    if (!block) return undefined;
    const y = block.y;
    if (y < GROUND_MIN_Y || y > GROUND_MAX_Y) return undefined;
    if (y > location.y + 2) return undefined; // That is ground above, not below.
    return y;
  } catch {
    return undefined;
  }
}

function readHome(entity) {
  try {
    const x = entity.getDynamicProperty(HOME_X);
    const y = entity.getDynamicProperty(HOME_Y);
    const z = entity.getDynamicProperty(HOME_Z);
    if (typeof x === "number" && typeof y === "number" && typeof z === "number") {
      return { x, y, z };
    }
  } catch {
    // Fall through and treat it as homeless.
  }
  return undefined;
}

function writeHome(entity, at) {
  try {
    entity.setDynamicProperty(HOME_X, at.x);
    entity.setDynamicProperty(HOME_Y, at.y);
    entity.setDynamicProperty(HOME_Z, at.z);
  } catch {
    // Not fatal: it will be re-derived on a later pass.
  }
}

function correct(entity, limits) {
  const location = entity.location;
  const ground = groundBelow(entity.dimension, location);

  // Claim a home the first time we see it over real ground.
  let home = readHome(entity);
  if (!home && ground !== undefined) {
    home = { x: location.x, y: ground, z: location.z };
    writeHome(entity, home);
  }
  if (!home) return; // Spawned over void and never grounded; nothing to anchor to.

  const dx = location.x - home.x;
  const dz = location.z - home.z;
  const drift = Math.hypot(dx, dz);
  const altitude = location.y - (ground !== undefined ? ground : home.y);

  if (drift <= limits.leash && altitude <= limits.ceiling) return;

  // One correction covers both cases: put it back over its home at a sensible
  // hover height. Setting it down rather than shoving it stops it fighting its
  // own navigation and climbing straight back up.
  const pullBack = drift > limits.leash;
  const target = pullBack
    ? { x: home.x, y: home.y + 3, z: home.z }
    : { x: location.x, y: (ground ?? home.y) + Math.max(2, limits.ceiling - 3), z: location.z };

  try {
    entity.teleport(target, { dimension: entity.dimension });
  } catch {
    // Blocked destination; try again next pass.
  }
}

/**
 * How often a flier leaves a puff behind it.
 *
 * The sweep runs every ten ticks, and a trail on every pass is a solid tube
 * of particles following the mob around. One pass in four gives a broken
 * dotted line, which is what actually reads as a wake.
 */
const TRAIL_EVERY = 4;
let sweeps = 0;

function trail(entity, effect) {
  if (!effect) return;
  const at = entity.location;
  try {
    entity.dimension.spawnParticle(effect, { x: at.x, y: at.y + 0.5, z: at.z });
  } catch {
    // Unloaded chunk, or a client that has not got the effect yet.
  }
}

function tick() {
  sweeps += 1;
  const laying = sweeps % TRAIL_EVERY === 0;
  let dimension;
  try {
    dimension = world.getDimension(END_DIMENSION);
  } catch {
    return;
  }
  for (const [typeId, limits] of FLYERS) {
    let entities;
    try {
      entities = dimension.getEntities({ type: typeId });
    } catch {
      continue;
    }
    for (const entity of entities) {
      if (!entity.isValid) continue;
      try {
        correct(entity, limits);
        if (laying) trail(entity, FLIGHT_TRAILS.get(typeId));
      } catch {
        // Entity died or unloaded mid-pass.
      }
    }
  }
}

export function startFlightControl() {
  system.runInterval(tick, CHECK_INTERVAL_TICKS);
}
