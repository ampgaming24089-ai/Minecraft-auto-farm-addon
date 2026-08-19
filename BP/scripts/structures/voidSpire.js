/**
 * Void Spire - a crystal needle punched up through a shattered island.
 *
 * The silhouette is the point: something you can see from a long way off and
 * decide to fly toward. The reward for arriving is echo ore exposed on the
 * shaft and a chest buried in the plinth at the base.
 */

import { at, blob, box, merge } from "../lib/blueprint.js";

export const VoidSpire = {
  id: "spire",
  name: "Void Spire",
  /** Rough horizontal footprint, used for site spacing and fog regions. */
  radius: 14,
  fog: "voidbound:fog_rift",

  build(rng) {
    const height = rng.int(22, 34);
    const baseRadius = rng.float(5.5, 7.5);

    // A cracked stone plinth the spire grows out of.
    const plinth = merge(
      blob(0, -2, 0, baseRadius, "voidbound:shattered_end_stone", undefined, 0.5),
      blob(0, -1, 0, baseRadius - 1.2, "minecraft:end_stone", undefined, 0.45),
      blob(0, 0, 0, baseRadius - 2.4, "voidbound:shattered_end_stone", undefined, 0.4)
    );

    // The shaft tapers as it climbs and drifts slightly off vertical.
    const shaft = [];
    let cx = 0;
    let cz = 0;
    for (let y = 0; y < height; y++) {
      const t = y / height;
      const radius = Math.max(0.6, 3.4 * (1 - t) + 0.4);
      cx += rng.float(-0.22, 0.22);
      cz += rng.float(-0.22, 0.22);
      const material = rng.chance(0.16 + t * 0.35)
        ? "voidbound:void_crystal_block"
        : "minecraft:end_stone";
      const r = Math.ceil(radius);
      for (let x = -r; x <= r; x++) {
        for (let z = -r; z <= r; z++) {
          if (x * x + z * z <= radius * radius) {
            shaft.push({ x: Math.round(cx) + x, y, z: Math.round(cz) + z, id: material });
          }
        }
      }
    }

    // A crystal crown, and ore veins where the shaft has split open.
    const crown = blob(Math.round(cx), height + 1, Math.round(cz), 2.6, "voidbound:void_crystal_block");
    const veins = [];
    for (let i = 0; i < rng.int(10, 18); i++) {
      const y = rng.int(1, height - 4);
      const angle = rng.float(0, Math.PI * 2);
      const reach = rng.float(1.5, 3.2);
      veins.push({
        x: Math.round(Math.cos(angle) * reach),
        y,
        z: Math.round(Math.sin(angle) * reach),
        id: "voidbound:echo_ore",
      });
    }

    // Flora clinging to the plinth.
    const flora = [];
    for (let i = 0; i < rng.int(6, 14); i++) {
      const angle = rng.float(0, Math.PI * 2);
      const reach = rng.float(3.0, baseRadius);
      flora.push({
        x: Math.round(Math.cos(angle) * reach),
        y: 1,
        z: Math.round(Math.sin(angle) * reach),
        id: rng.chance(0.6) ? "voidbound:voidbloom" : "voidbound:lumen_bulb",
      });
    }

    // Chest vault under the plinth, reached by breaking in.
    const vault = merge(
      box([-2, -4, -2], [2, -2, 2], "minecraft:end_bricks"),
      box([-1, -4, -1], [1, -3, 1], "minecraft:air"),
      at(0, -4, 0, "minecraft:chest"),
      at(-1, -3, -1, "voidbound:rift_lantern")
    );

    return {
      placements: merge(plinth, vault, shaft, crown, veins, flora),
      chests: [{ x: 0, y: -4, z: 0 }],
      beacon: { x: 0, y: height, z: 0 },
    };
  },
};
