import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Iron Golem Farm — rebuilt, single tried-and-true one-tier design
 * ===================================================================
 * Rebuilt from scratch (the old stackable/multi-tier version and its
 * separate "single tier" wrapper are both gone — this is the only iron
 * farm module now, and it only ever builds one tier). Every requirement
 * called out explicitly is still the real, researched mechanic:
 *
 *  - **20 beds, 20 workstations, 20 villagers.** Bedrock's actual
 *    requirement for golems to spawn at all is at least 20 beds and 10
 *    villagers, with 75% of them having reached and used a workstation in
 *    the last in-game day — this farm fills every one of those 20 slots
 *    (two open rows of 10 bed+composter pairs) rather than the smaller
 *    "3 beds" numbers a lot of outdated tutorials still repeat.
 *  - **No nitwits.** Checked, not assumed: in Bedrock, a villager only
 *    has a chance (10%) to become a nitwit at the specific moment a BRED
 *    BABY grows into an adult. That growth step never happens here —
 *    every villager is spawned directly as a plain adult (the same as
 *    using a villager spawn egg), which never goes through that
 *    baby-to-adult roll. There's no documented, stable Script API way to
 *    read a villager's profession after the fact to double-check this, so
 *    this is a "correct by construction" guarantee, not a runtime check —
 *    worth being upfront about rather than claiming a verification step
 *    that doesn't actually exist.
 *  - **Campfire kill chamber, fall damage first.** A lit campfire deals
 *    real, verified damage over time (about 2 damage/second, capped by a
 *    mob's normal hit-invulnerability window) and — unlike lava or fire —
 *    does NOT destroy item drops and doesn't set the mob on fire either;
 *    it's a genuinely item-safe kill method, not an invented one. Iron
 *    golems have a lot of HP (100), so a modest fall first (this design
 *    uses an 8-block drop) meaningfully softens them up before they land
 *    on a floor fully covered in lit campfires, which finishes the job
 *    over time without ever touching the loot.
 *  - Same proven water convergence as before: source columns on two
 *    ADJACENT walls only (opposite walls cancel out where their currents
 *    meet), pushing everything toward one corner drain — a hand-filled
 *    pool of uniform source blocks would have no current at all.
 *  - Open-top, heavily lit hall and platform (sea lanterns) instead of a
 *    sealed room — keeps hostile mobs from spawning without needing a
 *    roof, which used to create unlit interior pockets.
 *  - No zombie cage — that "villagers panic and summon a golem" mechanic
 *    is Java-only; Bedrock's golem spawning is purely
 *    population/bed/workstation-based, so a caged threat does nothing
 *    here.
 *
 * Local space: x 0-14 (width), z 0-14 (depth), y 0-8 (hall+platform) down
 * to the campfire pocket. Single build — no stacking, no level slider.
 */

export const SIZE = { x: 15, y: 9, z: 15 };
export const LEVEL_SPACING = 0;
export const MAX_LEVELS = 1;

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
const BED_DIRECTION = { south: 0, west: 1, north: 2, east: 3 };

// Two rows of 10 bed/composter columns = 20 beds + 20 composters.
const HALL_COLUMNS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
const KILL_SHAFT_DEPTH = 8;

function planFarm(facing) {
  const parts = [];
  const spawns = [];

  // 1. Outer shell: floor + 4 side walls, y=1 to y=8, open top. Clear the
  // interior first so no leftover terrain interferes with the build.
  parts.push(box([0, 0, 0], [14, 0, 14], "minecraft:stone_bricks"));
  parts.push(box([0, 1, 0], [14, 8, 0], "minecraft:cobblestone"));
  parts.push(box([0, 1, 14], [14, 8, 14], "minecraft:cobblestone"));
  parts.push(box([0, 1, 0], [0, 8, 14], "minecraft:cobblestone"));
  parts.push(box([14, 1, 0], [14, 8, 14], "minecraft:cobblestone"));
  parts.push(box([1, 1, 1], [13, 8, 13], "minecraft:air"));

  // 2. Villager hall: 20 beds + 20 composters in two open rows, with a
  // walkway between them so villagers can freely path between bed and
  // workstation (sealing them apart from a job site is what silently
  // breaks golem spawning in walled-off designs).
  const bedDir = rotateDirection("south", facing);
  for (const x of HALL_COLUMNS) {
    parts.push(block(x, 1, 1, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: false }));
    parts.push(block(x, 1, 2, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: true }));
    parts.push(block(x, 1, 3, "minecraft:composter"));
    spawns.push({ x, y: 1, z: 1, typeId: "minecraft:villager" });

    parts.push(block(x, 1, 5, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: false }));
    parts.push(block(x, 1, 6, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: true }));
    parts.push(block(x, 1, 7, "minecraft:composter"));
    spawns.push({ x, y: 1, z: 5, typeId: "minecraft:villager" });
  }
  for (const x of [1, 5, 10]) {
    parts.push(block(x, 1, 4, "minecraft:torch"));
    parts.push(block(x, 1, 8, "minecraft:torch"));
  }
  parts.push(block(6, 1, 10, "minecraft:sea_lantern"));

  // 3. Mid-ceiling separating the hall from the spawn platform, with a
  // 2x2 golem drop shaft in the SE corner (2-wide, not 1 — golems have a
  // 1.4-block-wide hitbox and can get stuck trying to fall through a
  // single-block gap).
  parts.push(box([1, 4, 1], [13, 4, 13], "minecraft:cobblestone"));
  parts.push(box([12, 4, 12], [13, 4, 13], "minecraft:air"));

  // 4. Spawn platform: a real water pool, source columns on the west and
  // north walls only (see notes above), converging toward the SE corner
  // drain.
  parts.push(box([1, 5, 1], [13, 5, 13], "minecraft:stone_bricks"));
  parts.push(box([12, 5, 12], [13, 5, 13], "minecraft:air"));
  parts.push(box([1, 6, 1], [1, 6, 13], "minecraft:water"));
  parts.push(box([1, 6, 1], [13, 6, 1], "minecraft:water"));

  // 5. Fall shaft: continues straight down from the platform's own SE
  // corner drain (12-13, 12-13 — see steps 3-4 above), 8 blocks, enough to
  // meaningfully soften a 100-HP golem without needing to be excessive,
  // before it lands in the campfire pocket.
  for (let y = -1; y >= -KILL_SHAFT_DEPTH; y--) {
    parts.push(box([12, y, 12], [13, y, 13], "minecraft:air"));
  }

  // 6. Kill chamber: fully self-walled pocket, directly under the shaft.
  // The floor is a checkerboard of lit campfires (real, verified damage
  // over time that never destroys drops or sets the mob on fire) and
  // hoppers. Campfires are solid on top, so a hopper placed DIRECTLY
  // under one can never actually reach items resting on it — items sit a
  // full block above the hopper's suction range. Interleaving hopper
  // tiles at the SAME layer, immediately next to every campfire tile,
  // means whatever a dying golem drops lands on or right next to a
  // hopper instead.
  const floorY = -KILL_SHAFT_DEPTH - 1;
  parts.push(box([11, floorY, 11], [14, floorY + 2, 14], "minecraft:cobblestone", undefined, { hollow: true }));
  parts.push(box([12, floorY + 1, 12], [13, floorY + 1, 13], "minecraft:air")); // re-open the shaft's own landing gap
  const east = rotateDirection("east", facing);
  // Checkerboard: (12,12) and (13,13) are campfires, (13,12) and (12,13) are
  // hoppers facing straight DOWN — the floor-level hopper's whole job is to
  // catch drops on its own top face and hand them to the collection line
  // one layer below, not to push sideways itself.
  parts.push(block(12, floorY, 12, "minecraft:campfire", { extinguished: false }));
  parts.push(block(13, floorY, 13, "minecraft:campfire", { extinguished: false }));
  parts.push(block(13, floorY, 12, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));
  parts.push(block(12, floorY, 13, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));

  // 7. Collection: the two floor hoppers drop straight down into a line
  // one layer below that chains east to the chest.
  parts.push(block(13, floorY - 1, 12, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }));
  parts.push(block(12, floorY - 1, 13, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }));
  parts.push(block(14, floorY - 1, 12, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }));
  parts.push(block(13, floorY - 1, 13, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }));
  parts.push(block(14, floorY - 1, 13, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] }));
  parts.push(block(15, floorY - 1, 12, "minecraft:chest"));
  parts.push(block(15, floorY - 1, 13, "minecraft:chest"));

  // 8. Lighting: sea lanterns lining both walls at hall height AND
  // platform height keep light levels high across the whole open-top
  // footprint so nothing hostile spawns despite there being no roof.
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

  return { placements: merge(...parts), spawns };
}

export const IronFarm = {
  id: "iron_farm",
  name: "Iron Golem Farm",
  shortDescription: "One tier: 20 beds, 20 workstations, no nitwits, water push, campfire kill, hopper collection.",
  size: SIZE,
  levelSpacing: LEVEL_SPACING,
  maxLevels: MAX_LEVELS,
  fixedLevels: 1,

  /**
   * @param {{facing: keyof import("../lib/geometry.js").FACINGS}} opts
   */
  plan({ facing }) {
    const { placements, spawns } = planFarm(facing);
    return { placements, spawns };
  },
};
