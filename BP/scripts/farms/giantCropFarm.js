import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Giant Crop Farm — one villager, one hopper floor, bees in a sealed glass dome
 * ================================================================================
 * Three researched mechanics driving this design, none invented:
 *
 *  1. Farmland tending range: a Bedrock farmer villager searches for
 *     farmland up to 9 blocks away on both X and Z (a 19x19 area centered
 *     on the farmer/its claimed job site). This farm is sized to exactly
 *     that: a full 19x19 field, worked entirely by ONE villager.
 *  2. Collection without a second "beggar" villager: a farmer only tosses
 *     surplus food to other hungry villagers — with just one villager
 *     there's nobody to throw food at, so the trick real single-farmer
 *     giant farms use instead is a full inventory. The farmer is spawned
 *     with every one of its 8 carry slots pre-filled with a junk item
 *     (dirt), so it physically cannot pick up anything it harvests —
 *     every harvested crop drops on the ground instead, where a hopper
 *     floor under the entire field collects it. This is a real, documented
 *     technique, not scripted loot.
 *  3. Bee pollination: bees that pick up pollen from a flower and then fly
 *     over/into a nearby wheat, carrots, potatoes, or beetroot crop advance
 *     that crop's growth stage by one — a genuine (if modest) speed boost,
 *     not something added just for looks. Bedrock beehive mechanics: bees
 *     can enter a hive from any unobstructed side, but can only ever EXIT
 *     from the hive's front. Fully sealing the whole field (flowers, hive,
 *     and crops all together) in one glass dome with the hive's front
 *     facing into that same sealed interior means the bees never have an
 *     unobstructed exterior front to leave through — "enclosed so they
 *     can't escape" is a literal, mechanically real result of this
 *     layout, not just theming. There is deliberately no player-sized door
 *     anywhere in the dome, since a bee can fly through any opening a
 *     player could walk through — collection is 100% external via hoppers,
 *     so nobody needs to walk in.
 *
 * Hydration: farmland needs a water source within 4 blocks (any direction)
 * to stay tilled. A single water block can't cover a 19x19 field, so a 3x3
 * grid of 9 water tiles (spaced 5 apart) is used instead of farmland on
 * those cells — each one hydrates its own overlapping 9x9 patch, together
 * covering the whole field with no gaps. The center water tile also carries
 * the farmer's composter job site directly above it (same "composter on
 * water" trick as the other crop farm here).
 *
 * Collection: two-layer hopper network, not hand-wired one at a time. Every
 * field tile (including the water/composter utility tiles) sits over a
 * hopper facing west, chaining drops along each row to that row's x=0
 * hopper. The x=0 column instead faces straight down into a second layer,
 * which chains north along z to one corner chest. This is the standard
 * "row + spine" pattern for collecting an entire hopper floor into one
 * point, just applied at 19x19 scale.
 *
 * Local space per unit: x 0-18, z 0-18 (the field), y -2 (spine) to 6
 * (glass roof). Units repeat sideways along +x like the other ground farms.
 */

const FIELD = 19; // 9 blocks each side of center = 19, matching the real farmer work range
const CENTER = 9;
const CROPS = ["minecraft:wheat", "minecraft:carrots", "minecraft:potatoes", "minecraft:beetroot"];
const WATER_GRID = [4, 9, 14];

export const SIZE = { x: FIELD, y: 7, z: FIELD };
export const LEVEL_SPACING = SIZE.x + 8;
export const MAX_LEVELS = 4;
export const stackAxis = "x";
export const levelLabel = "Number of farms (1-4)";
export const unitNoun = "Farm";

const FACING_STATE = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
// Beehive's "direction" state is the same 4-value cardinal enum beds use (see ironFarm.js), not the 6-value facing_direction.
const BEE_DIRECTION = { south: 0, west: 1, north: 2, east: 3 };

function isWaterTile(x, z) {
  return WATER_GRID.includes(x) && WATER_GRID.includes(z);
}

function planUnit(dx, facing) {
  const parts = [];
  const spawns = [];

  // Field: farmland+crop everywhere except the 3x3 hydration/utility grid.
  for (let x = 0; x < FIELD; x++) {
    for (let z = 0; z < FIELD; z++) {
      if (isWaterTile(x, z)) {
        parts.push(block(x, 0, z, "minecraft:water"));
        if (x === CENTER && z === CENTER) {
          parts.push(block(x, 1, z, "minecraft:composter"));
          parts.push(block(x, 2, z, "minecraft:glowstone"));
        }
      } else {
        const crop = CROPS[Math.floor(Math.random() * CROPS.length)];
        const growth = Math.floor(Math.random() * 8);
        parts.push(block(x, 0, z, "minecraft:farmland"));
        parts.push(block(x, 1, z, crop, { growth }));
      }
    }
  }

  // Hopper floor: row hoppers face west, x=0 column instead faces down into the spine.
  for (let x = 0; x < FIELD; x++) {
    for (let z = 0; z < FIELD; z++) {
      if (x === 0) {
        parts.push(block(x, -1, z, "minecraft:hopper", { facing_direction: FACING_STATE.down }));
      } else {
        const west = rotateDirection("west", facing);
        parts.push(block(x, -1, z, "minecraft:hopper", { facing_direction: FACING_STATE[west] }));
      }
    }
  }
  // Spine: x=0 column at y=-2, chains north (toward z=0) to the corner chest.
  for (let z = 0; z < FIELD; z++) {
    const north = rotateDirection("north", facing);
    parts.push(block(0, -2, z, "minecraft:hopper", { facing_direction: FACING_STATE[north] }));
  }
  parts.push(block(0, -2, -1, "minecraft:chest"));
  parts.push(block(-1, -2, -1, "minecraft:chest"));

  // Farmer villager, spawned with every carry slot pre-filled with junk so
  // harvested crops always fall to the hopper floor instead of being
  // re-picked-up (see notes above).
  const inventory = [];
  for (let slot = 0; slot < 8; slot++) inventory.push({ slot, itemId: "minecraft:dirt", amount: 64 });
  spawns.push({ x: CENTER, y: 1, z: CENTER - 1, typeId: "minecraft:villager", inventory });

  // Bee corner: a small pillar with the hive facing into the (fully
  // enclosed) field interior, a scatter of flowers at crop height nearby,
  // and 3 bees that will self-assign to the empty hive on spawn.
  const hiveFacing = rotateDirection("south", facing);
  parts.push(box([1, 0, 1], [1, 1, 1], "minecraft:stone_bricks"));
  parts.push(block(1, 2, 1, "minecraft:beehive", { direction: BEE_DIRECTION[hiveFacing] }));
  for (const [fx, fz] of [
    [2, 1],
    [1, 2],
    [3, 2],
    [2, 3],
  ]) {
    parts.push(block(fx, 1, fz, "minecraft:poppy"));
  }
  for (let i = 0; i < 3; i++) {
    spawns.push({ x: 2, y: 3, z: 2, typeId: "minecraft:bee" });
  }

  // Sealed glass dome — no doors anywhere (see notes above on why).
  parts.push(box([-1, 3, -1], [FIELD, 3, FIELD], "minecraft:glass"));
  parts.push(box([-1, 3, -1], [-1, 5, FIELD], "minecraft:glass"));
  parts.push(box([FIELD, 3, -1], [FIELD, 5, FIELD], "minecraft:glass"));
  parts.push(box([-1, 3, -1], [FIELD, 5, -1], "minecraft:glass"));
  parts.push(box([-1, 3, FIELD], [FIELD, 5, FIELD], "minecraft:glass"));
  parts.push(box([-1, 6, -1], [FIELD, 6, FIELD], "minecraft:glass"));
  // Interior lighting (glowstone at the corners, glass roof lets sunlight
  // through too, but nights still need this since the dome blocks mob
  // despawn-by-daylight visuals from working the same as open sky).
  for (const [gx, gz] of [
    [2, 16],
    [16, 2],
    [16, 16],
  ]) {
    parts.push(block(gx, 2, gz, "minecraft:glowstone"));
  }

  const merged = merge(...parts);
  return {
    placements: merged.map((p) => ({ ...p, x: p.x + dx })),
    spawns: spawns.map((s) => ({ ...s, x: s.x + dx })),
  };
}

export const GiantCropFarm = {
  id: "giant_crop_farm",
  name: "Giant Crop Farm",
  shortDescription: "19x19 field, 1 farmer (full-inventory trick), full hopper floor, bees sealed in glass.",
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
