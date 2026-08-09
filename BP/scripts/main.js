import { world, system, ItemStack } from "@minecraft/server";
import { HOLLOW_VEIL } from "./world/build.js";
import { startPortalTicking } from "./portal/portal.js";
import { startBossAI } from "./bosses/bossAI.js";
import { registerMobAbilities, startWraithPhasing } from "./mobs/abilities.js";
import { startMobSpawner } from "./mobs/spawner.js";
import { startStructureSpawners } from "./world/spawners.js";
import { registerItemHandlers, startPassiveItemEffects } from "./items/tools.js";
import { registerBossWeapons } from "./items/weapons.js";
import { registerDragonEgg } from "./items/dragon.js";
import { startArmorSetBonuses } from "./armor/setBonuses.js";

// Custom dimensions must be registered during the restricted "startup"
// phase - see docs/DIMENSION.md for why this replaced the old static
// BP/dimensions/*.json approach.
system.beforeEvents.startup.subscribe((ev) => {
  ev.dimensionRegistry.registerCustomDimension(HOLLOW_VEIL);
});

registerMobAbilities();
registerItemHandlers();
registerBossWeapons();
registerDragonEgg();

// --- one-time subsystem start -------------------------------------------
startPortalTicking();
startBossAI();
startWraithPhasing();
startMobSpawner();
startStructureSpawners();
startPassiveItemEffects();
startArmorSetBonuses();

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
