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

/**
 * Set bonuses, and why they carry more weight than they look like they do.
 *
 * Minecraft caps armour's contribution at 20 points - the damage formula is
 * `damage x (1 - min(20, armour) / 25)`, so 20 points is 80% reduction and
 * nothing in any edition does better. Netherite is exactly 20. Every set in
 * this pack is above that (see tools/balance.py for the table and the three
 * real things the surplus still buys), which means the ladder from the entry
 * suit to the tank suit cannot live in armour points alone.
 *
 * It lives here. Resistance stacks multiplicatively with armour, so each rung
 * is a genuine step: Resistance I on the mid tiers, Resistance II on the tank.
 * That is the difference between "the tooltip says a bigger number" and
 * "you survive the boss".
 */
export function startArmorSetBonuses() {
  system.runInterval(() => {
    for (const player of world.getAllPlayers()) {
      const hurt = healthRatio(player) < 0.3;

      // Wraithsteel is the entry suit and deliberately has no bonus - its
      // 24 points are already a fifth better than netherite.

      if (wornSet(player, "veilsteel")) {
        grant(player, "resistance");
      }
      // Hollowforged: the craftable top tier, and the suit you wear to go
      // mining the deepest ore in the dimension.
      if (wornSet(player, "hollowforged")) {
        grant(player, "resistance");
        grant(player, "haste");
        grant(player, "fire_resistance");
        if (hurt) grant(player, "absorption", 1);
      }
      // Spectral Regalia: escape, not endurance.
      if (wornSet(player, "spectral_regalia")) {
        grant(player, "resistance");
        if (hurt) {
          grant(player, "invisibility");
          grant(player, "water_breathing");
        }
      }
      // Mourner's Shroud: the lightest set in the pack, and the fastest.
      if (wornSet(player, "mourners_shroud")) {
        grant(player, "speed");
        if (hurt) grant(player, "speed", 1);
      }
      // Ashen Demonplate: the tank. Hardest boss, heaviest plate, and the
      // only Resistance II in the pack.
      if (wornSet(player, "ashen_demonplate")) {
        grant(player, "resistance", 1);
        grant(player, "fire_resistance");
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
