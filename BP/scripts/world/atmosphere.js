import { world, system } from "@minecraft/server";
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

/** Live portals breathe red embers and a lazy smoke column. Bedrock has no
 * block-attached particle emitter for custom blocks, so the effect is driven
 * from script off the portal blocks near each player. */
function portalFx() {
  for (const player of world.getAllPlayers()) {
    const dim = player.dimension;
    const o = player.location;
    for (let i = 0; i < 3; i++) {
      const x = Math.floor(o.x) + Math.round((Math.random() - 0.5) * 12);
      const y = Math.floor(o.y) + Math.round((Math.random() - 0.5) * 6);
      const z = Math.floor(o.z) + Math.round((Math.random() - 0.5) * 12);
      let block;
      try {
        block = dim.getBlock({ x, y, z });
      } catch {
        continue;
      }
      if (block?.typeId !== "hollowveil:veil_portal") continue;
      const at = { x: x + 0.5, y: y + 0.5, z: z + 0.5 };
      try {
        dim.spawnParticle("hollowveil:portal_particle", at);
        if (Math.random() < 0.4) {
          dim.spawnParticle("hollowveil:portal_smoke", { x: at.x, y: at.y + 0.6, z: at.z });
        }
      } catch {
        /* unloaded chunk */
      }
    }
  }
}

export function startAtmosphere() {
  system.runInterval(portalFx, 12);
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
