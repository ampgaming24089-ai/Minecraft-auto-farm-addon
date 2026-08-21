/**
 * Attack and hurt reactions for the pack's mobs.
 *
 * The alert stance and the death collapse are client-side: an animation
 * controller reads `query.has_target` and `query.is_alive` and needs nothing
 * from script. A swing landing is different - no Molang query can see it, and
 * hooking `minecraft:behavior.delayed_attack` would mean retuning every mob's
 * combat to get an animation. So those two fire from here instead, through
 * `/playanimation`, which reaches any entity's skeleton without touching its
 * behaviour at all.
 *
 * Identifiers are written out in full rather than assembled from the type id,
 * so `check:ids` can read them out of this file and resolve every one against
 * the resource pack. A name built at runtime is a name no validator can see.
 */

import { system, world } from "@minecraft/server";

/** typeId -> the clips that entity owns. */
const CLIPS = new Map([
  ["voidbound:astral_whale", {
    attack: "animation.voidbound.astral_whale.attack",
    hurt: "animation.voidbound.astral_whale.hurt",
  }],
  ["voidbound:chorus_cow", {
    attack: "animation.voidbound.chorus_cow.attack",
    hurt: "animation.voidbound.chorus_cow.hurt",
  }],
  ["voidbound:chorus_fiend", {
    attack: "animation.voidbound.chorus_fiend.attack",
    hurt: "animation.voidbound.chorus_fiend.hurt",
  }],
  ["voidbound:corrupted_enderman", {
    attack: "animation.voidbound.corrupted_enderman.attack",
    hurt: "animation.voidbound.corrupted_enderman.hurt",
  }],
  ["voidbound:echo_warden", {
    attack: "animation.voidbound.echo_warden.attack",
    hurt: "animation.voidbound.echo_warden.hurt",
  }],
  ["voidbound:end_crab", {
    attack: "animation.voidbound.end_crab.attack",
    hurt: "animation.voidbound.end_crab.hurt",
  }],
  ["voidbound:end_king", {
    attack: "animation.voidbound.end_king.attack",
    hurt: "animation.voidbound.end_king.hurt",
  }],
  ["voidbound:end_spider", {
    attack: "animation.voidbound.end_spider.attack",
    hurt: "animation.voidbound.end_spider.hurt",
  }],
  ["voidbound:end_villager", {
    attack: "animation.voidbound.end_villager.attack",
    hurt: "animation.voidbound.end_villager.hurt",
  }],
  ["voidbound:ender_bird", {
    attack: "animation.voidbound.ender_bird.attack",
    hurt: "animation.voidbound.ender_bird.hurt",
  }],
  ["voidbound:ender_deer", {
    attack: "animation.voidbound.ender_deer.attack",
    hurt: "animation.voidbound.ender_deer.hurt",
  }],
  ["voidbound:ender_ghost", {
    attack: "animation.voidbound.ender_ghost.attack",
    hurt: "animation.voidbound.ender_ghost.hurt",
  }],
  ["voidbound:ender_overlord", {
    attack: "animation.voidbound.ender_overlord.attack",
    hurt: "animation.voidbound.ender_overlord.hurt",
  }],
  ["voidbound:endermite_hive", {
    attack: "animation.voidbound.endermite_hive.attack",
    hurt: "animation.voidbound.endermite_hive.hurt",
  }],
  ["voidbound:endstone_golem", {
    attack: "animation.voidbound.endstone_golem.attack",
    hurt: "animation.voidbound.endstone_golem.hurt",
  }],
  ["voidbound:obsidian_beast", {
    attack: "animation.voidbound.obsidian_beast.attack",
    hurt: "animation.voidbound.obsidian_beast.hurt",
  }],
  ["voidbound:purpur_golem", {
    attack: "animation.voidbound.purpur_golem.attack",
    hurt: "animation.voidbound.purpur_golem.hurt",
  }],
  ["voidbound:rift_sovereign", {
    attack: "animation.voidbound.rift_sovereign.attack",
    hurt: "animation.voidbound.rift_sovereign.hurt",
  }],
  ["voidbound:shulker_beast", {
    attack: "animation.voidbound.shulker_beast.attack",
    hurt: "animation.voidbound.shulker_beast.hurt",
  }],
  ["voidbound:sky_ray", {
    attack: "animation.voidbound.sky_ray.attack",
    hurt: "animation.voidbound.sky_ray.hurt",
  }],
  ["voidbound:teleporter", {
    attack: "animation.voidbound.teleporter.attack",
    hurt: "animation.voidbound.teleporter.hurt",
  }],
  ["voidbound:void_dragon", {
    attack: "animation.voidbound.void_dragon.attack",
    hurt: "animation.voidbound.void_dragon.hurt",
  }],
  ["voidbound:void_hog", {
    attack: "animation.voidbound.void_hog.attack",
    hurt: "animation.voidbound.void_hog.hurt",
  }],
  ["voidbound:void_slime", {
    attack: "animation.voidbound.void_slime.attack",
    hurt: "animation.voidbound.void_slime.hurt",
  }],
  ["voidbound:void_stalker", {
    attack: "animation.voidbound.void_stalker.attack",
    hurt: "animation.voidbound.void_stalker.hurt",
  }],
  ["voidbound:void_titan", {
    attack: "animation.voidbound.void_titan.attack",
    hurt: "animation.voidbound.void_titan.hurt",
  }],
  ["voidbound:void_wisp", {
    attack: "animation.voidbound.void_wisp.attack",
    hurt: "animation.voidbound.void_wisp.hurt",
  }],
]);

/**
 * What a landed hit throws off, per mob.
 *
 * A swing with no particle reads as a swing that missed - the animation says
 * something happened, and then nothing on screen agrees with it. So each mob
 * has a signature: obsidian throws sparks, the slime throws gobbets, the cold
 * things throw motes. A mob with no entry here still swings, it just does not
 * spray, which is the right default for something with no obvious material.
 */
const IMPACTS = new Map([
  ["voidbound:obsidian_beast", "voidbound:hit_ember"],
  ["voidbound:end_king", "voidbound:hit_ember"],
  ["voidbound:purpur_golem", "voidbound:hit_stone"],
  ["voidbound:endstone_golem", "voidbound:hit_stone"],
  ["voidbound:void_slime", "voidbound:hit_slime"],
  ["voidbound:chorus_fiend", "voidbound:hit_slime"],
  ["voidbound:end_spider", "voidbound:hit_chitin"],
  ["voidbound:end_crab", "voidbound:hit_chitin"],
  ["voidbound:endermite_hive", "voidbound:hit_chitin"],
  ["voidbound:shulker_beast", "voidbound:hit_chitin"],
  ["voidbound:void_hog", "voidbound:hit_chitin"],
  ["voidbound:ender_ghost", "voidbound:hit_frost"],
  ["voidbound:void_wisp", "voidbound:hit_frost"],
  ["voidbound:echo_warden", "voidbound:hit_frost"],
  ["voidbound:void_stalker", "voidbound:hit_void"],
  ["voidbound:corrupted_enderman", "voidbound:hit_void"],
  ["voidbound:teleporter", "voidbound:hit_void"],
  ["voidbound:void_dragon", "voidbound:hit_void"],
  ["voidbound:ender_overlord", "voidbound:hit_void"],
  ["voidbound:rift_sovereign", "voidbound:hit_void"],
  ["voidbound:void_titan", "voidbound:hit_ember"],
]);

/** Trails for the things that are seen against the sky before they are
 *  identified. Emitted from the flight controller's own sweep. */
export const FLIGHT_TRAILS = new Map([
  ["voidbound:astral_whale", "voidbound:trail_astral"],
  ["voidbound:sky_ray", "voidbound:trail_cold"],
  ["voidbound:ender_bird", "voidbound:trail_cold"],
  ["voidbound:void_wisp", "voidbound:trail_cold"],
  ["voidbound:ender_ghost", "voidbound:trail_cold"],
  ["voidbound:void_dragon", "voidbound:trail_void"],
  ["voidbound:ender_overlord", "voidbound:trail_void"],
]);

/**
 * The *longest* clip of each kind, in seconds - a whale's swing runs 0.9s
 * where a beetle's runs 0.55s. One number for all of them is safe because
 * every attack and hurt clip ends back at its rest pose: a short clip that
 * holds its last frame for a few extra ticks holds a pose identical to not
 * playing at all. Only the death clips end away from rest, and those are
 * driven by the animation controller, not from here.
 */
const ATTACK_SECONDS = 0.9;
const HURT_SECONDS = 0.6;

/** One reaction at a time per entity, so a flurry of hits does not stack. */
const busyUntil = new Map();

function play(entity, clip, seconds, blend) {
  if (!entity?.isValid) return false;
  const now = system.currentTick;
  if (now < (busyUntil.get(entity.id) ?? 0)) return false;

  // Without a stop expression the final keyframe holds and the mob freezes
  // mid-swing, which is far worse than no animation at all.
  const stop = `query.anim_time >= ${seconds.toFixed(2)}`;
  try {
    entity.runCommand(`playanimation @s ${clip} none ${blend} "${stop}" ea_react`);
  } catch {
    return false;
  }
  busyUntil.set(entity.id, now + Math.ceil(seconds * 20));
  return true;
}

/**
 * Throw a mob's signature burst at the point of a landed hit.
 *
 * Aimed at the victim's chest rather than its feet - a puff at ankle height
 * under a three-block mob is a puff nobody sees - and spawned in the victim's
 * dimension, because the attacker may already have been knocked elsewhere.
 */
function spray(attacker, victim, effect) {
  if (!effect || !victim?.isValid) return;
  const at = victim.location;
  try {
    victim.dimension.spawnParticle(effect, {
      x: at.x,
      y: at.y + 1.0,
      z: at.z,
    });
  } catch {
    // A particle in an unloaded chunk, or one the client has not got yet.
  }
}

/** Drop entries for entities that have gone, so the map cannot grow forever. */
function sweep() {
  const now = system.currentTick;
  for (const [id, until] of busyUntil) {
    if (now >= until) busyUntil.delete(id);
  }
}

export function startMobActions() {
  world.afterEvents.entityHitEntity.subscribe((event) => {
    const attacker = event.damagingEntity;
    const clips = CLIPS.get(attacker?.typeId);
    if (!clips) return;
    play(attacker, clips.attack, ATTACK_SECONDS, 0.15);
    spray(attacker, event.hitEntity, IMPACTS.get(attacker.typeId));
  });

  world.afterEvents.entityHurt.subscribe((event) => {
    const clips = CLIPS.get(event.hurtEntity?.typeId);
    if (!clips) return;
    // An attacker mid-swing should finish the swing rather than flinch out of
    // it, so a hurt never interrupts an attack already playing.
    play(event.hurtEntity, clips.hurt, HURT_SECONDS, 0.1);
  });

  system.runInterval(sweep, 200);
}
