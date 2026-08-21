/**
 * Chest contents for generated structures.
 *
 * Kept in script rather than in loot tables because these chests are placed by
 * the generator, not by a block break, and because the reward curve is tied to
 * how far out in the End the structure sits - a spire 40,000 blocks from the
 * central island should be worth the trip.
 */

import { ItemStack } from "@minecraft/server";

/** @typedef {{ id: string, min: number, max: number, weight: number }} LootEntry */

const COMMON = [
  { id: "voidbound:echo_shard", min: 2, max: 6, weight: 10 },
  { id: "minecraft:ender_pearl", min: 1, max: 3, weight: 8 },
  { id: "minecraft:end_bricks", min: 4, max: 12, weight: 7 },
  { id: "minecraft:purpur_block", min: 3, max: 9, weight: 6 },
  { id: "voidbound:lumen_berry", min: 1, max: 4, weight: 6 },
  { id: "minecraft:chorus_fruit", min: 2, max: 5, weight: 6 },
];

const UNCOMMON = [
  { id: "voidbound:void_crystal", min: 1, max: 3, weight: 8 },
  { id: "minecraft:obsidian", min: 2, max: 5, weight: 6 },
  { id: "minecraft:diamond", min: 1, max: 2, weight: 4 },
  { id: "minecraft:iron_ingot", min: 3, max: 7, weight: 6 },
  { id: "minecraft:experience_bottle", min: 2, max: 6, weight: 5 },
];

const RARE = [
  { id: "voidbound:rift_compass", min: 1, max: 1, weight: 3 },
  { id: "voidbound:rift_lantern", min: 1, max: 2, weight: 4 },
  { id: "minecraft:enchanted_golden_apple", min: 1, max: 1, weight: 1 },
  { id: "minecraft:elytra", min: 1, max: 1, weight: 1 },
  { id: "minecraft:diamond_block", min: 1, max: 1, weight: 2 },
];

function pickWeighted(rng, entries) {
  const total = entries.reduce((sum, entry) => sum + entry.weight, 0);
  let roll = rng.float(0, total);
  for (const entry of entries) {
    roll -= entry.weight;
    if (roll <= 0) return entry;
  }
  return entries[entries.length - 1];
}

/**
 * Build a chest's worth of stacks.
 *
 * @param rng seeded generator, so a chest's contents are a property of the
 *   world rather than of when the player happened to open it
 * @param distance horizontal distance from the world origin, used to scale the
 *   odds of the rare pool
 */
export function rollChest(rng, distance, { rolls = 6, richness = 1 } = {}) {
  // Ramps from 0 near the central island to 1 around 30k blocks out.
  const remoteness = Math.max(0, Math.min(1, (distance - 1500) / 28500));
  const rareChance = (0.06 + remoteness * 0.22) * richness;
  const uncommonChance = 0.3 + remoteness * 0.15;

  const slots = rng.shuffle([...Array(27).keys()]);
  const items = [];
  const count = rng.int(Math.max(2, rolls - 2), rolls + 2);

  for (let i = 0; i < count && i < slots.length; i++) {
    const pool = rng.chance(rareChance) ? RARE : rng.chance(uncommonChance) ? UNCOMMON : COMMON;
    const entry = pickWeighted(rng, pool);
    const amount = rng.int(entry.min, entry.max);
    try {
      items.push({ slot: slots[i], stack: new ItemStack(entry.id, amount) });
    } catch {
      // An id this version does not know (e.g. a renamed vanilla item) is
      // skipped rather than aborting the whole chest.
    }
  }
  return items;
}
