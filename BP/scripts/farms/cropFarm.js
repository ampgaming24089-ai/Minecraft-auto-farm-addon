import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Auto Crop Farm — 4 separate ground-level units
 * ================================================
 * A real, documented Bedrock design: two farmer villagers, each in their
 * own 8x8 plot, with a composter-on-water tower in the center of each
 * plot, separated from a caged "collector" villager by a hopper-minecart
 * barrier topped with an open trapdoor.
 *
 * This used to be built as levels stacked vertically. It's a single-story
 * design, so stacking it added height for no real benefit and made the
 * collection hoppers unnecessarily long chains. Instead, each unit picked
 * (1-4) is a fully independent, complete farm placed on the ground, 10
 * blocks apart from the next one — build 1 for a quick start or all 4 for
 * full production, and every one of them works the same way at ground
 * level, easy to walk between and inspect.
 *
 *  - Farmland plots: farmers won't work land more than ~4 blocks from
 *    their composter, so an 8x8 plot centered on one composter is what
 *    they'll actually farm (a wider plot just wastes space).
 *  - Composter tower: a water source with a composter directly on top of
 *    it (survival players need a slab trick to place this; placing blocks
 *    directly via script skips that entirely) keeps the farmland hydrated
 *    *and* gives the villager standing there a job site in one tile.
 *    Glowstone on top lights the plot.
 *  - Collector villager: caged in a narrow pen so it can never wander off.
 *  - Barrier: a hopper + rail + parked hopper-minecart at every tile along
 *    the pen's edge (walkable — farmers can step right up to any of them),
 *    each topped with an open trapdoor blocking actual crossing. Farmers
 *    path to the edge and attempt to share surplus food with the caged
 *    collector across the gap; that attempt drops food onto whichever
 *    minecart they're standing at, which the hopper underneath catches.
 *  - Collection: every barrier hopper drains straight down, chains to the
 *    unit's front wall, and feeds one shared underground line that runs
 *    the full width of the build — every unit empties into ONE double
 *    chest, not a chest per unit.
 *  - No roof: keeps the plots naturally sky-lit (better for crop growth
 *    than relying on the tower's glowstone alone) and cuts unnecessary
 *    block usage. A knee-high fence ring keeps the villagers contained;
 *    corner + mid-wall sea lanterns keep light levels high so nothing
 *    hostile spawns at night despite the open top.
 *
 * Local space per unit: x 0-22 (width), z 0-9 (depth), y 0-5 (height).
 * Units repeat sideways along +x (stackAxis "x"), NOT stacked in y.
 */

export const SIZE = { x: 23, y: 6, z: 10 };
export const LEVEL_SPACING = SIZE.x + 10; // unit width + 10-block gap to the next unit
export const MAX_LEVELS = 4;
export const stackAxis = "x";
export const levelLabel = "Number of farms (1-4)";
export const unitNoun = "Farm";

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
// Same 0-3 enum Bedrock uses for bed "direction" (verified against
// bedrock-samples) — trapdoors and most other directional blocks reuse it.
const DIRECTION = { south: 0, west: 1, north: 2, east: 3 };
const CROPS = ["minecraft:wheat", "minecraft:carrots", "minecraft:potatoes"];

// Farmer plot A: x1-8, z1-8. Farmer plot B: x14-21, z1-8 (mirrored).
// Pen (collector villager): x10-12, z1-8. Barriers at x9 and x13.
const PLOTS = [
  { xMin: 1, xMax: 8, tower: [4, 4], farmerSpawn: [4, 3] },
  { xMin: 14, xMax: 21, tower: [17, 4], farmerSpawn: [17, 3] },
];
const BARRIERS = [9, 13];
const PEN_X_MIN = 10;
const PEN_X_MAX = 12;

/** Build one complete, independent farm unit at local x-offset dx. */
function planUnit(dx, facing) {
  const parts = [];
  const spawns = [];

  // Outer shell: floor + knee-high fence ring, no roof (see notes above).
  parts.push(box([0, 0, 0], [22, 0, 9], "minecraft:grass_block"));
  parts.push(box([1, 1, 1], [21, 5, 8], "minecraft:air"));
  parts.push(box([0, 1, 0], [22, 1, 0], "minecraft:oak_fence"));
  parts.push(box([0, 1, 9], [22, 1, 9], "minecraft:oak_fence"));
  parts.push(box([0, 1, 0], [0, 1, 9], "minecraft:oak_fence"));
  parts.push(box([22, 1, 0], [22, 1, 9], "minecraft:oak_fence"));
  for (const [x, z] of [[0, 4], [22, 4], [4, 0], [17, 0], [4, 9], [17, 9], [11, 0], [11, 9]]) {
    parts.push(block(x, 2, z, "minecraft:sea_lantern"));
  }

  // Two farmer plots.
  for (const plot of PLOTS) {
    for (let x = plot.xMin; x <= plot.xMax; x++) {
      for (let z = 1; z <= 8; z++) {
        if (x === plot.tower[0] && z === plot.tower[1]) continue; // tower tile, handled separately
        const crop = CROPS[Math.floor(Math.random() * CROPS.length)];
        const growth = Math.floor(Math.random() * 8);
        parts.push(block(x, 0, z, "minecraft:farmland"));
        parts.push(block(x, 1, z, crop, { growth }));
      }
    }
    // Composter-on-water tower: water hydrates the plot, composter is the
    // job site, glowstone lights it. All placed directly, no slab needed.
    const [tx, tz] = plot.tower;
    parts.push(block(tx, 0, tz, "minecraft:water"));
    parts.push(block(tx, 1, tz, "minecraft:composter"));
    parts.push(block(tx, 2, tz, "minecraft:glowstone"));
    spawns.push({ x: plot.farmerSpawn[0], y: 1, z: plot.farmerSpawn[1], typeId: "minecraft:villager" });
  }

  // Collector pen: fenced, holds one caged villager.
  parts.push(box([PEN_X_MIN, 1, 0], [PEN_X_MAX, 1, 0], "minecraft:oak_fence"));
  parts.push(box([PEN_X_MIN, 1, 9], [PEN_X_MAX, 1, 9], "minecraft:oak_fence"));
  spawns.push({ x: 11, y: 1, z: 4, typeId: "minecraft:villager" });

  // Barriers: hopper -> rail -> parked hopper minecart (walkable collection
  // pad) at every tile, topped with an open trapdoor blocking crossing
  // while still letting farmers approach and attempt to share food.
  const north = rotateDirection("north", facing);
  const trapdoorDir = DIRECTION[north];
  for (const bx of BARRIERS) {
    for (let z = 1; z <= 8; z++) {
      // Catch layer: always straight down, whatever lands on the minecart
      // above gets pulled into the chain layer directly below it.
      parts.push(block(bx, 0, z, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));
      parts.push(block(bx, 1, z, "minecraft:rail"));
      parts.push(block(bx, 2, z, "minecraft:oak_trapdoor", { open_bit: true, upside_down_bit: false, direction: trapdoorDir }));
      spawns.push({ x: bx, y: 1, z, typeId: "minecraft:hopper_minecart" });
      // Chain layer (z=2..8): walks every catch point north to z=1, where
      // it joins the shared external spine (built once in plan(), not
      // per-unit, since it runs the full width of the whole build).
      if (z >= 2) {
        parts.push(block(bx, -1, z, "minecraft:hopper", { facing_direction: HOPPER_FACING[north] }));
      }
    }
  }

  const merged = merge(...parts);
  return {
    placements: merged.map((p) => ({ ...p, x: p.x + dx })),
    spawns: spawns.map((s) => ({ ...s, x: s.x + dx })),
  };
}

/**
 * Shared external collection spine + one double chest for the whole build,
 * regardless of how many units (1-4) were placed. Runs the full width at
 * y=-1, z=1 — every unit's barrier chain empties into this same row at its
 * own x position, and the row itself carries everything west to the chest.
 */
function planSpine(levels, facing) {
  const west = rotateDirection("west", facing);
  const maxX = (levels - 1) * LEVEL_SPACING + Math.max(...BARRIERS);
  const parts = [block(-3, -1, 1, "minecraft:chest"), block(-4, -1, 1, "minecraft:chest")];
  for (let x = maxX; x >= -2; x--) {
    parts.push(block(x, -1, 1, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }));
  }
  return merge(...parts);
}

export const CropFarm = {
  id: "crop_farm",
  name: "Auto Crop Farm",
  shortDescription: "2 farmers + collector per unit, hopper-minecart collection, 4 separate ground farms.",
  size: SIZE,
  levelSpacing: LEVEL_SPACING,
  maxLevels: MAX_LEVELS,
  stackAxis,
  levelLabel,
  unitNoun,

  /**
   * @param {{levels:number, facing: keyof import("../lib/geometry.js").FACINGS}} opts
   */
  plan({ levels, facing }) {
    const placements = [];
    const spawns = [];
    for (let i = 0; i < levels; i++) {
      const { placements: p, spawns: s } = planUnit(i * LEVEL_SPACING, facing);
      placements.push(...p);
      spawns.push(...s);
    }
    placements.push(...planSpine(levels, facing));
    return { placements, spawns };
  },
};
