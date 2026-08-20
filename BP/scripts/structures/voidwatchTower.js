/**
 * Voidwatch Tower - the landmark structure.
 *
 * The other four sit on the ground and are found by flying over them. This one
 * is meant to be seen from a long way off and climbed: a narrow shaft with a
 * spiral stair cut into it, ringed galleries on the way up, and the reward at
 * the top rather than in a vault at the bottom.
 *
 * Building the stair as part of the shell rather than as a separate pass is
 * what keeps it climbable - the steps are carved out of the wall's interior, so
 * they can never end up floating or buried by the erosion pass.
 */

import { at, blob, box, merge, shell } from "../lib/blueprint.js";

const BRICK = "voidbound:ender_bricks";
const TILE = "voidbound:ender_tiles";
const PILLAR = "voidbound:ender_pillar";
const CHISELLED = "voidbound:chiseled_ender_bricks";

export const VoidwatchTower = {
  id: "tower",
  name: "Voidwatch Tower",
  radius: 11,
  fog: "voidbound:fog_rift",

  build(rng) {
    const height = rng.int(26, 38);
    const half = 4;

    const foundation = merge(
      blob(0, -3, 0, 8.5, BRICK, undefined, 0.4),
      box([-half - 1, -2, -half - 1], [half + 1, 0, half + 1], TILE)
    );

    // Shaft: a hollow square tower with corner pillars.
    const walls = [];
    for (let y = 1; y <= height; y++) {
      for (const p of shell([-half, y, -half], [half, y, half], BRICK)) walls.push(p);
      for (const [cx, cz] of [[-half, -half], [half, -half], [-half, half], [half, half]]) {
        walls.push({ x: cx, y, z: cz, id: PILLAR });
      }
      // Arrow slits, staggered so they spiral with the stair.
      if (y % 5 === 2) {
        const face = (y / 5 | 0) % 4;
        const slit = [
          { x: 0, z: -half }, { x: half, z: 0 }, { x: 0, z: half }, { x: -half, z: 0 },
        ][face];
        walls.push({ ...slit, y, id: "minecraft:air" });
        walls.push({ ...slit, y: y + 1, id: "minecraft:air" });
      }
    }

    const hollow = box([-half + 1, 1, -half + 1], [half - 1, height, half - 1], "minecraft:air");

    // Spiral stair: one step per level, walking the inner wall.
    const stairs = [];
    const ring = [];
    for (let x = -half + 1; x <= half - 1; x++) ring.push({ x, z: -half + 1 });
    for (let z = -half + 2; z <= half - 1; z++) ring.push({ x: half - 1, z });
    for (let x = half - 2; x >= -half + 1; x--) ring.push({ x, z: half - 1 });
    for (let z = half - 2; z >= -half + 2; z--) ring.push({ x: -half + 1, z });
    for (let y = 1; y <= height; y++) {
      const step = ring[(y - 1) % ring.length];
      stairs.push({ x: step.x, y, z: step.z, id: TILE });
    }

    // Galleries: a wider ring every eight levels, so the climb has landings.
    const galleries = [];
    for (let y = 9; y < height - 4; y += 8) {
      for (const p of box([-half - 2, y, -half - 2], [half + 2, y, half + 2], TILE)) {
        const onRim = Math.max(Math.abs(p.x), Math.abs(p.z)) > half;
        if (onRim) galleries.push(p);
      }
      for (const [cx, cz] of [[-half - 2, -half - 2], [half + 2, -half - 2],
                              [-half - 2, half + 2], [half + 2, half + 2]]) {
        galleries.push({ x: cx, y: y + 1, z: cz, id: CHISELLED });
        galleries.push({ x: cx, y: y + 2, z: cz, id: "voidbound:rift_lantern" });
      }
    }

    // Crown: an open watch deck with the cache on it.
    const deck = merge(
      box([-half - 1, height + 1, -half - 1], [half + 1, height + 1, half + 1], TILE),
      box([-half, height + 2, -half], [half, height + 2, half], "minecraft:air"),
      shell([-half - 1, height + 2, -half - 1], [half + 1, height + 3, half + 1], CHISELLED)
        .filter((p) => p.y > height + 1),
      box([-half, height + 2, -half], [half, height + 3, half], "minecraft:air"),
      at(0, height + 2, 0, "minecraft:chest"),
      at(-2, height + 2, -2, "voidbound:echo_lamp"),
      at(2, height + 2, 2, "voidbound:echo_lamp"),
      at(0, height + 4, 0, "voidbound:void_crystal_block")
    );

    // Erosion, heaviest at the top where the wind gets it.
    const ruin = [];
    for (const p of walls) {
      const exposure = p.y / height;
      if (rng.next() < exposure * 0.20) ruin.push({ ...p, id: "minecraft:air" });
      else if (rng.chance(0.05)) ruin.push({ ...p, id: CHISELLED });
    }

    const rubble = [];
    for (let i = 0; i < rng.int(10, 22); i++) {
      rubble.push({
        x: rng.int(-half - 5, half + 5),
        y: rng.int(0, 1),
        z: rng.int(-half - 5, half + 5),
        id: rng.chance(0.5) ? BRICK : "voidbound:shattered_end_stone",
      });
    }

    return {
      // Stairs land after the hollow so the climb is never carved away, and
      // the deck lands last so the cache survives the erosion pass.
      placements: merge(foundation, walls, hollow, ruin, stairs, galleries, rubble, deck),
      chests: [{ x: 0, y: height + 2, z: 0 }],
      beacon: { x: 0, y: height + 4, z: 0 },
      guards: rng.int(1, 3),
    };
  },
};
