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
 *  - No zombie cage. Earlier versions of this farm included one on the
 *    theory that a nearby threat raises golem-spawn urgency — that's real
 *    on Java (3 panicking villagers can emergency-summon a golem), but
 *    that panic mechanic doesn't exist on Bedrock at all. Bedrock's golem
 *    spawning is purely population/bed/workstation-based (see above), so a
 *    caged zombie does nothing here except waste space and materials.
 *  - A walled, lit spawn platform sits above the bedrooms on each level,
 *    inside the village bounds, and is a real water pool — not just a thin
 *    current over a dry floor — matching a well-known reference design. A
 *    source column on the west wall (flows east) and one on the north wall
 *    (flows south) combine to push everything toward the SE corner; the
 *    rest of the pool fills in naturally from those two sources within
 *    moments of the chunk loading, the same way it would in survival. A
 *    hand-placed pool of uniform source blocks would have NO push at all
 *    (source blocks touching other source blocks don't create a current —
 *    only the edge where a source meets open space does), so it matters
 *    that only those two walls are literal sources and the rest is left
 *    for the game's own fluid physics to fill in.
 *  - No roof — each level is open at the top. A sealed roof was blocking
 *    light and creating dark pockets hostile mobs could spawn in; leaving
 *    it open and lighting the place heavily (see step 8) keeps light
 *    levels high enough that nothing hostile spawns instead.
 *  - Golems drop down a corner shaft onto a magma kill pocket, with one
 *    hopper tile as a direct catch point, feeding a shared external shaft
 *    down to one base chest. An earlier version of this pocket used lava
 *    (matching a reference design's material list) — that was reverted.
 *    Lava is a FLUID and spreads into any open neighboring space; the
 *    pocket's walls only spanned the layer above the lava, not the lava's
 *    own floor layer, so it leaked out across the hall floor in testing.
 *    Magma is a solid block, not a fluid — it physically cannot spread or
 *    leak regardless of what does or doesn't wall it in, which is why it's
 *    used here instead. It deals the same real damage-over-time without
 *    touching item drops at all, so there's no loot-loss trade-off either.
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
export function planLevel(dy, facing) {
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

  // 4. Extra floor-level lighting in the open z=9-11 band between the hall
  //    and the kill pocket wall (no roof, so this has to be lit directly
  //    rather than relying on an enclosed room).
  parts.push(block(6, 1, 10, "minecraft:sea_lantern"));

  // 5. Mid-ceiling separating bedrooms from the spawn platform, with a
  //    golem drop shaft punched through the SE corner (above the kill
  //    pocket). 2x2, not 1-wide, since iron golems have a 1.4-block-wide
  //    hitbox and can get stuck trying to fall through a single-block gap.
  parts.push(box([1, 4, 1], [13, 4, 13], "minecraft:cobblestone"));
  parts.push(box([12, 4, 12], [13, 4, 13], "minecraft:air"));

  // 6. Spawn platform: a real pool (see notes above), source columns on
  //    the west and north walls only, converging toward the SE corner
  //    drain (2-wide, matching the shaft above).
  parts.push(box([1, 5, 1], [13, 5, 13], "minecraft:stone_bricks"));
  parts.push(box([12, 5, 12], [13, 5, 13], "minecraft:air"));
  parts.push(box([1, 6, 1], [1, 6, 13], "minecraft:water"));
  parts.push(box([1, 6, 1], [13, 6, 1], "minecraft:water"));

  // 7. Kill pocket: magma fills the landing zone under the corner drain
  //    (see the lava-vs-magma note above for why), with one hopper tile as
  //    a direct catch point. Walls seal the pocket off from the hall on
  //    every layer from the floor (y=0) up through y=3 — a wall that only
  //    starts one layer above the floor leaves the floor's own layer open,
  //    which is exactly how the lava version leaked before.
  parts.push(box([9, 0, 11], [9, 3, 13], "minecraft:cobblestone"));
  parts.push(box([9, 0, 11], [13, 3, 11], "minecraft:cobblestone"));
  parts.push(box([10, 0, 12], [13, 0, 13], "minecraft:magma"));
  const east = rotateDirection("east", facing);
  parts.push(block(13, 0, 13, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }));
  parts.push(block(14, 0, 13, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }));

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
export function planShaft(levels, facing) {
  const topY = (levels - 1) * LEVEL_SPACING;
  const east = rotateDirection("east", facing);
  const parts = [
    block(16, 0, 13, "minecraft:chest"),
    block(17, 0, 13, "minecraft:chest"),
    block(15, 0, 13, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }),
  ];
  for (let y = 1; y <= topY; y++) {
    parts.push(block(15, y, 13, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));
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
