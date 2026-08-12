import { world } from "@minecraft/server";
import { KEYS, getWorldFlag, setWorldFlag, setWorldJson } from "../lib/state.js";
import { buildHollowHamlet } from "../village/village.js";
import { SURFACE_Y, WORLD_RADIUS, biomeAt, heightAt, isWithinWorld } from "./biomes.js";
import { commandRunner } from "../lib/cmd.js";

export const HOLLOW_VEIL = "hollowveil:hollow_veil";

// A custom dimension registered via the Script API starts as an empty void,
// so every block of it is placed by this addon. What used to be a single
// 90-block island raised in one burst is now a 512-radius world streamed in
// sector by sector as players explore (see world/terrain.js) with landmarks
// scattered across it (see world/sites.js). This file only owns the hub:
// the arrival area, the three Warden altars and Hollow Hamlet, all of which
// have to exist immediately and at known positions.
export const ISLAND_CENTER = { x: 0, y: SURFACE_Y, z: 0 };
export const ISLAND_RADIUS = WORLD_RADIUS;

const HUB_CLEAR = 34;
const ALTAR_RING_RADIUS = 30;
const ALTAR_OFFSETS = [0, 120, 240].map((deg) => {
  const rad = (deg * Math.PI) / 180;
  return { x: Math.round(Math.cos(rad) * ALTAR_RING_RADIUS), z: Math.round(Math.sin(rad) * ALTAR_RING_RADIUS) };
});

export function isWithinIsland(pos) {
  return isWithinWorld(pos);
}

/** Which biome a position belongs to. Kept as `regionAt` because the mob
 * spawner and ambience systems key off it; it now returns the noise-based
 * biome id rather than a fixed quadrant. */
export function regionAt(pos) {
  return biomeAt(pos.x, pos.z).id;
}

/** Raises only the hub. Terrain beyond it streams in around players. */
export async function ensureWorldBuilt() {
  if (getWorldFlag(KEYS.ARRIVAL_BUILT)) return;
  setWorldFlag(KEYS.ARRIVAL_BUILT, true);

  const dim = world.getDimension(HOLLOW_VEIL);
  const { x: cx, z: cz } = ISLAND_CENTER;
  const y = SURFACE_Y;
  const r = HUB_CLEAR;

  const tickingId = "hollowveil_hub_build";
  await world.tickingAreaManager.createTickingArea(tickingId, {
    dimension: dim,
    from: { x: cx - r - 4, y: y - 16, z: cz - r - 4 },
    to: { x: cx + r + 4, y: y + 40, z: cz + r + 4 },
  });

  const run = commandRunner(dim);
  run(`fill ${cx - r} ${y - 12} ${cz - r} ${cx + r} ${y - 12} ${cz + r} minecraft:bedrock`);
  run(`fill ${cx - r} ${y - 11} ${cz - r} ${cx + r} ${y - 1} ${cz + r} minecraft:deepslate`);
  run(`fill ${cx - r} ${y} ${cz - r} ${cx + r} ${y} ${cz + r} hollowveil:bonestone`);
  run(`fill ${cx - r} ${y + 1} ${cz - r} ${cx + r} ${y + 30} ${cz + r} air`);

  for (const off of ALTAR_OFFSETS) {
    run(`setblock ${cx + off.x} ${y} ${cz + off.z} hollowveil:ritual_altar`);
  }
  setWorldJson(KEYS.ALTAR_POSITIONS, ALTAR_OFFSETS.map((o) => ({ x: cx + o.x, y: y + 1, z: cz + o.z })));
  setWorldJson(KEYS.SPAWNER_POSITIONS, []);

  buildHollowHamlet(dim, { x: cx, y: y + 1, z: cz });

  await world.tickingAreaManager.removeTickingArea(tickingId);
}

export { heightAt };
