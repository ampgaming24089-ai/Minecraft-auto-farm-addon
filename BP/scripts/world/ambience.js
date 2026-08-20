/**
 * Living air.
 *
 * The skybox is one static texture that the game tiles across every face, and
 * Bedrock gives a pack no way to animate it. What it does give is particles,
 * and particles in front of a sky do most of the work a moving sky would:
 * motes drifting up past the islands, and occasional streaks falling through
 * the dark overhead.
 *
 * Everything is spawned relative to the player and biased *away* from the
 * camera's immediate surroundings, so the effect reads as depth rather than as
 * dust on the lens. Rates are per-player and deliberately low - this runs
 * forever, for everyone in the dimension, on phones.
 */

import { system, world } from "@minecraft/server";
import { END_DIMENSION } from "./generator.js";
import { distanceTo, sitesNear } from "./sites.js";

const INTERVAL_TICKS = 10;

/** Drift emitters spawned per player per interval. */
const DRIFT_EMITTERS = 3;

/** Horizontal spread of drift motes around the player. */
const DRIFT_RADIUS = 22;

/** Chance per interval that a player sees a falling streak. */
const FALL_CHANCE = 0.16;

/** Chance per interval of seeding an aurora sheet high overhead. */
const AURORA_CHANCE = 0.22;

/** Chance per interval of spores, when the player is standing in a grove. */
const SPORE_CHANCE = 0.55;

/** How close to a grove counts as inside it. */
const GROVE_RANGE = 22;

function spawn(dimension, effect, at) {
  try {
    dimension.spawnParticle(effect, at);
  } catch {
    // Unloaded chunk or the player moved away mid-tick; purely cosmetic.
  }
}

function ambientFor(player) {
  const { x, y, z } = player.location;
  const dimension = player.dimension;

  for (let i = 0; i < DRIFT_EMITTERS; i++) {
    // Ring-biased placement: nothing spawns right on the camera, which is
    // what makes this read as atmosphere instead of a screen effect.
    const angle = Math.random() * Math.PI * 2;
    const distance = 6 + Math.random() * DRIFT_RADIUS;
    spawn(dimension, "voidbound:void_drift", {
      x: x + Math.cos(angle) * distance,
      y: y - 6 + Math.random() * 26,
      z: z + Math.sin(angle) * distance,
    });
  }

  // Aurora sheets sit far above the play space and drift slowly, so they read
  // as sky rather than as weather happening around the player.
  if (Math.random() < AURORA_CHANCE) {
    const angle = Math.random() * Math.PI * 2;
    const distance = 18 + Math.random() * 30;
    spawn(dimension, "voidbound:end_aurora", {
      x: x + Math.cos(angle) * distance,
      y: y + 40 + Math.random() * 26,
      z: z + Math.sin(angle) * distance,
    });
  }

  // Groves get their own drift, so walking into one is a visible change.
  if (Math.random() < SPORE_CHANCE) {
    for (const site of sitesNear(x, z, 1)) {
      if (site.blueprint.id !== "grove") continue;
      if (distanceTo(site, player.location) > GROVE_RANGE) continue;
      const angle = Math.random() * Math.PI * 2;
      const distance = 2 + Math.random() * 14;
      spawn(dimension, "voidbound:grove_spores", {
        x: x + Math.cos(angle) * distance,
        y: y + Math.random() * 8,
        z: z + Math.sin(angle) * distance,
      });
      break;
    }
  }

  if (Math.random() < FALL_CHANCE) {
    const angle = Math.random() * Math.PI * 2;
    const distance = 10 + Math.random() * 26;
    spawn(dimension, "voidbound:void_fall", {
      x: x + Math.cos(angle) * distance,
      y: y + 22 + Math.random() * 16,
      z: z + Math.sin(angle) * distance,
    });
  }
}

function tick() {
  for (const player of world.getAllPlayers()) {
    if (player.dimension.id !== END_DIMENSION) continue;
    try {
      ambientFor(player);
    } catch {
      // Never let ambience break the tick loop.
    }
  }
}

export function startAmbience() {
  system.runInterval(tick, INTERVAL_TICKS);
}
