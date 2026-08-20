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

const INTERVAL_TICKS = 10;

/** Drift emitters spawned per player per interval. */
const DRIFT_EMITTERS = 3;

/** Horizontal spread of drift motes around the player. */
const DRIFT_RADIUS = 22;

/** Chance per interval that a player sees a falling streak. */
const FALL_CHANCE = 0.16;

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
