import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Stackable Auto Crop Farm
 * ========================
 * This is a real, documented Bedrock design, not an invented one — two
 * farmer villagers, each in their own 8x8 plot, with a composter-on-water
 * tower in the center of each plot, separated from a caged "collector"
 * villager by a hopper-minecart barrier topped with an open trapdoor:
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
 *  - Barrier: a row of hopper-block + rail + parked hopper-minecart at
 *    the pen's edge (walkable — farmers can step right up to it), with an
 *    open trapdoor one block above blocking actual crossing. Farmers
 *    still path to the edge and attempt to share surplus food with the
 *    collector across the gap; the attempt drops food right onto the
 *    minecart row, which is being continuously drained by the hopper
 *    underneath.
 *
 * Local space: x 0-22 (width), z 0-9 (depth), y 0-6 (height per level).
 */

export const SIZE = { x: 23, y: 7, z: 10 };
export const LEVEL_SPACING = 9; // 7 tall level + 2 block gap to the level above
export const MAX_LEVELS = 4;

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
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

function planLevel(dy, facing) {
  const parts = [];
  const spawns = [];
  const y = (n) => n + dy;

  // Outer shell: floor, fence ring, roof.
  parts.push(box([0, 0, 0], [22, 0, 9], "minecraft:grass_block"));
  parts.push(box([1, 1, 1], [21, 5, 8], "minecraft:air"));
  parts.push(box([0, 6, 0], [22, 6, 9], "minecraft:cobblestone"));
  parts.push(box([0, 1, 0], [22, 1, 0], "minecraft:oak_fence"));
  parts.push(box([0, 1, 9], [22, 1, 9], "minecraft:oak_fence"));
  parts.push(box([0, 1, 0], [0, 1, 9], "minecraft:oak_fence"));
  parts.push(box([22, 1, 0], [22, 1, 9], "minecraft:oak_fence"));
  for (const [x, z] of [[4, 0], [17, 0], [4, 9], [17, 9], [11, 0], [11, 9]]) {
    parts.push(block(x, y(1), z, "minecraft:sea_lantern"));
  }

  // Two farmer plots.
  for (const plot of PLOTS) {
    for (let x = plot.xMin; x <= plot.xMax; x++) {
      for (let z = 1; z <= 8; z++) {
        if (x === plot.tower[0] && z === plot.tower[1]) continue; // tower tile, handled separately
        const crop = CROPS[Math.floor(Math.random() * CROPS.length)];
        const growth = Math.floor(Math.random() * 8);
        parts.push(block(x, y(0), z, "minecraft:farmland"));
        parts.push(block(x, y(1), z, crop, { growth }));
      }
    }
    // Composter-on-water tower: water hydrates the plot, composter is the
    // job site, glowstone lights it. All placed directly, no slab needed.
    const [tx, tz] = plot.tower;
    parts.push(block(tx, y(0), tz, "minecraft:water"));
    parts.push(block(tx, y(1), tz, "minecraft:composter"));
    parts.push(block(tx, y(2), tz, "minecraft:glowstone"));
    spawns.push({ x: plot.farmerSpawn[0], y: y(1), z: plot.farmerSpawn[1], typeId: "minecraft:villager" });
  }

  // Collector pen: fenced, holds one caged villager.
  parts.push(box([PEN_X_MIN, 1, 0], [PEN_X_MAX, 1, 0], "minecraft:oak_fence"));
  parts.push(box([PEN_X_MIN, 1, 9], [PEN_X_MAX, 1, 9], "minecraft:oak_fence"));
  spawns.push({ x: 11, y: y(1), z: 4, typeId: "minecraft:villager" });

  // Barriers: hopper -> rail -> parked hopper minecart (walkable collection
  // pad), with an open trapdoor one block above blocking actual crossing
  // while still letting farmers approach and attempt to share food.
  const west = rotateDirection("west", facing);
  const north = rotateDirection("north", facing);
  for (const bx of BARRIERS) {
    for (let z = 1; z <= 8; z++) {
      parts.push(block(bx, y(0), z, "minecraft:hopper", { facing_direction: HOPPER_FACING[z === 1 ? "down" : north] }));
      parts.push(block(bx, y(1), z, "minecraft:rail"));
      parts.push(block(bx, y(2), z, "minecraft:oak_trapdoor", { open_bit: true, upside_down_bit: false, direction: 0 }));
      spawns.push({ x: bx, y: y(1), z, typeId: "minecraft:hopper_minecart" });
    }
  }

  // Underground routing (y=-1): both barrier rows drain north to z=1, then
  // west out of the footprint. Barrier B's tunnel passes through and
  // merges into barrier A's at x=9 rather than redefining it.
  for (let x = 13; x >= 10; x--) {
    parts.push(block(x, -1, 1, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }));
  }
  for (let x = 9; x >= 0; x--) {
    parts.push(block(x, -1, 1, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }));
  }

  const merged = merge(...parts);
  return {
    placements: merged.map((p) => ({ ...p, y: p.y + dy })),
    spawns: spawns.map((s) => ({ ...s, y: s.y + dy })),
  };
}

/**
 * External collection shaft + base double chest, shared by every level.
 * The chest sits 1 block below ground right outside the west wall, so
 * it's easy to find: the bottom of the shaft redirects sideways into it.
 */
function planShaft(levels, facing) {
  const topY = (levels - 1) * LEVEL_SPACING - 1;
  const west = rotateDirection("west", facing);
  const parts = [
    block(-1, -1, 1, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }),
    block(-2, -1, 1, "minecraft:chest"),
    block(-3, -1, 1, "minecraft:chest"),
  ];
  for (let y = 0; y <= topY; y++) {
    parts.push(block(-1, y, 1, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));
  }
  return merge(...parts);
}

export const CropFarm = {
  id: "crop_farm",
  name: "Stackable Auto Crop Farm",
  shortDescription: "2 farmers, composter-on-water towers, hopper-minecart collection, quad-stackable.",
  size: SIZE,
  levelSpacing: LEVEL_SPACING,
  maxLevels: MAX_LEVELS,

  /**
   * @param {{levels:number, facing: keyof import("../lib/geometry.js").FACINGS}} opts
   */
  plan({ levels, facing }) {
    const placements = [];
    const spawns = [];
    for (let i = 0; i < levels; i++) {
      const { placements: p, spawns: s } = planLevel(i * LEVEL_SPACING, facing);
      placements.push(...p);
      spawns.push(...s);
    }
    placements.push(...planShaft(levels, facing));
    return { placements, spawns };
  },
};
