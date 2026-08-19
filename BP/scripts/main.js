/**
 * Voidbound - entry point.
 *
 * Four systems, started once at load:
 *   sites/generator  places seed-derived structures ahead of the player
 *   atmosphere       swaps fog by region, above what the client biome provides
 *   discovery        acknowledges arriving somewhere new
 *   rift compass     reads the structure map and points at it
 *
 * Everything visual - lighting, atmospherics, colour grading, PBR - is data in
 * the resource pack and needs no script at all. This file only covers the
 * things Bedrock has no data-driven answer for.
 */

import { world } from "@minecraft/server";
import { startRiftCompass } from "./content/riftCompass.js";
import { startAtmosphere } from "./world/atmosphere.js";
import { startDiscovery } from "./world/discovery.js";
import { startGenerator } from "./world/generator.js";

function start() {
  startGenerator();
  startAtmosphere();
  startDiscovery();
  startRiftCompass();
  console.log("[Voidbound] End systems online");
}

// worldLoad fires once the world is ready for world.seed and player queries.
// Subscribing at module scope is safe; the callback runs outside early execution.
world.afterEvents.worldLoad.subscribe(() => {
  try {
    start();
  } catch (error) {
    console.error(`[Voidbound] failed to start: ${error}`);
  }
});
