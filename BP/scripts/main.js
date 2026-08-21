/**
 * End Ascendant - entry point.
 *
 * Four systems, started once at load:
 *   sites/generator  places seed-derived structures ahead of the player
 *   atmosphere       swaps fog by region, above what the client biome provides
 *   ambience         drifting motes and falling streaks, so the sky has motion
 *   flight control   pulls flyers back when they climb or drift over the void
 *   discovery        acknowledges arriving somewhere new
 *   rift compass     reads the structure map and points at it
 *   armour set       grants the End Ascendant set bonus in the End
 *   ender sapling    grows planted saplings into End trees
 *   rift sovereign   drives the boss fight's phases, attacks and death
 *   void titan       drives the Titan's ground attacks and its core item
 *   utility items    the Rift Charm's anchor and the Echo Horn's survey
 *   waystones        the attuned travel network and its menu
 *
 * Everything visual - lighting, atmospherics, colour grading, PBR - is data in
 * the resource pack and needs no script at all. This file only covers the
 * things Bedrock has no data-driven answer for.
 */

import { world } from "@minecraft/server";
import { startArmorSet } from "./content/armorSet.js";
import { startEnderSapling } from "./content/enderSapling.js";
import { startRiftCompass } from "./content/riftCompass.js";
import { startRiftSovereign } from "./content/riftSovereign.js";
import { startVoidTitan } from "./content/voidTitan.js";
import { startUtilityItems } from "./content/utilityItems.js";
import { startWaystones } from "./content/waystones.js";
import { startAmbience } from "./world/ambience.js";
import { startAtmosphere } from "./world/atmosphere.js";
import { startDiscovery } from "./world/discovery.js";
import { startFlightControl } from "./world/flightControl.js";
import { startGenerator } from "./world/generator.js";

function start() {
  startGenerator();
  startAtmosphere();
  startAmbience();
  startFlightControl();
  startDiscovery();
  startRiftCompass();
  startArmorSet();
  startEnderSapling();
  startRiftSovereign();
  startVoidTitan();
  startUtilityItems();
  startWaystones();
  console.log("[End Ascendant] End systems online");
}

// worldLoad fires once the world is ready for world.seed and player queries.
// Subscribing at module scope is safe; the callback runs outside early execution.
world.afterEvents.worldLoad.subscribe(() => {
  try {
    start();
  } catch (error) {
    console.error(`[End Ascendant] failed to start: ${error}`);
  }
});
