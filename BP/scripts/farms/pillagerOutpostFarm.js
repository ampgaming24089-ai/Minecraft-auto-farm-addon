import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Pillager Outpost Farm (Ominous Bottle Farm)
 * ============================================
 * Build this directly above (or immediately beside) the tower of an
 * EXISTING pillager outpost — it does not generate or locate an outpost
 * itself. Script API has no stable way to search the world for a
 * generated structure, so, same as every other farm in this addon, you
 * position it yourself: stand at the top of your outpost's tower and use
 * the build tool there.
 *
 * Two things about the request this corrects, both checked rather than
 * guessed:
 *
 *  - "Ominous Bottle" is real and IS obtainable this way. Pillager
 *    Captains — the pillager carrying the Ominous Banner, which spawn at
 *    outposts and in patrols — have a chance to drop an Ominous Bottle
 *    when killed. (They're also found in Trial Chamber vaults, but that's
 *    a separate source, not what this farm targets.) A pillager-outpost
 *    kill farm is a legitimate way to farm them.
 *  - A real "auto trident killer" (a Channeling-enchanted trident thrown
 *    during a live thunderstorm, striking lightning that instantly kills
 *    whatever it hits) is a genuine mechanic, but it only works during an
 *    actual in-world thunderstorm and needs a Channeling trident to begin
 *    with — not something a static structure can keep running unattended,
 *    and not something this addon should hand you out of nowhere either.
 *
 * Kill system (rebuilt): the player does the killing, in a bottom chamber
 * reached by a safe ladder shaft — not an automated crusher. A shorter,
 * 12-block fall (about 9 damage — real fall-damage math, 1 damage per
 * block past the first 3) softens anything that drops without being
 * outright lethal on its own, so there's always something left for you to
 * actually finish off by hand when you climb down. This is also the
 * better choice for loot, not just the one that was asked for: several
 * bonus drop conditions (Looting's bonus rolls, certain rare drops) are
 * gated on the kill being a PLAYER kill, which an automated kill would
 * never qualify for.
 *
 * Mechanics used:
 *  - Outposts spawn pillagers (including captains) on the highest opaque
 *    block with open space above it, within the structure's own bounds —
 *    a structure-based spawn rule, not the normal light-level hostile
 *    spawn check. Building a platform that becomes the new "highest
 *    point" above the tower is what redirects those spawns onto it. This
 *    platform is deliberately left UNLIT (unlike every other farm here) —
 *    normal hostile mobs may also spawn here in the dark, but that's a
 *    non-issue: anything that spawns falls down the same shaft into the
 *    same chamber.
 *  - Same proven water convergence as the other farms: source columns on
 *    two ADJACENT walls only (opposite walls cancel out where their
 *    currents meet), pushing everything toward one corner drain.
 *  - Bottom chamber: a real room (6x6, 2 blocks tall) under the shaft, not
 *    a 1-block trap — enough space to actually fight in. The whole floor
 *    is a hopper grid (two layers: every floor tile drops straight down,
 *    then a spine drains everything to one corner chest), so whatever you
 *    kill gets collected automatically even though the kill itself isn't
 *    automated. A ladder shaft with a door at the bottom gives you a safe
 *    way in and out — mobs don't climb ladders (aside from spiders), so
 *    the door is there for your control, not because the shaft itself is
 *    dangerous.
 *
 * Local space: x 0-22, z 0-22 (platform), y 0-3 (platform height) down to
 * the chamber. Single build, not stackable — it's positional, like the
 * other farms, but tied to one real-world spot.
 */

export const SIZE = { x: 27, y: 4, z: 27 };
export const LEVEL_SPACING = SIZE.x;
export const MAX_LEVELS = 1;

const FACING_STATE = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
const DOOR_DIRECTION = { south: 0, west: 1, north: 2, east: 3 };
const SHAFT_DEPTH = 12;

function planFarm(facing) {
  const parts = [];

  // Open platform, low perimeter wall (keeps spawned mobs from wandering
  // off the edge before the water reaches them), deliberately unlit.
  parts.push(box([0, 0, 0], [22, 0, 22], "minecraft:cobblestone"));
  parts.push(box([0, 1, 0], [22, 2, 0], "minecraft:cobblestone"));
  parts.push(box([0, 1, 22], [22, 2, 22], "minecraft:cobblestone"));
  parts.push(box([0, 1, 0], [0, 2, 22], "minecraft:cobblestone"));
  parts.push(box([22, 1, 0], [22, 2, 22], "minecraft:cobblestone"));

  // Water convergence: west wall flows east, north wall flows south,
  // draining to a 2-wide SE corner (see notes above for why adjacent, not
  // opposite, walls are what actually pushes).
  parts.push(box([21, 0, 21], [22, 0, 22], "minecraft:air"));
  parts.push(box([1, 1, 1], [1, 1, 21], "minecraft:water"));
  parts.push(box([1, 1, 1], [21, 1, 1], "minecraft:water"));

  // Fall shaft — 12 blocks, softening but not lethal (see notes above).
  for (let y = -1; y >= -SHAFT_DEPTH; y--) {
    parts.push(box([21, y, 21], [22, y, 22], "minecraft:air"));
  }

  // Bottom chamber: a real 6x6, 2-tall room under the shaft, not a
  // 1-block trap. Shell first, floor hopper grid punched in afterward.
  const floorY = -SHAFT_DEPTH - 1;
  parts.push(box([18, floorY, 18], [25, floorY + 3, 25], "minecraft:cobblestone", undefined, { hollow: true }));
  // Re-open the shaft's own landing gap (defensive — the interior here is
  // already open at this layer, but this guarantees it regardless of
  // exactly how the hollow shell above resolves).
  parts.push(box([21, floorY + 1, 21], [22, floorY + 1, 22], "minecraft:air"));

  // Floor hopper grid: every interior tile (19-24, 19-24) drops straight
  // down, one layer below drains west to x=19, then a final column drains
  // north to the corner chest — same "row + spine" collection pattern
  // used by the giant crop farm's hopper floor, just smaller.
  for (let x = 19; x <= 24; x++) {
    for (let z = 19; z <= 24; z++) {
      parts.push(block(x, floorY, z, "minecraft:hopper", { facing_direction: FACING_STATE.down }));
    }
  }
  for (let z = 19; z <= 24; z++) {
    for (let x = 19; x <= 24; x++) {
      if (x === 19) {
        parts.push(block(x, floorY - 1, z, "minecraft:hopper", { facing_direction: FACING_STATE.down }));
      } else {
        const west = rotateDirection("west", facing);
        parts.push(block(x, floorY - 1, z, "minecraft:hopper", { facing_direction: FACING_STATE[west] }));
      }
    }
  }
  for (let z = 19; z <= 24; z++) {
    const north = rotateDirection("north", facing);
    parts.push(block(19, floorY - 2, z, "minecraft:hopper", { facing_direction: FACING_STATE[north] }));
  }
  parts.push(block(19, floorY - 2, 18, "minecraft:chest"));
  parts.push(block(18, floorY - 2, 18, "minecraft:chest"));

  // Player access: an enclosed ladder shaft just outside the chamber's
  // west wall, from the platform down to the chamber floor, opening
  // through a real 2-tall door at the bottom. Support column at x=16
  // (ladders need a solid block behind them), side walls at z=20/22 so
  // the shaft is fully self-contained regardless of what's naturally
  // around it, and the ladder column itself at x=17 stays untouched by
  // anything placed afterward (order matters — nothing below overlaps it).
  parts.push(box([16, floorY + 1, 21], [16, 3, 21], "minecraft:cobblestone"));
  parts.push(box([17, floorY + 1, 20], [17, 3, 20], "minecraft:cobblestone"));
  parts.push(box([17, floorY + 1, 22], [17, 3, 22], "minecraft:cobblestone"));
  for (let y = 3; y >= floorY + 1; y--) {
    parts.push(block(17, y, 21, "minecraft:ladder", { facing_direction: FACING_STATE.east }));
  }
  const doorDir = rotateDirection("east", facing);
  parts.push(
    block(18, floorY + 1, 21, "minecraft:wooden_door", { direction: DOOR_DIRECTION[doorDir], upper_block_bit: false, open_bit: false })
  );
  parts.push(
    block(18, floorY + 2, 21, "minecraft:wooden_door", { direction: DOOR_DIRECTION[doorDir], upper_block_bit: true, open_bit: false })
  );

  return merge(...parts);
}

export const PillagerOutpostFarm = {
  id: "pillager_outpost_farm",
  name: "Pillager Outpost Farm",
  shortDescription: "Build atop an existing outpost tower. Softening fall shaft, player-kill bottom chamber, hopper floor.",
  size: SIZE,
  levelSpacing: LEVEL_SPACING,
  maxLevels: MAX_LEVELS,
  fixedLevels: 1,

  /**
   * @param {{facing: keyof import("../lib/geometry.js").FACINGS}} opts
   */
  plan({ facing }) {
    return { placements: planFarm(facing), spawns: [] };
  },
};
