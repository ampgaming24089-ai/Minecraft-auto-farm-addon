import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Auto Crop Farm — pinwheel layout, 4 farmers around 1 collector
 * ================================================================
 * Rebuilt to match a specific, widely-used reference design (a 2.6M-view
 * Bedrock tutorial): 4 farmland quadrants arranged around a single small
 * walled pit at the center, not paired plots either side of a barrier.
 * The collector ("beggar") villager stands in that center pit; every
 * farmer works their own quadrant and, when their inventory fills up,
 * walks to the pit's edge and tries to share surplus food with the caged
 * villager across a short (1-block-high) wall. No minecarts, rails, or
 * trapdoors needed — a hopper floor under the pit itself catches whatever
 * gets tossed in or dropped nearby.
 *
 *  - Farmland quadrants: 9x9 each, farmers won't work land more than ~4
 *    blocks from their composter, so a composter centered in each 9x9
 *    quadrant covers the whole thing.
 *  - Composter-on-water tower: a water source with a composter directly on
 *    top of it (skips the slab trick survival players need) hydrates the
 *    whole quadrant and is that farmer's job site in one tile, with
 *    glowstone above for light.
 *  - Center pit: a 1-block-high stone brick wall around a 3x3 floor —
 *    tall enough to fully contain the collector villager (it can't jump
 *    it), short enough that a farmer standing right outside can still
 *    reach over to share food with it. A 3x3 hopper floor catches
 *    whatever lands there and funnels it out to the shared chest.
 *  - No roof: open and heavily lit like the other farms here.
 *
 * Local space per unit: x 0-22 (width), z 0-22 (depth), y 0-4. Units
 * repeat sideways along +x (stackAxis "x") like the other ground farms.
 */

export const SIZE = { x: 23, y: 5, z: 23 };
export const LEVEL_SPACING = SIZE.x + 10; // unit width + 10-block gap to the next unit
export const MAX_LEVELS = 4;
export const stackAxis = "x";
export const levelLabel = "Number of farms (1-4)";
export const unitNoun = "Farm";

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
const CROPS = ["minecraft:wheat", "minecraft:carrots", "minecraft:potatoes"];

// 4 quadrants around the center pit, each 9x9 with a composter at its center.
const QUADRANTS = [
  { xMin: 0, xMax: 8, zMin: 0, zMax: 8, tower: [4, 4] }, // NW
  { xMin: 14, xMax: 22, zMin: 0, zMax: 8, tower: [18, 4] }, // NE
  { xMin: 0, xMax: 8, zMin: 14, zMax: 22, tower: [4, 18] }, // SW
  { xMin: 14, xMax: 22, zMin: 14, zMax: 22, tower: [18, 18] }, // SE
];
// Center pit: outer wall ring at x=9/13, z=9/13, hollow interior x10-12,z10-12.
const PIT_MIN = 9;
const PIT_MAX = 13;

function planUnit(dx, facing) {
  const parts = [];
  const spawns = [];

  parts.push(box([0, 0, 0], [22, 0, 22], "minecraft:grass_block"));

  // Four farmland quadrants, each with its own composter-on-water tower.
  for (const q of QUADRANTS) {
    for (let x = q.xMin; x <= q.xMax; x++) {
      for (let z = q.zMin; z <= q.zMax; z++) {
        if (x === q.tower[0] && z === q.tower[1]) continue; // tower tile
        const crop = CROPS[Math.floor(Math.random() * CROPS.length)];
        const growth = Math.floor(Math.random() * 8);
        parts.push(block(x, 0, z, "minecraft:farmland"));
        parts.push(block(x, 1, z, crop, { growth }));
      }
    }
    const [tx, tz] = q.tower;
    parts.push(block(tx, 0, tz, "minecraft:water"));
    parts.push(block(tx, 1, tz, "minecraft:composter"));
    parts.push(block(tx, 2, tz, "minecraft:glowstone"));
    spawns.push({ x: tx, y: 1, z: tz - 1, typeId: "minecraft:villager" });
  }

  // Center pit: red sandstone floor under the whole gap (decorative, matches
  // the reference design's path), a 1-high stone brick wall ring around the
  // 3x3 interior (tall enough to contain the collector, short enough for
  // farmers outside to reach over it), and a hopper floor inside.
  parts.push(box([PIT_MIN, 0, PIT_MIN], [PIT_MAX, 0, PIT_MAX], "minecraft:red_sandstone"));
  parts.push(box([PIT_MIN, 1, PIT_MIN], [PIT_MAX, 1, PIT_MIN], "minecraft:stone_bricks"));
  parts.push(box([PIT_MIN, 1, PIT_MAX], [PIT_MAX, 1, PIT_MAX], "minecraft:stone_bricks"));
  parts.push(box([PIT_MIN, 1, PIT_MIN], [PIT_MIN, 1, PIT_MAX], "minecraft:stone_bricks"));
  parts.push(box([PIT_MAX, 1, PIT_MIN], [PIT_MAX, 1, PIT_MAX], "minecraft:stone_bricks"));
  parts.push(block(11, 2, 11, "minecraft:glowstone"));
  spawns.push({ x: 11, y: 1, z: 11, typeId: "minecraft:villager" });

  // 3x3 hopper floor, funneled toward the center tile then straight down
  // into the shared external collection line (built once in plan()).
  const east = rotateDirection("east", facing);
  const west = rotateDirection("west", facing);
  const north = rotateDirection("north", facing);
  const south = rotateDirection("south", facing);
  parts.push(block(10, 0, 10, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }));
  parts.push(block(12, 0, 10, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }));
  parts.push(block(10, 0, 12, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }));
  parts.push(block(12, 0, 12, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }));
  parts.push(block(11, 0, 10, "minecraft:hopper", { facing_direction: HOPPER_FACING[south] }));
  parts.push(block(11, 0, 12, "minecraft:hopper", { facing_direction: HOPPER_FACING[north] }));
  parts.push(block(10, 0, 11, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }));
  parts.push(block(12, 0, 11, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }));
  parts.push(block(11, 0, 11, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));

  // Lighting: perimeter sea lanterns, no roof.
  for (const [x, z] of [[0, 11], [22, 11], [11, 0], [11, 22]]) {
    parts.push(block(x, 2, z, "minecraft:sea_lantern"));
  }

  const merged = merge(...parts);
  return {
    placements: merged.map((p) => ({ ...p, x: p.x + dx })),
    spawns: spawns.map((s) => ({ ...s, x: s.x + dx })),
  };
}

/**
 * Shared external collection spine + one double chest for the whole build.
 * Every unit's center hopper (at local x=11, z=11) drops straight down to
 * y=-1, where this spine carries everything west to the chest.
 */
function planSpine(levels, facing) {
  const west = rotateDirection("west", facing);
  const maxX = (levels - 1) * LEVEL_SPACING + 11;
  const parts = [block(-3, -1, 11, "minecraft:chest"), block(-4, -1, 11, "minecraft:chest")];
  for (let x = maxX; x >= -2; x--) {
    parts.push(block(x, -1, 11, "minecraft:hopper", { facing_direction: HOPPER_FACING[west] }));
  }
  return merge(...parts);
}

export const CropFarm = {
  id: "crop_farm",
  name: "Auto Crop Farm",
  shortDescription: "4 farmers + 1 collector per pinwheel unit, hopper-floor collection.",
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
