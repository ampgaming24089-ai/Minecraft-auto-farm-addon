import { world, system } from "@minecraft/server";
import { HOLLOW_VEIL, isWithinIsland, regionAt } from "../world/build.js";

// A script-registered custom dimension has no generated biome, so the
// data-driven spawn_rules/*.json files (which gate on a biome tag) never
// fire naturally. This is the real spawning mechanism for the dimension;
// the spawn_rules files are kept as harmless, forward-compatible data in
// case a future engine version assigns custom dimensions a real biome.
// Tables are keyed per region (see world/build.js regionAt) so each
// quadrant actually feels distinct, not just re-painted ground.
const REGION_TABLES = {
  // One roster per biome (see world/biomes.js). Every biome has mobs that
  // are only common there, so which territory you are standing in is
  // readable from what is hunting you.
  hub: [
    { id: "hollowveil:soul_wisp", weight: 20 },
    { id: "hollowveil:wraith", weight: 6 },
  ],
  moors: [
    { id: "hollowveil:wraith", weight: 20 },
    { id: "hollowveil:banshee", weight: 14 },
    { id: "hollowveil:shade", weight: 12 },
    { id: "hollowveil:poltergeist", weight: 12 },
    { id: "hollowveil:fallen_knight", weight: 5 },
    { id: "hollowveil:soul_wisp", weight: 8 },
  ],
  ashlands: [
    { id: "hollowveil:hellhound", weight: 18 },
    { id: "hollowveil:imp", weight: 16 },
    { id: "hollowveil:ashen_whelp", weight: 14 },
    { id: "hollowveil:bastion_sentinel", weight: 6 },
  ],
  marsh: [
    { id: "hollowveil:bonehide_elk", weight: 18 },
    { id: "hollowveil:glimmershroom_toad", weight: 18 },
    { id: "hollowveil:marrow_crawler", weight: 14 },
    { id: "hollowveil:ashwing_bat", weight: 10 },
  ],
  ruins: [
    { id: "hollowveil:city_wraithguard", weight: 16 },
    { id: "hollowveil:ashwing_bat", weight: 14 },
    { id: "hollowveil:shade", weight: 12 },
    { id: "hollowveil:fallen_knight", weight: 8 },
  ],
};const NEARBY_CAP = 14;
const NEARBY_RADIUS = 32;
const MIN_SPAWN_DIST = 16;
const MAX_SPAWN_DIST = 28;
const VILLAGE_SAFE_RADIUS = 24;

function pickMob(region) {
  const table = REGION_TABLES[region] ?? REGION_TABLES.hub;
  const total = table.reduce((s, m) => s + m.weight, 0);
  let roll = Math.random() * total;
  for (const m of table) {
    roll -= m.weight;
    if (roll <= 0) return m.id;
  }
  return table[0].id;
}

export function startMobSpawner() {
  system.runInterval(() => {
    let dim;
    try {
      dim = world.getDimension(HOLLOW_VEIL);
    } catch {
      return;
    }
    const players = dim.getPlayers();
    for (const player of players) {
      spawnNear(dim, player);
    }
  }, 100);
}

function spawnNear(dim, player) {
  const nearby = dim.getEntities({ location: player.location, maxDistance: NEARBY_RADIUS, families: ["hollow_veil"] });
  if (nearby.length >= NEARBY_CAP) return;

  const angle = Math.random() * Math.PI * 2;
  const dist = MIN_SPAWN_DIST + Math.random() * (MAX_SPAWN_DIST - MIN_SPAWN_DIST);
  const pos = {
    x: Math.round(player.location.x + Math.cos(angle) * dist),
    y: Math.round(player.location.y),
    z: Math.round(player.location.z + Math.sin(angle) * dist),
  };
  if (!isWithinIsland(pos)) return;
  if (Math.hypot(pos.x, pos.z) < VILLAGE_SAFE_RADIUS) return;

  const mobId = pickMob(regionAt(pos));
  try {
    dim.spawnEntity(mobId, pos);
  } catch {
    /* obstructed/unloaded spot - just skip this cycle */
  }
}
