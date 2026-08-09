import { world, system } from "@minecraft/server";
import { knockback, getNearbyPlayers } from "../lib/combat.js";
import { hasGhostWard } from "../items/tools.js";

const FLEE_CHANCE = 0.12;

function isPlayer(entity) {
  return entity?.typeId === "minecraft:player";
}

export function registerMobAbilities() {
  world.afterEvents.entityHurt.subscribe((ev) => {
    const attacker = ev.damageSource.damagingEntity;
    const victim = ev.hurtEntity;
    if (!attacker || !victim) return;

    switch (attacker.typeId) {
      case "hollowveil:wraith":
        if (isPlayer(victim) && !hasGhostWard(victim)) {
          try {
            victim.addEffect("hunger", 100, { amplifier: 1, showParticles: false });
          } catch {
            /* effect may not exist on some versions; harmless to skip */
          }
        }
        break;
      case "hollowveil:hellhound":
        try {
          victim.setOnFire(4, true);
        } catch {
          /* target may be fire-immune */
        }
        break;
      case "hollowveil:imp":
        if (isPlayer(victim) && Math.random() < FLEE_CHANCE) {
          stealFromPlayer(victim, attacker);
        }
        break;
      default:
        break;
    }

    if (victim.typeId === "hollowveil:fallen_knight") {
      const shielding = victim.getDynamicProperty("hollowveil:shielding");
      if (shielding) {
        try {
          const health = victim.getComponent("minecraft:health");
          const refund = (ev.damage ?? 0) * 0.5;
          if (health && refund > 0) {
            health.setCurrentValue(Math.min(health.effectiveMax, health.currentValue + refund));
          }
        } catch {
          /* health component always present on living mobs; ignore if API shape differs */
        }
      }
    }
  });

  world.afterEvents.dataDrivenEntityTriggerEvent.subscribe((ev) => {
    switch (ev.eventId) {
      case "hollowveil:scream_tick":
        bansheeScream(ev.entity);
        break;
      case "hollowveil:shade_blink":
        shadeBlink(ev.entity);
        break;
      case "hollowveil:shield_up":
        ev.entity.setDynamicProperty("hollowveil:shielding", true);
        break;
      case "hollowveil:shield_down":
        ev.entity.setDynamicProperty("hollowveil:shielding", false);
        break;
      case "hollowveil:go_fleeing":
      case "hollowveil:calm_down":
      case "minecraft:entity_spawned":
        break;
      default:
        break;
    }
  });
}

function stealFromPlayer(player, imp) {
  const inv = player.getComponent("minecraft:inventory")?.container;
  if (!inv) return;
  const candidates = [];
  for (let i = 0; i < inv.size; i++) {
    const stack = inv.getItem(i);
    if (stack && !stack.typeId.startsWith("hollowveil:sigil_")) candidates.push(i);
  }
  if (candidates.length === 0) return;
  const slot = candidates[Math.floor(Math.random() * candidates.length)];
  const stack = inv.getItem(slot);
  if (!stack) return;
  const stolen = stack.clone();
  stolen.amount = 1;
  if (stack.amount <= 1) inv.setItem(slot, undefined);
  else {
    stack.amount -= 1;
    inv.setItem(slot, stack);
  }
  try {
    player.dimension.spawnItem(stolen, imp.location);
  } catch {
    /* if this fails the player simply keeps the item */
  }
  player.sendMessage("§cAn imp snatched something from your bag!");
  try {
    imp.triggerEvent("hollowveil:go_fleeing");
  } catch {
    /* event always defined on the imp entity; ignore if missing */
  }
}

function bansheeScream(banshee) {
  const dim = banshee.dimension;
  const players = getNearbyPlayers(dim, banshee.location, 7);
  for (const p of players) {
    try {
      p.addEffect("nausea", 60, { amplifier: 1, showParticles: false });
    } catch {
      /* ignore */
    }
    knockback(p, p.location.x - banshee.location.x, p.location.z - banshee.location.z, 0.8, 0.4);
  }
  try {
    dim.spawnParticle("hollowveil:banshee_scream_particle", banshee.location);
    dim.playSound("hollowveil.banshee.scream", banshee.location);
  } catch {
    /* purely cosmetic */
  }
}

function shadeBlink(shade) {
  const dim = shade.dimension;
  const players = getNearbyPlayers(dim, shade.location, 10);
  if (players.length === 0) return;
  const target = players[Math.floor(Math.random() * players.length)];
  const angle = Math.random() * Math.PI * 2;
  const dest = {
    x: target.location.x + Math.cos(angle) * 2.5,
    y: target.location.y,
    z: target.location.z + Math.sin(angle) * 2.5,
  };
  try {
    shade.teleport(dest);
    dim.spawnParticle("hollowveil:shade_teleport_particle", shade.location);
  } catch {
    /* if the destination is unloaded/obstructed, just skip this blink */
  }
}

export function startWraithPhasing() {
  system.runInterval(() => {
    for (const dim of dimensionsWithHollowVeilMobs()) {
      const wraiths = dim.getEntities({ type: "hollowveil:wraith" });
      for (const wraith of wraiths) {
        tryPhaseWraith(wraith);
      }
    }
  }, 8);
}

function dimensionsWithHollowVeilMobs() {
  try {
    return [world.getDimension("hollowveil:hollow_veil")];
  } catch {
    return [];
  }
}

function tryPhaseWraith(wraith) {
  const players = getNearbyPlayers(wraith.dimension, wraith.location, 6);
  if (players.length === 0) return;
  const target = players[0];
  const from = wraith.getHeadLocation ? wraith.getHeadLocation() : wraith.location;
  const dir = {
    x: target.location.x - from.x,
    y: target.location.y - from.y,
    z: target.location.z - from.z,
  };
  const dist = Math.hypot(dir.x, dir.y, dir.z);
  if (dist < 1.5 || dist > 6) return;
  const norm = { x: dir.x / dist, y: dir.y / dist, z: dir.z / dist };
  let hit;
  try {
    hit = wraith.dimension.getBlockFromRay(from, norm, { maxDistance: Math.min(dist, 5) });
  } catch {
    return;
  }
  if (!hit || !hit.block || hit.block.isAir) return;
  const beyond = {
    x: hit.block.location.x + norm.x * 2 + 0.5,
    y: hit.block.location.y + 0.5,
    z: hit.block.location.z + norm.z * 2 + 0.5,
  };
  try {
    wraith.teleport(beyond);
  } catch {
    /* obstructed destination: just try again next tick */
  }
}
