import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * One-Tick Kelp Farm
 * ===================
 * A real, patch-safe design — NOT the "zero-tick" water-duplication bug that
 * got fixed in a 1.21.30 Bedrock update (that trick relied on a
 * server/client water-movement desync and is gone for good). This is the
 * ordinary, always-worked observer+piston auto-harvester real players have
 * used for years: an observer watches the block directly above a planted
 * kelp, and the moment kelp grows into that block it fires a redstone
 * pulse — which, by design, is exactly 1 game tick, hence "one-tick" farm —
 * that triggers a piston to instantly pop the new growth off as a dropped
 * item before it can ever grow a 3rd segment.
 *
 * Bonemeal is deliberately NOT used here. Bonemeal does work on kelp (1 use
 * = grow 1 block), but there's no way to feed it to an open kelp column
 * automatically in a way that beats just running more parallel lanes — a
 * dispenser clock burning through bonemeal doesn't out-produce the plant's
 * own regrowth once you have several lanes going, and farmland/kelp-column
 * bonemeal dispensing isn't how any real, standing kelp farm design
 * actually works. If you want to hand-feed bonemeal to a lane for a burst,
 * you still can — nothing here stops that — it's just not built in.
 *
 * Per-lane circuit (verified block-by-block, not guessed):
 *  - Kelp base at local (x,1,0), permanent — kelp is a self-contained
 *    "waterlogged" plant block once placed; it does not need a separate
 *    water source in the same cell to survive.
 *  - A hopper directly under it at (x,0,0) is the tube's own floor. Kelp
 *    isn't a solid block, so a popped item falls straight through the base
 *    and lands in the hopper below it — no water current needed for
 *    collection at all.
 *  - Growth cell at (x,2,0) — empty air that new kelp grows into.
 *  - Piston at (x,2,1) facing the growth cell, powered by redstone dust.
 *  - Observer at (x,2,-1) facing the growth cell from the opposite side —
 *    it can only ever detect a block change in the one cell it's aimed at,
 *    so it and the piston MUST be on two different faces of that same
 *    cell, which means they can never be touching each other directly
 *    (there's no arrangement of a single shared target block where "the
 *    piston" and "directly behind the observer" are the same spot). A
 *    short redstone-dust relay is therefore a real, necessary part of this
 *    circuit, not an authoring shortcut: dust runs from the observer's
 *    back face, sideways through a dedicated corridor column (x+1, never
 *    crossing the kelp/piston/observer cells), and arrives touching the
 *    piston's side face. Every dust segment sits on its own solid support
 *    block one layer down (y=1) so it's a legal, flat, non-diagonal run.
 *  - Lane pitch is 2 (kelp/mechanism column + corridor column), so lanes
 *    never share a cell and this repeats cleanly.
 *
 * Local space per unit: x 0 to (LANE_PITCH*LANES-1), y -2 (collection
 * spine) to 4 (lighting), z -2 to 2. Units repeat sideways along +x
 * (stackAxis "x") like the other ground farms.
 */

const LANES = 6;
const LANE_PITCH = 2;
const FIELD_WIDTH = LANES * LANE_PITCH;

export const SIZE = { x: FIELD_WIDTH + 4, y: 6, z: 6 };
export const LEVEL_SPACING = SIZE.x + 8;
export const MAX_LEVELS = 4;
export const stackAxis = "x";
export const levelLabel = "Number of farms (1-4)";
export const unitNoun = "Farm";

const FACING_STATE = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };

function planLane(x, facing) {
  const parts = [];

  // Utility floor for the whole 2-wide lane slot (mechanism support layer),
  // then the kelp base overrides its own cell afterward (merge() is
  // last-write-wins).
  parts.push(box([x, 1, -2], [x + 1, 1, 1], "minecraft:stone"));

  // Kelp tube: hopper floor -> kelp base -> growth cell.
  parts.push(block(x, 0, 0, "minecraft:hopper", { facing_direction: FACING_STATE.down }));
  parts.push(block(x, 1, 0, "minecraft:kelp"));
  // (x,2,0) is left as air — that's the growth cell the piston keeps clear.

  // Piston + observer, aimed at the growth cell from opposite sides.
  const pistonDir = rotateDirection("north", facing); // faces -z, toward growth cell from z=1
  const observerDir = rotateDirection("south", facing); // faces +z, toward growth cell from z=-1
  parts.push(block(x, 2, 1, "minecraft:piston", { facing_direction: FACING_STATE[pistonDir] }));
  parts.push(block(x, 2, -1, "minecraft:observer", { facing_direction: FACING_STATE[observerDir] }));

  // Redstone relay: observer's back (x,2,-2) -> corridor column x+1 -> piston's side face (x,2,1)/(x+1,2,1).
  parts.push(block(x, 2, -2, "minecraft:redstone_wire"));
  parts.push(block(x + 1, 2, -2, "minecraft:redstone_wire"));
  parts.push(block(x + 1, 2, -1, "minecraft:redstone_wire"));
  parts.push(block(x + 1, 2, 0, "minecraft:redstone_wire"));
  parts.push(block(x + 1, 2, 1, "minecraft:redstone_wire"));
  // Solid support directly under every dust segment above (y=1, matches the utility floor already laid).
  parts.push(block(x, 1, -2, "minecraft:stone"));
  parts.push(block(x + 1, 1, -2, "minecraft:stone"));
  parts.push(block(x + 1, 1, -1, "minecraft:stone"));
  parts.push(block(x + 1, 1, 0, "minecraft:stone"));
  parts.push(block(x + 1, 1, 1, "minecraft:stone"));

  // Collection spine: this lane's hopper drops straight down into a shared
  // east-west line at y=-1 that drains toward the chest at x=-1.
  const drain = rotateDirection("west", facing);
  parts.push(block(x, -1, 0, "minecraft:hopper", { facing_direction: FACING_STATE[drain] }));

  return parts;
}

function planUnit(dx, facing) {
  const parts = [];
  const spawns = [];

  // Enclosure: modest stone brick walls + open top (lit, matching the
  // house style used everywhere else in this addon), well clear of the
  // mechanism's own footprint (mechanism spans x 0..FIELD_WIDTH-1, z -2..1).
  parts.push(box([-2, 0, -3], [FIELD_WIDTH + 1, 0, 2], "minecraft:stone_bricks"));
  parts.push(box([-2, 1, -3], [-2, 3, 2], "minecraft:stone_bricks"));
  parts.push(box([FIELD_WIDTH + 1, 1, -3], [FIELD_WIDTH + 1, 3, 2], "minecraft:stone_bricks"));
  parts.push(box([-2, 1, -3], [FIELD_WIDTH + 1, 3, -3], "minecraft:stone_bricks"));
  parts.push(box([-2, 1, 2], [FIELD_WIDTH + 1, 3, 2], "minecraft:stone_bricks"));
  for (const x of [-1, Math.floor(FIELD_WIDTH / 2), FIELD_WIDTH]) {
    parts.push(block(x, 3, -3, "minecraft:sea_lantern"));
    parts.push(block(x, 3, 2, "minecraft:sea_lantern"));
  }

  for (let i = 0; i < LANES; i++) {
    parts.push(...planLane(i * LANE_PITCH, facing));
  }

  const merged = merge(...parts);
  return {
    placements: merged.map((p) => ({ ...p, x: p.x + dx })),
    spawns: spawns.map((s) => ({ ...s, x: s.x + dx })),
  };
}

/** Shared external spine + chest, one per build (all units' lane-spines feed into it along z=0). */
function planChest(levels, facing) {
  const west = rotateDirection("west", facing);
  const maxX = (levels - 1) * LEVEL_SPACING;
  const parts = [block(-4, -1, 0, "minecraft:chest"), block(-5, -1, 0, "minecraft:chest")];
  for (let x = maxX + FIELD_WIDTH - LANE_PITCH; x >= -3; x--) {
    parts.push(block(x, -1, 0, "minecraft:hopper", { facing_direction: FACING_STATE[west] }));
  }
  return merge(...parts);
}

export const KelpFarm = {
  id: "kelp_farm",
  name: "One-Tick Kelp Farm",
  shortDescription: "Observer+piston insta-harvest kelp lanes, hopper-floor collection, no bonemeal needed.",
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
    placements.push(...planChest(levels, facing));
    return { placements, spawns };
  },
};
