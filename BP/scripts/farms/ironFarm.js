import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Stackable Iron Farm
 * ===================
 * Real vanilla mechanics only — no commands, no fake loot tables:
 *
 *  - A 4-bed village (one bed per corner room, each claimed by a spawned
 *    villager) makes the level a valid village for iron golem spawning.
 *  - A caged zombie gives villagers a nearby threat, which vanilla uses to
 *    raise golem-spawn urgency ("village under attack").
 *  - A walled, lit 13x13 spawn platform sits above the bedrooms, inside the
 *    village bounds, with a center drain hole. Perimeter water sources
 *    create an inward current that walks any spawned golem into the drain
 *    (the same "flat floor + edge water + center hole" mob funnel used in
 *    countless vanilla mob farms).
 *  - Golems drop down a shaft onto a magma-block kill trench. Magma deals
 *    real damage over time (not instant, not scripted) until the golem
 *    dies; a water current in the trench carries the drops into a hopper.
 *  - Each level's hopper feeds sideways into a shared vertical hopper shaft
 *    on the outside of the tower, which drains to a double chest at the
 *    base. Multiple levels share one shaft/chest.
 *
 * Local space: x 0-14 (width), z 0-14 (depth), y 0-9 (height per level).
 * +z is "forward" (away from the player), +x is "right".
 */

export const SIZE = { x: 15, y: 10, z: 15 };
export const LEVEL_SPACING = 12; // 10 tall level + 2 block gap to the level above
export const MAX_LEVELS = 4;

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
const BED_DIRECTION = { south: 0, west: 1, north: 2, east: 3 };

const BED_ROOMS = [
  { bx: 1, bz: 1, extraWallX: 4, extraWallZ: 4, bed: { x: 2, z: 2 } }, // NW
  { bx: 11, bz: 1, extraWallX: 10, extraWallZ: 4, bed: { x: 12, z: 2 } }, // NE
  { bx: 1, bz: 11, extraWallX: 4, extraWallZ: 10, bed: { x: 2, z: 12 } }, // SW
  { bx: 11, bz: 11, extraWallX: 10, extraWallZ: 10, bed: { x: 12, z: 12 } }, // SE
];

/** Build the placement + spawn list for a single level, in local space (y already offset). */
function planLevel(dy, facing) {
  const parts = [];
  const spawns = [];

  // 1. Outer shell: fills the full floor (y=0), full roof (y=9) and the
  //    perimeter wall ring for every y in between, in one hollow box.
  parts.push(box([0, 0, 0], [14, 9, 14], "minecraft:cobblestone", undefined, { hollow: true }));

  // 2. Proper floor material, then clear the interior volume to air so no
  //    leftover terrain interferes with the rest of the build.
  parts.push(box([0, 0, 0], [14, 0, 14], "minecraft:stone_bricks"));
  parts.push(box([1, 1, 1], [13, 8, 13], "minecraft:air"));

  // 3. Four corner bedrooms, each a sealed 3x3 room with one claimed bed.
  for (const room of BED_ROOMS) {
    // Interior-facing walls only — the two shell-facing sides are already
    // covered by the outer cobblestone shell placed in step 1.
    parts.push(box([room.extraWallX, 1, room.bz], [room.extraWallX, 3, room.bz + 2], "minecraft:cobblestone"));
    parts.push(box([room.bx, 1, room.extraWallZ], [room.bx + 2, 3, room.extraWallZ], "minecraft:cobblestone"));
    parts.push(box([room.bx, 4, room.bz], [room.bx + 2, 4, room.bz + 2], "minecraft:cobblestone"));

    const bedDir = rotateDirection("south", facing);
    parts.push(block(room.bed.x, 1, room.bed.z - 1, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: false }));
    parts.push(block(room.bed.x, 1, room.bed.z, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: true }));
    parts.push(block(room.bx, 1, room.bz, "minecraft:torch"));

    spawns.push({ x: room.bed.x, y: 1, z: room.bed.z - 1, typeId: "minecraft:villager" });
  }

  // 4. Mid-ceiling separating bedrooms from the spawn platform, with a
  //    golem drop shaft punched through the center. 2 blocks wide (not 1)
  //    since iron golems have a 1.4-block-wide hitbox and can get stuck
  //    trying to fall through a single-block gap.
  parts.push(box([1, 4, 1], [13, 4, 13], "minecraft:cobblestone"));
  parts.push(box([7, 4, 7], [8, 4, 7], "minecraft:air"));

  // 5. Caged zombie: visible threat that raises golem-spawn urgency.
  parts.push(box([10, 1, 6], [10, 3, 8], "minecraft:glass"));
  parts.push(box([12, 1, 6], [12, 3, 8], "minecraft:glass"));
  parts.push(box([10, 1, 6], [12, 3, 6], "minecraft:glass"));
  parts.push(box([10, 1, 8], [12, 3, 8], "minecraft:glass"));
  spawns.push({ x: 11, y: 1, z: 7, typeId: "minecraft:zombie" });

  // 6. Spawn platform (village bounds, valid golem spawn surface), drop hole
  //    in the center (2 wide, matching the shaft above), and an inward
  //    water current from the edges. A full perimeter ring of water
  //    sources (not a handful of scattered points) is what actually
  //    creates a reliable connected current toward the only low point
  //    (the drain hole) — a few isolated sources just form separate
  //    puddles that don't push anything anywhere.
  parts.push(box([1, 5, 1], [13, 5, 13], "minecraft:stone_bricks"));
  parts.push(box([7, 5, 7], [8, 5, 7], "minecraft:air"));
  parts.push(box([1, 6, 1], [13, 6, 1], "minecraft:water"));
  parts.push(box([1, 6, 13], [13, 6, 13], "minecraft:water"));
  parts.push(box([1, 6, 1], [1, 6, 13], "minecraft:water"));
  parts.push(box([13, 6, 1], [13, 6, 13], "minecraft:water"));

  // 7. Kill trench: magma floor the golem lands in after falling down the
  //    shaft, with a water current sweeping drops into a hopper embedded
  //    in the east wall, which pushes out to the external collection shaft.
  parts.push(box([4, 1, 6], [13, 2, 6], "minecraft:cobblestone")); // trench north wall
  parts.push(box([4, 1, 8], [13, 2, 8], "minecraft:cobblestone")); // trench south wall
  parts.push(box([4, 1, 7], [4, 2, 7], "minecraft:cobblestone")); // trench closed end
  parts.push(box([5, 0, 7], [13, 0, 7], "minecraft:magma"));
  parts.push(block(5, 1, 7, "minecraft:water"));
  const hopperDir = rotateDirection("east", facing);
  parts.push(block(14, 0, 7, "minecraft:hopper", { facing_direction: HOPPER_FACING[hopperDir] }));

  // 8. Lighting to keep hostile mobs from spawning inside (golems are not
  //    light-gated, so this is safe for the spawn platform too).
  for (const [x, y, z] of [[0, 2, 7], [14, 2, 7], [7, 2, 0], [7, 2, 14], [0, 7, 7], [14, 7, 7], [7, 7, 0], [7, 7, 14]]) {
    parts.push(block(x, y, z, "minecraft:sea_lantern"));
  }

  const merged = merge(...parts);
  return {
    placements: merged.map((p) => ({ ...p, y: p.y + dy })),
    spawns: spawns.map((s) => ({ ...s, y: s.y + dy })),
  };
}

/**
 * External collection shaft + base double chest, shared by every level.
 * The chest sits at ground level right next to the tower (not buried),
 * so it's immediately visible/reachable without digging: the shaft
 * hoppers all face down except the bottom one, which redirects sideways
 * into the chest.
 */
function planShaft(levels, facing) {
  const topY = (levels - 1) * LEVEL_SPACING;
  const east = rotateDirection("east", facing);
  const parts = [
    block(16, 0, 7, "minecraft:chest"),
    block(17, 0, 7, "minecraft:chest"),
    block(15, 0, 7, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }),
  ];
  for (let y = 1; y <= topY; y++) {
    parts.push(block(15, y, 7, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));
  }
  return merge(...parts);
}

export const IronFarm = {
  id: "iron_farm",
  name: "Stackable Iron Farm",
  shortDescription: "Village + golem trap, quad-stackable. Real spawns, real drops.",
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
