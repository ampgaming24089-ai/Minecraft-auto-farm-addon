/**
 * The waystone network.
 *
 * The End is wide and mostly empty, and once a player has found a grove, a
 * sanctum and a tower there is no reason to walk between them a second time.
 * Waystones close that loop: place one, attune it, and it joins a network any
 * player can travel between - but only to the stones they have personally
 * stood at, so the map still has to be earned once.
 *
 * Two pieces of state, both in dynamic properties so they survive a restart:
 *   world  voidbound.waystones   every attuned stone, as JSON
 *   player voidbound.ws_known    the keys that player has visited, as JSON
 *
 * The world list is capped, because dynamic property strings are not free and
 * a network of eighty stones is a menu nobody wants to read.
 */

import { system, world } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";
import { END_DIMENSION } from "../world/generator.js";

const BLOCK_ID = "voidbound:waystone";

const WORLD_KEY = "voidbound.waystones";
const PLAYER_KEY = "voidbound.ws_known";

/** Beyond this the menu stops being useful, so the oldest stone drops off. */
const MAX_STONES = 40;

/** Name parts, picked by hashing the coordinates - stable for a given spot. */
const FIRST = [
  "Pale", "Hollow", "Silent", "Drifting", "Broken", "Distant", "Quiet", "Amber",
  "Hushed", "Outer", "Sunken", "Riven", "Wandering", "Cold", "Last", "Deep",
];
const SECOND = [
  "Landing", "Vigil", "Threshold", "Marker", "Crossing", "Perch", "Waypoint",
  "Rest", "Anchor", "Cairn", "Step", "Gate", "Watch", "Reach", "Hold", "Post",
];

function keyOf(location) {
  return `${Math.floor(location.x)},${Math.floor(location.y)},${Math.floor(location.z)}`;
}

/** A small deterministic hash, so one spot always earns the same name. */
function hash(x, y, z) {
  let h = (x * 374761393 + y * 668265263 + z * 2246822519) >>> 0;
  h = ((h ^ (h >>> 13)) * 1274126177) >>> 0;
  return (h ^ (h >>> 16)) >>> 0;
}

function nameFor(location) {
  const h = hash(Math.floor(location.x), Math.floor(location.y), Math.floor(location.z));
  return `${FIRST[h % FIRST.length]} ${SECOND[(h >>> 8) % SECOND.length]}`;
}

function readJson(holder, key, fallback) {
  try {
    const raw = holder.getDynamicProperty(key);
    if (typeof raw !== "string" || raw.length === 0) return fallback;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : fallback;
  } catch {
    // Corrupt or absent: start over rather than break every later read.
    return fallback;
  }
}

function writeJson(holder, key, value) {
  try {
    holder.setDynamicProperty(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

function allStones() {
  return readJson(world, WORLD_KEY, []);
}

function saveStones(stones) {
  return writeJson(world, WORLD_KEY, stones);
}

function knownTo(player) {
  return readJson(player, PLAYER_KEY, []);
}

function register(location) {
  const stones = allStones();
  const key = keyOf(location);
  if (stones.some((stone) => stone.k === key)) return undefined;

  const stone = {
    k: key,
    x: Math.floor(location.x),
    y: Math.floor(location.y),
    z: Math.floor(location.z),
    n: nameFor(location),
  };
  stones.push(stone);
  // Oldest out first, so a long-lived world's network stays navigable.
  while (stones.length > MAX_STONES) stones.shift();
  saveStones(stones);
  return stone;
}

function unregister(location) {
  const key = keyOf(location);
  const stones = allStones();
  const kept = stones.filter((stone) => stone.k !== key);
  if (kept.length !== stones.length) saveStones(kept);
}

function learn(player, key) {
  const known = knownTo(player);
  if (known.includes(key)) return false;
  known.push(key);
  while (known.length > MAX_STONES) known.shift();
  writeJson(player, PLAYER_KEY, known);
  return true;
}

function spawnParticle(dimension, effect, location) {
  try {
    dimension.spawnParticle(effect, location);
  } catch {
    // Decoration only.
  }
}

/** A column of light, so an activation is visible from outside the menu. */
function beam(dimension, location, effect) {
  for (let height = 0; height <= 6; height++) {
    spawnParticle(dimension, effect, {
      x: location.x + 0.5,
      y: location.y + 1 + height,
      z: location.z + 0.5,
    });
  }
}

function travel(player, stone) {
  const dimension = player.dimension;
  beam(dimension, player.location, "voidbound:rift_burst");

  try {
    player.teleport(
      { x: stone.x + 0.5, y: stone.y + 1.05, z: stone.z + 0.5 },
      { dimension, keepVelocity: false }
    );
  } catch {
    try {
      player.onScreenDisplay.setActionBar("§cThat waystone will not answer.");
    } catch {
      // Nothing further to do.
    }
    return;
  }

  // Slow falling covers the one case the destination cannot: a stone that has
  // since been undermined, leaving the arrival point over open air.
  try {
    player.addEffect("slow_falling", 100, { amplifier: 0, showParticles: false });
    player.onScreenDisplay.setActionBar(`§b${stone.n}`);
  } catch {
    // Cosmetic.
  }
  beam(dimension, { x: stone.x, y: stone.y, z: stone.z }, "voidbound:rift_burst");
}

function openMenu(player, here) {
  const known = knownTo(player);
  const stones = allStones().filter((stone) => known.includes(stone.k) && stone.k !== here);

  if (stones.length === 0) {
    try {
      player.onScreenDisplay.setActionBar("§7Attuned. Find another waystone to travel between them.");
    } catch {
      // Cosmetic.
    }
    return;
  }

  const form = new ActionFormData()
    .title("Waystone Network")
    .body(`§7${stones.length} attuned ${stones.length === 1 ? "stone" : "stones"}`);
  for (const stone of stones) {
    form.button(`${stone.n}\n§8${stone.x}, ${stone.y}, ${stone.z}`);
  }

  // Roughly five seconds of retries, then give up rather than nag forever.
  const attempt = (remaining) => {
    form
      .show(player)
      .then((response) => {
        if (response.canceled) {
          // "Busy" means a screen is still up, not that the player declined.
          if (response.cancelationReason === "UserBusy" && remaining > 0 && player.isValid) {
            system.runTimeout(() => attempt(remaining - 1), 10);
          }
          return;
        }
        const stone = stones[response.selection ?? 0];
        if (stone) travel(player, stone);
      })
      .catch(() => {
        // The player left, or the world closed mid-prompt.
      });
  };
  attempt(10);
}

export function startWaystones() {
  world.afterEvents.playerPlaceBlock.subscribe((event) => {
    if (event.block?.typeId !== BLOCK_ID) return;
    const player = event.player;
    if (!player?.isValid) return;

    const stone = register(event.block.location);
    learn(player, keyOf(event.block.location));
    try {
      player.onScreenDisplay.setActionBar(
        stone ? `§bWaystone raised: ${stone.n}` : "§7This waystone is already attuned."
      );
    } catch {
      // Cosmetic.
    }
    beam(player.dimension, event.block.location, "voidbound:rift_burst");
  });

  world.afterEvents.playerBreakBlock.subscribe((event) => {
    if (event.brokenBlockPermutation?.type?.id !== BLOCK_ID) return;
    unregister(event.block.location);
  });

  world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
    if (event.block?.typeId !== BLOCK_ID) return;
    // Sneaking suppresses the block's own interaction, as it does for chests
    // and crafting tables, so a waystone can still be built against.
    if (event.player?.isSneaking) return;
    event.cancel = true;

    const player = event.player;
    if (!player?.isValid) return;
    const location = event.block.location;

    // Forms cannot open from inside a before-event, so hop out of it first.
    system.run(() => {
      if (!player.isValid) return;
      if (player.dimension.id !== END_DIMENSION) {
        try {
          player.onScreenDisplay.setActionBar("§8The network only reaches within the End.");
        } catch {
          // Cosmetic.
        }
        return;
      }
      const stone = register(location) ?? allStones().find((s) => s.k === keyOf(location));
      const fresh = learn(player, keyOf(location));
      if (fresh && stone) {
        try {
          player.onScreenDisplay.setActionBar(`§bAttuned to ${stone.n}`);
        } catch {
          // Cosmetic.
        }
        beam(player.dimension, location, "voidbound:rift_burst");
      }
      openMenu(player, keyOf(location));
    });
  });
}
