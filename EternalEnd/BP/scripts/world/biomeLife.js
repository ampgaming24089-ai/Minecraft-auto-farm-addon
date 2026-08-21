/**
 * Telling the player where they are, and putting the right things there.
 *
 * Two jobs that both hang off the same fact - which region a player is
 * standing in - and both of which Bedrock cannot do on its own here.
 *
 * The announcement, because a biome nobody can name is just a colour change.
 * Vanilla has no biome readout in the HUD, so this draws one on crossing a
 * border, the same way every End pack with "biomes" does it.
 *
 * The spawning, because spawn rules can only filter on the *engine's* idea of
 * biome, and the engine thinks the whole End is one. So each region's roster
 * is spawned from script instead, at a rate low enough that it supplements
 * natural spawning rather than replacing it - vanilla endermen keep their
 * share of the spawn budget, which was a specific thing to protect.
 */

import { system, world } from "@minecraft/server";
import { biomeAt } from "./biomes.js";
import { END_DIMENSION } from "./generator.js";

const CHECK_INTERVAL_TICKS = 20;

/** Where the player was last seen, so a crossing can be detected. */
const lastBiome = new Map();

/** Grace period after login before announcing, so joining is not shouted at. */
const SETTLE_TICKS = 60;
const joinedAt = new Map();

const SPAWN_INTERVAL_TICKS = 200;

/** Ceiling on pack mobs near one player. Deliberately low: this tops up a
 *  region's character, it does not populate it. */
const NEARBY_CAP = 6;
const SPAWN_RADIUS = 34;
const SPAWN_CHANCE = 0.5;

/** Ground band an island can occupy. */
const GROUND_MIN_Y = 4;
const GROUND_MAX_Y = 128;

function announce(player, biome) {
  try {
    player.onScreenDisplay.setActionBar(`${biome.colour}${biome.name}`);
  } catch {
    // Cosmetic; a player mid-teleport may have no display yet.
  }
}

function checkCrossings() {
  const now = system.currentTick;
  for (const player of world.getAllPlayers()) {
    if (player.dimension.id !== END_DIMENSION) {
      lastBiome.delete(player.id);
      continue;
    }
    if (!joinedAt.has(player.id)) joinedAt.set(player.id, now);
    if (now - joinedAt.get(player.id) < SETTLE_TICKS) continue;

    let biome;
    try {
      biome = biomeAt(player.location.x, player.location.z);
    } catch {
      continue;
    }
    const previous = lastBiome.get(player.id);
    lastBiome.set(player.id, biome.id);
    // First reading after arriving in the End still announces - that is the
    // moment a player most wants to know where they have landed.
    if (previous === biome.id) continue;
    announce(player, biome);
  }
}

/** Ground height under a column, or undefined if it cannot be read. */
function groundHeight(dimension, x, z) {
  try {
    if (!dimension.isChunkLoaded({ x, y: GROUND_MIN_Y, z })) return undefined;
    const block = dimension.getTopmostBlock({ x, z });
    if (!block) return undefined;
    if (block.y < GROUND_MIN_Y || block.y > GROUND_MAX_Y) return undefined;
    return block.y + 1;
  } catch {
    return undefined;
  }
}

function packMobsNear(dimension, location) {
  try {
    return dimension
      .getEntities({ location, maxDistance: SPAWN_RADIUS, families: ["voidbound"] })
      .length;
  } catch {
    return NEARBY_CAP; // Assume full rather than risk a spawn storm.
  }
}

function topUp(player) {
  if (Math.random() > SPAWN_CHANCE) return;

  const { x, y, z } = player.location;
  const dimension = player.dimension;
  const biome = biomeAt(x, z);
  if (!biome.mobs || biome.mobs.length === 0) return;
  if (packMobsNear(dimension, player.location) >= NEARBY_CAP) return;

  // Out past the near edge of the player's view, so nothing pops in in front
  // of them, but close enough that they will actually meet it.
  const angle = Math.random() * Math.PI * 2;
  const distance = 22 + Math.random() * (SPAWN_RADIUS - 22);
  const spawnX = Math.floor(x + Math.cos(angle) * distance);
  const spawnZ = Math.floor(z + Math.sin(angle) * distance);

  // The roster is the region's, so the spot has to still be in the region.
  if (biomeAt(spawnX, spawnZ).id !== biome.id) return;

  const groundY = groundHeight(dimension, spawnX, spawnZ);
  if (groundY === undefined) return;
  if (Math.abs(groundY - y) > 24) return; // A different island entirely.

  const type = biome.mobs[Math.floor(Math.random() * biome.mobs.length)];
  try {
    dimension.spawnEntity(type, { x: spawnX + 0.5, y: groundY, z: spawnZ + 0.5 });
  } catch {
    // Blocked, or the chunk went away. Nothing to do.
  }
}

function spawnPass() {
  for (const player of world.getAllPlayers()) {
    if (player.dimension.id !== END_DIMENSION) continue;
    try {
      topUp(player);
    } catch {
      // Never let spawning break the interval.
    }
  }
}

export function startBiomeLife() {
  system.runInterval(checkCrossings, CHECK_INTERVAL_TICKS);
  system.runInterval(spawnPass, SPAWN_INTERVAL_TICKS);

  world.afterEvents.playerLeave.subscribe((event) => {
    lastBiome.delete(event.playerId);
    joinedAt.delete(event.playerId);
  });
}
