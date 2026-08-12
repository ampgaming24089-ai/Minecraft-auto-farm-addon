import { world, system, ItemStack } from "@minecraft/server";
import { HOLLOW_VEIL } from "./world/build.js";
import { startPortalTicking } from "./portal/portal.js";
import { startBossAI } from "./bosses/bossAI.js";
import { registerMobAbilities, startWraithPhasing } from "./mobs/abilities.js";
import { startMobSpawner } from "./mobs/spawner.js";
import { startStructureSpawners } from "./world/spawners.js";
import {
  registerItemHandlers, startPassiveItemEffects, registerFoodConversions, registerIgniterComponent,
} from "./items/tools.js";
import { registerBossWeapons } from "./items/weapons.js";
import { registerDragonEgg } from "./items/dragon.js";
import { startArmorSetBonuses } from "./armor/setBonuses.js";
import { registerShop } from "./ui/shop.js";
import { startAmbience } from "./mobs/ambience.js";
import { startTerrainStreaming } from "./world/terrain.js";
import { startSiteBuilding } from "./world/sites.js";
import { startAtmosphere } from "./world/atmosphere.js";
import { registerTravelCommands } from "./portal/travel.js";

// Custom dimensions must be registered during the restricted "startup"
// phase - see docs/DIMENSION.md for why this replaced the old static
// BP/dimensions/*.json approach.
system.beforeEvents.startup.subscribe((ev) => {
  // Each registration is isolated for the same reason the subsystems below
  // are: one throw in here would take the custom dimension down with it, and
  // a pack whose dimension does not exist has nothing left to offer.
  try {
    ev.dimensionRegistry.registerCustomDimension(HOLLOW_VEIL);
  } catch (err) {
    console.error(`[Hollow Veil] dimension registration failed: ${err}`);
  }
  try {
    // Makes the Soulfire Igniter respond to a single tap on a block. See
    // items/tools.js for why this is needed on top of the event handlers.
    registerIgniterComponent(ev.itemComponentRegistry);
  } catch (err) {
    console.error(`[Hollow Veil] igniter component registration failed: ${err}`);
  }
});

// Each subsystem is started in isolation. Previously these were bare calls,
// so a single throw (a mistyped event name in one file) aborted the whole
// module and silently disabled every subsystem after it - the igniter,
// sigils, dragon egg, shop and boss AI all went dead at once with no
// in-game clue why. Now a broken subsystem reports itself and the rest
// still run.
const failed = [];

function startSubsystem(name, fn) {
  try {
    fn();
  } catch (err) {
    // NOTE: no world.sendMessage here. Script modules run during "early
    // execution", where native world calls are not permitted - calling one
    // throws and aborts the whole module, taking every subsystem after it
    // down. Report to the content log now, and defer the in-game notice to
    // a normal tick.
    console.error(`[Hollow Veil] subsystem "${name}" failed to start: ${err}`);
    failed.push(name);
  }
}

for (const [name, fn] of [
  ["mob abilities", registerMobAbilities],
  ["item handlers", registerItemHandlers],
  ["food conversions", registerFoodConversions],
  ["boss weapons", registerBossWeapons],
  ["dragon egg", registerDragonEgg],
  ["shop UI", registerShop],
  ["portal ticking", startPortalTicking],
  ["travel commands", registerTravelCommands],
  ["boss AI", startBossAI],
  ["wraith phasing", startWraithPhasing],
  ["mob spawner", startMobSpawner],
  ["structure spawners", startStructureSpawners],
  ["terrain streaming", startTerrainStreaming],
  ["site building", startSiteBuilding],
  ["atmosphere", startAtmosphere],
  ["ambience", startAmbience],
  ["passive item effects", startPassiveItemEffects],
  ["armor set bonuses", startArmorSetBonuses],
]) {
  startSubsystem(name, fn);
}

// --- give every new player a journal on first join -----------------------
world.afterEvents.playerSpawn.subscribe((ev) => {
  if (!ev.initialSpawn) return;
  const player = ev.player;
  if (player.getDynamicProperty("hollowveil:got_journal")) return;
  player.setDynamicProperty("hollowveil:got_journal", true);
  try {
    const inv = player.getComponent("minecraft:inventory")?.container;
    inv?.addItem(new ItemStack("hollowveil:journal", 1));
  } catch {
    /* inventory may be full; player can still get one from the Occultist */
  }
});

// Deferred to a real tick for the same early-execution reason.
system.run(() => {
  for (const name of failed) {
    world.sendMessage(`§c[Hollow Veil] "${name}" failed to start - see content log.`);
  }
});
