import { box, block, merge } from "../lib/builder.js";

/**
 * AFK Fish Farm
 * =============
 * Two honest halves, because they're not the same kind of mechanic:
 *
 *  1. A real, physical AFK-friendly fishing pool. Bedrock does NOT support
 *     true hands-off AFK fishing — casting, waiting for the bobber to dip,
 *     and reeling in all require actual player input every time; there is
 *     no vanilla mechanic (and no supported Script API hook) that lets a
 *     structure alone auto-reel a real fishing rod. What this structure
 *     *does* do for real: a roofed, enclosed 5x5 water pool blocks rain
 *     (which otherwise makes the bobber harder to see/track) and keeps the
 *     platform dark-mob-free with lighting, so once you're standing at the
 *     dock and casting by hand, nothing else interrupts you. A chest sits
 *     right there for stowing what you catch.
 *  2. The "auto casts and catches fish" tool asked for is the Auto Fishing
 *     Rod item (see BP/items/auto_fishing_rod.json and
 *     scripts/lib/autoFishingRod.js) — a deliberately SCRIPTED item, not a
 *     recreation of the real fishing_hook entity/bobber cycle (there's no
 *     stable Script API event for "bobber caught something, awaiting
 *     reel-in" to drive automatically). It rolls the same odds as vanilla's
 *     real fishing loot table on a timer while you hold it near water, so
 *     it's a genuine convenience tool, just clearly a custom mechanic
 *     rather than automated vanilla fishing. Use it standing at this pool
 *     (or any open water) for a truly hands-off setup.
 *
 * Local space: x 0-8, z 0-8, y 0-4.
 */

export const SIZE = { x: 9, y: 5, z: 9 };
export const LEVEL_SPACING = SIZE.x + 6;
export const MAX_LEVELS = 4;
export const stackAxis = "x";
export const levelLabel = "Number of pools (1-4)";
export const unitNoun = "Pool";

function planUnit(dx) {
  const parts = [];

  // Floor + walls + glass roof (rain-proof, sky-open for daylight, mob-proof once lit).
  parts.push(box([0, 0, 0], [8, 0, 8], "minecraft:oak_planks"));
  parts.push(box([0, 1, 0], [8, 3, 0], "minecraft:oak_fence"));
  parts.push(box([0, 1, 8], [8, 3, 8], "minecraft:oak_fence"));
  parts.push(box([0, 1, 0], [0, 3, 8], "minecraft:oak_fence"));
  parts.push(box([8, 1, 0], [8, 3, 8], "minecraft:oak_fence"));
  parts.push(box([0, 4, 0], [8, 4, 8], "minecraft:glass"));

  // 5x5 water pool in the middle.
  parts.push(box([2, 0, 2], [6, 0, 6], "minecraft:water"));

  // Dock: a clear standing tile at the south edge, torch-lit, facing the pool.
  parts.push(block(4, 1, 7, "minecraft:torch"));
  parts.push(block(2, 1, 7, "minecraft:torch"));
  parts.push(block(6, 1, 7, "minecraft:torch"));

  // Storage right at the dock.
  parts.push(block(3, 1, 8, "minecraft:chest"));
  parts.push(block(5, 1, 8, "minecraft:chest"));

  const merged = merge(...parts);
  return { placements: merged.map((p) => ({ ...p, x: p.x + dx })) };
}

export const FishFarm = {
  id: "fish_farm",
  name: "AFK Fish Farm",
  shortDescription: "Roofed, lit, rain-proof pool + dock + chest. Pair with the Auto Fishing Rod for hands-off fishing.",
  size: SIZE,
  levelSpacing: LEVEL_SPACING,
  maxLevels: MAX_LEVELS,
  stackAxis,
  levelLabel,
  unitNoun,

  /**
   * @param {{levels:number, facing: keyof import("../lib/geometry.js").FACINGS}} opts
   */
  plan({ levels }) {
    const placements = [];
    for (let i = 0; i < levels; i++) {
      const { placements: p } = planUnit(i * LEVEL_SPACING);
      placements.push(...p);
    }
    return { placements, spawns: [] };
  },
};
