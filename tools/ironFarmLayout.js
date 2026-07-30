import { fill, set, summon } from "./cmdBuilder.js";

/**
 * Stackable Iron Farm — command-based layout (see BP/scripts/farms history
 * in git for the original Script API version this was ported from; the
 * mechanics/geometry are unchanged, only *how* it gets placed changed).
 *
 * Fixed orientation: always builds extending +x/+z from wherever the
 * beacon item is used, no rotation. Local space: x 0-14, z 0-14, y 0-9
 * per level, relative to the executing player's position at ~0 ~0 ~0.
 */

export const SIZE = { x: 15, y: 10, z: 15 };
export const LEVEL_SPACING = 12; // 10 tall level + 2 block gap to the level above
export const MAX_LEVELS = 4;

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
const BED_DIRECTION = { south: 0 };

const BED_ROOMS = [
  { bx: 1, bz: 1, extraWallX: 4, extraWallZ: 4, bed: { x: 2, z: 2 } }, // NW
  { bx: 11, bz: 1, extraWallX: 10, extraWallZ: 4, bed: { x: 12, z: 2 } }, // NE
  { bx: 1, bz: 11, extraWallX: 4, extraWallZ: 10, bed: { x: 2, z: 12 } }, // SW
  { bx: 11, bz: 11, extraWallX: 10, extraWallZ: 10, bed: { x: 12, z: 12 } }, // SE
];

function planLevel(dy) {
  const L = []; // command lines, in execution order (later overwrites earlier at same coord)
  const y = (n) => n + dy;

  // 1. Outer shell in one command: hollow mode fills the shell (floor, roof,
  //    wall ring) and clears the interior to air in a single /fill.
  L.push(fill([0, y(0), 0], [14, y(9), 14], "minecraft:cobblestone", undefined, "hollow"));

  // 2. Proper floor material.
  L.push(fill([0, y(0), 0], [14, y(0), 14], "minecraft:stone_bricks"));

  // 3. Four corner bedrooms, each a sealed 3x3 room with one claimed bed.
  for (const room of BED_ROOMS) {
    L.push(fill([room.extraWallX, y(1), room.bz], [room.extraWallX, y(3), room.bz + 2], "minecraft:cobblestone"));
    L.push(fill([room.bx, y(1), room.extraWallZ], [room.bx + 2, y(3), room.extraWallZ], "minecraft:cobblestone"));
    L.push(fill([room.bx, y(4), room.bz], [room.bx + 2, y(4), room.bz + 2], "minecraft:cobblestone"));

    L.push(set(room.bed.x, y(1), room.bed.z - 1, "minecraft:bed", { direction: BED_DIRECTION.south, head_piece_bit: false }));
    L.push(set(room.bed.x, y(1), room.bed.z, "minecraft:bed", { direction: BED_DIRECTION.south, head_piece_bit: true }));
    L.push(set(room.bx, y(1), room.bz, "minecraft:torch"));

    L.push(summon(room.bed.x, y(1), room.bed.z - 1, "minecraft:villager"));
  }

  // 4. Mid-ceiling with a golem drop shaft punched through the center.
  L.push(fill([1, y(4), 1], [13, y(4), 13], "minecraft:cobblestone"));
  L.push(set(7, y(4), 7, "minecraft:air"));

  // 5. Caged zombie: visible threat that raises golem-spawn urgency.
  L.push(fill([10, y(1), 6], [10, y(3), 8], "minecraft:glass"));
  L.push(fill([12, y(1), 6], [12, y(3), 8], "minecraft:glass"));
  L.push(fill([10, y(1), 6], [12, y(3), 6], "minecraft:glass"));
  L.push(fill([10, y(1), 8], [12, y(3), 8], "minecraft:glass"));
  L.push(summon(11, y(1), 7, "minecraft:zombie"));

  // 6. Spawn platform with a center drain hole and an inward water current.
  L.push(fill([1, y(5), 1], [13, y(5), 13], "minecraft:stone_bricks"));
  L.push(set(7, y(5), 7, "minecraft:air"));
  const currentPoints = [
    [3, 3], [11, 3], [3, 11], [11, 11],
    [7, 3], [7, 11], [3, 7], [11, 7],
  ];
  for (const [x, z] of currentPoints) L.push(set(x, y(6), z, "minecraft:water"));

  // 7. Kill trench: magma floor + water current sweeping drops into a
  //    hopper embedded in the east wall, pushing out to the collection shaft.
  L.push(fill([4, y(1), 6], [13, y(2), 6], "minecraft:cobblestone"));
  L.push(fill([4, y(1), 8], [13, y(2), 8], "minecraft:cobblestone"));
  L.push(fill([4, y(1), 7], [4, y(2), 7], "minecraft:cobblestone"));
  L.push(fill([5, y(0), 7], [13, y(0), 7], "minecraft:magma"));
  L.push(set(5, y(1), 7, "minecraft:water"));
  L.push(set(14, y(0), 7, "minecraft:hopper", { facing_direction: HOPPER_FACING.east }));

  // 8. Lighting (golems aren't light-gated, so this is safe for the platform too).
  for (const [x, py, z] of [[0, 2, 7], [14, 2, 7], [7, 2, 0], [7, 2, 14], [0, 7, 7], [14, 7, 7], [7, 7, 0], [7, 7, 14]]) {
    L.push(set(x, y(py), z, "minecraft:sea_lantern"));
  }

  return L;
}

/** External collection shaft + base double chest, shared by every level. */
function planShaft(levels) {
  const topY = (levels - 1) * LEVEL_SPACING;
  const L = [
    set(15, -2, 7, "minecraft:chest"),
    set(16, -2, 7, "minecraft:chest"),
  ];
  for (let y = -1; y <= topY; y++) {
    L.push(set(15, y, 7, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));
  }
  return L;
}

/** @param {number} levels 1-4 @returns {string[]} full ordered command list */
export function generateIronFarm(levels) {
  const lines = [];
  for (let i = 0; i < levels; i++) {
    lines.push(...planLevel(i * LEVEL_SPACING));
  }
  lines.push(...planShaft(levels));
  return lines;
}
