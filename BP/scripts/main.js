import { world, system, ItemStack } from "@minecraft/server";
import { HOLLOW_VEIL } from "./world/build.js";
import { startPortalTicking } from "./portal/portal.js";
import { startBossAI } from "./bosses/bossAI.js";
import { registerMobAbilities, startWraithPhasing } from "./mobs/abilities.js";
import { startMobSpawner } from "./mobs/spawner.js";
import { startStructureSpawners } from "./world/spawners.js";
import { registerItemHandlers, startPassiveItemEffects, registerFoodConversions } from "./items/tools.js";
import { registerBossWeapons } from "./items/weapons.js";
import { registerDragonEgg } from "./items/dragon.js";
import { startArmorSetBonuses } from "./armor/setBonuses.js";
import { registerShop } from "./ui/shop.js";
import { startAmbience } from "./mobs/ambience.js";

// Custom dimensions must be registered during the restricted "startup"
// phase - see docs/DIMENSION.md for why this replaced the old static
// BP/dimensions/*.json approach.
system.beforeEvents.startup.subscribe((ev) => {
  ev.dimensionRegistry.registerCustomDimension(HOLLOW_VEIL);
});

// Each subsystem is started in isolation. Previously these were bare calls,
// so a single throw (a mistyped event name in one file) aborted the whole
// module and silently disabled every subsystem after it - the igniter,
// sigils, dragon egg, shop and boss AI all went dead at once with no
// in-game clue why. Now a broken subsystem reports itself and the rest
// still run.
function startSubsystem(name, fn) {
  try {
    fn();
  } catch (err) {
    console.error(`[Hollow Veil] subsystem "${name}" failed to start: ${err}`);
    world.sendMessage(`§c[Hollow Veil] "${name}" failed to start - see content log.`);
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
  ["boss AI", startBossAI],
  ["wraith phasing", startWraithPhasing],
  ["mob spawner", startMobSpawner],
  ["structure spawners", startStructureSpawners],
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

world.sendMessage("§5[Hollow Veil] §7Addon loaded.");
