import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Stackable Iron Farm
 * ===================
 * Real vanilla mechanics only — no commands, no fake loot tables:
 *
 *  - Bedrock requires a MUCH bigger village than most people assume for
 *    golems to spawn at all: at least 20 beds and 10 villagers, with 75%
 *    of villagers having actually reached and used a workstation in the
 *    last in-game day. Each level here has 20 beds in two open rows of 10,
 *    each bed paired with its own composter workstation, all in one room
 *    villagers can freely path around in (sealing them in isolated pods,
 *    an earlier design, silently breaks this).
 *  - The golem population cap is **1 golem per 10 villagers** in a village.
 *    Levels are stacked CLOSE together on purpose so they merge into one
 *    combined village instead of staying separate — a 4-level build is
 *    80 villagers in one village, capping at 8 concurrent golems.
 *  - Why not spread levels far apart for "independent" villages instead?
 *    Because a village only spawns golems while a player is inside its
 *    activation region — the village's bounds expanded by roughly
 *    simulation-distance-dependent 32-48 blocks. The distance needed to
 *    keep two villages from merging (~64+ blocks beyond each village's own
 *    bounds) is bigger than that activation range, so there is no single
 *    spot a player can stand that keeps two truly separate villages both
 *    active at once — only whichever one they're currently near. Spreading
 *    levels out (vertically or horizontally) trades a taller/wider build
 *    for farms that can only run one at a time, which is strictly worse.
 *    Keeping levels close and letting them merge into one bigger village
 *    is what actually lets every floor spawn golems simultaneously from a
 *    single AFK spot at the base.
 *  - A caged zombie on each level gives villagers a nearby threat, which
 *    vanilla uses to raise golem-spawn urgency ("village under attack").
 *  - A walled, lit spawn platform sits above the bedrooms on each level,
 *    inside the village bounds, with a center drain trough. Water only
 *    flows a limited distance from a source block (about 7 tiles) before
 *    it stops, and two currents flowing head-on into each other from
 *    opposite edges create a dead/ambiguous push right where they meet —
 *    which is exactly where a center drain needs the push to be strongest.
 *    So the current here only converges on ONE axis: a full-depth water
 *    column on the west wall flows east, one on the east wall flows west,
 *    and there is no water on the north/south walls at all. Every tile
 *    only ever has one clear push direction toward the center trough.
 *  - No roof — each level is open at the top. A sealed roof was blocking
 *    light and creating dark pockets hostile mobs could spawn in; leaving
 *    it open and lighting the place heavily (see step 8) keeps light
 *    levels high enough that nothing hostile spawns instead.
 *  - Golems drop down a shaft onto a magma-block kill trench. Magma deals
 *    real damage over time (not instant, not scripted) until the golem
 *    dies; a water current in the trench carries the drops into a hopper
 *    that feeds a shared external shaft down to one base chest — every
 *    level drains into the same chest, nothing to check per floor.
 *
 * Local space: x 0-14 (width), z 0-14 (depth), y 0-8 (height per level).
 * +z is "forward" (away from the player), +x is "right".
 */

export const SIZE = { x: 15, y: 9, z: 15 };
// 10-tall level + 2-block gap to the level above — deliberately compact so
// all built levels merge into one combined village (see notes above).
export const LEVEL_SPACING = 12;
export const MAX_LEVELS = 4;

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
const BED_DIRECTION = { south: 0, west: 1, north: 2, east: 3 };

// Two rows of 10 bed/composter columns = 20 beds + 20 composters per level.
const HALL_COLUMNS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

/** Build the placement + spawn list for a single level, in local space (y already offset). */
function planLevel(dy, facing) {
  const parts = [];
  const spawns = [];

  // 1. Outer shell: floor plus the 4 side walls only, y=1 to y=8 — no roof
  //    (open top, see notes above), then clear the interior volume to air
  //    so no leftover terrain interferes with the rest of the build.
  parts.push(box([0, 0, 0], [14, 0, 14], "minecraft:stone_bricks"));
  parts.push(box([0, 1, 0], [14, 8, 0], "minecraft:cobblestone"));
  parts.push(box([0, 1, 14], [14, 8, 14], "minecraft:cobblestone"));
  parts.push(box([0, 1, 0], [0, 8, 14], "minecraft:cobblestone"));
  parts.push(box([14, 1, 0], [14, 8, 14], "minecraft:cobblestone"));
  parts.push(box([1, 1, 1], [13, 8, 13], "minecraft:air"));

  // 2. Villager hall: two open rows of 10 beds each, every bed paired with
  //    its own composter one tile further in, plus a walkway row between
  //    and after each set of rows so villagers can freely path between bed
  //    and workstation — sealing them apart from a job site is what
  //    silently broke golem spawning in the original per-corner design.
  const bedDir = rotateDirection("south", facing);
  for (const x of HALL_COLUMNS) {
    // Row A: beds z=1-2, composter z=3.
    parts.push(block(x, 1, 1, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: false }));
    parts.push(block(x, 1, 2, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: true }));
    parts.push(block(x, 1, 3, "minecraft:composter"));
    spawns.push({ x, y: 1, z: 1, typeId: "minecraft:villager" });

    // Row B: beds z=5-6, composter z=7.
    parts.push(block(x, 1, 5, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: false }));
    parts.push(block(x, 1, 6, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: true }));
    parts.push(block(x, 1, 7, "minecraft:composter"));
    spawns.push({ x, y: 1, z: 5, typeId: "minecraft:villager" });
  }
  // Walkway torches: buffer row between/after the two hall rows.
  for (const x of [1, 5, 10]) {
    parts.push(block(x, 1, 4, "minecraft:torch"));
    parts.push(block(x, 1, 8, "minecraft:torch"));
  }

  // 4. Caged zombie: visible threat that raises golem-spawn urgency.
  //    Sits past the hall in its own z-band (z=9-11) so it never overlaps
  //    the two bed rows.
  parts.push(box([10, 1, 9], [10, 3, 11], "minecraft:glass"));
  parts.push(box([12, 1, 9], [12, 3, 11], "minecraft:glass"));
  parts.push(box([10, 1, 9], [12, 3, 9], "minecraft:glass"));
  parts.push(box([10, 1, 11], [12, 3, 11], "minecraft:glass"));
  spawns.push({ x: 11, y: 1, z: 10, typeId: "minecraft:zombie" });

  // 5. Mid-ceiling separating bedrooms from the spawn platform, with a
  //    golem drop shaft punched through the center (above the trench).
  //    2 blocks wide (not 1) since iron golems have a 1.4-block-wide
  //    hitbox and can get stuck trying to fall through a single-block gap.
  parts.push(box([1, 4, 1], [13, 4, 13], "minecraft:cobblestone"));
  parts.push(box([7, 4, 10], [8, 4, 10], "minecraft:air"));

  // 6. Spawn platform (village bounds, valid golem spawn surface), drop hole
  //    in the center (2 wide, matching the shaft above), and a one-axis
  //    inward water current: a full-depth column on the west wall flows
  //    east, one on the east wall flows west, nothing on north/south. Every
  //    tile has exactly one push direction, straight toward the trough —
  //    no head-on currents canceling out at the middle.
  parts.push(box([1, 5, 1], [13, 5, 13], "minecraft:stone_bricks"));
  parts.push(box([7, 5, 10], [8, 5, 10], "minecraft:air"));
  parts.push(box([1, 6, 1], [1, 6, 13], "minecraft:water"));
  parts.push(box([13, 6, 1], [13, 6, 13], "minecraft:water"));

  // 7. Kill trench: magma floor the golem lands in after falling down the
  //    shaft, with a water current sweeping drops into a hopper embedded
  //    in the east wall, which pushes out into the shared external
  //    collection shaft (see planShaft) — one shaft is fine here since
  //    levels are close together, not hundreds of blocks apart.
  parts.push(box([4, 1, 9], [13, 2, 9], "minecraft:cobblestone")); // trench north wall
  parts.push(box([4, 1, 11], [13, 2, 11], "minecraft:cobblestone")); // trench south wall
  parts.push(box([4, 1, 10], [4, 2, 10], "minecraft:cobblestone")); // trench closed end
  parts.push(box([5, 0, 10], [13, 0, 10], "minecraft:magma"));
  parts.push(block(5, 1, 10, "minecraft:water"));
  const hopperDir = rotateDirection("east", facing);
  parts.push(block(14, 0, 10, "minecraft:hopper", { facing_direction: HOPPER_FACING[hopperDir] }));

  // 8. Lighting: with no roof, this has to do the job an enclosed room's
  //    darkness-based hostile-mob immunity used to do for free. Sea
  //    lanterns (light level 15, don't burn in the sun/rain either) lining
  //    both walls at hall height AND platform height, plus corner posts,
  //    keep light levels high enough across the whole footprint that
  //    nothing hostile spawns even with the top wide open.
  for (const z of [2, 6, 10]) {
    parts.push(block(0, 2, z, "minecraft:sea_lantern"));
    parts.push(block(14, 2, z, "minecraft:sea_lantern"));
    parts.push(block(0, 7, z, "minecraft:sea_lantern"));
    parts.push(block(14, 7, z, "minecraft:sea_lantern"));
  }
  for (const x of [4, 10]) {
    parts.push(block(x, 2, 0, "minecraft:sea_lantern"));
    parts.push(block(x, 2, 14, "minecraft:sea_lantern"));
    parts.push(block(x, 7, 0, "minecraft:sea_lantern"));
    parts.push(block(x, 7, 14, "minecraft:sea_lantern"));
  }

  const merged = merge(...parts);
  return {
    placements: merged.map((p) => ({ ...p, y: p.y + dy })),
    spawns: spawns.map((s) => ({ ...s, y: s.y + dy })),
  };
}

/**
 * External collection shaft + base double chest, shared by every level.
 * The chest sits at ground level right next to the tower (not buried), so
 * it's immediately visible/reachable without digging: the shaft hoppers
 * all face down except the bottom one, which redirects sideways into the
 * chest. Fine as one shared shaft since levels are only 12 blocks apart,
 * not hundreds — the hopper chain drains in well under a second.
 */
function planShaft(levels, facing) {
  const topY = (levels - 1) * LEVEL_SPACING;
  const east = rotateDirection("east", facing);
  const parts = [
    block(16, 0, 10, "minecraft:chest"),
    block(17, 0, 10, "minecraft:chest"),
    block(15, 0, 10, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }),
  ];
  for (let y = 1; y <= topY; y++) {
    parts.push(block(15, y, 10, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));
  }
  return merge(...parts);
}

export const IronFarm = {
  id: "iron_farm",
  name: "Stackable Iron Farm",
  shortDescription: "Village + golem trap, quad-stackable. Merged village, bigger cap.",
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
