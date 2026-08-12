import { KEYS, getWorldFlag, setWorldFlag, setWorldJson } from "../lib/state.js";
import { commandRunner } from "../lib/cmd.js";

/** Procedurally raises Hollow Hamlet: a small perimeter of lit boundary
 * stones, three ashwood/bonestone huts, and a central shrine where the
 * Occultist trader stands. See docs/STORY.md for the narrative reasoning
 * and docs/STRUCTURES.md for why this is built in code instead of shipped
 * as a static structure file. Runs once per world (guarded by a dynamic
 * property flag). */
export function buildHollowHamlet(dimension, origin) {
  if (getWorldFlag(KEYS.VILLAGE_BUILT)) return;
  setWorldFlag(KEYS.VILLAGE_BUILT, true);

  const { x, y, z } = origin;
  const run = commandRunner(dimension);

  // clear + flatten a modest plaza
  run(`fill ${x - 16} ${y} ${z - 16} ${x + 16} ${y + 10} ${z + 16} air`);
  run(`fill ${x - 16} ${y - 1} ${z - 16} ${x + 16} ${y - 1} ${z + 16} hollowveil:bonestone`);

  // boundary stones (soulforged obsidian pillars topped with soul lanterns)
  const corners = [
    { cx: x - 15, cz: z - 15 },
    { cx: x + 15, cz: z - 15 },
    { cx: x - 15, cz: z + 15 },
    { cx: x + 15, cz: z + 15 },
  ];
  for (const { cx, cz } of corners) {
    run(`fill ${cx} ${y} ${cz} ${cx} ${y + 2} ${cz} hollowveil:soulforged_obsidian`);
    run(`setblock ${cx} ${y + 3} ${cz} hollowveil:soul_lantern`);
  }

  buildHut(run, { x: x - 9, y, z: z - 9 });
  buildHut(run, { x: x + 9, y, z: z - 9 });
  buildHut(run, { x: x, y, z: z + 10 });

  // central shrine: a raised bonestone dais with the Occultist and a ring of lanterns
  run(`fill ${x - 2} ${y} ${z - 2} ${x + 2} ${y} ${z + 2} hollowveil:bonestone`);
  run(`setblock ${x} ${y + 1} ${z - 2} hollowveil:soul_lantern`);
  run(`setblock ${x} ${y + 1} ${z + 2} hollowveil:soul_lantern`);
  run(`setblock ${x - 2} ${y + 1} ${z} hollowveil:soul_lantern`);
  run(`setblock ${x + 2} ${y + 1} ${z} hollowveil:soul_lantern`);
  run(`summon hollowveil:occultist ${x} ${y + 1} ${z - 4} facing ${x} ${y + 1} ${z}`);

  setWorldJson(KEYS.VILLAGE_SHRINE_POS, { x, y: y + 1, z });
}

function buildHut(run, { x, y, z }) {
  const w = 5; // footprint w x w
  const h = 3;
  run(`fill ${x - w} ${y} ${z - w} ${x + w} ${y} ${z + w} hollowveil:bonestone`);
  run(`fill ${x - w} ${y + 1} ${z - w} ${x + w} ${y + h} ${z - w} hollowveil:ashwood_planks`);
  run(`fill ${x - w} ${y + 1} ${z + w} ${x + w} ${y + h} ${z + w} hollowveil:ashwood_planks`);
  run(`fill ${x - w} ${y + 1} ${z - w} ${x - w} ${y + h} ${z + w} hollowveil:ashwood_planks`);
  run(`fill ${x + w} ${y + 1} ${z - w} ${x + w} ${y + h} ${z + w} hollowveil:ashwood_planks`);
  run(`fill ${x - w} ${y + h + 1} ${z - w} ${x + w} ${y + h + 1} ${z + w} hollowveil:ashwood_log`);
  // doorway + interior hollow-out
  run(`fill ${x - 1} ${y + 1} ${z - w} ${x + 1} ${y + 2} ${z - w} air`);
  run(`fill ${x - w + 1} ${y + 1} ${z - w + 1} ${x + w - 1} ${y + h} ${z + w - 1} air`);
  run(`setblock ${x} ${y + 2} ${z} hollowveil:soul_lantern`);
}
