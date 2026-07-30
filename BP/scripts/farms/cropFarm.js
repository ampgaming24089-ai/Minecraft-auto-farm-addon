import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Stackable Auto Crop Farm
 * ========================
 * Real vanilla mechanics only:
 *
 *  - Four small hydrated farmland plots, each with a composter job-site
 *    block. A spawned villager standing in claim range of an unclaimed
 *    composter automatically becomes a Farmer and will harvest/replant
 *    the plot on its own (vanilla farmer AI — nothing scripted).
 *  - A fenced corridor connects each plot to a shared center pen holding
 *    one extra villager. Farmer villagers that accumulate surplus food
 *    periodically try to share/trade it with nearby villagers — a real
 *    vanilla behavior — which drops items on the ground near whoever
 *    they approach.
 *  - The pen floor (center + the four cells around it) is built from a
 *    hopper block topped with a rail holding a parked hopper minecart.
 *    Any item dropped there lands on/above the minecart and is pulled in;
 *    the block hopper underneath continuously drains the minecart, so
 *    nothing needs to be collected by hand.
 *  - All five collection points funnel into a shared external hopper
 *    shaft that drains to a base chest below the whole stack.
 *
 * Local space: x 0-12 (width), z 0-12 (depth), y 0-6 (height per level).
 */

export const SIZE = { x: 13, y: 7, z: 13 };
export const LEVEL_SPACING = 9; // 7 tall level + 2 block gap to the level above
export const MAX_LEVELS = 4;

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };

/** One plot's layout, authored explicitly (not derived by rotation, to keep it simple/robust). */
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

const CROPS = [
  { id: "minecraft:wheat" },
  { id: "minecraft:carrots" },
  { id: "minecraft:potatoes" },
];

// Collection pads sit at the pen's 4 corridor mouths (where farmers must
// physically walk through to reach the pen) plus the center itself, where
// the trapped villager stands. All feed straight down into local routing.
const PADS = [
  { x: 6, z: 4 }, // north gap
  { x: 6, z: 8 }, // south gap
  { x: 4, z: 6 }, // west gap
  { x: 8, z: 6 }, // east gap
  { x: 6, z: 6 }, // center
];

function planLevel(dy, facing) {
  const parts = [];
  const spawns = [];

  // Base floor, then clear the interior to air so leftover terrain can't interfere.
  parts.push(box([0, 0, 0], [12, 0, 12], "minecraft:grass_block"));
  parts.push(box([1, 1, 1], [11, 5, 11], "minecraft:air"));

  // Roof caps the level so farms can stack; crop growth only needs light
  // level >= 9, which the lanterns below provide regardless of sky access.
  parts.push(box([0, 6, 0], [12, 6, 12], "minecraft:cobblestone"));

  // Outer fence ring (perimeter containment).
  parts.push(box([0, 1, 0], [12, 1, 0], "minecraft:oak_fence"));
  parts.push(box([0, 1, 12], [12, 1, 12], "minecraft:oak_fence"));
  parts.push(box([0, 1, 0], [0, 1, 12], "minecraft:oak_fence"));
  parts.push(box([12, 1, 0], [12, 1, 12], "minecraft:oak_fence"));

  // Corner sea lanterns for reliable growth + hostile-mob-proof lighting.
  for (const [x, z] of [[6, 0], [6, 12], [0, 6], [12, 6]]) {
    parts.push(block(x, 1, z, "minecraft:sea_lantern"));
  }

  // Four farmland plots.
  for (const plot of PLOTS) {
    for (const [x, z] of plot.farmland) {
      const growth = Math.floor(Math.random() * 8);
      const crop = CROPS[Math.floor(Math.random() * CROPS.length)];
      parts.push(block(x, 0, z, "minecraft:farmland"));
      parts.push(block(x, 1, z, crop.id, { growth }));
    }
    parts.push(block(plot.water[0], 0, plot.water[1], "minecraft:water"));
    // Composter takes the place of a farmland tile as the plot's job site.
    parts.push(block(plot.composter[0], 0, plot.composter[1], "minecraft:grass_block"));
    parts.push(block(plot.composter[0], 1, plot.composter[1], "minecraft:composter"));
    for (const [from, to] of plot.borderWalls) {
      parts.push(box([from[0], 1, from[1]], [to[0], 1, to[1]], "minecraft:oak_fence"));
    }
    for (const [x, z] of plot.corridorFlanks) parts.push(block(x, 1, z, "minecraft:oak_fence"));
    parts.push(block(plot.corridor[0], 1, plot.corridor[1], "minecraft:air"));
    spawns.push({ x: plot.farmerSpawn[0], y: 1, z: plot.farmerSpawn[1], typeId: "minecraft:villager" });
  }

  // Center pen perimeter, with one gap per plot corridor.
  parts.push(box([4, 1, 4], [4, 1, 8], "minecraft:oak_fence"));
  parts.push(box([8, 1, 4], [8, 1, 8], "minecraft:oak_fence"));
  parts.push(box([4, 1, 4], [8, 1, 4], "minecraft:oak_fence"));
  parts.push(box([4, 1, 8], [8, 1, 8], "minecraft:oak_fence"));
  parts.push(block(4, 1, 6, "minecraft:air"));
  parts.push(block(8, 1, 6, "minecraft:air"));
  parts.push(block(6, 1, 4, "minecraft:air"));
  parts.push(block(6, 1, 8, "minecraft:air"));

  // Cage the center villager into its own 1x1 cell (fenced on all 4 sides)
  // so it can never wander out and off to a farmland plot — farmers still
  // reach it, since the collection pads below sit right at the corridor
  // mouths the farmers have to walk through anyway.
  parts.push(block(6, 1, 5, "minecraft:oak_fence"));
  parts.push(block(6, 1, 7, "minecraft:oak_fence"));
  parts.push(block(5, 1, 6, "minecraft:oak_fence"));
  parts.push(block(7, 1, 6, "minecraft:oak_fence"));
  spawns.push({ x: 6, y: 1, z: 6, typeId: "minecraft:villager" });

  // Collection pads: hopper -> rail -> parked hopper minecart. All face
  // straight down into local underground routing that converges on the
  // westbound tunnel out of the footprint.
  for (const pad of PADS) {
    parts.push(block(pad.x, 0, pad.z, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));
    parts.push(block(pad.x, 1, pad.z, "minecraft:rail"));
    spawns.push({ x: pad.x, y: 1, z: pad.z, typeId: "minecraft:hopper_minecart" });
  }

  // Underground routing (y=-1): north/south/east pads relay to the (6,-1,6)
  // junction below the center pad; the west pad already sits on the
  // westbound tunnel line. Directions below are pre-rotated with the
  // build's facing since, unlike block positions, state values aren't
  // rotated automatically.
  const south = rotateDirection("south", facing);
  const north = rotateDirection("north", facing);
  const west = rotateDirection("west", facing);
  const east = rotateDirection("east", facing);
  parts.push(block(6, -1, 4, "minecraft:hopper", { facing_direction: HOPPER_FACING[south] }));
  parts.push(block(6, -1, 5, "minecraft:hopper", { facing_direction: HOPPER_FACING[south] }));
  parts.push(block(6, -1, 8, "minecraft:hopper", { facing_direction: HOPPER_FACING[north] }));
  parts.push(block(6, -1, 7, "minecraft:hopper", { facing_direction: HOPPER_FACING[north] }));
  parts.push(block(8, -1, 6, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }));
  parts.push(block(7, -1, 6, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }));

  // Underground tunnel from the center junction out to the west wall.
  for (let x = 6; x >= 0; x--) {
    parts.push(block(x, -1, 6, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }));
  }
  parts.push(block(-1, -1, 6, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));

  const merged = merge(...parts);
  return {
    placements: merged.map((p) => ({ ...p, y: p.y + dy })),
    spawns: spawns.map((s) => ({ ...s, y: s.y + dy })),
  };
}

/**
 * External collection shaft + base double chest, shared by every level.
 * The chest sits just 1 block below ground right outside the west wall
 * (not buried deep), so it's easy to find: the bottom of the shaft
 * redirects sideways into it instead of continuing straight down.
 */
function planShaft(levels, facing) {
  const topY = (levels - 1) * LEVEL_SPACING - 1;
  const west = rotateDirection("west", facing);
  const parts = [
    block(-1, -1, 6, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }),
    block(-2, -1, 6, "minecraft:chest"),
    block(-3, -1, 6, "minecraft:chest"),
  ];
  for (let y = 0; y <= topY; y++) {
    parts.push(block(-1, y, 6, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));
  }
  return merge(...parts);
}

export const CropFarm = {
  id: "crop_farm",
  name: "Stackable Auto Crop Farm",
  shortDescription: "Farmer villagers + trading pen + hopper minecarts, quad-stackable.",
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
