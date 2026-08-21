/**
 * Rift Anchor - an obsidian frame holding a tear in the End open.
 *
 * The most hostile of the four, and the only structure that carries a boss:
 * the Rift Sovereign holds the tear open, so the anchor doubles as its arena.
 * The fog closes in and the payoff sits in the open, where you have to stand
 * still to take it.
 */

import { at, blob, box, merge } from "../lib/blueprint.js";

const OBSIDIAN = "minecraft:obsidian";

export const RiftAnchor = {
  id: "anchor",
  name: "Rift Anchor",
  radius: 12,
  fog: "voidbound:fog_rift",

  build(rng) {
    const frameWidth = rng.int(5, 7);
    const frameHeight = rng.int(7, 10);

    // Stepped obsidian dais.
    const dais = merge(
      blob(0, -1, 0, 8.0, OBSIDIAN, undefined, 0.35),
      blob(0, 0, 0, 6.0, "minecraft:crying_obsidian", undefined, 0.3),
      blob(0, 1, 0, 3.5, OBSIDIAN, undefined, 0.3)
    );

    // The frame itself: two uprights and a lintel, standing on the dais.
    const frame = merge(
      box([-frameWidth, 2, 0], [-frameWidth, frameHeight, 0], OBSIDIAN),
      box([frameWidth, 2, 0], [frameWidth, frameHeight, 0], OBSIDIAN),
      box([-frameWidth, frameHeight, 0], [frameWidth, frameHeight, 0], OBSIDIAN),
      box([-frameWidth, 2, 0], [frameWidth, 2, 0], "minecraft:crying_obsidian")
    );

    // The tear: a curtain of crystal suspended inside the frame.
    const tear = [];
    for (let x = -frameWidth + 1; x <= frameWidth - 1; x++) {
      const span = Math.cos((x / frameWidth) * (Math.PI / 2));
      const top = 3 + Math.round((frameHeight - 4) * span);
      for (let y = 3; y <= top; y++) {
        if (rng.chance(0.82)) {
          tear.push({ x, y, z: 0, id: "voidbound:void_glass" });
        }
      }
    }
    tear.push({ x: 0, y: Math.floor(frameHeight / 2) + 1, z: 0, id: "voidbound:void_crystal_block" });

    // Broken outer ring of pillars.
    const pillars = [];
    for (let i = 0; i < 8; i++) {
      const angle = (i / 8) * Math.PI * 2 + rng.float(-0.15, 0.15);
      const px = Math.round(Math.cos(angle) * 9);
      const pz = Math.round(Math.sin(angle) * 9);
      const height = rng.int(2, 6);
      for (let y = 0; y < height; y++) {
        pillars.push({ x: px, y, z: pz, id: y === height - 1 ? "voidbound:void_crystal_block" : OBSIDIAN });
      }
    }

    const offerings = merge(
      at(0, 2, 3, "minecraft:chest"),
      at(-2, 2, 3, "voidbound:rift_lantern"),
      at(2, 2, 3, "voidbound:rift_lantern")
    );

    return {
      placements: merge(dais, frame, tear, pillars, offerings),
      chests: [{ x: 0, y: 2, z: 3 }],
      beacon: { x: 0, y: frameHeight, z: 0 },
      guards: rng.int(1, 2),
      boss: true,
      // Anchors are a hole in the world. Sometimes something came through it.
      lords: rng.chance(0.14)
        ? [{ id: "eternal_end:ender_overlord", x: 0, y: frameHeight - 4, z: 0 }]
        : [],
    };
  },
};
