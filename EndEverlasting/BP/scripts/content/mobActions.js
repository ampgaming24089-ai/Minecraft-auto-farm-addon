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
import { ETERNAL_END_CLIPS } from "./eternalEndClips.js";

/** typeId -> the clips that entity owns. */
const CLIPS = new Map([
  ["voidbound:astral_whale", {
    attack: "animation.voidbound.astral_whale.attack",
    hurt: "animation.voidbound.astral_whale.hurt",
  }],
  ["voidbound:chorus_hopper", {
    attack: "animation.voidbound.chorus_hopper.attack",
    hurt: "animation.voidbound.chorus_hopper.hurt",
  }],
  ["voidbound:crystal_crawler", {
    attack: "animation.voidbound.crystal_crawler.attack",
    hurt: "animation.voidbound.crystal_crawler.hurt",
  }],
  ["voidbound:echo_sentinel", {
    attack: "animation.voidbound.echo_sentinel.attack",
    hurt: "animation.voidbound.echo_sentinel.hurt",
  }],
  ["voidbound:echo_warden", {
    attack: "animation.voidbound.echo_warden.attack",
    hurt: "animation.voidbound.echo_warden.hurt",
  }],
  ["voidbound:ender_beetle", {
    attack: "animation.voidbound.ender_beetle.attack",
    hurt: "animation.voidbound.ender_beetle.hurt",
  }],
  ["voidbound:endstone_golem", {
    attack: "animation.voidbound.endstone_golem.attack",
    hurt: "animation.voidbound.endstone_golem.hurt",
  }],
  ["voidbound:glimmerfin", {
    attack: "animation.voidbound.glimmerfin.attack",
    hurt: "animation.voidbound.glimmerfin.hurt",
  }],
  ["voidbound:lumen_wisp", {
    attack: "animation.voidbound.lumen_wisp.attack",
    hurt: "animation.voidbound.lumen_wisp.hurt",
  }],
  ["voidbound:rift_sovereign", {
    attack: "animation.voidbound.rift_sovereign.attack",
    hurt: "animation.voidbound.rift_sovereign.hurt",
  }],
  ["voidbound:rift_stalker", {
    attack: "animation.voidbound.rift_stalker.attack",
    hurt: "animation.voidbound.rift_stalker.hurt",
  }],
  ["voidbound:shard_wraith", {
    attack: "animation.voidbound.shard_wraith.attack",
    hurt: "animation.voidbound.shard_wraith.hurt",
  }],
  ["voidbound:void_moth", {
    attack: "animation.voidbound.void_moth.attack",
    hurt: "animation.voidbound.void_moth.hurt",
  }],
  ["voidbound:void_serpent", {
    attack: "animation.voidbound.void_serpent.attack",
    hurt: "animation.voidbound.void_serpent.hurt",
  }],
  ["voidbound:void_titan", {
    attack: "animation.voidbound.void_titan.attack",
    hurt: "animation.voidbound.void_titan.hurt",
  }],
  ["voidbound:voidling", {
    attack: "animation.voidbound.voidling.attack",
    hurt: "animation.voidbound.voidling.hurt",
  }],
]);

// The Eternal End roster's clips are generated rather than written out here,
// but they are still literal strings in a source file the checker can read -
// see eternalEndClips.js.
for (const [typeId, clips] of ETERNAL_END_CLIPS) {
  CLIPS.set(typeId, clips);
}

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

/** Drop entries for entities that have gone, so the map cannot grow forever. */
function sweep() {
  const now = system.currentTick;
  for (const [id, until] of busyUntil) {
    if (now >= until) busyUntil.delete(id);
  }
}

export function startMobActions() {
  world.afterEvents.entityHitEntity.subscribe((event) => {
    const clips = CLIPS.get(event.damagingEntity?.typeId);
    if (!clips) return;
    play(event.damagingEntity, clips.attack, ATTACK_SECONDS, 0.15);
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
