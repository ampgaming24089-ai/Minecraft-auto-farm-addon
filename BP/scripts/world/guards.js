import { world, system } from "@minecraft/server";
import { HOLLOW_VEIL } from "./build.js";
import { BEDROCK_Y, biomeAt, heightAt, isWithinWorld } from "./biomes.js";

/**
 * Two things the Hollow Veil has to guarantee that nothing else was doing.
 *
 * 1. It is the Hollow Veil, not a dark overworld. A zombie and a creeper
 *    turned up in the owner's screenshots, which breaks the illusion harder
 *    than any missing texture: a custom dimension gets no biome, so it gets no
 *    spawn rules of its own, and the engine happily runs vanilla surface
 *    spawning in it. Vanilla hostiles are removed on sight.
 *
 * 2. You cannot fall out of the world. Blocks can only be written to loaded
 *    chunks, so however far ahead the builder works there is always some
 *    frontier, and walking onto it means falling forever. Anyone who drops
 *    below the bedrock floor is put back on the surface.
 */

// Vanilla entities that are fine here: the player's own things, projectiles,
// drops, and the vehicles and display entities a build might use. Everything
// else vanilla is a mob that does not belong.
const ALLOWED_VANILLA = new Set([
  "minecraft:player",
  "minecraft:item",
  "minecraft:xp_orb",
  "minecraft:xp_bottle",
  "minecraft:arrow",
  "minecraft:snowball",
  "minecraft:egg",
  "minecraft:ender_pearl",
  "minecraft:fishing_hook",
  "minecraft:thrown_trident",
  "minecraft:splash_potion",
  "minecraft:lingering_potion",
  "minecraft:fireball",
  "minecraft:small_fireball",
  "minecraft:dragon_fireball",
  "minecraft:wither_skull",
  "minecraft:wither_skull_dangerous",
  "minecraft:shulker_bullet",
  "minecraft:llama_spit",
  "minecraft:tnt",
  "minecraft:falling_block",
  "minecraft:armor_stand",
  "minecraft:boat",
  "minecraft:chest_boat",
  "minecraft:minecart",
  "minecraft:chest_minecart",
  "minecraft:hopper_minecart",
  "minecraft:tnt_minecart",
  "minecraft:command_block_minecart",
  "minecraft:lightning_bolt",
  "minecraft:eye_of_ender_signal",
  "minecraft:fireworks_rocket",
  "minecraft:leash_knot",
  "minecraft:painting",
  "minecraft:item_frame",
  "minecraft:glow_item_frame",
  "minecraft:area_effect_cloud",
  "minecraft:evocation_fang",
  "minecraft:agent",
]);

function isIntruder(entity) {
  const id = entity.typeId;
  if (!id.startsWith("minecraft:")) return false;   // ours, or another addon's
  return !ALLOWED_VANILLA.has(id);
}

export function startDimensionGuards() {
  world.afterEvents.entitySpawn.subscribe((ev) => {
    const e = ev.entity;
    try {
      if (e.dimension.id !== HOLLOW_VEIL || !isIntruder(e)) return;
    } catch {
      return;                       // entity already gone
    }
    // Deferred: removing an entity inside its own spawn event is a good way to
    // fight the engine over its lifetime. One tick later is soon enough that
    // nobody sees it.
    system.run(() => {
      try {
        e.remove();
      } catch {
        /* already gone */
      }
    });
  });

  // A sweep as well as the event, because entities also arrive by portal,
  // command, spawn egg and chunk load, and not all of those raise entitySpawn.
  system.runInterval(() => {
    let dim;
    try {
      dim = world.getDimension(HOLLOW_VEIL);
    } catch {
      return;
    }
    for (const e of dim.getEntities()) {
      if (!isIntruder(e)) continue;
      try {
        e.remove();
      } catch {
        /* already gone */
      }
    }
  }, 100);

  system.runInterval(voidNet, 10);
}

/**
 * Catches anyone who has fallen past the bottom of the world.
 *
 * The builder can only write to loaded chunks, so there is always a frontier
 * somewhere, and a player who reaches it walks into nothing. Rather than
 * pretend that can never happen, this notices the fall and puts them back on
 * solid ground - with the ground placed under them first, because the reason
 * they fell is that it was not there.
 */
function voidNet() {
  for (const player of world.getAllPlayers()) {
    let loc;
    try {
      if (player.dimension.id !== HOLLOW_VEIL) continue;
      loc = player.location;
    } catch {
      continue;
    }
    if (loc.y > BEDROCK_Y - 4) continue;

    const x = Math.floor(loc.x);
    const z = Math.floor(loc.z);
    const inside = isWithinWorld({ x, z });
    // Somebody who fell off the rim of a 100,000-block disc gets returned to
    // the hub; everyone else lands where they were, on new ground.
    const tx = inside ? x : 0;
    const tz = inside ? z : 0;
    const b = biomeAt(tx, tz);
    const y = heightAt(tx, tz, b);
    const dim = player.dimension;
    try {
      for (let dx = -2; dx <= 2; dx++) {
        for (let dz = -2; dz <= 2; dz++) {
          dim.setBlockType({ x: tx + dx, y, z: tz + dz }, b.surface);
        }
      }
    } catch {
      /* chunk not loaded; the teleport below still saves them */
    }
    try {
      player.teleport({ x: tx + 0.5, y: y + 1, z: tz + 0.5 }, { dimension: dim });
      player.sendMessage("§7The Veil catches you before the dark does.");
    } catch {
      /* try again next pass */
    }
  }
}
