/**
 * End Village - the only place out here anybody lives.
 *
 * Every other structure in the pack is a ruin or a threat. This is the one
 * that is occupied, and everything about how it is built is trying to say so
 * from a distance: dressed stone rather than any biome's rock, lantern posts
 * on the paths, tilled crops in rows, and roofs at different heights so the
 * silhouette is a settlement rather than a compound.
 *
 * Huts are placed around a central well on a ring, each rotated to face it,
 * because a village that all faces one way reads as a barracks.
 */

import { at, blob, box, merge, shell } from "../lib/blueprint.js";

const STONE = "voidbound:dressed_end_stone";
const PLANK = "voidbound:ender_planks";
const BRICK = "voidbound:ender_bricks";
const POST = "voidbound:lantern_post";
const TILE = "voidbound:ender_tiles";
const CROP = "voidbound:bloomstalk";

/**
 * One hut: a floor, four walls with a gap for the door, and a raised roof.
 *
 * Returns a single flat placement list. Every helper in blueprint.js already
 * returns one - `at` included - so this collects them with push(...list)
 * rather than nesting, and merge() sees exactly what it expects.
 */
function hut(cx, cz, width, depth, height, facing, rng) {
  const hw = Math.floor(width / 2);
  const hd = Math.floor(depth / 2);
  const parts = [];

  parts.push(...box([cx - hw, 0, cz - hd], [cx + hw, 0, cz + hd], TILE));
  for (let y = 1; y <= height; y++) {
    parts.push(...shell([cx - hw, y, cz - hd], [cx + hw, y, cz + hd],
                        y === 1 ? STONE : PLANK));
  }

  // Doorway on the side that faces the well, so every hut opens inward.
  const door = {
    north: { x: cx, z: cz - hd },
    south: { x: cx, z: cz + hd },
    east: { x: cx + hw, z: cz },
    west: { x: cx - hw, z: cz },
  }[facing];
  parts.push(...at(door.x, 1, door.z, "minecraft:air"));
  parts.push(...at(door.x, 2, door.z, "minecraft:air"));

  // A window on the opposite wall, so light gets through the hut.
  const back = {
    north: { x: cx, z: cz + hd },
    south: { x: cx, z: cz - hd },
    east: { x: cx - hw, z: cz },
    west: { x: cx + hw, z: cz },
  }[facing];
  parts.push(...at(back.x, 2, back.z, "voidbound:void_glass"));

  // Roof: a slab one block proud of the walls, then a cap.
  parts.push(...box([cx - hw - 1, height + 1, cz - hd - 1],
                    [cx + hw + 1, height + 1, cz + hd + 1], BRICK));
  parts.push(...box([cx - hw, height + 2, cz - hd], [cx + hw, height + 2, cz + hd], BRICK));

  // Somewhere to put the trade goods, and a light inside.
  parts.push(...at(cx - hw + 1, 1, cz - hd + 1, "minecraft:barrel"));
  parts.push(...at(cx, height, cz, "voidbound:echo_lamp"));
  if (rng.chance(0.5)) parts.push(...at(cx + hw - 1, 1, cz + hd - 1, "minecraft:crafting_table"));

  return parts;
}

export const EndVillage = {
  id: "village",
  name: "End Village",
  radius: 20,
  fog: "voidbound:fog_luminous_grove",

  build(rng) {
    // A platform first. Villages sit on level ground, and the End has none.
    const plaza = merge(
      blob(0, -3, 0, 15, STONE, undefined, 0.35),
      box([-14, 0, -14], [14, 0, 14], TILE)
    );

    // The well at the centre: everything else is arranged around it.
    const well = merge(
      box([-2, 0, -2], [2, 0, 2], STONE),
      shell([-2, 1, -2], [2, 1, 2], BRICK),
      box([-1, 0, -1], [1, 0, 1], "minecraft:water"),
      at(-2, 2, -2, POST),
      at(2, 2, 2, POST)
    );

    // A market stall beside the well: four posts, a plank canopy, and the
    // village's stock underneath. This is where the structure's chest goes,
    // so the loot is somewhere a player walks past rather than inside a hut
    // whose position is random.
    const stall = merge(
      box([-2, 1, 3], [2, 1, 5], "minecraft:air"),
      at(-2, 1, 3, PLANK),
      at(2, 1, 3, PLANK),
      at(-2, 1, 5, PLANK),
      at(2, 1, 5, PLANK),
      at(-2, 2, 3, PLANK),
      at(2, 2, 3, PLANK),
      at(-2, 2, 5, PLANK),
      at(2, 2, 5, PLANK),
      box([-2, 3, 3], [2, 3, 5], BRICK),
      at(0, 1, 4, "minecraft:chest"),
      at(-1, 1, 4, "minecraft:barrel"),
      at(1, 3, 4, POST)
    );

    // Huts on a ring, each facing the well. The ring radius varies per hut so
    // the outline is not a perfect circle.
    const huts = [];
    const count = rng.int(4, 6);
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2 + rng.float(-0.25, 0.25);
      const reach = rng.float(8.5, 12.0);
      const hx = Math.round(Math.cos(angle) * reach);
      const hz = Math.round(Math.sin(angle) * reach);
      // Face whichever axis points back toward the middle.
      const facing = Math.abs(hx) > Math.abs(hz)
        ? (hx > 0 ? "west" : "east")
        : (hz > 0 ? "north" : "south");
      huts.push(hut(hx, hz, rng.int(5, 7) | 1, rng.int(5, 7) | 1, rng.int(3, 4), facing, rng));
    }

    // Lantern posts along the approach to each hut, which is what makes the
    // place read as lit and lived-in from the air at night.
    const lights = [];
    for (let i = 0; i < count * 2; i++) {
      const angle = (i / (count * 2)) * Math.PI * 2;
      const reach = rng.float(5.0, 6.5);
      lights.push({
        x: Math.round(Math.cos(angle) * reach),
        y: 1,
        z: Math.round(Math.sin(angle) * reach),
        id: POST,
      });
    }

    // A crop plot, planted at full growth so a village is worth raiding for
    // seed even if the player never trades.
    const farm = [];
    const fx = rng.int(-13, 6);
    const fz = rng.int(-13, 6);
    for (let dx = 0; dx < rng.int(4, 7); dx++) {
      for (let dz = 0; dz < rng.int(4, 7); dz++) {
        farm.push({ x: fx + dx, y: 0, z: fz + dz, id: "voidbound:glowspore_soil" });
        if (rng.chance(0.78)) {
          farm.push({
            x: fx + dx, y: 1, z: fz + dz, id: CROP,
            states: { "voidbound:growth": rng.int(1, 3) },
          });
        }
      }
    }

    return {
      // Order is what stops the village building over itself. Later entries
      // win at a coordinate, so the ground goes down first, then the crops
      // and the lights, then everything anyone actually built - a hut wall
      // or the stall must never come up as a row of bloomstalk.
      placements: merge(plaza, farm, lights, well, ...huts, stall),
      chests: [{ x: 0, y: 1, z: 4 }],
      beacon: { x: 0, y: 6, z: 0 },
      villagers: rng.int(3, 5),
    };
  },
};
