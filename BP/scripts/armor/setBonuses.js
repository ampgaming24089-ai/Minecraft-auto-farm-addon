import { world, system } from "@minecraft/server";

const INTERVAL = 20;
const SLOTS = ["Head", "Chest", "Legs", "Feet"];

function wornSet(player, prefix) {
  const equip = player.getComponent("minecraft:equippable");
  if (!equip) return false;
  try {
    return SLOTS.every((slot) => equip.getEquipment(slot)?.typeId === `hollowveil:${prefix}_${slotName(slot)}`);
  } catch {
    return false;
  }
}

function slotName(slot) {
  switch (slot) {
    case "Head":
      return "helmet";
    case "Chest":
      return "chestplate";
    case "Legs":
      return "leggings";
    case "Feet":
      return "boots";
    default:
      return slot.toLowerCase();
  }
}

function healthRatio(player) {
  const h = player.getComponent("minecraft:health");
  if (!h) return 1;
  return h.currentValue / h.effectiveMax;
}

function grant(player, effect, amplifier = 0) {
  try {
    player.addEffect(effect, INTERVAL + 5, { amplifier, showParticles: false });
  } catch {
    /* effect id may differ across versions; skip gracefully */
  }
}

export function startArmorSetBonuses() {
  system.runInterval(() => {
    for (const player of world.getAllPlayers()) {
      if (wornSet(player, "spectral_regalia") && healthRatio(player) < 0.3) {
        grant(player, "invisibility");
        grant(player, "water_breathing");
      }
      if (wornSet(player, "mourners_shroud")) {
        if (healthRatio(player) < 0.3) grant(player, "speed", 1);
      }
      if (wornSet(player, "ashen_demonplate")) {
        grant(player, "fire_resistance");
        grant(player, "resistance");
      }
      // Hollowforged is the craftable top tier - better raw protection than
      // any boss set - yet it was the only full set in the pack with no set
      // bonus at all, which made the three boss sets feel like a downgrade
      // for no reason. Haste and fire resistance suit what it is: the armour
      // you wear to go mining the deepest ore in the dimension.
      if (wornSet(player, "hollowforged")) {
        grant(player, "haste");
        grant(player, "fire_resistance");
        if (healthRatio(player) < 0.3) grant(player, "absorption", 1);
      }
    }
  }, INTERVAL);

  world.afterEvents.entityHurt.subscribe((ev) => {
    if (ev.hurtEntity?.typeId !== "minecraft:player") return;
    if (ev.damageSource.cause !== "fall") return;
    if (!wornSet(ev.hurtEntity, "mourners_shroud")) return;
    try {
      const health = ev.hurtEntity.getComponent("minecraft:health");
      const refund = (ev.damage ?? 0) * 0.5;
      if (health && refund > 0) {
        health.setCurrentValue(Math.min(health.effectiveMax, health.currentValue + refund));
      }
    } catch {
      /* best effort */
    }
  });
}
