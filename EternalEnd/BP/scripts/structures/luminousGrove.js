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

    // Ender trees: a pale trunk that leans as it climbs, under a violet
    // canopy. The lean is what stops a stand of them reading as fenceposts.
    const trees = [];
    const canopies = [];
    const treeCount = rng.int(4, 7);
    for (let i = 0; i < treeCount; i++) {
      const angle = rng.float(0, Math.PI * 2);
      const reach = rng.float(1.5, spread - 4);
      let tx = Math.cos(angle) * reach;
      let tz = Math.sin(angle) * reach;
      const height = rng.int(6, 11);
      const leanX = rng.float(-0.18, 0.18);
      const leanZ = rng.float(-0.18, 0.18);
      for (let y = 1; y <= height; y++) {
        tx += leanX;
        tz += leanZ;
        trees.push({ x: Math.round(tx), y, z: Math.round(tz), id: "voidbound:ender_log" });
      }
      const crownX = Math.round(tx);
      const crownZ = Math.round(tz);
      const crownRadius = rng.float(2.6, 4.0);
      canopies.push(
        ...blob(crownX, height + 2, crownZ, crownRadius, "voidbound:ender_leaves", undefined, 0.62)
      );
      // A couple of fruit-bearing bushes at the foot of each trunk.
      for (let f = 0; f < rng.int(1, 3); f++) {
        canopies.push({
          x: crownX + rng.int(-2, 2),
          y: 1,
          z: crownZ + rng.int(-2, 2),
          id: "voidbound:ender_bush",
        });
      }
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
      at(-1, 1, -1, "voidbound:lumen_bulb"),
      // Every structure carries a waystone, so the network is something a
      // player joins by exploring rather than by crafting their way into it.
      at(2, 1, -2, "voidbound:waystone")
    );

    return {
      placements: merge(crust, trees, canopies, flora, cache),
      chests: [{ x: 0, y: 1, z: 0 }],
      beacon: { x: 0, y: 6, z: 0 },
    };
  },
};
