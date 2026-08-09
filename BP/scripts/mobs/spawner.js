import { world, system } from "@minecraft/server";
import { HOLLOW_VEIL, isWithinIsland } from "../world/build.js";

// A script-registered custom dimension has no generated biome, so the
// data-driven spawn_rules/*.json files (which gate on a biome tag) never
// fire naturally. This is the real spawning mechanism for the dimension;
// the spawn_rules files are kept as harmless, forward-compatible data in
// case a future engine version assigns custom dimensions a real biome.
const MOB_TABLE = [
  { id: "hollowveil:wraith", weight: 18 },
  { id: "hollowveil:banshee", weight: 8 },
  { id: "hollowveil:poltergeist", weight: 12 },
  { id: "hollowveil:hellhound", weight: 10 },
  { id: "hollowveil:imp", weight: 12 },
  { id: "hollowveil:shade", weight: 10 },
  { id: "hollowveil:fallen_knight", weight: 3 },
  { id: "hollowveil:soul_wisp", weight: 16 },
];
const TOTAL_WEIGHT = MOB_TABLE.reduce((s, m) => s + m.weight, 0);
const NEARBY_CAP = 10;
const NEARBY_RADIUS = 32;
const MIN_SPAWN_DIST = 16;
const MAX_SPAWN_DIST = 28;
const VILLAGE_SAFE_RADIUS = 24;

function pickMob(rnd) {
  let roll = rnd() * TOTAL_WEIGHT;
  for (const m of MOB_TABLE) {
    roll -= m.weight;
    if (roll <= 0) return m.id;
  }
  return MOB_TABLE[0].id;
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

  const mobId = pickMob(Math.random);
  try {
    dim.spawnEntity(mobId, pos);
  } catch {
    /* obstructed/unloaded spot - just skip this cycle */
  }
}
