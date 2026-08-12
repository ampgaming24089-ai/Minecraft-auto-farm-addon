import { world, system, ItemStack } from "@minecraft/server";
import { HOLLOW_VEIL } from "./build.js";
import { BIOMES, BEDROCK_Y, WORLD_RADIUS, biomeAt, heightAt, featureRoll, isWithinWorld } from "./biomes.js";
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

const SITE_BUILD_RADIUS = 56;
const TICK_INTERVAL = 40;

// Landmarks are placed by a deterministic grid, not a stored list.
//
// A pre-rolled array of every site in the world worked at radius 512, but a
// radius-10000 world has ~340,000 candidate cells; persisting that list (or
// the set of built ones) would run to megabytes of dynamic property. Instead
// each SITE_CELL-sized cell hashes to "is there a site here, what type, and
// where in the cell", so a site's existence and position are recomputed
// identically every time from its coordinates alone, with zero storage.
//
// Whether a site is already built is answered by the world itself: building
// one stamps a marker block deep under its centre, so the check is a single
// block read rather than bookkeeping.
export const SITE_CELL = 176;
const SITE_CHANCE = 0.62;
const MARKER = "hollowveil:bonestone";

// which site types can appear in which biome
const BY_BIOME = {
  moors: ["graveyard", "graveyard", "mausoleum", "watchtower", "crypt",
          "ruin_arch", "gallows", "standing_stones"],
  ashlands: ["bastion", "ember_camp", "ember_camp", "watchtower", "forge",
             "standing_stones"],
  marsh: ["bone_nest", "bone_nest", "witch_hut", "ruin_arch", "drowned_shrine"],
  ruins: ["sunken_city", "ruin_arch", "ruin_arch", "watchtower", "crypt",
          "drowned_shrine", "gallows"],
  hub: [],
};

/** Human-readable name for a site type, for the compass and the guide. */
export const SITE_LABELS = {
  sunken_city: "a sunken city",
  ruin_arch: "a broken arch",
  watchtower: "a watchtower",
  crypt: "a crypt",
  bastion: "an ember bastion",
  graveyard: "a graveyard",
  shrine: "a roadside shrine",
  camp: "an abandoned camp",
  mushroom_ring: "a glimmershroom ring",
  obelisk: "an obelisk",
  gallows: "a crossroads gallows",
  standing_stones: "a ring of standing stones",
  forge: "an abandoned forge",
  drowned_shrine: "a drowned shrine",
  mausoleum: "a mausoleum",
  ember_camp: "an ember camp",
  bone_nest: "a bone nest",
  witch_hut: "a witch's hut",
};

/**
 * The nearest site to a position, searched outward through the cell grid.
 *
 * Pure maths on coordinates, like siteForCell itself - no world access and no
 * stored state - so the Soul Compass can answer "what is near me" instantly
 * anywhere in a 50,000-block world.
 */
export function nearestSite(x, z, maxRings = 3) {
  const cx = Math.floor(x / SITE_CELL);
  const cz = Math.floor(z / SITE_CELL);
  let best = null;
  for (let ring = 0; ring <= maxRings; ring++) {
    for (let dx = -ring; dx <= ring; dx++) {
      for (let dz = -ring; dz <= ring; dz++) {
        // Only the newly added shell each ring, not the whole square again.
        if (ring > 0 && Math.max(Math.abs(dx), Math.abs(dz)) !== ring) continue;
        const site = siteForCell(cx + dx, cz + dz);
        if (!site) continue;
        const dist = Math.hypot(site.x - x, site.z - z);
        if (!best || dist < best.dist) best = { ...site, dist };
      }
    }
    if (best) break;              // the nearest ring with anything in it wins
  }
  return best;
}

/** The site in this cell, or null. Pure function of the cell coordinates. */
export function siteForCell(cx, cz) {
  if (featureRoll(cx, cz, 401) > SITE_CHANCE) return null;
  const x = Math.round(cx * SITE_CELL + featureRoll(cx, cz, 403) * SITE_CELL);
  const z = Math.round(cz * SITE_CELL + featureRoll(cx, cz, 405) * SITE_CELL);
  if (!isWithinWorld({ x, z })) return null;
  if (Math.hypot(x, z) < 90) return null; // keep the hub clear
  const pool = BY_BIOME[biomeAt(x, z).id] || [];
  if (!pool.length) return null;
  const type = pool[Math.floor(featureRoll(cx, cz, 407) * pool.length) % pool.length];
  return { type, x, z };
}

function alreadyBuilt(dim, site) {
  try {
    return dim.getBlock({ x: site.x, y: BEDROCK_Y + 1, z: site.z })?.typeId === MARKER;
  } catch {
    return true; // unloaded - do not build blind
  }
}

function stampMarker(run, site) {
  run(`setblock ${site.x} ${BEDROCK_Y + 1} ${site.z} ${MARKER}`);
}

export function startSiteBuilding() {
  system.runInterval(() => {
    let dim;
    try {
      dim = world.getDimension(HOLLOW_VEIL);
    } catch {
      return;
    }
    for (const p of world.getAllPlayers()) {
      if (p.dimension.id !== HOLLOW_VEIL) continue;
      const pcx = Math.floor(p.location.x / SITE_CELL);
      const pcz = Math.floor(p.location.z / SITE_CELL);
      for (let dx = -1; dx <= 1; dx++) {
        for (let dz = -1; dz <= 1; dz++) {
          const site = siteForCell(pcx + dx, pcz + dz);
          if (!site) continue;
          if (Math.hypot(p.location.x - site.x, p.location.z - site.z) > SITE_BUILD_RADIUS) continue;
          if (alreadyBuilt(dim, site)) continue;
          try {
            buildSite(dim, site);
            p.sendMessage(`§8You come upon §7${LABEL[site.type] ?? site.type}§8...`);
          } catch {
            /* chunk not ready - retry next pass */
          }
          return; // one site per pass, keeps the command budget flat
        }
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
  stampMarker(run, site);
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
    case "gallows": return buildGallows(ctx);
    case "standing_stones": return buildStandingStones(ctx);
    case "forge": return buildForge(ctx);
    case "drowned_shrine": return buildDrownedShrine(ctx);
    default: return undefined;
  }
}

// --- the sites -----------------------------------------------------------

/** A crossroads gallows: three empty nooses and a lantern that never went out.
 * The smallest of the landmarks, and the most common thing to stumble on. */
function buildGallows({ run, x, y, z }) {
  run(`fill ${x - 3} ${y} ${z} ${x + 3} ${y} ${z} hollowveil:bonestone`);
  run(`fill ${x - 3} ${y + 1} ${z} ${x - 3} ${y + 5} ${z} hollowveil:ashwood_log`);
  run(`fill ${x + 3} ${y + 1} ${z} ${x + 3} ${y + 5} ${z} hollowveil:ashwood_log`);
  run(`fill ${x - 3} ${y + 5} ${z} ${x + 3} ${y + 5} ${z} hollowveil:ashwood_log`);
  for (const ox of [-2, 0, 2]) {
    run(`fill ${x + ox} ${y + 2} ${z} ${x + ox} ${y + 4} ${z} minecraft:chain`);
  }
  run(`setblock ${x} ${y + 1} ${z + 1} hollowveil:soul_lantern`);
  run(`fill ${x - 1} ${y + 1} ${z - 1} ${x + 1} ${y + 1} ${z - 1} minecraft:cobblestone_wall`);
}

/** A ring of monoliths around a lit altar stone. Visible from a long way off,
 * which is the point in country this open. */
function buildStandingStones({ run, dim, x, y, z }) {
  const r = 7;
  for (let i = 0; i < 8; i++) {
    const a = (Math.PI * 2 * i) / 8;
    const sx = Math.round(x + Math.cos(a) * r);
    const sz = Math.round(z + Math.sin(a) * r);
    const h = 4 + Math.floor(featureRoll(sx, sz, 211) * 4);
    run(`fill ${sx} ${y} ${sz} ${sx} ${y + h} ${sz} hollowveil:soulforged_obsidian`);
    if (i % 2 === 0) run(`setblock ${sx} ${y + h + 1} ${sz} hollowveil:soul_lantern`);
  }
  run(`fill ${x - 1} ${y} ${z - 1} ${x + 1} ${y} ${z + 1} hollowveil:bonestone`);
  run(`setblock ${x} ${y + 1} ${z} hollowveil:ritual_altar`);
}

/** An abandoned forge, still hot. The one place you can find Hollowforged
 * material above ground, so it is worth crossing the Ashlands for. */
function buildForge({ run, dim, x, y, z }) {
  const r = 5;
  run(`fill ${x - r} ${y} ${z - r} ${x + r} ${y} ${z + r} hollowveil:bastion_brick`);
  run(`fill ${x - r} ${y + 1} ${z - r} ${x + r} ${y + 4} ${z + r} hollowveil:bastion_brick hollow`);
  run(`fill ${x - r + 1} ${y + 1} ${z - r} ${x + r - 1} ${y + 3} ${z - r} air`);
  run(`fill ${x - 1} ${y + 1} ${z + 2} ${x + 1} ${y + 2} ${z + 3} minecraft:magma_block`);
  run(`setblock ${x} ${y + 1} ${z} minecraft:anvil`);
  run(`setblock ${x - 2} ${y + 1} ${z - 2} hollowveil:soul_lantern`);
  run(`setblock ${x + 2} ${y + 1} ${z - 2} hollowveil:soul_lantern`);
  run(`fill ${x - 3} ${y - 1} ${z + 3} ${x - 2} ${y - 1} ${z + 4} hollowveil:hollowforged_ore`);
  chest(dim, run, x + 2, y + 1, z + 2, [
    S("hollowveil:hollowforged_scrap", 2), S("hollowveil:ember_coal", 6),
    S("hollowveil:veilsteel_ingot", 2),
  ]);
  spawner(run, dim, x, y + 1, z - 3, "hollowveil:bastion_sentinel", "hollowveil:sentinel_spawner");
}

/** A shrine that went under when the marsh rose. Half-flooded, still lit. */
function buildDrownedShrine({ run, dim, x, y, z }) {
  const r = 6;
  run(`fill ${x - r} ${y - 2} ${z - r} ${x + r} ${y - 1} ${z + r} hollowveil:sunken_bricks`);
  run(`fill ${x - r + 1} ${y - 1} ${z - r + 1} ${x + r - 1} ${y} ${z + r - 1} minecraft:water`);
  for (const [ox, oz] of [[-4, -4], [4, -4], [-4, 4], [4, 4]]) {
    run(`fill ${x + ox} ${y} ${z + oz} ${x + ox} ${y + 4} ${z + oz} hollowveil:sunken_bricks`);
    run(`setblock ${x + ox} ${y + 5} ${z + oz} hollowveil:soul_lantern`);
  }
  run(`fill ${x - 1} ${y} ${z - 1} ${x + 1} ${y} ${z + 1} hollowveil:bonestone`);
  run(`setblock ${x} ${y + 1} ${z} hollowveil:ritual_altar`);
  chest(dim, run, x + 1, y + 1, z + 1, [
    S("hollowveil:toad_mucus", 4), S("hollowveil:glimmershroom_item", 3),
    S("hollowveil:spectral_dust", 4),
  ]);
}

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
