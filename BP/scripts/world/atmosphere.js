import { world, system, BlockVolume } from "@minecraft/server";
import { HOLLOW_VEIL } from "./build.js";
import { biomeAt, BIOMES } from "./biomes.js";
import { setPlayerJson, getPlayerJson, KEYS } from "../lib/state.js";

// Per-biome atmosphere.
//
// A script-registered dimension gets no biome, so it also gets no biome fog
// - which is why the whole place looked identically flat before. The `/fog`
// command can push a fog definition onto a player directly, so the biome
// they are standing in is resolved in script and the matching fog swapped
// in as they cross a border. Each biome's fog is dark and close (see
// RP/fogs/), which is what actually sells the darkness, far more than
// removing light sources does.

const FOG_TAG = "hollowveil_biome"; // the /fog "user id" we own and reuse
const CHECK_INTERVAL = 40;

/**
 * Live portals breathe embers and a lazy smoke column.
 *
 * The old version guessed: it picked three random offsets in a 12x6x12 box
 * around each player and checked whether any of them happened to be a portal
 * block. A 3-block sample of an 864-block box almost never hits a 12-block
 * doorway, so in practice the effect never fired - which is exactly what the
 * owner reported ("portal is still and has no particle effects").
 *
 * `Dimension.getBlocks` takes a volume and a block filter and does the search
 * natively, so instead of guessing we ask for every portal block in range and
 * then emit off the real list. The search is the expensive half, so it runs
 * infrequently and the emission runs off the cached result.
 */
const PORTAL_BLOCK = "hollowveil:veil_portal";
const portalCache = new Map();     // player id -> {tick, blocks:[{x,y,z}]}
const SEARCH_INTERVAL = 60;
const SEARCH_RADIUS = 14;

function findPortals(player) {
  const cached = portalCache.get(player.id);
  if (cached && system.currentTick - cached.tick < SEARCH_INTERVAL) return cached.blocks;

  const o = player.location;
  const blocks = [];
  try {
    const volume = new BlockVolume(
      { x: Math.floor(o.x) - SEARCH_RADIUS, y: Math.floor(o.y) - 8, z: Math.floor(o.z) - SEARCH_RADIUS },
      { x: Math.floor(o.x) + SEARCH_RADIUS, y: Math.floor(o.y) + 12, z: Math.floor(o.z) + SEARCH_RADIUS },
    );
    const found = player.dimension.getBlocks(volume, { includeTypes: [PORTAL_BLOCK] }, false);
    for (const loc of found.getBlockLocationIterator()) {
      blocks.push({ x: loc.x, y: loc.y, z: loc.z });
      if (blocks.length >= 64) break;      // a 21x21 portal is plenty of emitters
    }
  } catch {
    // unloaded chunks, or the player moved out from under us - keep whatever
    // the last search found rather than blanking the effect
    return cached?.blocks ?? [];
  }
  portalCache.set(player.id, { tick: system.currentTick, blocks });
  return blocks;
}

function portalFx() {
  for (const player of world.getAllPlayers()) {
    let blocks;
    try {
      blocks = findPortals(player);
    } catch {
      continue;
    }
    if (!blocks.length) continue;
    const dim = player.dimension;
    // Emit from a rolling subset so a big portal is not spawning sixty
    // particles a tick, but every block still gets its turn.
    const start = system.currentTick % blocks.length;
    const n = Math.min(blocks.length, 6);
    for (let i = 0; i < n; i++) {
      const b = blocks[(start + i) % blocks.length];
      const at = { x: b.x + 0.5, y: b.y + 0.5, z: b.z + 0.5 };
      try {
        dim.spawnParticle("hollowveil:portal_particle", at);
        if ((system.currentTick + i) % 3 === 0) {
          dim.spawnParticle("hollowveil:portal_smoke", { x: at.x, y: at.y + 0.8, z: at.z });
        }
        if ((system.currentTick + i) % 7 === 0) {
          dim.spawnParticle("hollowveil:ember_particle", { x: at.x, y: at.y + 1.2, z: at.z });
        }
      } catch {
        /* unloaded chunk */
      }
    }
  }
}

export function startAtmosphere() {
  system.runInterval(portalFx, 4);
  system.runInterval(() => {
    for (const player of world.getAllPlayers()) {
      try {
        applyFor(player);
      } catch {
        /* player left mid-pass */
      }
    }
  }, CHECK_INTERVAL);

  // leaving the dimension has to clear our fog, or the Veil's murk follows
  // the player back into the overworld
  world.afterEvents.playerDimensionChange.subscribe((ev) => {
    if (ev.toDimension.id !== HOLLOW_VEIL) {
      popFog(ev.player);
      setPlayerJson(ev.player, KEYS.CURRENT_BIOME, null);
    }
  });
}

function applyFor(player) {
  if (player.dimension.id !== HOLLOW_VEIL) return;
  const biome = biomeAt(player.location.x, player.location.z);
  const last = getPlayerJson(player, KEYS.CURRENT_BIOME, null);
  if (last === biome.id) return;

  popFog(player);
  player.runCommand(`fog @s push hollowveil:fog_${biome.id} ${FOG_TAG}`);
  setPlayerJson(player, KEYS.CURRENT_BIOME, biome.id);

  // a quiet nudge that the territory changed - no spam, it only fires on a
  // real border crossing
  if (last !== null && BIOMES[biome.id]) {
    player.onScreenDisplay.setActionBar(`§7${BIOMES[biome.id].name}`);
  }
}

function popFog(player) {
  try {
    player.runCommand(`fog @s remove ${FOG_TAG}`);
  } catch {
    /* nothing pushed yet */
  }
}
