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
 *    last in-game day. Each level here is a full, self-sufficient village
 *    on its own: 20 beds in two open rows of 10, each bed paired with its
 *    own composter workstation, all in one room villagers can freely path
 *    around in (sealing them in isolated pods, an earlier design, silently
 *    breaks this).
 *  - The golem population cap is **1 golem per 10 villagers** — 20
 *    villagers on a level caps that level at 2 concurrent golems.
 *  - Bedrock **merges** separate villages into one if their bounds come
 *    within 64 blocks of each other. A stack with levels close together
 *    (earlier versions of this farm used 12) is really just ONE combined
 *    village sharing ONE population cap no matter how many total villagers
 *    exist — stacking more floors close together does not add more
 *    concurrent golems. To make every floor its own independent village
 *    with its own 2-golem cap, floors here are spaced 80 blocks apart
 *    (comfortably clearing the 64-block merge threshold with margin), so a
 *    4-level build gives 4 independent villages = up to 8 concurrent
 *    golems, not 2. This is the direct trade for a MUCH taller structure —
 *    a 4-level build is roughly 250 blocks tall. There's no way around
 *    that and still get real independent per-floor spawn caps.
 *  - Because a shared vertical hopper shaft spanning hundreds of blocks
 *    would take real minutes per item to reach the bottom, each level
 *    collects into its OWN chest right next to its own kill trench instead
 *    of one shaft feeding a single base chest. Check every level, not just
 *    the bottom.
 *  - A caged zombie gives villagers a nearby threat, which vanilla uses to
 *    raise golem-spawn urgency ("village under attack").
 *  - A walled, lit spawn platform sits above the bedrooms, inside the
 *    village bounds, with a center drain hole. Perimeter water sources
 *    create an inward current that walks any spawned golem into the drain
 *    (the same "flat floor + edge water + center hole" mob funnel used in
 *    countless vanilla mob farms).
 *  - Golems drop down a shaft onto a magma-block kill trench. Magma deals
 *    real damage over time (not instant, not scripted) until the golem
 *    dies; a water current in the trench carries the drops into a hopper
 *    feeding that level's own chest.
 *
 * Local space: x 0-14 (width), z 0-14 (depth), y 0-9 (height per level).
 * +z is "forward" (away from the player), +x is "right".
 */

export const SIZE = { x: 15, y: 10, z: 15 };
// 10-tall level + 70-block gap to the next level's beds — clears the
// 64-block village-merge threshold with margin so each floor stays its
// own independent village (own golem population cap).
export const LEVEL_SPACING = 80;
export const MAX_LEVELS = 4;

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
const BED_DIRECTION = { south: 0, west: 1, north: 2, east: 3 };

// Two rows of 10 bed/composter columns = 20 beds + 20 composters per level.
const HALL_COLUMNS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

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

  // 3. Villager hall: two open rows of 10 beds each, every bed paired with
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
  //    in the center (2 wide, matching the shaft above), and an inward
  //    water current from the edges. A full perimeter ring of water
  //    sources (not a handful of scattered points) is what actually
  //    creates a reliable connected current toward the only low point
  //    (the drain hole) — a few isolated sources just form separate
  //    puddles that don't push anything anywhere.
  parts.push(box([1, 5, 1], [13, 5, 13], "minecraft:stone_bricks"));
  parts.push(box([7, 5, 10], [8, 5, 10], "minecraft:air"));
  parts.push(box([1, 6, 1], [13, 6, 1], "minecraft:water"));
  parts.push(box([1, 6, 13], [13, 6, 13], "minecraft:water"));
  parts.push(box([1, 6, 1], [1, 6, 13], "minecraft:water"));
  parts.push(box([13, 6, 1], [13, 6, 13], "minecraft:water"));

  // 7. Kill trench: magma floor the golem lands in after falling down the
  //    shaft, with a water current sweeping drops into a hopper that feeds
  //    this level's OWN chest right outside the east wall (a shared shaft
  //    across an 80-block level spacing would take real minutes per item).
  parts.push(box([4, 1, 9], [13, 2, 9], "minecraft:cobblestone")); // trench north wall
  parts.push(box([4, 1, 11], [13, 2, 11], "minecraft:cobblestone")); // trench south wall
  parts.push(box([4, 1, 10], [4, 2, 10], "minecraft:cobblestone")); // trench closed end
  parts.push(box([5, 0, 10], [13, 0, 10], "minecraft:magma"));
  parts.push(block(5, 1, 10, "minecraft:water"));
  const hopperDir = rotateDirection("east", facing);
  parts.push(block(14, 0, 10, "minecraft:hopper", { facing_direction: HOPPER_FACING[hopperDir] }));
  parts.push(block(15, 0, 10, "minecraft:chest"));
  parts.push(block(16, 0, 10, "minecraft:chest"));

  // 8. Lighting to keep hostile mobs from spawning inside (golems are not
  //    light-gated, so this is safe for the spawn platform too).
  for (const [x, y, z] of [[0, 2, 4], [14, 2, 4], [7, 2, 0], [7, 2, 14], [0, 7, 10], [14, 7, 10], [7, 7, 0], [7, 7, 14]]) {
    parts.push(block(x, y, z, "minecraft:sea_lantern"));
  }

  const merged = merge(...parts);
  return {
    placements: merged.map((p) => ({ ...p, y: p.y + dy })),
    spawns: spawns.map((s) => ({ ...s, y: s.y + dy })),
  };
}

export const IronFarm = {
  id: "iron_farm",
  name: "Stackable Iron Farm",
  shortDescription: "Village + golem trap, quad-stackable. Independent village per floor.",
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
    return { placements, spawns };
  },
};
