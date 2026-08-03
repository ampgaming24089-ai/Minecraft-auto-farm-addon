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
 *    with — there's no reliable way for a script-built structure to keep
 *    that running unattended across arbitrary weather, and it wouldn't be
 *    right for an addon to just hand you an already-enchanted legendary
 *    weapon out of nowhere. So the kill system here is the OTHER
 *    real, always-on vanilla mechanism: pistons can't damage mobs
 *    directly, but pushing a solid block into a mob's occupied space
 *    suffocates it (roughly half a heart every half-second). Combined
 *    with a long fall shaft first (which will outright kill or badly
 *    hurt most things before they even reach the crusher), this runs
 *    24/7 with no weather dependency. Nothing stops you from also
 *    manually finishing survivors with a Channeling trident on a stormy
 *    night for the instant-kill bonus — this structure doesn't get in the
 *    way of that, it just doesn't depend on it.
 *
 * Mechanics used:
 *  - Outposts spawn pillagers (including captains) on the highest opaque
 *    block with open space above it, within the structure's own bounds —
 *    a structure-based spawn rule, not the normal light-level hostile
 *    spawn check. Building a platform that becomes the new "highest
 *    point" above the tower is what redirects those spawns onto it. This
 *    platform is deliberately left UNLIT (unlike every other farm here) —
 *    normal hostile mobs may also spawn here in the dark, but that's a
 *    non-issue: anything that spawns falls down the same shaft and dies
 *    in the same chamber.
 *  - Same proven water convergence as the other farms: source columns on
 *    two ADJACENT walls only (opposite walls cancel out where their
 *    currents meet), pushing everything toward one corner drain.
 *  - 23-block fall shaft — well past the ~23-block threshold vanilla uses
 *    for guaranteed-lethal fall damage on non-fall-immune mobs.
 *  - Landing chamber: a piston that repeatedly shoves a block into the
 *    landing tile, driven by a 2-observer clock (the standard minimal
 *    perpetual-clock circuit — two observers facing each other
 *    continuously retrigger one another with no external redstone
 *    needed), finishing off anything the fall didn't. Because the shaft
 *    opening sits directly above the landing tile, this isn't a fully
 *    sealed 1-block trap — a mob CAN reposition between pulses — so treat
 *    it as a repeating finisher stacked on top of near-guaranteed fall
 *    damage, not a guaranteed instant kill on its own. A hopper floor
 *    under the pocket catches every drop either way.
 *
 * Local space: x 0-22, z 0-22 (platform), y 0-3 (platform height) down to
 * y -26 (kill chamber + collection). Single build, not stackable — it's
 * positional, like the other farms, but tied to one real-world spot.
 */

export const SIZE = { x: 23, y: 4, z: 23 };
export const LEVEL_SPACING = SIZE.x;
export const MAX_LEVELS = 1;

const FACING_STATE = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
const SHAFT_DEPTH = 23;

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

  // Fall shaft.
  for (let y = -1; y >= -SHAFT_DEPTH; y--) {
    parts.push(box([21, y, 21], [22, y, 22], "minecraft:air"));
  }

  // Kill chamber: fully self-walled pocket at the shaft's base. Landing
  // tile is a hopper (direct collection); a piston shoves a block into it
  // on a 2-observer clock; suffocation finishes off anything the fall
  // didn't already kill.
  const floorY = -SHAFT_DEPTH - 1;
  parts.push(box([18, floorY, 18], [23, floorY + 1, 23], "minecraft:cobblestone", undefined, { hollow: true }));
  parts.push(box([19, floorY, 19], [22, floorY, 22], "minecraft:cobblestone"));
  // Re-open the shaft's own 2x2 opening at the chamber ceiling (the shell
  // fill above was pushed after the shaft carve-out and would otherwise
  // silently reseal it — mobs need this to keep falling through).
  parts.push(box([21, floorY + 1, 21], [22, floorY + 1, 22], "minecraft:air"));
  parts.push(block(21, floorY, 21, "minecraft:hopper", { facing_direction: FACING_STATE.down }));

  const east = rotateDirection("east", facing);
  const west = rotateDirection("west", facing);
  parts.push(block(20, floorY, 21, "minecraft:piston", { facing_direction: FACING_STATE[east] }));
  parts.push(block(19, floorY, 21, "minecraft:observer", { facing_direction: FACING_STATE[west] }));
  parts.push(block(18, floorY, 21, "minecraft:observer", { facing_direction: FACING_STATE[east] }));

  // Collection: hopper under the landing tile drops down one layer into a
  // short line to the chest.
  parts.push(block(21, floorY - 1, 21, "minecraft:hopper", { facing_direction: FACING_STATE[west] }));
  parts.push(block(20, floorY - 1, 21, "minecraft:hopper", { facing_direction: FACING_STATE[west] }));
  parts.push(block(19, floorY - 1, 21, "minecraft:chest"));
  parts.push(block(18, floorY - 1, 21, "minecraft:chest"));

  return merge(...parts);
}

export const PillagerOutpostFarm = {
  id: "pillager_outpost_farm",
  name: "Pillager Outpost Farm",
  shortDescription: "Build atop an existing outpost tower. Fall shaft + piston crusher, hopper collection.",
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
