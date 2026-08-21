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
 *
 * One layer is not decoration. Standing near a drop into the void raises a
 * column of motes off the edge, which makes the edge legible: in a dimension
 * where the ground simply stops and the fall is fatal, that is worth more than
 * any amount of sparkle.
 */

import { system, world } from "@minecraft/server";
import { END_DIMENSION } from "./generator.js";
import { biomeAt, borderProximity } from "./biomes.js";
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

/** Biome emitters per player per interval, and how far out they scatter. */
const BIOME_EMITTERS = 3;
const BIOME_RADIUS = 20;

/**
 * Edge detection: how far out to sample, and the band an island can live in.
 * Four samples per player every other interval is a handful of block reads a
 * second - cheap enough to run forever, dense enough to catch a ledge.
 */
const EDGE_REACH = 5;
const EDGE_INTERVALS = 2;
const GROUND_MIN_Y = 4;
const GROUND_MAX_Y = 128;

/** Nothing below within this many blocks means the player is over open void. */
const EDGE_DROP = 12;

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

  edgeDraft(player);
  biomeAir(player);
}

/**
 * The biome's own particles.
 *
 * This is the layer that does most of the work of making a region feel like a
 * place: spores hanging in the Glowspore Basin, frost falling through the
 * Bonespire Reach, embers climbing out of the Ashen Wastes. Rates come from
 * the biome table, so a quiet biome stays quiet.
 *
 * Emitters are placed on a ring around the player and faded out near a border,
 * because a biome that switches its air on like a light gives away that it is
 * a script rather than a place.
 */
function biomeAir(player) {
  const { x, y, z } = player.location;
  const biome = biomeAt(x, z);
  if (!biome.particle) return;

  // Near a border the rate halves, so the change reads as a transition.
  const rate = (biome.particleChance ?? 0.5) * (borderProximity(x, z) ? 1 : 0.45);
  if (Math.random() > rate) return;

  const dimension = player.dimension;
  for (let i = 0; i < BIOME_EMITTERS; i++) {
    const angle = Math.random() * Math.PI * 2;
    const distance = 4 + Math.random() * BIOME_RADIUS;
    const at = {
      x: x + Math.cos(angle) * distance,
      y: y + biome.particleLift + Math.random() * 10,
      z: z + Math.sin(angle) * distance,
    };
    // A particle spawned in a biome the player is not standing in reads as a
    // leak across the border, so each emitter checks its own footing.
    if (biomeAt(at.x, at.z).id !== biome.id) continue;
    spawn(dimension, biome.particle, at);
  }
}

/**
 * Ground height under a column, or undefined when the chunk is not loaded.
 *
 * Block handles are lazy: getTopmostBlock hands one back and reading typeId is
 * what actually touches the chunk, so the whole read has to sit inside the
 * guard, not just the call.
 */
function groundHeight(dimension, x, z) {
  try {
    if (!dimension.isChunkLoaded({ x, y: GROUND_MIN_Y, z })) return undefined;
    const block = dimension.getTopmostBlock({ x, z });
    if (!block) return undefined;
    const height = block.y;
    if (height < GROUND_MIN_Y || height > GROUND_MAX_Y) return undefined;
    return height;
  } catch {
    return undefined;
  }
}

/** Raise motes off any edge the player is standing near. */
function edgeDraft(player) {
  if (system.currentTick % (INTERVAL_TICKS * EDGE_INTERVALS) !== 0) return;

  const { x, y, z } = player.location;
  const dimension = player.dimension;
  const here = groundHeight(dimension, Math.floor(x), Math.floor(z));
  // Airborne or over unloaded ground: nothing to stand on the edge of.
  if (here === undefined || Math.abs(y - here) > 3) return;

  for (const [dx, dz] of [[EDGE_REACH, 0], [-EDGE_REACH, 0], [0, EDGE_REACH], [0, -EDGE_REACH]]) {
    const sampleX = Math.floor(x) + dx;
    const sampleZ = Math.floor(z) + dz;
    const there = groundHeight(dimension, sampleX, sampleZ);
    // Undefined means nothing at all below - the void. A long drop counts too.
    if (there !== undefined && here - there < EDGE_DROP) continue;
    spawn(dimension, "voidbound:void_updraft", {
      x: sampleX + 0.5,
      y: here - 2,
      z: sampleZ + 0.5,
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
