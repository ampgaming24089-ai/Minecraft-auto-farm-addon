/**
 * Player action animations, fired at moments the game already cares about.
 *
 * The continuous half of the animation pack - the sprint lean, the fall brace,
 * the draw tremor - is pure client data and needs nothing from here. This is
 * the other half: one-shot poses that no Molang query can predict, because
 * they answer events. Killing a boss, arriving through a waystone, biting an
 * ender fruit, driving the Titan Core into the floor.
 *
 * `/playanimation` is the only route from script to a player's skeleton, so
 * that is what this uses. It takes the animation, a state to fall back to, a
 * blend-out time and a stop expression; passing an empty next state and a
 * timed stop expression makes it play once and release the bones cleanly.
 *
 * An emote never blocks anything. If the command fails - an old client, a
 * player who left mid-frame - the game carries on exactly as before.
 */

import { system, world } from "@minecraft/server";
import { END_DIMENSION } from "../world/generator.js";

/**
 * Clip identifiers are written out in full rather than assembled from a
 * prefix, so `check:ids` can find them by reading the source and resolve each
 * one against the animation file. A name assembled at runtime is a name no
 * validator can see.
 *
 * `length` is in seconds and must match each clip's own animation_length: the
 * stop expression is built from it, and a clip that outlives its entry here
 * would hold its last pose instead of releasing the bones.
 */
const EMOTES = {
  victory: { clip: "animation.voidbound.player.emote_victory", length: 1.8, blend: 0.35 },
  reach: { clip: "animation.voidbound.player.emote_reach", length: 1.0, blend: 0.25 },
  slam: { clip: "animation.voidbound.player.emote_slam", length: 0.85, blend: 0.2 },
  savour: { clip: "animation.voidbound.player.emote_savour", length: 1.35, blend: 0.3 },
  salute: { clip: "animation.voidbound.player.emote_salute", length: 1.25, blend: 0.3 },
  recoil: { clip: "animation.voidbound.player.emote_recoil", length: 0.55, blend: 0.2 },
};

/** Foods the pack adds that are worth reacting to. */
const SAVOURED = new Set([
  "voidbound:ender_fruit",
  "voidbound:ender_fruit_pie",
  "voidbound:lumen_berry",
  "voidbound:echo_bread",
  "voidbound:cooked_haunch",
]);

const BOSSES = new Set([
  "voidbound:rift_sovereign",
  "voidbound:echo_warden",
  "voidbound:void_titan",
]);

/** One emote at a time per player, so two events cannot fight over the pose. */
const busyUntil = new Map();

/**
 * Play a one-shot emote on one player.
 *
 * Returns false when the player is already emoting or the command could not
 * run, so callers can fall back to doing nothing rather than stacking poses.
 */
export function playEmote(player, name) {
  const emote = EMOTES[name];
  if (!emote || !player?.isValid) return false;

  const now = system.currentTick;
  const until = busyUntil.get(player.id) ?? 0;
  if (now < until) return false;

  // Stop when the clip's own timer runs out. Without this the last keyframe
  // holds and the player stands frozen in the pose.
  const stop = `query.anim_time >= ${emote.length.toFixed(2)}`;
  try {
    player.runCommand(
      `playanimation @s ${emote.clip} none ${emote.blend} "${stop}" vb_emote`
    );
  } catch {
    return false;
  }
  busyUntil.set(player.id, now + Math.ceil(emote.length * 20));
  return true;
}

/** Everyone within range of a point, used for the boss-kill salute. */
function playersNear(dimension, location, radius) {
  try {
    return dimension.getPlayers({ location, maxDistance: radius }).filter((p) => p.isValid);
  } catch {
    return [];
  }
}

export function startEmotes() {
  // A boss dying is the pack's biggest moment; everyone present gets it.
  world.afterEvents.entityDie.subscribe((event) => {
    const dead = event.deadEntity;
    if (!BOSSES.has(dead?.typeId)) return;
    const killer = event.damageSource?.damagingEntity;

    for (const player of playersNear(dead.dimension, dead.location, 40)) {
      // The one who landed the blow celebrates; everyone else salutes.
      const isKiller = killer?.isValid && killer.id === player.id;
      system.runTimeout(() => playEmote(player, isKiller ? "victory" : "salute"), 12);
    }
  });

  // Eating something the pack added.
  world.afterEvents.itemCompleteUse.subscribe((event) => {
    if (!SAVOURED.has(event.itemStack?.typeId)) return;
    playEmote(event.source, "savour");
  });

  // Taking a real hit in the End. Small threshold, so ordinary chip damage
  // does not turn the dimension into a flinching contest.
  world.afterEvents.entityHurt.subscribe((event) => {
    const player = event.hurtEntity;
    if (player?.typeId !== "minecraft:player") return;
    if (event.damage < 6) return;
    if (player.dimension.id !== END_DIMENSION) return;
    playEmote(player, "recoil");
  });

  // Players who leave should not hold a slot in the busy map for ever.
  world.afterEvents.playerLeave.subscribe((event) => {
    busyUntil.delete(event.playerId);
  });
}
