import { world, system, ItemStack } from "@minecraft/server";
import { HOLLOW_VEIL } from "./build.js";
import { BIOMES, WORLD_RADIUS, biomeAt, heightAt, featureRoll, isWithinWorld } from "./biomes.js";
import { KEYS, getWorldJson, setWorldJson } from "../lib/state.js";

// Landmarks.
//
// There used to be exactly two structures, at two hard-coded offsets, so
// every world was identical and there was nothing to find. Now a whole
// catalogue of sites is rolled out across the map at positions derived from
// the world layout, each one filtered to the biome it belongs in, and each
// built the first time a player gets near it. Because placement comes from
// featureRoll() rather than Math.random(), the site list is stable - you can
// leave and come back and the crypt is still where it was.

const SITE_BUILD_RADIUS = 48;
const TICK_INTERVAL = 40;

let sites = null;
let builtSites = null;

/** Rolls the world's site list once, then reuses it forever. */
export function getSites() {
  if (sites) return sites;
  const stored = getWorldJson(KEYS.SITES, null);
  if (stored) {
    sites = stored;
    return sites;
  }
  sites = rollSites();
  setWorldJson(KEYS.SITES, sites);
  return sites;
}

const CATALOGUE = [
  // type,             biomes,                     count
  { type: "graveyard", biomes: ["moors"], count: 34 },
  { type: "mausoleum", biomes: ["moors"], count: 16 },
  { type: "watchtower", biomes: ["moors", "ruins"], count: 22 },
  { type: "bastion", biomes: ["ashlands"], count: 14 },
  { type: "ember_camp", biomes: ["ashlands"], count: 22 },
  { type: "bone_nest", biomes: ["marsh"], count: 24 },
  { type: "witch_hut", biomes: ["marsh"], count: 14 },
  { type: "sunken_city", biomes: ["ruins"], count: 12 },
  { type: "ruin_arch", biomes: ["ruins"], count: 28 },
  { type: "crypt", biomes: ["moors", "ruins"], count: 20 },
];

function rollSites() {
  const out = [];
  let salt = 300;
  for (const entry of CATALOGUE) {
    let placed = 0;
    for (let attempt = 0; attempt < entry.count * 40 && placed < entry.count; attempt++) {
      salt++;
      const a = featureRoll(attempt * 13, salt, 5) * Math.PI * 2;
      // sqrt keeps sites evenly spread by area instead of clumping at the hub
      const d = 70 + Math.sqrt(featureRoll(salt, attempt * 7, 9)) * (WORLD_RADIUS - 110);
      const x = Math.round(Math.cos(a) * d);
      const z = Math.round(Math.sin(a) * d);
      if (!isWithinWorld({ x, z })) continue;
      if (!entry.biomes.includes(biomeAt(x, z).id)) continue;
      if (out.some((s) => Math.hypot(s.x - x, s.z - z) < 46)) continue;
      out.push({ type: entry.type, x, z });
      placed++;
    }
  }
  return out;
}

export function startSiteBuilding() {
  system.runInterval(() => {
    let dim;
    try {
      dim = world.getDimension(HOLLOW_VEIL);
    } catch {
      return;
    }
    if (!builtSites) builtSites = new Set(getWorldJson(KEYS.BUILT_SITES, []));
    const all = getSites();
    for (const p of world.getAllPlayers()) {
      if (p.dimension.id !== HOLLOW_VEIL) continue;
      for (const s of all) {
        const key = `${s.type}@${s.x},${s.z}`;
        if (builtSites.has(key)) continue;
        if (Math.hypot(p.location.x - s.x, p.location.z - s.z) > SITE_BUILD_RADIUS) continue;
        try {
          buildSite(dim, s);
          builtSites.add(key);
          setWorldJson(KEYS.BUILT_SITES, [...builtSites]);
          p.sendMessage(`§8You come upon §7${LABEL[s.type] ?? s.type}§8...`);
        } catch {
          /* chunk not ready - retry next pass */
        }
        return; // one site per pass, keeps the command budget flat
      }
    }
  }, TICK_INTERVAL);
}

const LABEL = {
  graveyard: "a field of graves",
  mausoleum: "a sealed mausoleum",
  watchtower: "a ruined watchtower",
  bastion: "an ember bastion",
  ember_camp: "a smouldering camp",
  bone_nest: "a nest of bones",
  witch_hut: "an abandoned hut",
  sunken_city: "a drowned city",
  ruin_arch: "a broken arch",
  crypt: "a crypt entrance",
};

function buildSite(dim, site) {
  const run = (cmd) => dim.runCommandAsync(cmd);
  const y = heightAt(site.x, site.z);
  const ctx = { dim, run, x: site.x, y, z: site.z };
  switch (site.type) {
    case "graveyard": return buildGraveyard(ctx);
    case "mausoleum": return buildMausoleum(ctx);
    case "watchtower": return buildWatchtower(ctx);
    case "bastion": return buildBastion(ctx);
    case "ember_camp": return buildEmberCamp(ctx);
    case "bone_nest": return buildBoneNest(ctx);
    case "witch_hut": return buildWitchHut(ctx);
    case "sunken_city": return buildSunkenCity(ctx);
    case "ruin_arch": return buildRuinArch(ctx);
    case "crypt": return buildCrypt(ctx);
    default: return undefined;
  }
}

// --- the sites -----------------------------------------------------------

function buildGraveyard({ run, dim, x, y, z }) {
  const r = 9;
  run(`fill ${x - r} ${y} ${z - r} ${x + r} ${y} ${z + r} minecraft:podzol`);
  // iron fence around the plot
  run(`fill ${x - r} ${y + 1} ${z - r} ${x + r} ${y + 1} ${z - r} minecraft:iron_bars`);
  run(`fill ${x - r} ${y + 1} ${z + r} ${x + r} ${y + 1} ${z + r} minecraft:iron_bars`);
  run(`fill ${x - r} ${y + 1} ${z - r} ${x - r} ${y + 1} ${z + r} minecraft:iron_bars`);
  run(`fill ${x + r} ${y + 1} ${z - r} ${x + r} ${y + 1} ${z + r} minecraft:iron_bars`);
  run(`fill ${x - 1} ${y + 1} ${z - r} ${x + 1} ${y + 1} ${z - r} air`); // gate
  // rows of headstones
  for (let gx = -6; gx <= 6; gx += 3) {
    for (let gz = -6; gz <= 6; gz += 4) {
      run(`setblock ${x + gx} ${y + 1} ${z + gz} minecraft:cobblestone_wall`);
      run(`setblock ${x + gx} ${y + 2} ${z + gz} minecraft:stone_brick_slab`);
      run(`fill ${x + gx - 1} ${y} ${z + gz + 1} ${x + gx + 1} ${y} ${z + gz + 1} minecraft:coarse_dirt`);
    }
  }
  run(`setblock ${x} ${y + 1} ${z} hollowveil:soul_lantern`);
  spawner(run, dim, x + 5, y + 1, z + 5, "hollowveil:wraith", "hollowveil:wraith_spawner");
  chest(dim, run, x - 5, y + 1, z - 5, graveLoot());
}

function buildMausoleum({ run, dim, x, y, z }) {
  const r = 5;
  run(`fill ${x - r} ${y} ${z - r} ${x + r} ${y + 6} ${z + r} minecraft:deepslate_bricks hollow`);
  run(`fill ${x - r + 1} ${y + 1} ${z - r + 1} ${x + r - 1} ${y + 5} ${z + r - 1} air`);
  run(`fill ${x - 1} ${y + 1} ${z - r} ${x + 1} ${y + 3} ${z - r} air`); // doorway
  run(`fill ${x - 2} ${y + 1} ${z + 1} ${x + 2} ${y + 1} ${z + 2} minecraft:polished_deepslate`);
  run(`setblock ${x} ${y + 2} ${z + 2} hollowveil:soul_lantern`);
  chest(dim, run, x, y + 2, z + 1, cryptLoot());
  spawner(run, dim, x - 3, y + 1, z + 3, "hollowveil:banshee", "hollowveil:wraith_spawner");
}

function buildWatchtower({ run, dim, x, y, z }) {
  const h = 14;
  run(`fill ${x - 3} ${y} ${z - 3} ${x + 3} ${y + h} ${z + 3} hollowveil:sunken_bricks hollow`);
  run(`fill ${x - 2} ${y + 1} ${z - 2} ${x + 2} ${y + h - 1} ${z + 2} air`);
  run(`fill ${x - 1} ${y + 1} ${z - 3} ${x + 1} ${y + 2} ${z - 3} air`);
  for (let ly = 3; ly < h; ly += 4) {
    run(`fill ${x - 2} ${y + ly} ${z - 2} ${x + 2} ${y + ly} ${z + 2} minecraft:deepslate_tile_slab`);
    run(`setblock ${x} ${y + ly} ${z} air`);
    run(`setblock ${x + 2} ${y + ly + 1} ${z + 2} hollowveil:soul_lantern`);
  }
  run(`fill ${x - 3} ${y + h} ${z - 3} ${x + 3} ${y + h} ${z + 3} air`);
  chest(dim, run, x + 1, y + h - 2, z + 1, towerLoot());
  spawner(run, dim, x - 1, y + 1, z + 1, "hollowveil:fallen_knight", "hollowveil:wraith_spawner");
}

function buildBastion({ run, dim, x, y, z }) {
  const w = 12;
  run(`fill ${x - w} ${y} ${z - w} ${x + w} ${y} ${z + w} hollowveil:bastion_brick`);
  run(`fill ${x - w} ${y + 1} ${z - w} ${x + w} ${y + 7} ${z + w} hollowveil:bastion_brick hollow`);
  run(`fill ${x - w + 1} ${y + 1} ${z - w + 1} ${x + w - 1} ${y + 7} ${z + w - 1} air`);
  run(`fill ${x - 2} ${y + 1} ${z - w} ${x + 2} ${y + 4} ${z - w} air`);
  for (const [ox, oz] of [[-w, -w], [w, -w], [-w, w], [w, w]]) {
    run(`fill ${x + ox - 1} ${y} ${z + oz - 1} ${x + ox + 1} ${y + 11} ${z + oz + 1} hollowveil:bastion_brick`);
    run(`setblock ${x + ox} ${y + 12} ${z + oz} hollowveil:soul_lantern`);
  }
  run(`fill ${x - 2} ${y} ${z - 2} ${x + 2} ${y} ${z + 2} minecraft:magma_block`);
  chest(dim, run, x, y + 1, z, bastionLoot());
  spawner(run, dim, x - 6, y + 1, z - 6, "hollowveil:bastion_sentinel", "hollowveil:sentinel_spawner");
  spawner(run, dim, x + 6, y + 1, z + 6, "hollowveil:bastion_sentinel", "hollowveil:sentinel_spawner");
}

function buildEmberCamp({ run, dim, x, y, z }) {
  run(`fill ${x - 4} ${y} ${z - 4} ${x + 4} ${y} ${z + 4} minecraft:blackstone`);
  run(`fill ${x - 1} ${y} ${z - 1} ${x + 1} ${y} ${z + 1} minecraft:magma_block`);
  run(`setblock ${x} ${y + 1} ${z} minecraft:campfire`);
  for (const [ox, oz] of [[-4, -4], [4, 4], [-4, 4]]) {
    run(`fill ${x + ox} ${y + 1} ${z + oz} ${x + ox} ${y + 3} ${z + oz} minecraft:polished_blackstone_wall`);
  }
  chest(dim, run, x + 2, y + 1, z - 2, emberLoot());
  spawner(run, dim, x - 2, y + 1, z + 2, "hollowveil:hellhound", "hollowveil:hellhound_spawner");
}

function buildBoneNest({ run, dim, x, y, z }) {
  run(`fill ${x - 5} ${y} ${z - 5} ${x + 5} ${y} ${z + 5} hollowveil:veil_mud`);
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * Math.PI * 2;
    const bx = x + Math.round(Math.cos(a) * 4);
    const bz = z + Math.round(Math.sin(a) * 4);
    run(`fill ${bx} ${y + 1} ${bz} ${bx} ${y + 2 + (i % 3)} ${bz} minecraft:bone_block`);
  }
  run(`fill ${x - 1} ${y + 1} ${z - 1} ${x + 1} ${y + 1} ${z + 1} minecraft:bone_block`);
  chest(dim, run, x, y + 2, z, marshLoot());
  spawner(run, dim, x + 3, y + 1, z, "hollowveil:marrow_crawler", "hollowveil:crawler_spawner");
}

function buildWitchHut({ run, dim, x, y, z }) {
  run(`fill ${x - 4} ${y} ${z - 4} ${x + 4} ${y} ${z + 4} hollowveil:ashwood_planks`);
  run(`fill ${x - 4} ${y + 1} ${z - 4} ${x + 4} ${y + 4} ${z + 4} hollowveil:ashwood_planks hollow`);
  run(`fill ${x - 3} ${y + 1} ${z - 3} ${x + 3} ${y + 3} ${z + 3} air`);
  run(`fill ${x - 1} ${y + 1} ${z - 4} ${x} ${y + 2} ${z - 4} air`);
  run(`setblock ${x + 2} ${y + 1} ${z + 2} minecraft:cauldron`);
  run(`setblock ${x - 2} ${y + 1} ${z + 2} hollowveil:soul_lantern`);
  chest(dim, run, x + 2, y + 1, z - 2, marshLoot());
}

function buildSunkenCity({ run, dim, x, y, z }) {
  const towers = [
    { ox: -10, oz: -10, h: 12 }, { ox: 10, oz: -8, h: 17 }, { ox: -8, oz: 10, h: 9 },
    { ox: 9, oz: 9, h: 14 }, { ox: 0, oz: -14, h: 20 }, { ox: -14, oz: 2, h: 11 },
  ];
  run(`fill ${x - 18} ${y} ${z - 18} ${x + 18} ${y} ${z + 18} hollowveil:sunken_bricks`);
  for (const t of towers) {
    const tx = x + t.ox;
    const tz = z + t.oz;
    run(`fill ${tx - 2} ${y} ${tz - 2} ${tx + 2} ${y + t.h} ${tz + 2} hollowveil:sunken_bricks hollow`);
    run(`fill ${tx - 1} ${y + 1} ${tz - 1} ${tx + 1} ${y + t.h - 1} ${tz + 1} air`);
    run(`setblock ${tx} ${y + t.h + 1} ${tz} hollowveil:soul_lantern`);
  }
  chest(dim, run, x, y + 1, z - 14, cityLoot());
  spawner(run, dim, x - 10, y + 1, z - 10, "hollowveil:city_wraithguard", "hollowveil:wraithguard_spawner");
  spawner(run, dim, x + 9, y + 1, z + 9, "hollowveil:city_wraithguard", "hollowveil:wraithguard_spawner");
}

function buildRuinArch({ run, x, y, z }) {
  run(`fill ${x - 4} ${y + 1} ${z} ${x - 4} ${y + 6} ${z} hollowveil:sunken_bricks`);
  run(`fill ${x + 4} ${y + 1} ${z} ${x + 4} ${y + 6} ${z} hollowveil:sunken_bricks`);
  run(`fill ${x - 4} ${y + 7} ${z} ${x + 4} ${y + 7} ${z} hollowveil:sunken_bricks`);
  run(`setblock ${x} ${y + 6} ${z} hollowveil:soul_lantern`);
}

/** A stair down into a buried loot room - the one site type that rewards
 * actually going underground. */
function buildCrypt({ run, dim, x, y, z }) {
  run(`fill ${x - 2} ${y} ${z - 2} ${x + 2} ${y} ${z + 2} minecraft:deepslate_bricks`);
  run(`fill ${x - 1} ${y} ${z - 1} ${x + 1} ${y} ${z + 1} air`);
  for (let i = 1; i <= 6; i++) {
    run(`fill ${x - 1} ${y - i} ${z - 1} ${x + 1} ${y - i} ${z + 1} air`);
    run(`setblock ${x} ${y - i} ${z + 1} minecraft:deepslate_brick_stairs`);
  }
  const cy = y - 7;
  run(`fill ${x - 6} ${cy - 1} ${z - 6} ${x + 6} ${cy + 4} ${z + 6} minecraft:deepslate_bricks hollow`);
  run(`fill ${x - 5} ${cy} ${z - 5} ${x + 5} ${cy + 3} ${z + 5} air`);
  run(`fill ${x - 1} ${cy + 4} ${z - 1} ${x + 1} ${cy + 4} ${z + 1} air`); // shaft joins the room
  run(`setblock ${x - 4} ${cy + 2} ${z - 4} hollowveil:soul_lantern`);
  run(`setblock ${x + 4} ${cy + 2} ${z + 4} hollowveil:soul_lantern`);
  chest(dim, run, x, cy, z - 4, cryptLoot());
  chest(dim, run, x + 3, cy, z + 3, cryptLoot());
  spawner(run, dim, x - 3, cy, z + 3, "hollowveil:shade", "hollowveil:wraith_spawner");
}

// --- helpers -------------------------------------------------------------

function spawner(run, dim, x, y, z, mob, block) {
  run(`setblock ${x} ${y} ${z} ${block}`);
  const list = getWorldJson(KEYS.SPAWNER_POSITIONS, []);
  list.push({ x, y, z, mob });
  setWorldJson(KEYS.SPAWNER_POSITIONS, list);
}

async function chest(dim, run, x, y, z, items) {
  await run(`setblock ${x} ${y} ${z} minecraft:chest`);
  try {
    const inv = dim.getBlock({ x, y, z })?.getComponent("minecraft:inventory");
    if (!inv?.container) return;
    let slot = 0;
    for (const it of items) inv.container.setItem(slot++, it);
  } catch {
    /* chest fell out of a loaded chunk; it is still placed, just empty */
  }
}

const S = (id, n) => new ItemStack(id, n);

function graveLoot() {
  return [S("hollowveil:soul_shard", 4), S("hollowveil:spectral_dust", 3), S("minecraft:bone", 6)];
}
function cryptLoot() {
  const l = [S("hollowveil:spectral_dust", 5), S("hollowveil:wraithsteel_scrap", 3), S("hollowveil:soul_shard", 6)];
  l.push(S("hollowveil:veilsteel_scrap", 2));
  return l;
}
function towerLoot() {
  return [S("hollowveil:wraithsteel_ingot", 2), S("hollowveil:ember_coal", 6), S("hollowveil:soul_shard", 3)];
}
function bastionLoot() {
  return [S("hollowveil:sentinel_core", 2), S("hollowveil:ember_coal", 8), S("hollowveil:veilsteel_scrap", 3), S("hollowveil:ember_dust", 6)];
}
function emberLoot() {
  return [S("hollowveil:ember_dust", 5), S("hollowveil:ember_coal", 6), S("hollowveil:ember_fruit", 3)];
}
function marshLoot() {
  return [S("hollowveil:elk_hide", 3), S("hollowveil:chitin", 4), S("hollowveil:glimmershroom_item", 5)];
}
function cityLoot() {
  const l = [S("hollowveil:veilsteel_plating", 2), S("hollowveil:veilsteel_scrap", 4), S("hollowveil:spectral_dust", 5)];
  l.push(S("hollowveil:hollowforged_scrap", 1));
  l.push(S("hollowveil:dragon_egg", 1));
  return l;
}

export { BIOMES };
