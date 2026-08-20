/**
 * Per-region atmosphere.
 *
 * Two things are going on here.
 *
 * First, the client biome file gives the whole End one look, because Bedrock
 * exposes a single `minecraft:the_end` biome to bind lighting and fog to. To
 * get more than one mood out of it, this pushes a fog definition onto the
 * player's fog stack - the layer that sits above biome fog - based on where
 * they actually are: down in the void, inside a grove, or beside a rift.
 *
 * Second, the fog stack is pushed to from script rather than left to the
 * client biome alone. A client biome file is all-or-nothing: if any one
 * identifier in it fails to resolve, the engine rejects the whole file and the
 * End silently falls back to vanilla fog, sky colour and lighting. Pushing a
 * base layer from here means the fog survives that failure, so the dimension
 * still reads as this pack's even when the biome binding does not take.
 *
 * Each player carries at most two pushed fogs under fixed handles, and they
 * are only re-pushed when the region actually changes, so this costs a couple
 * of commands per boundary crossing rather than any per-tick work.
 */

import { system, world } from "@minecraft/server";
import { distanceTo, sitesNear } from "./sites.js";
import { END_DIMENSION } from "./generator.js";

/** Always-on layer while in the End. */
const BASE_HANDLE = "voidbound_base";
const BASE_FOG = "voidbound:fog_end_open";

/** Region override, pushed on top of the base so it wins where it applies. */
const REGION_HANDLE = "voidbound_region";

/** Below this height the player is out over the void rather than on an island. */
const VOID_HEIGHT = 0;

const APPLY_INTERVAL_TICKS = 20;

/** playerId -> { base: boolean, region: string | undefined } */
const applied = new Map();

function stateFor(playerId) {
  let state = applied.get(playerId);
  if (!state) {
    state = { base: false, region: undefined };
    applied.set(playerId, state);
  }
  return state;
}

function regionFogFor(player) {
  const position = player.location;
  if (position.y < VOID_HEIGHT) return "voidbound:fog_void_deep";

  for (const site of sitesNear(position.x, position.z, 1)) {
    if (!site.blueprint.fog) continue;
    if (distanceTo(site, position) < site.blueprint.radius + 24) return site.blueprint.fog;
  }
  return undefined;
}

function runFogCommand(player, command) {
  try {
    player.runCommand(command);
    return true;
  } catch {
    // The player may have left, or there was nothing pushed to remove.
    return false;
  }
}

function apply() {
  for (const player of world.getAllPlayers()) {
    const inEnd = player.dimension.id === END_DIMENSION;
    const state = stateFor(player.id);

    // Base layer first, so a region push lands on top of it.
    if (inEnd !== state.base) {
      if (inEnd) {
        state.base = runFogCommand(player, `fog @s push ${BASE_FOG} ${BASE_HANDLE}`);
      } else {
        runFogCommand(player, `fog @s remove ${BASE_HANDLE}`);
        state.base = false;
      }
    }

    const wanted = inEnd ? regionFogFor(player) : undefined;
    if (wanted === state.region) continue;

    if (state.region) runFogCommand(player, `fog @s remove ${REGION_HANDLE}`);
    if (wanted && !runFogCommand(player, `fog @s push ${wanted} ${REGION_HANDLE}`)) {
      state.region = undefined;
      continue;
    }
    state.region = wanted;
  }
}

function clearAll(player) {
  runFogCommand(player, `fog @s remove ${REGION_HANDLE}`);
  runFogCommand(player, `fog @s remove ${BASE_HANDLE}`);
}

export function startAtmosphere() {
  system.runInterval(apply, APPLY_INTERVAL_TICKS);

  // Leaving the End must drop our fog immediately rather than at the next
  // tick, otherwise the Overworld briefly inherits void haze.
  world.afterEvents.playerDimensionChange.subscribe((event) => {
    if (event.toDimension.id === END_DIMENSION) return;
    clearAll(event.player);
    applied.set(event.player.id, { base: false, region: undefined });
  });

  world.afterEvents.playerLeave.subscribe((event) => {
    applied.delete(event.playerId);
  });
}
