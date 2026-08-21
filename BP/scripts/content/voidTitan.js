/**
 * The Void Titan fight, and the core it drops.
 *
 * The Sovereign fights in the air: it lances, blinks and calls its court. The
 * Titan is the opposite reading of the same threat - it never leaves the
 * ground, and everything it does travels along it. Slams ripple outwards,
 * fissures walk in a straight line towards whoever is furthest away, and the
 * only safe answer to either is to stop standing on the floor.
 *
 * Cooldowns live on the entity, as they do for the Sovereign, so a chunk
 * reload mid-fight does not hand the player a free rotation.
 */

import { EntityDamageCause, system, world } from "@minecraft/server";
import { END_DIMENSION } from "../world/generator.js";
import { playEmote } from "./emotes.js";

const BOSS_ID = "voidbound:void_titan";
const CORE_ID = "voidbound:titan_core";

const TICK_INTERVAL = 2;
const MAX_HEALTH = 550;

/** Health fraction at which the Titan stops pacing itself. */
const ENRAGE = 0.4;

const COOLDOWNS = {
  slam: 110,
  fissure: 170,
  quake: 300,
  grab: 220,
};

const AGGRO_RANGE = 36;
const SLAM_RANGE = 8;
const QUAKE_RANGE = 18;
const FISSURE_LENGTH = 16;

function cooldownKey(attack) {
  return `voidbound.tcd.${attack}`;
}

function ready(boss, attack, enraged) {
  let last = 0;
  try {
    const stored = boss.getDynamicProperty(cooldownKey(attack));
    if (typeof stored === "number") last = stored;
  } catch {
    return false;
  }
  return system.currentTick - last >= COOLDOWNS[attack] * (enraged ? 0.6 : 1.0);
}

function markUsed(boss, attack) {
  try {
    boss.setDynamicProperty(cooldownKey(attack), system.currentTick);
  } catch {
    // Unloaded or dying; the attack simply comes up again next tick.
  }
}

function spawnParticle(dimension, effect, location) {
  try {
    dimension.spawnParticle(effect, location);
  } catch {
    // Decoration only.
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

/** Ground level under a column, or undefined if the chunk is not loaded. */
function groundAt(dimension, x, z, near) {
  try {
    if (!dimension.isChunkLoaded({ x, y: near, z })) return undefined;
    const block = dimension.getTopmostBlock({ x, z });
    if (!block) return undefined;
    return block.y + 1;
  } catch {
    return undefined;
  }
}

/** A ring of debris that damages and lifts everyone standing near the Titan. */
function slam(boss) {
  const origin = boss.location;
  spawnParticle(boss.dimension, "voidbound:titan_slam", origin);

  for (const player of playersNear(boss, SLAM_RANGE)) {
    const dx = player.location.x - origin.x;
    const dz = player.location.z - origin.z;
    const distance = Math.hypot(dx, dz) || 1;
    // Falloff, so the edge of the ring is survivable and the centre is not.
    const damage = Math.round(14 - 8 * (distance / SLAM_RANGE));
    try {
      player.applyDamage(Math.max(4, damage), {
        cause: EntityDamageCause.entityAttack,
        damagingEntity: boss,
      });
      player.applyKnockback({ x: (dx / distance) * 1.4, z: (dz / distance) * 1.4 }, 1.1);
      player.onScreenDisplay.setActionBar("§6The ground answers the Titan.");
    } catch {
      // Left, died, or immune to knockback.
    }
  }
}

/**
 * A crack that walks along the floor towards one player.
 *
 * Drawn one block at a time on a timer so it reads as travelling rather than
 * appearing, and so a player who moves out of the line escapes it.
 */
function fissure(boss, target) {
  const origin = boss.location;
  const dx = target.location.x - origin.x;
  const dz = target.location.z - origin.z;
  const length = Math.hypot(dx, dz) || 1;
  const stepX = (dx / length) * 1.4;
  const stepZ = (dz / length) * 1.4;
  const dimension = boss.dimension;
  const steps = Math.min(FISSURE_LENGTH, Math.max(4, Math.round(length)));

  for (let step = 1; step <= steps; step++) {
    system.runTimeout(() => {
      const x = origin.x + stepX * step;
      const z = origin.z + stepZ * step;
      const y = groundAt(dimension, Math.floor(x), Math.floor(z), Math.floor(origin.y)) ?? origin.y;
      spawnParticle(dimension, "voidbound:titan_fissure", { x, y, z });

      let caught;
      try {
        caught = dimension.getPlayers({ location: { x, y, z }, maxDistance: 2.2 });
      } catch {
        return;
      }
      for (const player of caught) {
        try {
          player.applyDamage(8, { cause: EntityDamageCause.magic, damagingEntity: boss });
          player.addEffect("slowness", 60, { amplifier: 1, showParticles: true });
        } catch {
          // Gone by the time the crack reached them.
        }
      }
    }, step * 2);
  }
}

/** The arena-wide version: no safe distance, only a safe height. */
function quake(boss) {
  const origin = boss.location;
  const dimension = boss.dimension;

  for (let ring = 0; ring < 4; ring++) {
    system.runTimeout(() => {
      const radius = 4 + ring * 4;
      for (let i = 0; i < 16; i++) {
        const angle = (i / 16) * Math.PI * 2;
        spawnParticle(dimension, "voidbound:titan_fissure", {
          x: origin.x + Math.cos(angle) * radius,
          y: origin.y,
          z: origin.z + Math.sin(angle) * radius,
        });
      }
    }, ring * 5);
  }

  for (const player of playersNear(boss, QUAKE_RANGE)) {
    // Anyone airborne rides it out - that is the counterplay.
    let grounded = true;
    try {
      grounded = player.isOnGround;
    } catch {
      grounded = true;
    }
    if (!grounded) continue;
    try {
      player.applyDamage(10, { cause: EntityDamageCause.entityAttack, damagingEntity: boss });
      player.addEffect("slowness", 100, { amplifier: 2, showParticles: true });
      player.onScreenDisplay.setActionBar("§cThe island itself shudders. Get off the ground.");
    } catch {
      // Nothing to do.
    }
  }
}

/** Drag the furthest player in, so the fight cannot be won from a ledge. */
function grab(boss, target) {
  const origin = boss.location;
  const dx = origin.x - target.location.x;
  const dz = origin.z - target.location.z;
  const distance = Math.hypot(dx, dz) || 1;
  if (distance < 6) return;

  const dimension = boss.dimension;
  const steps = Math.min(20, Math.round(distance));
  for (let step = 1; step <= steps; step++) {
    const t = step / steps;
    spawnParticle(dimension, "voidbound:titan_fissure", {
      x: target.location.x + dx * t,
      y: target.location.y + 0.2,
      z: target.location.z + dz * t,
    });
  }
  try {
    target.applyKnockback({ x: (dx / distance) * 2.6, z: (dz / distance) * 2.6 }, 0.35);
    target.onScreenDisplay.setActionBar("§6Stone closes around your feet.");
  } catch {
    // Immune or gone.
  }
}

function driveBoss(boss) {
  const enraged = healthFraction(boss) <= ENRAGE;
  const origin = boss.location;

  spawnParticle(boss.dimension, "voidbound:titan_aura", { x: origin.x, y: origin.y + 2.2, z: origin.z });
  if (enraged) {
    spawnParticle(boss.dimension, "voidbound:titan_aura", { x: origin.x, y: origin.y + 4.0, z: origin.z });
  }

  const targets = playersNear(boss, AGGRO_RANGE);
  if (targets.length === 0) return;

  if (ready(boss, "slam", enraged)) {
    slam(boss);
    markUsed(boss, "slam");
    return; // One attack per tick keeps the fight readable.
  }
  if (ready(boss, "fissure", enraged)) {
    fissure(boss, targets[Math.floor(Math.random() * targets.length)]);
    markUsed(boss, "fissure");
    return;
  }
  if (enraged && ready(boss, "quake", enraged)) {
    quake(boss);
    markUsed(boss, "quake");
    return;
  }
  if (ready(boss, "grab", enraged)) {
    // The furthest player, since this attack exists to punish range.
    let furthest = targets[0];
    let best = -1;
    for (const player of targets) {
      const d = Math.hypot(player.location.x - origin.x, player.location.z - origin.z);
      if (d > best) {
        best = d;
        furthest = player;
      }
    }
    grab(boss, furthest);
    markUsed(boss, "grab");
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
      console.warn(`[End Everlasting] titan tick failed: ${error}`);
    }
  }
}

/**
 * The Titan Core: the fight's reward, and a compressed version of the fight.
 *
 * Using it borrows the Titan's own footing for twelve seconds - resistance and
 * strength, plus the slam. The item's own cooldown component handles the wait.
 */
function useCore(player) {
  try {
    player.addEffect("resistance", 240, { amplifier: 2, showParticles: true });
    player.addEffect("strength", 240, { amplifier: 1, showParticles: true });
  } catch {
    return;
  }

  const origin = player.location;
  spawnParticle(player.dimension, "voidbound:titan_slam", origin);
  playEmote(player, "slam");

  let nearby;
  try {
    nearby = player.dimension.getEntities({
      location: origin,
      maxDistance: 6,
      excludeTypes: ["minecraft:player", "minecraft:item"],
    });
  } catch {
    nearby = [];
  }
  for (const entity of nearby) {
    try {
      entity.applyDamage(9, { cause: EntityDamageCause.entityAttack, damagingEntity: player });
      const dx = entity.location.x - origin.x;
      const dz = entity.location.z - origin.z;
      const distance = Math.hypot(dx, dz) || 1;
      entity.applyKnockback({ x: (dx / distance) * 1.8, z: (dz / distance) * 1.8 }, 0.8);
    } catch {
      // Immune, dead, or a mob that ignores knockback.
    }
  }
  try {
    player.onScreenDisplay.setActionBar("§6The Titan's footing is yours.");
  } catch {
    // Cosmetic.
  }
}

export function startVoidTitan() {
  system.runInterval(tick, TICK_INTERVAL);

  world.afterEvents.itemUse.subscribe((event) => {
    if (event.itemStack?.typeId !== CORE_ID) return;
    const player = event.source;
    if (!player?.isValid) return;
    if (player.dimension.id !== END_DIMENSION) {
      try {
        player.onScreenDisplay.setActionBar("§8The core is inert outside the End.");
      } catch {
        // Cosmetic.
      }
      return;
    }
    useCore(player);
  });

  world.afterEvents.entityDie.subscribe((event) => {
    const dead = event.deadEntity;
    if (dead?.typeId !== BOSS_ID) return;
    const at = dead.location;
    const dimension = dead.dimension;

    // It falls apart rather than vanishing: rings of debris, widening.
    for (let ring = 0; ring < 6; ring++) {
      system.runTimeout(() => {
        for (let i = 0; i < 12; i++) {
          const angle = (i / 12) * Math.PI * 2;
          const radius = 1 + ring * 1.6;
          spawnParticle(dimension, "voidbound:titan_fissure", {
            x: at.x + Math.cos(angle) * radius,
            y: at.y + 0.5,
            z: at.z + Math.sin(angle) * radius,
          });
        }
      }, ring * 7);
    }
    try {
      world.sendMessage("§6The Void Titan comes apart. Its watchtower falls silent.");
    } catch {
      // World shutting down.
    }
  });
}
