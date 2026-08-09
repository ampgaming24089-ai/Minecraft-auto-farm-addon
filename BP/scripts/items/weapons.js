import { world } from "@minecraft/server";
import { getNearbyEntities, knockback } from "../lib/combat.js";

const MAX_BURN_STACK = 12;

export function registerBossWeapons() {
  world.afterEvents.entityHurt.subscribe((ev) => {
    const attacker = ev.damageSource.damagingEntity;
    const victim = ev.hurtEntity;
    if (!attacker || attacker.typeId !== "minecraft:player" || !victim) return;

    let held;
    try {
      held = attacker.getComponent("minecraft:equippable")?.getEquipment("Mainhand");
    } catch {
      return;
    }
    if (!held) return;

    switch (held.typeId) {
      case "hollowveil:hollow_kings_reaper":
        hollowKingsReaper(attacker, victim, ev.damage ?? 0);
        break;
      case "hollowveil:wailing_edge":
        wailingEdge(attacker, victim);
        break;
      case "hollowveil:malacodas_fang":
        malacodasFang(victim);
        break;
      default:
        break;
    }
  });
}

function hollowKingsReaper(attacker, victim, damage) {
  try {
    victim.addEffect("wither", 60, { amplifier: 0, showParticles: true });
  } catch {
    /* ignore */
  }
  try {
    const health = attacker.getComponent("minecraft:health");
    if (health) {
      health.setCurrentValue(Math.min(health.effectiveMax, health.currentValue + damage * 0.2));
    }
  } catch {
    /* ignore */
  }
}

function wailingEdge(attacker, victim) {
  if (!attacker.isSneaking) return;
  const nearby = getNearbyEntities(victim.dimension, victim.location, 4, undefined).filter(
    (e) => e.id !== attacker.id && e.typeId !== attacker.typeId
  );
  for (const e of nearby) {
    knockback(e, e.location.x - victim.location.x, e.location.z - victim.location.z, 1.1, 0.4);
  }
  try {
    victim.dimension.spawnParticle("hollowveil:banshee_scream_particle", victim.location);
    victim.dimension.playSound("hollowveil.widow.wail", victim.location);
  } catch {
    /* cosmetic only */
  }
}

function malacodasFang(victim) {
  const stacks = Math.min(MAX_BURN_STACK, (victim.getDynamicProperty("hollowveil:burn_stacks") ?? 0) + 2);
  victim.setDynamicProperty("hollowveil:burn_stacks", stacks);
  try {
    victim.setOnFire(stacks, true);
  } catch {
    /* fire-immune targets simply don't burn */
  }
  if (stacks >= MAX_BURN_STACK && Math.random() < 0.35) {
    try {
      victim.dimension.createExplosion(victim.location, 1.2, {
        causesFire: false,
        breaksBlocks: false,
        allowUnderwater: false,
        source: undefined,
      });
    } catch {
      /* cosmetic-scale explosion only; skip if unsupported */
    }
    victim.setDynamicProperty("hollowveil:burn_stacks", 0);
  }
}
