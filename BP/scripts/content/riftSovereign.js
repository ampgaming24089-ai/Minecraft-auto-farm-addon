/**
 * The Rift Sovereign fight.
 *
 * Bedrock's behaviour components can give a mob a health bar and a melee
 * swing, but they cannot give it phases, telegraphed attacks or a death
 * sequence. All of that lives here: every two ticks the script reads each
 * living Sovereign's health, picks a phase, and runs whichever attack is off
 * cooldown.
 *
 * Cooldowns are stored on the entity rather than in a map keyed by id, so they
 * survive the chunk unloading and reloading mid-fight.
 */

import { EntityDamageCause, system, world } from "@minecraft/server";
import { END_DIMENSION } from "../world/generator.js";

const BOSS_ID = "voidbound:rift_sovereign";

const TICK_INTERVAL = 2;

/** Health fractions at which the fight escalates. */
const PHASE_TWO = 0.66;
const PHASE_THREE = 0.33;

const MAX_HEALTH = 400;

/** Attack cooldowns in ticks, before the per-phase speed-up. */
const COOLDOWNS = {
  lance: 60,
  summon: 320,
  shockwave: 180,
  blink: 240,
};

const AGGRO_RANGE = 40;
const SHOCKWAVE_RANGE = 9;

function cooldownKey(attack) {
  return `voidbound.cd.${attack}`;
}

function ready(boss, attack, phase) {
  let last = 0;
  try {
    const stored = boss.getDynamicProperty(cooldownKey(attack));
    if (typeof stored === "number") last = stored;
  } catch {
    return false;
  }
  // Phase 2 shaves a fifth off every cooldown, phase 3 a third.
  const scale = phase === 3 ? 0.66 : phase === 2 ? 0.8 : 1.0;
  return system.currentTick - last >= COOLDOWNS[attack] * scale;
}

function markUsed(boss, attack) {
  try {
    boss.setDynamicProperty(cooldownKey(attack), system.currentTick);
  } catch {
    // A dead or unloaded boss cannot store cooldowns; the attack simply
    // repeats next tick, which is harmless.
  }
}

function spawnParticle(dimension, effect, location) {
  try {
    dimension.spawnParticle(effect, location);
  } catch {
    // Particles are decoration; an unloaded chunk is not an error.
  }
}

function playersNear(boss, radius) {
  try {
    return boss.dimension
      .getPlayers({ location: boss.location, maxDistance: radius })
      .filter((player) => player.isValid);
  } catch {
    return [];
  }
}

function healthFraction(boss) {
  try {
    const health = boss.getComponent("minecraft:health");
    if (!health) return 1;
    return Math.max(0, Math.min(1, health.currentValue / (health.effectiveMax || MAX_HEALTH)));
  } catch {
    return 1;
  }
}

/** A bolt drawn along the line to one player, damaging whoever it reaches. */
function lance(boss, target) {
  const from = boss.location;
  const to = target.location;
  const dx = to.x - from.x;
  const dy = to.y + 1 - (from.y + 2);
  const dz = to.z - from.z;
  const length = Math.hypot(dx, dy, dz) || 1;
  const steps = Math.min(48, Math.max(6, Math.round(length)));

  for (let step = 1; step <= steps; step++) {
    const t = step / steps;
    spawnParticle(boss.dimension, "voidbound:rift_lance", {
      x: from.x + dx * t,
      y: from.y + 2 + dy * t,
      z: from.z + dz * t,
    });
  }
  try {
    target.applyDamage(7, { cause: EntityDamageCause.magic, damagingEntity: boss });
  } catch {
    // Target may have died or left between selection and impact.
  }
}

/** A ring that knocks everyone in the arena off their feet. */
function shockwave(boss) {
  const origin = boss.location;
  spawnParticle(boss.dimension, "voidbound:rift_shockwave", origin);
  spawnParticle(boss.dimension, "voidbound:rift_burst", { x: origin.x, y: origin.y + 1.5, z: origin.z });

  for (const player of playersNear(boss, SHOCKWAVE_RANGE)) {
    const dx = player.location.x - origin.x;
    const dz = player.location.z - origin.z;
    const distance = Math.hypot(dx, dz) || 1;
    try {
      player.applyDamage(9, { cause: EntityDamageCause.entityAttack, damagingEntity: boss });
      player.applyKnockback({ x: (dx / distance) * 2.2, z: (dz / distance) * 2.2 }, 0.8);
      player.onScreenDisplay.setActionBar("§dThe rift buckles.");
    } catch {
      // Player left, died, or is in a mode that ignores knockback.
    }
  }
}

/** Reposition behind the target so the fight cannot be kited in a straight line. */
function blink(boss, target) {
  const origin = boss.location;
  spawnParticle(boss.dimension, "voidbound:rift_burst", { x: origin.x, y: origin.y + 1.5, z: origin.z });

  const angle = Math.random() * Math.PI * 2;
  const destination = {
    x: target.location.x + Math.cos(angle) * 5,
    y: target.location.y + 3,
    z: target.location.z + Math.sin(angle) * 5,
  };
  try {
    boss.teleport(destination, { dimension: boss.dimension });
    spawnParticle(boss.dimension, "voidbound:rift_burst", destination);
  } catch {
    // Blocked destination - stay put and try again on the next cooldown.
  }
}

/** Call in the guard. Phase 3 sends sentinels instead of stalkers. */
function summon(boss, phase) {
  const origin = boss.location;
  const roster = phase === 3
    ? ["voidbound:ender_ghost", "voidbound:void_wisp"]
    : ["voidbound:void_stalker", "voidbound:end_spider"];
  const count = phase === 3 ? 3 : 4;

  for (let i = 0; i < count; i++) {
    const angle = (i / count) * Math.PI * 2 + Math.random();
    const at = {
      x: origin.x + Math.cos(angle) * 6,
      y: origin.y,
      z: origin.z + Math.sin(angle) * 6,
    };
    try {
      boss.dimension.spawnEntity(roster[i % roster.length], at);
      spawnParticle(boss.dimension, "voidbound:rift_burst", at);
    } catch {
      // No room to spawn there; skip this one.
    }
  }
  for (const player of playersNear(boss, AGGRO_RANGE)) {
    try {
      player.onScreenDisplay.setActionBar("§5The Sovereign calls its court.");
    } catch {
      // Cosmetic only.
    }
  }
}

function driveBoss(boss) {
  const fraction = healthFraction(boss);
  const phase = fraction <= PHASE_THREE ? 3 : fraction <= PHASE_TWO ? 2 : 1;

  // Aura, always. Denser as the fight escalates.
  const origin = boss.location;
  spawnParticle(boss.dimension, "voidbound:sovereign_aura", { x: origin.x, y: origin.y + 1.6, z: origin.z });
  if (phase >= 2) {
    spawnParticle(boss.dimension, "voidbound:sovereign_aura", { x: origin.x, y: origin.y + 2.6, z: origin.z });
  }

  const targets = playersNear(boss, AGGRO_RANGE);
  if (targets.length === 0) return;
  const target = targets[Math.floor(Math.random() * targets.length)];

  if (ready(boss, "lance", phase)) {
    lance(boss, target);
    markUsed(boss, "lance");
    return; // One attack per tick keeps the fight readable.
  }
  if (phase >= 2 && ready(boss, "shockwave", phase)) {
    shockwave(boss);
    markUsed(boss, "shockwave");
    return;
  }
  if (phase >= 2 && ready(boss, "blink", phase)) {
    blink(boss, target);
    markUsed(boss, "blink");
    return;
  }
  if (ready(boss, "summon", phase)) {
    summon(boss, phase);
    markUsed(boss, "summon");
  }
}

function tick() {
  let dimension;
  try {
    dimension = world.getDimension(END_DIMENSION);
  } catch {
    return;
  }
  let bosses;
  try {
    bosses = dimension.getEntities({ type: BOSS_ID });
  } catch {
    return;
  }
  for (const boss of bosses) {
    if (!boss.isValid) continue;
    try {
      driveBoss(boss);
    } catch (error) {
      console.warn(`[Endrealm] sovereign tick failed: ${error}`);
    }
  }
}

export function startRiftSovereign() {
  system.runInterval(tick, TICK_INTERVAL);

  world.afterEvents.entityDie.subscribe((event) => {
    const dead = event.deadEntity;
    if (dead?.typeId !== BOSS_ID) return;
    const at = dead.location;
    const dimension = dead.dimension;

    // A slow collapse rather than one more burst, so the end of the fight
    // reads differently from every attack that preceded it.
    for (let delay = 0; delay <= 40; delay += 8) {
      system.runTimeout(() => {
        spawnParticle(dimension, "voidbound:sovereign_death", { x: at.x, y: at.y + 1.5, z: at.z });
      }, delay);
    }
    try {
      world.sendMessage("§5The Rift Sovereign collapses. The void closes over it.");
    } catch {
      // Nothing to do if the world is shutting down.
    }
  });
}
