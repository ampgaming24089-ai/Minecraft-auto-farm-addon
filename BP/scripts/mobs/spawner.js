import { world, system } from "@minecraft/server";
import { HOLLOW_VEIL, isWithinIsland, regionAt } from "../world/build.js";

/**
 * Mob spawning for the Hollow Veil.
 *
 * A script-registered custom dimension has no generated biome, so the
 * data-driven spawn_rules/*.json files (which gate on a biome tag) never fire.
 * This is the real spawning mechanism; the spawn_rules files stay as harmless,
 * forward-compatible data in case a future engine version gives custom
 * dimensions a real biome.
 *
 * The rules below are vanilla's, not invented ones. The old version spawned
 * exactly one mob every five seconds at a fixed 16-28 blocks with no regard
 * for light or ground, which made the dimension feel simultaneously empty
 * (nothing in the distance) and artificial (a mob materialising beside you on
 * a clock). What vanilla actually does, and what this now mirrors:
 *
 *   - attempts are frequent and mostly fail, rather than rare and guaranteed
 *   - a successful attempt spawns a PACK of 1-4, not a single mob
 *   - hostiles need darkness; passives need light and open sky
 *   - nothing spawns within 24 blocks of a player, and nothing beyond 128
 *   - a spawn needs solid ground with two blocks of air above it
 *   - the population is capped by density, so a lit base stays clear while
 *     open country stays dangerous
 *
 * Vanilla numbers, for the record: hostile mobs spawn at block light 0 in
 * modern versions, packs are 1-4, the no-spawn radius is 24 blocks, the
 * despawn radius is 128, and the hostile cap is ~70 per player's simulation
 * area. Those are the constants used here.
 */

// --- vanilla spawn constants ----------------------------------------------
const TICKS_PER_CYCLE = 20;      // one spawn cycle a second, like vanilla's
const ATTEMPTS_PER_CYCLE = 12;   // most of these fail; that is the point
const MIN_SPAWN_DIST = 24;       // vanilla's no-spawn bubble around a player
const MAX_SPAWN_DIST = 96;       // inside the 128-block despawn radius
const PACK_SPREAD = 4;           // blocks between pack members
const HOSTILE_LIGHT_MAX = 7;     // torch-lit ground stops hostile spawns
const PASSIVE_LIGHT_MIN = 7;     // passives want a lit, open surface
const VILLAGE_SAFE_RADIUS = 32;  // Hollow Hamlet is a refuge

// Density caps, counted inside DENSITY_RADIUS of the player. Vanilla's
// hostile cap is ~70 across a whole simulation area; this is a tighter
// radius, so the numbers are scaled to match the same felt density.
const DENSITY_RADIUS = 96;
const HOSTILE_CAP = 22;
const PASSIVE_CAP = 10;
const TOTAL_CAP = 30;

/**
 * Per-biome rosters. `weight` is relative within the biome, `pack` is how
 * many spawn together, `kind` decides which light rule applies.
 *
 * Pack sizes follow what the mob is: lone stalkers come one at a time, herd
 * animals and vermin arrive in groups, and bosses are not in here at all.
 */
const HOSTILE = "hostile";
const PASSIVE = "passive";

const REGION_TABLES = {
  hub: [
    { id: "hollowveil:soul_wisp", weight: 20, pack: [1, 3], kind: PASSIVE },
    { id: "hollowveil:wraith", weight: 4, pack: [1, 1], kind: HOSTILE },
  ],
  moors: [
    { id: "hollowveil:wraith", weight: 20, pack: [1, 2], kind: HOSTILE },
    { id: "hollowveil:banshee", weight: 12, pack: [1, 1], kind: HOSTILE },
    { id: "hollowveil:shade", weight: 12, pack: [1, 2], kind: HOSTILE },
    { id: "hollowveil:poltergeist", weight: 10, pack: [1, 1], kind: HOSTILE },
    { id: "hollowveil:fallen_knight", weight: 5, pack: [1, 1], kind: HOSTILE },
    { id: "hollowveil:soul_wisp", weight: 10, pack: [2, 4], kind: PASSIVE },
  ],
  ashlands: [
    { id: "hollowveil:hellhound", weight: 18, pack: [2, 4], kind: HOSTILE },
    { id: "hollowveil:imp", weight: 16, pack: [2, 3], kind: HOSTILE },
    { id: "hollowveil:ashen_whelp", weight: 14, pack: [1, 3], kind: HOSTILE },
    { id: "hollowveil:bastion_sentinel", weight: 5, pack: [1, 1], kind: HOSTILE },
    // Wild adult dragons. Rare on purpose: finding one should be the moment
    // of the trip, not a routine encounter.
    { id: "hollowveil:veil_dragon", weight: 1, pack: [1, 1], kind: PASSIVE },
  ],
  marsh: [
    { id: "hollowveil:bonehide_elk", weight: 18, pack: [2, 4], kind: PASSIVE },
    { id: "hollowveil:glimmershroom_toad", weight: 16, pack: [1, 3], kind: PASSIVE },
    { id: "hollowveil:marrow_crawler", weight: 14, pack: [2, 4], kind: HOSTILE },
    { id: "hollowveil:ashwing_bat", weight: 10, pack: [2, 4], kind: PASSIVE },
  ],
  ruins: [
    { id: "hollowveil:city_wraithguard", weight: 16, pack: [1, 2], kind: HOSTILE },
    { id: "hollowveil:ashwing_bat", weight: 14, pack: [2, 4], kind: PASSIVE },
    { id: "hollowveil:shade", weight: 12, pack: [1, 2], kind: HOSTILE },
    { id: "hollowveil:fallen_knight", weight: 8, pack: [1, 2], kind: HOSTILE },
  ],
};

function pickEntry(region) {
  const table = REGION_TABLES[region] ?? REGION_TABLES.hub;
  const total = table.reduce((sum, m) => sum + m.weight, 0);
  let roll = Math.random() * total;
  for (const entry of table) {
    roll -= entry.weight;
    if (roll <= 0) return entry;
  }
  return table[0];
}

function randomInt(lo, hi) {
  return lo + Math.floor(Math.random() * (hi - lo + 1));
}

export function startMobSpawner() {
  system.runInterval(() => {
    let dim;
    try {
      dim = world.getDimension(HOLLOW_VEIL);
    } catch {
      return;                          // dimension not registered yet
    }
    for (const player of dim.getPlayers()) {
      runSpawnCycle(dim, player);
    }
  }, TICKS_PER_CYCLE);
}

function runSpawnCycle(dim, player) {
  const census = countNearby(dim, player);
  if (census.total >= TOTAL_CAP) return;

  for (let i = 0; i < ATTEMPTS_PER_CYCLE; i++) {
    const spot = randomSpawnSpot(dim, player);
    if (!spot) continue;

    const entry = pickEntry(regionAt(spot));
    const cap = entry.kind === HOSTILE ? HOSTILE_CAP : PASSIVE_CAP;
    if (census[entry.kind] >= cap) continue;
    if (!lightAllows(dim, spot, entry.kind)) continue;

    const packed = spawnPack(dim, spot, entry);
    census[entry.kind] += packed;
    census.total += packed;
    if (census.total >= TOTAL_CAP) return;
  }
}

/** How crowded it already is around this player, split by kind. */
function countNearby(dim, player) {
  const census = { [HOSTILE]: 0, [PASSIVE]: 0, total: 0 };
  let nearby;
  try {
    nearby = dim.getEntities({
      location: player.location,
      maxDistance: DENSITY_RADIUS,
      families: ["hollow_veil"],
    });
  } catch {
    return census;
  }
  for (const entity of nearby) {
    census.total++;
    // Vanilla's own "monster" family, which every hostile mob in this pack
    // now declares. Cheaper than a lookup table and impossible to drift out
    // of sync with the rosters above.
    let hostile = false;
    try {
      hostile = entity.matches({ families: ["monster"] });
    } catch {
      hostile = true;                  // unknown: count against the tighter cap
    }
    census[hostile ? HOSTILE : PASSIVE]++;
  }
  return census;
}

/**
 * A random point in the spawn annulus with solid ground and headroom.
 *
 * Returns the position a mob's feet would occupy, or null - and null is the
 * common case. Vanilla spawning is mostly failed attempts; that is what makes
 * mob density follow the terrain instead of a timer.
 */
function randomSpawnSpot(dim, player) {
  const angle = Math.random() * Math.PI * 2;
  const dist = MIN_SPAWN_DIST + Math.random() * (MAX_SPAWN_DIST - MIN_SPAWN_DIST);
  const x = Math.round(player.location.x + Math.cos(angle) * dist);
  const z = Math.round(player.location.z + Math.sin(angle) * dist);

  if (!isWithinIsland({ x, y: 0, z })) return null;
  if (Math.hypot(x, z) < VILLAGE_SAFE_RADIUS) return null;

  try {
    if (!dim.isChunkLoaded({ x, y: player.location.y, z })) return null;
    const ground = dim.getTopmostBlock({ x, z });
    if (!ground || ground.isLiquid) return null;

    const feet = { x, y: ground.y + 1, z };
    const head = { x, y: ground.y + 2, z };
    if (!dim.getBlock(feet)?.isAir) return null;
    if (!dim.getBlock(head)?.isAir) return null;
    // Never drop a mob directly on top of the player's head or into their lap
    // vertically - the horizontal distance check alone allows both.
    if (Math.abs(feet.y - player.location.y) > 24) return null;
    return feet;
  } catch {
    return null;                       // unloaded or outside the build height
  }
}

/** Vanilla's light rules: hostiles need the dark, passives need light. */
function lightAllows(dim, pos, kind) {
  let light;
  try {
    light = dim.getLightLevel(pos);
  } catch {
    return kind === HOSTILE;           // no reading available: assume gloom
  }
  return kind === HOSTILE ? light <= HOSTILE_LIGHT_MAX : light >= PASSIVE_LIGHT_MIN;
}

/**
 * Spawns a pack around `origin`, returning how many actually appeared.
 *
 * Pack members are scattered rather than stacked, and each one re-checks its
 * own footing, so a group arriving at the edge of a cliff spills along the
 * ridge instead of half of it falling off.
 */
function spawnPack(dim, origin, entry) {
  const [lo, hi] = entry.pack ?? [1, 1];
  const wanted = randomInt(lo, hi);
  let spawned = 0;
  for (let i = 0; i < wanted; i++) {
    const pos = i === 0 ? origin : scatter(dim, origin);
    if (!pos) continue;
    try {
      dim.spawnEntity(entry.id, { x: pos.x + 0.5, y: pos.y, z: pos.z + 0.5 });
      spawned++;
    } catch {
      /* obstructed spot - the rest of the pack still arrives */
    }
  }
  return spawned;
}

function scatter(dim, origin) {
  const x = origin.x + randomInt(-PACK_SPREAD, PACK_SPREAD);
  const z = origin.z + randomInt(-PACK_SPREAD, PACK_SPREAD);
  try {
    const ground = dim.getTopmostBlock({ x, z });
    if (!ground || ground.isLiquid) return null;
    const feet = { x, y: ground.y + 1, z };
    if (!dim.getBlock(feet)?.isAir) return null;
    return feet;
  } catch {
    return null;
  }
}
