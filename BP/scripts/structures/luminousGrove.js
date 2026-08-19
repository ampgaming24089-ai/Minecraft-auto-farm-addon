/**
 * Luminous Grove - the one place in the End that is not hostile.
 *
 * A crust of verdant end stone carrying crystal trees whose canopies light
 * the ground. Groves are the safe camps of a long expedition, so they carry
 * food and no chest worth fighting over.
 */

import { at, blob, merge } from "../lib/blueprint.js";

export const LuminousGrove = {
  id: "grove",
  name: "Luminous Grove",
  radius: 18,
  fog: "voidbound:fog_luminous_grove",

  build(rng) {
    const spread = rng.float(9, 14);

    // Soft crust of moss over the island top, thinning at the edges.
    const crust = [];
    for (let x = -Math.ceil(spread); x <= Math.ceil(spread); x++) {
      for (let z = -Math.ceil(spread); z <= Math.ceil(spread); z++) {
        const d = Math.sqrt(x * x + z * z) / spread;
        if (d > 1) continue;
        if (rng.next() < 1 - d * d) {
          crust.push({ x, y: 0, z, id: "voidbound:verdant_end_stone" });
        }
      }
    }

    // Crystal trees: a pale trunk under a glowing canopy.
    const trees = [];
    const canopies = [];
    const treeCount = rng.int(3, 6);
    for (let i = 0; i < treeCount; i++) {
      const angle = rng.float(0, Math.PI * 2);
      const reach = rng.float(1.5, spread - 4);
      const tx = Math.round(Math.cos(angle) * reach);
      const tz = Math.round(Math.sin(angle) * reach);
      const height = rng.int(5, 9);
      for (let y = 1; y <= height; y++) {
        trees.push({ x: tx, y, z: tz, id: "minecraft:end_bricks" });
      }
      canopies.push(
        ...blob(tx, height + 2, tz, rng.float(2.4, 3.6), "voidbound:void_crystal_block", undefined, 0.7)
      );
      canopies.push({ x: tx, y: height + 1, z: tz, id: "voidbound:rift_lantern" });
    }

    // Undergrowth: bulbs cluster under the trees, blooms wander the edges.
    const flora = [];
    for (let i = 0; i < rng.int(24, 44); i++) {
      const angle = rng.float(0, Math.PI * 2);
      const reach = rng.float(0.5, spread);
      const fx = Math.round(Math.cos(angle) * reach);
      const fz = Math.round(Math.sin(angle) * reach);
      const nearTree = reach < spread * 0.6;
      flora.push({
        x: fx,
        y: 1,
        z: fz,
        id: nearTree && rng.chance(0.65) ? "voidbound:lumen_bulb" : "voidbound:voidbloom",
      });
    }

    // A small cache at the centre, deliberately modest.
    const cache = merge(
      blob(0, 0, 0, 2.2, "voidbound:verdant_end_stone", undefined, 0.4),
      at(0, 1, 0, "minecraft:barrel"),
      at(1, 1, 1, "voidbound:lumen_bulb"),
      at(-1, 1, -1, "voidbound:lumen_bulb")
    );

    return {
      placements: merge(crust, trees, canopies, flora, cache),
      chests: [{ x: 0, y: 1, z: 0 }],
      beacon: { x: 0, y: 6, z: 0 },
    };
  },
};
