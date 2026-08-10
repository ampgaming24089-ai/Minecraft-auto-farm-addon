import { world, ItemStack } from "@minecraft/server";
import { KEYS, getWorldFlag, setWorldFlag, setWorldJson } from "../lib/state.js";
import { buildHollowHamlet } from "../village/village.js";

export const HOLLOW_VEIL = "hollowveil:hollow_veil";

// A custom dimension registered via the Script API starts as an empty void -
// there is no terrain generator to lean on, so the whole island (including
// its four themed regions and both landmark structures) is raised by hand
// the first time anyone steps through the portal. See docs/DIMENSION.md and
// docs/WORLD.md.
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

/** The island is split into four outer-ring quadrants around a neutral
 * "Misty Reach" core (where Hollow Hamlet sits). Purely a script-side
 * classification - there's no real Bedrock biome under any of this, see
 * docs/WORLD.md - but it drives both terrain palette and ambient mob
 * spawning, so it reads as distinct territory in practice. */
export function regionAt(pos) {
  const dx = pos.x - ISLAND_CENTER.x;
  const dz = pos.z - ISLAND_CENTER.z;
  const dist = Math.hypot(dx, dz);
  if (dist < 26) return "misty";
  if (dx >= 0 && dz < 0) return "bastion";
  if (dx >= 0 && dz >= 0) return "ashlands";
  if (dx < 0 && dz >= 0) return "marsh";
  return "ruins";
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
    to: { x: cx + r + 4, y: cy + 40, z: cz + r + 4 },
  });

  const run = (cmd) => dim.runCommandAsync(cmd);

  // Raise the island: bedrock base, a stone body (ore-bearing), a bonestone
  // topsoil layer, then clear headroom above it.
  run(`fill ${cx - r} ${BEDROCK_Y} ${cz - r} ${cx + r} ${BEDROCK_Y} ${cz + r} minecraft:bedrock replace`);
  run(`fill ${cx - r} ${BEDROCK_Y + 1} ${cz - r} ${cx + r} ${STONE_TOP_Y} ${cz + r} minecraft:stone replace`);
  run(`fill ${cx - r} ${SURFACE_Y - 1} ${cz - r} ${cx + r} ${SURFACE_Y - 1} ${cz + r} hollowveil:bonestone replace`);
  run(`fill ${cx - r} ${SURFACE_Y} ${cz - r} ${cx + r} ${SURFACE_Y + 30} ${cz + r} air replace`);

  scatterOre(run, cx, cz, r);
  paintRegions(run, cx, cz, r);

  for (const off of ALTAR_OFFSETS) {
    run(`setblock ${cx + off.x} ${SURFACE_Y - 1} ${cz + off.z} hollowveil:ritual_altar`);
  }
  setWorldJson(KEYS.ALTAR_POSITIONS, ALTAR_OFFSETS.map((o) => ({ x: cx + o.x, y: SURFACE_Y, z: cz + o.z })));

  buildHollowHamlet(dim, { x: cx, y: SURFACE_Y, z: cz });

  const spawnerPositions = [];
  await buildEmberBastion(dim, run, { x: cx + 46, y: SURFACE_Y, z: cz - 46 }, spawnerPositions);
  await buildSunkenCity(dim, run, { x: cx - 46, y: SURFACE_Y, z: cz - 46 }, spawnerPositions);
  setWorldJson(KEYS.SPAWNER_POSITIONS, spawnerPositions);

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
  // ember coal: shallower and more common, mostly under the ashlands/bastion half
  const coalRnd = mulberry32(9001);
  for (let i = 0; i < 30; i++) {
    const angle = coalRnd() * Math.PI * 2;
    const dist = coalRnd() * (r - 10);
    const x = Math.round(cx + Math.cos(angle) * dist);
    const z = Math.round(cz + Math.sin(angle) * dist);
    const y = STONE_TOP_Y - 1 - Math.floor(coalRnd() * 4);
    run(`setblock ${x} ${y} ${z} hollowveil:ember_coal_ore`);
  }
  // veilsteel: rare, deep, clustered near the bastion quadrant
  const veilRnd = mulberry32(4242);
  for (let i = 0; i < 14; i++) {
    const angle = (Math.PI / 2) * (1.5 + veilRnd() * 0.9); // biased toward +x/-z (bastion)
    const dist = 20 + veilRnd() * (r - 30);
    const x = Math.round(cx + Math.cos(angle) * dist);
    const z = Math.round(cz + Math.sin(angle) * dist);
    const y = BEDROCK_Y + 2 + Math.floor(veilRnd() * 5);
    run(`setblock ${x} ${y} ${z} hollowveil:veilsteel_ore`);
    if (veilRnd() > 0.4) run(`setblock ${x + 1} ${y} ${z} hollowveil:veilsteel_ore`);
  }
  // hollowforged: the rarest material in the Veil - a handful of single
  // blocks on the bedrock floor, scattered without regard to region so
  // finding one means actually digging, not just visiting the right quadrant
  const hfRnd = mulberry32(70071);
  for (let i = 0; i < 5; i++) {
    const angle = hfRnd() * Math.PI * 2;
    const dist = hfRnd() * (r - 12);
    const x = Math.round(cx + Math.cos(angle) * dist);
    const z = Math.round(cz + Math.sin(angle) * dist);
    run(`setblock ${x} ${BEDROCK_Y + 1} ${z} hollowveil:hollowforged_ore`);
  }
}

function paintRegions(run, cx, cz, r) {
  // Bastion quadrant (+x, -z): scorched, blackstone-flecked ground.
  run(`fill ${cx + 12} ${SURFACE_Y - 1} ${cz - r} ${cx + r} ${SURFACE_Y - 1} ${cz - 12} minecraft:blackstone replace hollowveil:bonestone`);
  // Ashlands quadrant (+x, +z): existing demon theme, warm ash ground.
  run(`fill ${cx + 12} ${SURFACE_Y - 1} ${cz + 12} ${cx + r} ${SURFACE_Y - 1} ${cz + r} minecraft:blackstone replace hollowveil:bonestone`);
  // Boneyard Marsh quadrant (-x, +z): mud, patches of shallow water.
  run(`fill ${cx - r} ${SURFACE_Y - 1} ${cz + 12} ${cx - 12} ${SURFACE_Y - 1} ${cz + r} hollowveil:veil_mud replace hollowveil:bonestone`);
  // Sunken Ruins quadrant (-x, -z): deepslate-grey drowned stonework.
  run(`fill ${cx - r} ${SURFACE_Y - 1} ${cz - r} ${cx - 12} ${SURFACE_Y - 1} ${cz - 12} minecraft:deepslate_tiles replace hollowveil:bonestone`);

  // scatter magma accents through the ashlands and glimmershroom light through the marsh
  const magmaRnd = mulberry32(555);
  for (let i = 0; i < 18; i++) {
    const x = Math.round(cx + 14 + magmaRnd() * (r - 20));
    const z = Math.round(cz + 14 + magmaRnd() * (r - 20));
    run(`setblock ${x} ${SURFACE_Y - 1} ${z} minecraft:magma_block`);
  }
  const rnd = mulberry32(777);
  for (let i = 0; i < 24; i++) {
    const x = Math.round(cx - 14 - rnd() * (r - 20));
    const z = Math.round(cz + 14 + rnd() * (r - 20));
    run(`setblock ${x} ${SURFACE_Y} ${z} hollowveil:glimmershroom`);
  }
}

async function buildEmberBastion(dim, run, origin, spawnerPositions) {
  const { x, y, z } = origin;
  const w = 12;
  run(`fill ${x - w} ${y} ${z - w} ${x + w} ${y} ${z + w} hollowveil:bastion_brick`);
  run(`fill ${x - w} ${y + 1} ${z - w} ${x + w} ${y + 6} ${z - w} hollowveil:bastion_brick`);
  run(`fill ${x - w} ${y + 1} ${z + w} ${x + w} ${y + 6} ${z + w} hollowveil:bastion_brick`);
  run(`fill ${x - w} ${y + 1} ${z - w} ${x - w} ${y + 6} ${z + w} hollowveil:bastion_brick`);
  run(`fill ${x + w} ${y + 1} ${z - w} ${x + w} ${y + 6} ${z + w} hollowveil:bastion_brick`);
  run(`fill ${x - w + 1} ${y + 1} ${z - w + 1} ${x + w - 1} ${y + 6} ${z + w - 1} air`);
  // corner towers
  for (const [ox, oz] of [[-w, -w], [w, -w], [-w, w], [w, w]]) {
    run(`fill ${x + ox - 1} ${y} ${z + oz - 1} ${x + ox + 1} ${y + 9} ${z + oz + 1} hollowveil:bastion_brick`);
    run(`setblock ${x + ox} ${y + 10} ${z + oz} hollowveil:soul_lantern`);
  }
  // molten floor accents
  run(`fill ${x - 2} ${y} ${z - 2} ${x + 2} ${y} ${z + 2} minecraft:magma_block`);
  await run(`setblock ${x} ${y + 1} ${z} minecraft:chest`);
  fillContainer(dim, { x, y: y + 1, z }, bastionLoot());

  const spawnSpots = [
    { x: x - 6, z: z - 6 },
    { x: x + 6, z: z + 6 },
  ];
  for (const s of spawnSpots) {
    run(`setblock ${s.x} ${y + 1} ${s.z} hollowveil:sentinel_spawner`);
    spawnerPositions.push({ x: s.x, y: y + 1, z: s.z, mob: "hollowveil:bastion_sentinel" });
  }
}

async function buildSunkenCity(dim, run, origin, spawnerPositions) {
  const { x, y, z } = origin;
  // a small ruined skyline: towers of varying height around a plaza
  const towers = [
    { ox: -8, oz: -8, h: 10 },
    { ox: 8, oz: -6, h: 14 },
    { ox: -6, oz: 8, h: 8 },
    { ox: 7, oz: 7, h: 12 },
    { ox: 0, oz: -12, h: 16 },
  ];
  run(`fill ${x - 16} ${y - 1} ${z - 16} ${x + 16} ${y - 1} ${z + 16} hollowveil:sunken_bricks`);
  for (const t of towers) {
    const tx = x + t.ox;
    const tz = z + t.oz;
    run(`fill ${tx - 2} ${y} ${tz - 2} ${tx + 2} ${y + t.h} ${tz + 2} hollowveil:sunken_bricks`);
    run(`fill ${tx - 1} ${y + 1} ${tz - 1} ${tx + 1} ${y + t.h - 1} ${tz + 1} air`);
    run(`setblock ${tx} ${y + t.h + 1} ${tz} hollowveil:soul_lantern`);
  }
  // central vault under the tallest tower
  await run(`setblock ${x} ${y + 1} ${z - 12} minecraft:chest`);
  fillContainer(dim, { x, y: y + 1, z: z - 12 }, cityLoot());

  const spawnSpots = [
    { x: x - 8, z: z - 8 },
    { x: x + 7, z: z + 7 },
  ];
  for (const s of spawnSpots) {
    run(`setblock ${s.x} ${y + 1} ${s.z} hollowveil:wraithguard_spawner`);
    spawnerPositions.push({ x: s.x, y: y + 1, z: s.z, mob: "hollowveil:city_wraithguard" });
  }
  // a marrow crawler nest in the ruin's undercroft
  run(`setblock ${x} ${y + 1} ${z + 10} hollowveil:crawler_spawner`);
  spawnerPositions.push({ x: x, y: y + 1, z: z + 10, mob: "hollowveil:marrow_crawler" });
}

function fillContainer(dim, pos, items) {
  try {
    const block = dim.getBlock(pos);
    const inv = block?.getComponent("minecraft:inventory");
    if (!inv?.container) return;
    let slot = 0;
    for (const stack of items) {
      inv.container.setItem(slot, stack);
      slot++;
    }
  } catch {
    /* structure still stands even if the chest ends up empty */
  }
}

function bastionLoot() {
  return [
    new ItemStack("hollowveil:sentinel_core", 2),
    new ItemStack("hollowveil:ember_coal", 8),
    new ItemStack("hollowveil:veilsteel_scrap", 3),
    new ItemStack("hollowveil:ember_dust", 6),
  ];
}

function cityLoot() {
  const picks = [
    new ItemStack("hollowveil:veilsteel_plating", 2),
    new ItemStack("hollowveil:veilsteel_scrap", 4),
    new ItemStack("hollowveil:spectral_dust", 5),
  ];
  if (Math.random() < 0.15) picks.push(new ItemStack("hollowveil:dragon_egg", 1));
  if (Math.random() < 0.1) picks.push(new ItemStack("hollowveil:hollowforged_scrap", 1));
  return picks;
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
