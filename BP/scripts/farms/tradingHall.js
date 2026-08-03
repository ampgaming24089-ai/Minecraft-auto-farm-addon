import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Librarian Trading Hall
 * ======================
 * A row of individual librarian stalls — bed + lectern (the librarian job
 * site) per stall, a fence front (blocks the villager from walking out,
 * but you can still reach over it to trade — the same "short barrier"
 * trick the other crop farm here uses), and decorative bookshelves on the
 * back wall. Spawning an unemployed villager next to each unclaimed
 * lectern is enough for it to become a librarian on its own — that's
 * standard profession-claiming, nothing scripted about it. Bookshelves are
 * decoration only: they boost an ENCHANTING TABLE's max level when placed
 * near it, they have no effect on villager trades, so don't expect them to
 * change what a librarian offers.
 *
 * On "checking for Mending and other good rolls, else replacing the
 * villager": this is the one piece of the original request that Script API
 * genuinely cannot fully automate, and it's worth being upfront about
 * rather than faking it. There is no stable, documented way for
 * @minecraft/server to read a villager's currently-offered (unclaimed)
 * trade before you trade with it — trade offers simply aren't exposed to
 * script for inspection. What IS real and verified: breaking and
 * replacing a librarian's claimed lectern re-rolls its enchanted-book
 * trade, but ONLY before you've made your first trade with it (after that,
 * its trades are locked for good). So this hall ships with a companion
 * tool — the Villager Manager Wand (see
 * scripts/lib/villagerManager.js) — that does the reroll (and, for
 * villagers already locked into a bad trade, a full replace-with-a-fresh-
 * villager) in one tap instead of manually breaking/placing a lectern each
 * time. You still have to glance at the trade screen yourself to see what
 * came up — nothing can do that step for you — but the wand turns "reroll
 * until it's good" into a few seconds of tapping instead of manual block
 * breaking.
 *
 * For reference (Bedrock max enchant levels — see README for the full
 * researched list and why Mending/Unbreaking/Efficiency/Fortune etc. are
 * worth holding out for), Mending is the single most commonly recommended
 * "don't trade until you see this" pick for a librarian specifically.
 *
 * Local space per stall: x 0-2, z 0-3, y 0-2. Stalls repeat along +x.
 */

const STALL_WIDTH = 3;
const STALLS_PER_UNIT = 5;
export const SIZE = { x: STALL_WIDTH * STALLS_PER_UNIT, y: 4, z: 4 };
export const LEVEL_SPACING = SIZE.x + 4;
export const MAX_LEVELS = 4;
export const stackAxis = "x";
export const levelLabel = "Number of 5-librarian sections (1-4)";
export const unitNoun = "Section";

const BED_DIRECTION = { south: 0, west: 1, north: 2, east: 3 };
const LECTERN_DIRECTION = { south: 0, west: 1, north: 2, east: 3 };

function planStall(x, facing) {
  const parts = [];
  const spawns = [];

  parts.push(box([x, 0, 0], [x + 2, 0, 3], "minecraft:stone_bricks"));
  parts.push(box([x, 1, 0], [x + 2, 2, 0], "minecraft:bookshelf")); // back wall
  parts.push(box([x, 1, 0], [x, 2, 3], "minecraft:stone_bricks")); // left wall
  parts.push(box([x + 2, 1, 0], [x + 2, 2, 3], "minecraft:stone_bricks")); // right wall
  parts.push(box([x, 1, 3], [x + 2, 1, 3], "minecraft:oak_fence")); // front barrier (reach-through height)
  parts.push(box([x, 3, 0], [x + 2, 3, 3], "minecraft:glass")); // roof

  const bedDir = rotateDirection("south", facing);
  parts.push(block(x, 1, 1, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: false }));
  parts.push(block(x, 1, 2, "minecraft:bed", { direction: BED_DIRECTION[bedDir], head_piece_bit: true }));

  const lecternDir = rotateDirection("north", facing);
  parts.push(block(x + 2, 1, 1, "minecraft:lectern", { direction: LECTERN_DIRECTION[lecternDir] }));
  parts.push(block(x + 1, 2, 1, "minecraft:glowstone"));

  spawns.push({ x: x + 1, y: 1, z: 1, typeId: "minecraft:villager" });

  return { parts, spawns };
}

function planUnit(dx, facing) {
  const allParts = [];
  const spawns = [];
  for (let i = 0; i < STALLS_PER_UNIT; i++) {
    const { parts, spawns: s } = planStall(i * STALL_WIDTH, facing);
    allParts.push(...parts);
    spawns.push(...s);
  }
  const merged = merge(...allParts);
  return {
    placements: merged.map((p) => ({ ...p, x: p.x + dx })),
    spawns: spawns.map((s) => ({ ...s, x: s.x + dx })),
  };
}

export const TradingHall = {
  id: "trading_hall",
  name: "Librarian Trading Hall",
  shortDescription: "5 librarian stalls per section (bed+lectern each). Use the Villager Manager Wand to reroll/replace.",
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
    return { placements, spawns };
  },
};
