import { system } from "@minecraft/server";

/**
 * Manages the particle bounding-box preview shown to a player before they
 * confirm a build. One active outline per player at a time.
 * @type {Map<string, number>} playerId -> system.runInterval id
 */
const activeOutlines = new Map();

/**
 * Sample points along the 12 edges of an AABB, spaced ~1 block apart.
 * @param {Vec3} min
 * @param {Vec3} max
 */
function edgePoints(min, max) {
  const points = [];
  const xs = { lo: min.x, hi: max.x + 1 };
  const ys = { lo: min.y, hi: max.y + 1 };
  const zs = { lo: min.z, hi: max.z + 1 };

  const lerpEdge = (fixed1, fixed2, axis) => {
    const lo = axis === "x" ? xs.lo : axis === "y" ? ys.lo : zs.lo;
    const hi = axis === "x" ? xs.hi : axis === "y" ? ys.hi : zs.hi;
    const len = Math.max(1, Math.round(hi - lo));
    for (let i = 0; i <= len; i++) {
      const t = lo + i;
      if (axis === "x") points.push({ x: t, y: fixed1, z: fixed2 });
      else if (axis === "y") points.push({ x: fixed1, y: t, z: fixed2 });
      else points.push({ x: fixed1, y: fixed2, z: t });
    }
  };

  for (const y of [ys.lo, ys.hi]) {
    for (const z of [zs.lo, zs.hi]) lerpEdge(y, z, "x");
  }
  for (const x of [xs.lo, xs.hi]) {
    for (const z of [zs.lo, zs.hi]) lerpEdge(x, z, "y");
  }
  for (const x of [xs.lo, xs.hi]) {
    for (const y of [ys.lo, ys.hi]) lerpEdge(x, y, "z");
  }
  return points;
}

/**
 * Start (or replace) the outline preview for a player.
 * @param {import("@minecraft/server").Player} player
 * @param {Vec3} min
 * @param {Vec3} max
 * @param {string} [particleId]
 */
export function showOutline(player, min, max, particleId = "minecraft:villager_happy") {
  clearOutline(player);
  const points = edgePoints(min, max);
  const dimension = player.dimension;
  const id = system.runInterval(() => {
    for (const p of points) {
      try {
        dimension.spawnParticle(particleId, { x: p.x + 0.5, y: p.y, z: p.z + 0.5 });
      } catch {
        // Chunk not loaded / out of world bounds — ignore, preview is best-effort.
      }
    }
  }, 10);
  activeOutlines.set(player.id, id);
}

/**
 * Stop a player's active outline preview, if any.
 * @param {import("@minecraft/server").Player} player
 */
export function clearOutline(player) {
  const id = activeOutlines.get(player.id);
  if (id !== undefined) {
    system.clearRun(id);
    activeOutlines.delete(player.id);
  }
}
