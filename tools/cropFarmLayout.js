import { fill, set, summon } from "./cmdBuilder.js";

/**
 * Stackable Auto Crop Farm — command-based layout, mechanics unchanged
 * from the original design (see git history for the Script API version).
 * Fixed orientation: always builds extending +x/+z from wherever the
 * beacon item is used. Local space: x 0-12, z 0-12, y 0-6 per level.
 */

export const SIZE = { x: 13, y: 7, z: 13 };
export const LEVEL_SPACING = 9; // 7 tall level + 2 block gap to the level above
export const MAX_LEVELS = 4;

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };

const PLOTS = [
  {
    // North
    farmland: [[5, 1], [6, 1], [7, 1], [5, 2], [7, 2], [5, 3], [6, 3], [7, 3]],
    water: [6, 2],
    composter: [5, 1],
    corridor: [6, 4],
    corridorFlanks: [[5, 4], [7, 4]],
    borderWalls: [[[4, 0], [4, 4]], [[8, 0], [8, 4]]],
    farmerSpawn: [7, 2],
  },
  {
    // South
    farmland: [[5, 9], [6, 9], [7, 9], [5, 10], [7, 10], [5, 11], [6, 11], [7, 11]],
    water: [6, 10],
    composter: [5, 11],
    corridor: [6, 8],
    corridorFlanks: [[5, 8], [7, 8]],
    borderWalls: [[[4, 8], [4, 12]], [[8, 8], [8, 12]]],
    farmerSpawn: [7, 10],
  },
  {
    // West
    farmland: [[1, 5], [1, 6], [1, 7], [2, 5], [2, 7], [3, 5], [3, 6], [3, 7]],
    water: [2, 6],
    composter: [1, 5],
    corridor: [4, 6],
    corridorFlanks: [[4, 5], [4, 7]],
    borderWalls: [[[0, 4], [4, 4]], [[0, 8], [4, 8]]],
    farmerSpawn: [2, 7],
  },
  {
    // East
    farmland: [[9, 5], [9, 6], [9, 7], [10, 5], [10, 7], [11, 5], [11, 6], [11, 7]],
    water: [10, 6],
    composter: [11, 5],
    corridor: [8, 6],
    corridorFlanks: [[8, 5], [8, 7]],
    borderWalls: [[[8, 4], [12, 4]], [[8, 8], [12, 8]]],
    farmerSpawn: [10, 7],
  },
];

// Pen collection pads: [x, z, facing-toward-center]
const PADS = [
  { x: 6, z: 5, facing: "south" }, // north pad
  { x: 6, z: 7, facing: "north" }, // south pad
  { x: 5, z: 6, facing: "east" }, // west pad
  { x: 7, z: 6, facing: "west" }, // east pad
  { x: 6, z: 6, facing: "down" }, // center pad
];

function planLevel(dy) {
  const L = [];
  const y = (n) => n + dy;

  L.push(fill([0, y(0), 0], [12, y(0), 12], "minecraft:grass_block"));
  L.push(fill([1, y(1), 1], [11, y(5), 11], "minecraft:air"));
  L.push(fill([0, y(6), 0], [12, y(6), 12], "minecraft:cobblestone"));

  L.push(fill([0, y(1), 0], [12, y(1), 0], "minecraft:oak_fence"));
  L.push(fill([0, y(1), 12], [12, y(1), 12], "minecraft:oak_fence"));
  L.push(fill([0, y(1), 0], [0, y(1), 12], "minecraft:oak_fence"));
  L.push(fill([12, y(1), 0], [12, y(1), 12], "minecraft:oak_fence"));

  for (const [x, z] of [[6, 0], [6, 12], [0, 6], [12, 6]]) {
    L.push(set(x, y(1), z, "minecraft:sea_lantern"));
  }

  for (const plot of PLOTS) {
    for (const [x, z] of plot.farmland) {
      const growth = Math.floor(Math.random() * 8);
      L.push(set(x, y(0), z, "minecraft:farmland"));
      L.push(set(x, y(1), z, "minecraft:wheat", { growth }));
    }
    L.push(set(plot.water[0], y(0), plot.water[1], "minecraft:water"));
    L.push(set(plot.composter[0], y(0), plot.composter[1], "minecraft:grass_block"));
    L.push(set(plot.composter[0], y(1), plot.composter[1], "minecraft:composter"));
    for (const [from, to] of plot.borderWalls) {
      L.push(fill([from[0], y(1), from[1]], [to[0], y(1), to[1]], "minecraft:oak_fence"));
    }
    for (const [x, z] of plot.corridorFlanks) L.push(set(x, y(1), z, "minecraft:oak_fence"));
    L.push(set(plot.corridor[0], y(1), plot.corridor[1], "minecraft:air"));
    L.push(summon(plot.farmerSpawn[0], y(1), plot.farmerSpawn[1], "minecraft:villager"));
  }

  L.push(fill([4, y(1), 4], [4, y(1), 8], "minecraft:oak_fence"));
  L.push(fill([8, y(1), 4], [8, y(1), 8], "minecraft:oak_fence"));
  L.push(fill([4, y(1), 4], [8, y(1), 4], "minecraft:oak_fence"));
  L.push(fill([4, y(1), 8], [8, y(1), 8], "minecraft:oak_fence"));
  L.push(set(4, y(1), 6, "minecraft:air"));
  L.push(set(8, y(1), 6, "minecraft:air"));
  L.push(set(6, y(1), 4, "minecraft:air"));
  L.push(set(6, y(1), 8, "minecraft:air"));
  L.push(summon(6, y(1), 6, "minecraft:villager"));

  for (const pad of PADS) {
    const facingValue = pad.facing === "down" ? HOPPER_FACING.down : HOPPER_FACING[pad.facing];
    L.push(set(pad.x, y(0), pad.z, "minecraft:hopper", { facing_direction: facingValue }));
    L.push(set(pad.x, y(1), pad.z, "minecraft:rail"));
    L.push(summon(pad.x, y(1), pad.z, "minecraft:hopper_minecart"));
  }

  for (let x = 6; x >= 0; x--) {
    L.push(set(x, y(-1), 6, "minecraft:hopper", { facing_direction: HOPPER_FACING.west }));
  }
  L.push(set(-1, y(-1), 6, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));

  return L;
}

/** External collection shaft + base double chest, shared by every level. */
function planShaft(levels) {
  const topY = (levels - 1) * LEVEL_SPACING - 1;
  const L = [
    set(-1, -3, 6, "minecraft:chest"),
    set(-2, -3, 6, "minecraft:chest"),
  ];
  for (let y = -2; y <= topY; y++) {
    L.push(set(-1, y, 6, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));
  }
  return L;
}

/** @param {number} levels 1-4 @returns {string[]} full ordered command list */
export function generateCropFarm(levels) {
  const lines = [];
  for (let i = 0; i < levels; i++) {
    lines.push(...planLevel(i * LEVEL_SPACING));
  }
  lines.push(...planShaft(levels));
  return lines;
}
