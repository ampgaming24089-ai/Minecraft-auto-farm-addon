/**
 * Flying a tamed Sky Ray.
 *
 * Bedrock's data-driven mounts steer on the ground. `minecraft:rideable` puts
 * a player on the ray's back and `minecraft:behavior.player_ride_tamed` keeps
 * them there, but nothing in the component set turns a rider's look direction
 * into flight - the ray would simply drift on its own hover behaviour with a
 * passenger along for the trip.
 *
 * So the steering lives here. Every other tick, each ridden ray is pushed
 * toward where its rider is looking, at a speed the rider sets by holding
 * forward. Two things keep it from becoming a rocket:
 *
 *   - Velocity is *set*, not accumulated, so there is a hard ceiling on how
 *     fast a ray can ever go, however long the rider holds the stick.
 *   - Below a gentle threshold the ray settles into a slow sink rather than
 *     hanging motionless in the air, which is what stops a parked mount from
 *     turning into a permanent floating platform over the void.
 *
 * Dismounting hands the ray straight back to its own hover behaviour, and a
 * ray that loses its rider mid-air glides down rather than dropping, because
 * the entity has no gravity to begin with.
 */

import { system, world } from "@minecraft/server";
import { END_DIMENSION } from "../world/generator.js";

const RAY = "eternal_end:sky_ray";

/** How often steering is applied. Two ticks is smooth and costs little. */
const INTERVAL_TICKS = 2;

/** Top speed in blocks per tick, and how hard the rider can climb. */
const CRUISE = 0.62;
const CLIMB_LIMIT = 0.55;

/** Speed a rider has to be asking for before the ray stops sinking. */
const IDLE_THRESHOLD = 0.08;

/** How fast an unsteered ray settles, in blocks per tick. */
const SINK = -0.04;

function ridersOf(ray) {
  try {
    const rideable = ray.getComponent("minecraft:rideable");
    return rideable?.getRiders?.() ?? [];
  } catch {
    return [];
  }
}

/**
 * Steer one ray from its rider's view.
 *
 * `inputInfo.getMovementVector()` gives the rider's own stick, so pushing
 * forward flies forward and letting go coasts - the rider is not committed to
 * a heading just by looking at one.
 */
function steer(ray, rider) {
  let forward = 1;
  try {
    const movement = rider.inputInfo?.getMovementVector?.();
    if (movement) {
      // y is the forward axis of the movement vector; back-pedalling brakes.
      forward = Math.max(0, movement.y);
    }
  } catch {
    // Older runtimes without inputInfo simply always fly forward, which is
    // still a usable mount.
  }

  const view = rider.getViewDirection();
  const throttle = forward * CRUISE;

  if (throttle < IDLE_THRESHOLD) {
    try {
      ray.setVelocity({ x: 0, y: SINK, z: 0 });
    } catch {
      // The ray unloaded between the query and the push.
    }
    return;
  }

  const climb = Math.max(-CLIMB_LIMIT, Math.min(CLIMB_LIMIT, view.y * throttle));
  try {
    ray.setVelocity({ x: view.x * throttle, y: climb, z: view.z * throttle });
    // Point the ray where it is going, or it flies sideways.
    ray.setRotation({ x: 0, y: rider.getRotation().y });
  } catch {
    // Same: the entity went away. Nothing to do but skip this tick.
  }
}

function tick() {
  let dimension;
  try {
    dimension = world.getDimension(END_DIMENSION);
  } catch {
    return;
  }

  let rays;
  try {
    rays = dimension.getEntities({ type: RAY });
  } catch {
    return;
  }

  for (const ray of rays) {
    if (!ray.isValid) continue;
    const riders = ridersOf(ray);
    if (riders.length === 0) continue;
    const rider = riders[0];
    if (!rider?.isValid) continue;
    steer(ray, rider);
  }
}

export function startSkyRay() {
  system.runInterval(tick, INTERVAL_TICKS);
}
