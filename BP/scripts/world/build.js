import { world, BlockVolume } from "@minecraft/server";
import { KEYS, getWorldFlag, setWorldFlag, setWorldJson } from "../lib/state.js";
import { buildHollowHamlet } from "../village/village.js";
import { SURFACE_Y, BEDROCK_Y, WORLD_RADIUS, biomeAt, heightAt, isWithinWorld } from "./biomes.js";

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

export const HUB_CLEAR = 34;
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

/**
 * Raises only the hub. Terrain beyond it streams in around players.
 *
 * This used to set its "already built" flag on the FIRST line and build
 * afterwards. When the build threw - which it did, on every v10 world, because
 * every fill in here went through the removed `runCommandAsync` - the world was
 * left permanently marked as having a hub it had never received. The terrain
 * streamer then laid solid ground straight over the arrival point, and players
 * arrived sealed inside rock with a stone ceiling overhead.
 *
 * So: the flag is set only after the build is verified to have landed, and the
 * verification is a real block read rather than the absence of an exception.
 * A world that was flagged by the old code self-heals on the next arrival,
 * because `hubIsStanding()` finds no altar and rebuilds regardless of the flag.
 */
export async function ensureWorldBuilt() {
  const dim = world.getDimension(HOLLOW_VEIL);
  if (getWorldFlag(KEYS.ARRIVAL_BUILT) && hubIsStanding(dim)) return;

  const { x: cx, z: cz } = ISLAND_CENTER;
  const y = SURFACE_Y;
  const r = HUB_CLEAR;

  const tickingId = "hollowveil_hub_build";
  try {
    await world.tickingAreaManager.createTickingArea(tickingId, {
      dimension: dim,
      from: { x: cx - r - 4, y: y - 16, z: cz - r - 4 },
      to: { x: cx + r + 4, y: y + 40, z: cz + r + 4 },
    });
  } catch {
    // Already exists, or capacity is full. The hub is inside the arriving
    // player's own loaded chunks either way, so the build can still proceed.
  }

  // The hub has to be laid out the same way the generator lays out everywhere
  // else, or it does not join up with it. That means a bedrock floor at the
  // bottom of the world, an underground level above it, open cavern, and then
  // the plateau the village stands on - not a slab hanging in the air.
  //
  // The bedrock floor also doubles as the terrain streamer's "is this sector
  // built" probe, so laying it here is what stops the streamer from deciding
  // the hub is empty and filling the village in with rock.
  fillBox(dim, cx - r, BEDROCK_Y, cz - r, cx + r, BEDROCK_Y, cz + r, "minecraft:bedrock");
  fillBox(dim, cx - r, BEDROCK_Y + 1, cz - r, cx + r, BEDROCK_Y + 12, cz + r, "minecraft:deepslate");
  fillBox(dim, cx - r, y - 9, cz - r, cx + r, y - 1, cz + r, "minecraft:deepslate");
  fillBox(dim, cx - r, y, cz - r, cx + r, y, cz + r, "hollowveil:bonestone");
  // Headroom. This is the fill whose absence buried people.
  fillBox(dim, cx - r, y + 1, cz - r, cx + r, y + 30, cz + r, "minecraft:air");

  for (const off of ALTAR_OFFSETS) {
    try {
      dim.setBlockType({ x: cx + off.x, y, z: cz + off.z }, "hollowveil:ritual_altar");
    } catch {
      /* verified below */
    }
  }
  setWorldJson(KEYS.ALTAR_POSITIONS, ALTAR_OFFSETS.map((o) => ({ x: cx + o.x, y: y + 1, z: cz + o.z })));
  setWorldJson(KEYS.SPAWNER_POSITIONS, []);

  buildHollowHamlet(dim, { x: cx, y: y + 1, z: cz });

  if (hubIsStanding(dim)) setWorldFlag(KEYS.ARRIVAL_BUILT, true);

  try {
    await world.tickingAreaManager.removeTickingArea(tickingId);
  } catch {
    /* nothing to remove */
  }
}

/** Native fill, split so no single volume is large enough to be refused. */
function fillBox(dim, x0, y0, z0, x1, y1, z1, type) {
  const STEP = 16;
  for (let y = y0; y <= y1; y += STEP) {
    const yb = Math.min(y1, y + STEP - 1);
    try {
      dim.fillBlocks(new BlockVolume({ x: x0, y, z: z0 }, { x: x1, y: yb, z: z1 }), type);
    } catch {
      /* unloaded chunk; hubIsStanding() is what decides whether this counted */
    }
  }
}

/**
 * Is the hub actually there? Checks the three things whose absence is what
 * players actually experience: ground to stand on, air to stand in, and an
 * altar to use.
 */
function hubIsStanding(dim) {
  const { x: cx, z: cz } = ISLAND_CENTER;
  const y = SURFACE_Y;
  try {
    if (dim.getBlock({ x: cx, y, z: cz })?.isAir !== false) return false;
    if (dim.getBlock({ x: cx, y: y + 2, z: cz })?.isAir !== true) return false;
    const a = ALTAR_OFFSETS[0];
    return dim.getBlock({ x: cx + a.x, y, z: cz + a.z })?.typeId === "hollowveil:ritual_altar";
  } catch {
    return false;                 // chunk not loaded: cannot claim it is built
  }
}

export { heightAt };
