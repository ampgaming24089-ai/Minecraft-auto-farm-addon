/**
 * Shattered Sanctum - a collapsed hall left by whoever was in the End first.
 *
 * Built as a complete building and then deliberately ruined: the roof is
 * eaten away from one corner outward, so every instance reads as the same
 * architecture at a different stage of collapse.
 *
 * Each sanctum is an Echo Warden's hall - the second boss, and the one you are
 * likely to meet first, since sanctums sit closer in than rift anchors.
 */

import { at, box, merge, shell } from "../lib/blueprint.js";

const BRICK = "minecraft:end_bricks";
const PURPUR = "minecraft:purpur_block";

export const ShatteredSanctum = {
  id: "sanctum",
  name: "Shattered Sanctum",
  radius: 13,
  fog: undefined,

  build(rng) {
    const halfWidth = rng.int(5, 7);
    const halfDepth = rng.int(6, 9);
    const wallHeight = rng.int(5, 7);
    const decay = rng.float(0.25, 0.55);

    const foundation = box([-halfWidth - 1, -3, -halfDepth - 1], [halfWidth + 1, -1, halfDepth + 1], BRICK);
    const floor = box([-halfWidth, 0, -halfDepth], [halfWidth, 0, halfDepth], PURPUR);
    const walls = shell(
      [-halfWidth, 0, -halfDepth],
      [halfWidth, wallHeight, halfDepth],
      BRICK
    ).filter((p) => p.y > 0);
    const hollow = box([-halfWidth + 1, 1, -halfDepth + 1], [halfWidth - 1, wallHeight - 1, halfDepth - 1], "minecraft:air");

    // Colonnade down the long axis.
    const pillars = [];
    for (let z = -halfDepth + 2; z <= halfDepth - 2; z += 3) {
      for (const x of [-halfWidth + 2, halfWidth - 2]) {
        for (let y = 1; y < wallHeight; y++) {
          pillars.push({ x, y, z, id: y === wallHeight - 1 ? PURPUR : "minecraft:purpur_pillar" });
        }
      }
    }

    // Doorway on the -z face.
    const doorway = box([-1, 1, -halfDepth], [1, 3, -halfDepth], "minecraft:air");

    // Ruin it: erode from a random corner, hardest at the top.
    const erosionX = rng.chance(0.5) ? 1 : -1;
    const erosionZ = rng.chance(0.5) ? 1 : -1;
    const ruin = [];
    const standing = merge(foundation, floor, walls, pillars);
    for (const placement of standing) {
      if (placement.y <= 0) continue;
      const towardCorner =
        (placement.x * erosionX) / halfWidth + (placement.z * erosionZ) / halfDepth;
      const exposure = (towardCorner + 2) / 4 + (placement.y / wallHeight) * 0.8;
      if (rng.next() < exposure * decay) {
        ruin.push({ ...placement, id: "minecraft:air" });
      } else if (rng.chance(0.07)) {
        ruin.push({ ...placement, id: "voidbound:shattered_end_stone" });
      }
    }

    // Altar with the chest, plus lanterns that survived.
    const altar = merge(
      box([-1, 1, halfDepth - 3], [1, 1, halfDepth - 2], PURPUR),
      at(0, 2, halfDepth - 3, "minecraft:chest"),
      at(-2, 1, halfDepth - 2, "voidbound:rift_lantern"),
      at(2, 1, halfDepth - 2, "voidbound:rift_lantern"),
      // The waystone sits opposite the altar, past the Warden.
      at(0, 1, -halfDepth + 2, "voidbound:waystone")
    );

    const rubble = [];
    for (let i = 0; i < rng.int(14, 26); i++) {
      rubble.push({
        x: rng.int(-halfWidth - 3, halfWidth + 3),
        y: rng.int(0, 1),
        z: rng.int(-halfDepth - 3, halfDepth + 3),
        id: rng.chance(0.55) ? "voidbound:shattered_end_stone" : BRICK,
      });
    }

    return {
      placements: merge(foundation, floor, walls, hollow, pillars, doorway, ruin, rubble, altar),
      chests: [{ x: 0, y: 2, z: halfDepth - 3 }],
      beacon: { x: 0, y: wallHeight, z: 0 },
      warden: true,
    };
  },
};
