import { world, system } from "@minecraft/server";
import { HOLLOW_VEIL } from "./build.js";
import { getWorldJson, KEYS } from "../lib/state.js";

const CHECK_INTERVAL_TICKS = 60; // 3s
const COOLDOWN_TICKS = 200; // ~10s per spawner
const ACTIVATE_RADIUS = 20;
const NEARBY_CAP = 4;

// Per-spawner cooldowns are kept in memory only (not persisted): worst case
// after a restart every spawner is immediately available again, which is a
// far smaller problem than trying to keep a growing dynamic-property map in
// sync with every fire.
const cooldowns = new Map();

export function startStructureSpawners() {
  system.runInterval(() => {
    const spawners = getWorldJson(KEYS.SPAWNER_POSITIONS, []);
    if (spawners.length === 0) return;
    let dim;
    try {
      dim = world.getDimension(HOLLOW_VEIL);
    } catch {
      return;
    }
    const players = dim.getPlayers();
    if (players.length === 0) return;

    const now = system.currentTick;
    for (const spawner of spawners) {
      const key = `${spawner.x},${spawner.y},${spawner.z}`;
      if ((cooldowns.get(key) ?? 0) > now) continue;
      const near = players.some((p) => distance(p.location, spawner) < ACTIVATE_RADIUS);
      if (!near) continue;

      const guardCount = dim.getEntities({ location: spawner, maxDistance: ACTIVATE_RADIUS, type: spawner.mob }).length;
      if (guardCount >= NEARBY_CAP) continue;

      try {
        dim.spawnEntity(spawner.mob, { x: spawner.x + 0.5, y: spawner.y, z: spawner.z + 0.5 });
        dim.spawnParticle("hollowveil:shade_teleport_particle", { x: spawner.x + 0.5, y: spawner.y + 1, z: spawner.z + 0.5 });
      } catch {
        /* obstructed spawn point - try again next cycle */
      }
      cooldowns.set(key, now + COOLDOWN_TICKS);
    }
  }, CHECK_INTERVAL_TICKS);
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}
