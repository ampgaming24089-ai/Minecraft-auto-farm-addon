/**
 * Per-region atmosphere.
 *
 * The client biome file gives the whole End one look, because Bedrock exposes
 * a single `minecraft:the_end` biome to bind lighting and fog to. To get more
 * than one mood out of it, this pushes a fog definition onto the player's fog
 * stack - the layer that sits above biome fog - based on where they actually
 * are: down in the void, inside a grove, or standing next to a rift.
 *
 * Each player carries at most one pushed fog under a fixed handle, and it is
 * only re-pushed when the region actually changes, so this costs one command
 * per boundary crossing rather than one per tick.
 */

import { system, world } from "@minecraft/server";
import { distanceTo, sitesNear } from "./sites.js";
import { END_DIMENSION } from "./generator.js";

/** The name this pack's fog is pushed under, so it can be replaced cleanly. */
const HANDLE = "voidbound_region";

/** Below this height the player is out over the void rather than on an island. */
const VOID_HEIGHT = 0;

const APPLY_INTERVAL_TICKS = 20;

/** playerId -> fog identifier currently pushed (or undefined for none). */
const applied = new Map();

function regionFogFor(player) {
  const position = player.location;
  if (position.y < VOID_HEIGHT) return "voidbound:fog_void_deep";

  for (const site of sitesNear(position.x, position.z, 1)) {
    if (!site.blueprint.fog) continue;
    if (distanceTo(site, position) < site.blueprint.radius + 24) return site.blueprint.fog;
  }
  return undefined; // Fall through to the biome's own fog.
}

function clearFog(player) {
  try {
    player.runCommand(`fog @s remove ${HANDLE}`);
  } catch {
    // The player may have left, or nothing was pushed; either way, nothing to undo.
  }
}

function apply() {
  for (const player of world.getAllPlayers()) {
    const inEnd = player.dimension.id === END_DIMENSION;
    const wanted = inEnd ? regionFogFor(player) : undefined;
    const current = applied.get(player.id);
    if (wanted === current) continue;

    if (current) clearFog(player);
    if (wanted) {
      try {
        player.runCommand(`fog @s push ${wanted} ${HANDLE}`);
      } catch (error) {
        console.warn(`[Riftborne] could not push fog ${wanted}: ${error}`);
        applied.set(player.id, undefined);
        continue;
      }
    }
    applied.set(player.id, wanted);
  }
}

export function startAtmosphere() {
  system.runInterval(apply, APPLY_INTERVAL_TICKS);

  // Leaving the End must drop our fog immediately rather than at the next tick,
  // otherwise the Overworld briefly inherits void haze.
  world.afterEvents.playerDimensionChange.subscribe((event) => {
    if (event.toDimension.id === END_DIMENSION) return;
    if (applied.get(event.player.id)) clearFog(event.player);
    applied.set(event.player.id, undefined);
  });

  world.afterEvents.playerLeave.subscribe((event) => {
    applied.delete(event.playerId);
  });
}
