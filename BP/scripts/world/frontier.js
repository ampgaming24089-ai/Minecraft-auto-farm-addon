/**
 * Which sectors to build next, as pure arithmetic.
 *
 * Extracted from world/terrain.js for the same reason portal/frame.js was
 * extracted from the portal: the bug that mattered was a policy bug - the
 * build radius was smaller than the distance a player can see - and policy
 * with no engine imports can be run and measured in Node. tools/test_terrain.js
 * sprints a simulated player across the world and asserts nothing inside view
 * distance is ever missing. That test fails on the old radius.
 */

export const SECTOR = 32;

/** Bedrock's render distance runs to 96 blocks on the lowest setting and past
 * 250 on a good device. The build radius has to clear the high end, or the
 * generation frontier is something you can stand and look at. */
export const VIEW_BLOCKS = 256;

export const BUILD_RADIUS = 10;   // sectors: 320 blocks, clear of VIEW_BLOCKS
export const LOOKAHEAD = 5;       // sectors of bias toward where you are going

export function sectorOf(v) {
  return Math.floor(v / SECTOR);
}

/** Centre of a sector, in world coordinates. */
export function sectorCenter(sx, sz) {
  return { x: sx * SECTOR + SECTOR / 2, z: sz * SECTOR + SECTOR / 2 };
}

/**
 * The sectors worth considering this pass, nearest first.
 *
 * `heading` is a unit vector (or zeroes when standing still). Anything in
 * front of the player has up to LOOKAHEAD sectors subtracted from its sort
 * distance and anything behind has it added, so ground is laid down ahead of
 * someone running rather than catching up behind them.
 */
export function sectorCandidates(px, pz, heading, opts = {}) {
  const radius = opts.radius ?? BUILD_RADIUS;
  const lookahead = opts.lookahead ?? LOOKAHEAD;
  const worldRadius = opts.worldRadius ?? Infinity;
  const isBuilt = opts.isBuilt ?? (() => false);

  const psx = sectorOf(px);
  const psz = sectorOf(pz);
  const out = [];
  for (let dx = -radius; dx <= radius; dx++) {
    for (let dz = -radius; dz <= radius; dz++) {
      const sx = psx + dx;
      const sz = psz + dz;
      if (isBuilt(sx, sz)) continue;
      const c = sectorCenter(sx, sz);
      if (Math.hypot(c.x, c.z) > worldRadius + SECTOR) continue;
      const dist = Math.hypot(dx, dz);
      const ahead = dist > 0 ? (heading.x * dx + heading.z * dz) / dist : 0;
      out.push({ sx, sz, d: dist - ahead * lookahead });
    }
  }
  out.sort((a, b) => a.d - b.d);
  return out;
}

/** Unit heading from one position to the next, or zeroes if barely moved. */
export function headingFrom(prev, now) {
  if (!prev) return { x: 0, z: 0 };
  const dx = now.x - prev.x;
  const dz = now.z - prev.z;
  const len = Math.hypot(dx, dz);
  if (len < 0.05) return { x: 0, z: 0 };
  return { x: dx / len, z: dz / len };
}

/** Every sector any part of which lies within `blocks` of (px,pz). */
export function sectorsWithin(px, pz, blocks) {
  const out = [];
  const r = Math.ceil(blocks / SECTOR) + 1;
  const psx = sectorOf(px);
  const psz = sectorOf(pz);
  for (let dx = -r; dx <= r; dx++) {
    for (let dz = -r; dz <= r; dz++) {
      const sx = psx + dx;
      const sz = psz + dz;
      // nearest point of the sector box to the player
      const nx = Math.max(sx * SECTOR, Math.min(px, sx * SECTOR + SECTOR - 1));
      const nz = Math.max(sz * SECTOR, Math.min(pz, sz * SECTOR + SECTOR - 1));
      if (Math.hypot(nx - px, nz - pz) <= blocks) out.push({ sx, sz });
    }
  }
  return out;
}
