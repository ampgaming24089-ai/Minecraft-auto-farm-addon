import { box, block, merge } from "../lib/builder.js";
import { rotateDirection } from "../lib/geometry.js";

/**
 * Passive Mob Farm
 * ================
 * A lit, open grass platform for passive mobs (cow/pig/sheep/chicken) with
 * a water funnel pushing them into a fall, an auto-cooker, and a chest —
 * fully automatic once seeded, using the same real mechanics as the other
 * farms here (no commands, no fake drops):
 *
 *  - Grass platform, wide open on top and heavily lit (sea lanterns), so
 *    vanilla's passive mob spawning keeps replenishing the population over
 *    time on its own — no breeding required, though feeding the starter
 *    animals wheat/seeds/carrots will speed things up.
 *  - A 2-block-high fence barrier rings the platform so animals can wander
 *    and graze without being pushed (or wandering) off the edge early.
 *  - The same one-axis water convergence used on the iron farm's platform —
 *    a full-depth column on the west wall flowing east, one on the north
 *    wall flowing south, converging on a 2-wide drain in the SE corner.
 *    Two currents flowing head-on into each other (e.g. west+east, or
 *    north+south) create a dead/ambiguous push right where they'd meet;
 *    two currents on ADJACENT walls only ever combine, they never cancel,
 *    which is why the drain is a corner here and not the center.
 *  - The drain drops mobs down a 14-block shaft — enough fall damage to
 *    kill cows/pigs/sheep outright. Chickens take no fall damage in
 *    vanilla, so the landing zone is also lined with magma blocks (safe
 *    for item drops, unlike lava — magma is a solid block, not a fluid, so
 *    unlike lava it physically cannot spread/leak beyond where it's
 *    placed) as a guaranteed finisher for anything that survives the fall.
 *  - Raw drops get swept by a water current into a hopper that feeds
 *    straight into a smoker's input slot from above (standard vanilla
 *    hopper-into-furnace behavior — no scripting needed for the smelting
 *    itself). The smoker's fuel slot is pre-loaded with a stack of coal at
 *    build time (512 smelts worth) so it starts cooking immediately. A
 *    second hopper below the smoker pulls the cooked output into the final
 *    chest automatically.
 *
 * Local space per unit: x 0-14 (width), z 0-14 (depth), y 0-6 (platform
 * height) plus a shaft going down to y -17 for the kill/cook/collect
 * chain. Units repeat sideways along +x (stackAxis "x") like the crop farm.
 */

export const SIZE = { x: 15, y: 7, z: 15 };
export const LEVEL_SPACING = SIZE.x + 10; // unit width + 10-block gap to the next unit
export const MAX_LEVELS = 4;
export const stackAxis = "x";
export const levelLabel = "Number of farms (1-4)";
export const unitNoun = "Farm";

const HOPPER_FACING = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5 };
const STARTER_MOBS = ["minecraft:cow", "minecraft:pig", "minecraft:sheep", "minecraft:chicken"];

const SHAFT_DEPTH = 14; // fall distance below the platform floor before the kill zone

function planUnit(dx, facing) {
  const parts = [];
  const spawns = [];

  // Platform floor + 2-high fence barrier ring (no roof — see notes above).
  parts.push(box([0, 0, 0], [14, 0, 14], "minecraft:grass_block"));
  parts.push(box([1, 1, 1], [13, 3, 13], "minecraft:air"));
  parts.push(box([0, 1, 0], [14, 2, 0], "minecraft:oak_fence"));
  parts.push(box([0, 1, 14], [14, 2, 14], "minecraft:oak_fence"));
  parts.push(box([0, 1, 0], [0, 2, 14], "minecraft:oak_fence"));
  parts.push(box([14, 1, 0], [14, 2, 14], "minecraft:oak_fence"));

  // One-axis water convergence toward a 2-wide SE corner drain: west wall
  // flows east, north wall flows south. See notes above for why adjacent
  // (not opposite) walls are what actually works.
  parts.push(box([12, 0, 12], [13, 0, 13], "minecraft:air"));
  parts.push(box([1, 1, 1], [1, 1, 13], "minecraft:water"));
  parts.push(box([1, 1, 1], [13, 1, 1], "minecraft:water"));

  // Fall shaft straight down from the drain to the kill zone.
  for (let y = -1; y >= -SHAFT_DEPTH; y--) {
    parts.push(box([12, y, 12], [13, y, 13], "minecraft:air"));
  }

  // Kill zone: a fully self-walled pocket (nothing pre-existing to lean on
  // down here, unlike the above-ground platform). Walls span every y-layer
  // from the magma's own floor layer up through the ceiling — a wall that
  // only starts one layer above the floor leaves the floor's own layer
  // open on that side, which is exactly how a fluid would leak out
  // undetected. Magma doesn't have that failure mode at all (it's a solid
  // block, not a fluid — nothing to contain), which is why it's used here
  // instead of lava.
  const floorY = -SHAFT_DEPTH - 1;
  parts.push(box([9, floorY, 9], [14, floorY + 2, 9], "minecraft:cobblestone"));
  parts.push(box([9, floorY, 14], [14, floorY + 2, 14], "minecraft:cobblestone"));
  parts.push(box([9, floorY, 9], [9, floorY + 2, 14], "minecraft:cobblestone"));
  parts.push(box([14, floorY, 9], [14, floorY + 2, 14], "minecraft:cobblestone"));
  parts.push(box([10, floorY, 10], [13, floorY, 13], "minecraft:magma"));
  parts.push(block(13, floorY, 13, "minecraft:hopper", { facing_direction: HOPPER_FACING.down }));

  // Cooking chain: catch hopper (above) -> smoker (fed from above) ->
  // output hopper -> chest. Fuel is pre-loaded separately via fills below.
  const east = rotateDirection("east", facing);
  parts.push(block(13, floorY - 1, 13, "minecraft:smoker", { "minecraft:cardinal_direction": east }));
  parts.push(block(13, floorY - 2, 13, "minecraft:hopper", { facing_direction: HOPPER_FACING[east] })); // pulls cooked output, pushes toward chest
  parts.push(block(14, floorY - 2, 13, "minecraft:chest"));
  parts.push(block(15, floorY - 2, 13, "minecraft:chest"));

  // Lighting: same open-top philosophy as the iron farm — heavy sea
  // lantern coverage keeps light levels high with no roof to rely on.
  for (const z of [2, 7, 12]) {
    parts.push(block(0, 2, z, "minecraft:sea_lantern"));
    parts.push(block(14, 2, z, "minecraft:sea_lantern"));
  }
  for (const x of [2, 7, 12]) {
    parts.push(block(x, 2, 0, "minecraft:sea_lantern"));
    parts.push(block(x, 2, 14, "minecraft:sea_lantern"));
  }

  // Starter animals — natural spawning on the lit grass keeps the
  // population going after this, but a running start helps immediately.
  for (const [x, z] of [[3, 3], [11, 3], [3, 11], [11, 11], [7, 3], [7, 11], [3, 7], [11, 7]]) {
    const typeId = STARTER_MOBS[Math.floor(Math.random() * STARTER_MOBS.length)];
    spawns.push({ x, y: 1, z, typeId });
  }

  const fills = [{ x: 13, y: floorY - 1, z: 13, slot: 1, itemId: "minecraft:coal", amount: 64 }];

  const merged = merge(...parts);
  return {
    placements: merged.map((p) => ({ ...p, x: p.x + dx })),
    spawns: spawns.map((s) => ({ ...s, x: s.x + dx })),
    fills: fills.map((f) => ({ ...f, x: f.x + dx })),
  };
}

export const MobFarm = {
  id: "mob_farm",
  name: "Passive Mob Farm",
  shortDescription: "Grass platform, water funnel, fall + magma kill, auto-smoker, hopper to chest.",
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
    const fills = [];
    for (let i = 0; i < levels; i++) {
      const { placements: p, spawns: s, fills: f } = planUnit(i * LEVEL_SPACING, facing);
      placements.push(...p);
      spawns.push(...s);
      fills.push(...f);
    }
    return { placements, spawns, fills };
  },
};
