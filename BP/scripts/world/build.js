import { world } from "@minecraft/server";
import { KEYS, getWorldFlag, setWorldFlag, setWorldJson } from "../lib/state.js";
import { buildHollowHamlet } from "../village/village.js";

export const HOLLOW_VEIL = "hollowveil:hollow_veil";

// A custom dimension registered via the Script API starts as an empty void -
// there is no terrain generator to lean on, so the whole island is raised
// by hand the first time anyone steps through the portal. See docs/DIMENSION.md.
export const ISLAND_CENTER = { x: 0, y: 64, z: 0 };
export const ISLAND_RADIUS = 90;
const SURFACE_Y = ISLAND_CENTER.y;
const BEDROCK_Y = SURFACE_Y - 11;
const STONE_TOP_Y = SURFACE_Y - 2;

const ALTAR_RING_RADIUS = 68;
const ALTAR_OFFSETS = [0, 120, 240].map((deg) => {
  const rad = (deg * Math.PI) / 180;
  return { x: Math.round(Math.cos(rad) * ALTAR_RING_RADIUS), z: Math.round(Math.sin(rad) * ALTAR_RING_RADIUS) };
});

export function isWithinIsland(pos) {
  const dx = pos.x - ISLAND_CENTER.x;
  const dz = pos.z - ISLAND_CENTER.z;
  return Math.hypot(dx, dz) < ISLAND_RADIUS - 4;
}

export async function ensureWorldBuilt() {
  if (getWorldFlag(KEYS.ARRIVAL_BUILT)) return;
  setWorldFlag(KEYS.ARRIVAL_BUILT, true);

  const dim = world.getDimension(HOLLOW_VEIL);
  const r = ISLAND_RADIUS;
  const { x: cx, y: cy, z: cz } = ISLAND_CENTER;

  const tickingId = "hollowveil_island_build";
  await world.tickingAreaManager.createTickingArea(tickingId, {
    dimension: dim,
    from: { x: cx - r - 4, y: BEDROCK_Y - 2, z: cz - r - 4 },
    to: { x: cx + r + 4, y: cy + 12, z: cz + r + 4 },
  });

  const run = (cmd) => dim.runCommandAsync(cmd);

  // Raise the island: bedrock base, a stone body (ore-bearing), a bonestone
  // topsoil layer, then clear headroom above it.
  run(`fill ${cx - r} ${BEDROCK_Y} ${cz - r} ${cx + r} ${BEDROCK_Y} ${cz + r} minecraft:bedrock replace`);
  run(`fill ${cx - r} ${BEDROCK_Y + 1} ${cz - r} ${cx + r} ${STONE_TOP_Y} ${cz + r} minecraft:stone replace`);
  run(`fill ${cx - r} ${SURFACE_Y - 1} ${cz - r} ${cx + r} ${SURFACE_Y - 1} ${cz + r} hollowveil:bonestone replace`);
  run(`fill ${cx - r} ${SURFACE_Y} ${cz - r} ${cx + r} ${SURFACE_Y + 30} ${cz + r} air replace`);

  scatterOre(run, cx, cz, r);

  for (const off of ALTAR_OFFSETS) {
    run(`setblock ${cx + off.x} ${SURFACE_Y - 1} ${cz + off.z} hollowveil:ritual_altar`);
  }
  setWorldJson(KEYS.ALTAR_POSITIONS, ALTAR_OFFSETS.map((o) => ({ x: cx + o.x, y: SURFACE_Y, z: cz + o.z })));

  buildHollowHamlet(dim, { x: cx, y: SURFACE_Y, z: cz });

  await world.tickingAreaManager.removeTickingArea(tickingId);
}

function scatterOre(run, cx, cz, r) {
  const rnd = mulberry32(1337);
  const veins = 36;
  for (let i = 0; i < veins; i++) {
    const angle = rnd() * Math.PI * 2;
    const dist = rnd() * (r - 8);
    const x = Math.round(cx + Math.cos(angle) * dist);
    const z = Math.round(cz + Math.sin(angle) * dist);
    const y = BEDROCK_Y + 2 + Math.floor(rnd() * (STONE_TOP_Y - BEDROCK_Y - 2));
    run(`setblock ${x} ${y} ${z} hollowveil:wraithsteel_ore`);
    if (rnd() > 0.5) run(`setblock ${x + 1} ${y} ${z} hollowveil:wraithsteel_ore`);
    if (rnd() > 0.5) run(`setblock ${x} ${y} ${z + 1} hollowveil:wraithsteel_ore`);
  }
}

// Small deterministic PRNG so the ore scatter is reproducible without
// depending on Math.random() ordering across command batches.
function mulberry32(seed) {
  let a = seed;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
