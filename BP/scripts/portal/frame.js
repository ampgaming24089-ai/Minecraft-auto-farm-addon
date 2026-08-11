/**
 * Portal frame detection - pure geometry, no engine imports.
 *
 * This lives apart from portal.js for one reason: it can be unit-tested.
 * The igniter shipped broken twice, and the second time the cause was here,
 * not in the event wiring: frame detection demanded gold blocks at the four
 * CORNERS. A nether portal frame has no corners - it is ten obsidian, not
 * fourteen - and the instructions say to build this one "the same as a nether
 * portal". So every correctly-built frame was rejected and the igniter did
 * nothing at all, with no message explaining why.
 *
 * tools/test_portal.js drives this file against a stub world, including a
 * corner-less frame built exactly the way the game teaches you to build a
 * nether portal. validate.py runs that test on every build.
 *
 * `world` here is any object with { isAir(pos), isFrame(pos) }.
 */

export const FRAME_BLOCK = "minecraft:gold_block";

export const MIN_WIDTH = 2;
export const MAX_WIDTH = 21;
export const MIN_HEIGHT = 3;
export const MAX_HEIGHT = 21;

/** Ordered worst-to-best: a later reason tells the player more than an
 * earlier one, so when every candidate fails we report the most specific. */
export const REASONS = ["no_air", "not_rectangular", "too_small", "too_large", "not_enclosed", "frame_gaps"];

function rank(reason) {
  const i = REASONS.indexOf(reason);
  return i < 0 ? -1 : i;
}

/**
 * Flood-fills the air pocket containing `seed` within the vertical plane
 * whose perpendicular horizontal axis is fixed, then checks that the pocket
 * is a rectangle enclosed by frame blocks.
 *
 * `axis` is the horizontal axis the portal runs along ("x" or "z").
 */
export function findFrame(world, seed, axis) {
  const fixedAxis = axis === "x" ? "z" : "x";
  const fixedVal = seed[fixedAxis];

  if (!world.isAir(seed)) return { ok: false, reason: "no_air" };

  const visited = new Set();
  const queue = [seed];
  const cells = [];
  const MAX_CELLS = MAX_WIDTH * MAX_HEIGHT;

  while (queue.length) {
    const cur = queue.pop();
    const key = `${cur[axis]},${cur.y}`;
    if (visited.has(key)) continue;
    visited.add(key);
    if (!world.isAir(cur)) continue;
    cells.push(cur);
    // Running past the largest legal portal means the air is not enclosed at
    // all - there is a gap in the ring and the fill is escaping into the
    // world. Distinct from a portal that is simply too big, and far more
    // likely to be what the player actually did wrong.
    if (cells.length > MAX_CELLS) return { ok: false, reason: "not_enclosed" };

    for (const n of [
      { ...cur, [axis]: cur[axis] + 1 },
      { ...cur, [axis]: cur[axis] - 1 },
      { ...cur, y: cur.y + 1 },
      { ...cur, y: cur.y - 1 },
    ]) {
      if (!visited.has(`${n[axis]},${n.y}`)) queue.push(n);
    }
  }

  if (cells.length === 0) return { ok: false, reason: "no_air" };

  let minA = Infinity, maxA = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const c of cells) {
    minA = Math.min(minA, c[axis]);
    maxA = Math.max(maxA, c[axis]);
    minY = Math.min(minY, c.y);
    maxY = Math.max(maxY, c.y);
  }
  const width = maxA - minA + 1;
  const height = maxY - minY + 1;

  if (cells.length !== width * height) return { ok: false, reason: "not_rectangular" };
  if (width > MAX_WIDTH || height > MAX_HEIGHT) {
    return { ok: false, reason: "too_large", width, height };
  }
  if (width < MIN_WIDTH || height < MIN_HEIGHT) {
    return { ok: false, reason: "too_small", width, height };
  }

  // Sides are full columns. Top and bottom run the interior width only -
  // the corners are deliberately NOT required, which is what makes a
  // nether-portal-shaped frame (10 blocks, not 14) light correctly.
  let gaps = 0;
  const at = (a, y) => ({ [axis]: a, y, [fixedAxis]: fixedVal });
  for (let a = minA; a <= maxA; a++) {
    if (!world.isFrame(at(a, maxY + 1))) gaps++;
    if (!world.isFrame(at(a, minY - 1))) gaps++;
  }
  for (let y = minY; y <= maxY; y++) {
    if (!world.isFrame(at(minA - 1, y))) gaps++;
    if (!world.isFrame(at(maxA + 1, y))) gaps++;
  }
  if (gaps > 0) return { ok: false, reason: "frame_gaps", gaps, width, height };

  return { ok: true, frame: { axis, fixedAxis, fixedVal, minA, maxA, minY, maxY, width, height } };
}

/**
 * Tries every seed against both orientations and returns the first frame
 * found, or the most informative failure if there is none.
 */
export function findAnyFrame(world, seeds) {
  let best = { ok: false, reason: "no_air" };
  for (const seed of seeds) {
    for (const axis of ["x", "z"]) {
      const result = findFrame(world, seed, axis);
      if (result.ok) return result;
      if (rank(result.reason) > rank(best.reason)) best = result;
    }
  }
  return best;
}

/**
 * Candidate seed positions for a click on `pos`, most likely first.
 *
 * `face` is the clicked face when the engine reports one ("Up", "North", ...).
 * The block on that side is where a flint and steel would put its fire, so it
 * is the best guess at the portal interior - a player lighting a portal
 * clicks the frame from inside the doorway or stands on the bottom row and
 * clicks upward. The six neighbours follow as a fallback, which also covers
 * clicking the frame from outside.
 */
export function seedsForClick(pos, face) {
  const offsets = {
    Up: { x: 0, y: 1, z: 0 },
    Down: { x: 0, y: -1, z: 0 },
    North: { x: 0, y: 0, z: -1 },
    South: { x: 0, y: 0, z: 1 },
    West: { x: -1, y: 0, z: 0 },
    East: { x: 1, y: 0, z: 0 },
  };
  const seeds = [];
  const push = (d) => {
    const p = { x: pos.x + d.x, y: pos.y + d.y, z: pos.z + d.z };
    if (!seeds.some((s) => s.x === p.x && s.y === p.y && s.z === p.z)) seeds.push(p);
  };
  const faceOffset = offsets[face];
  if (faceOffset) push(faceOffset);
  push({ x: 0, y: 1, z: 0 });
  push({ x: 0, y: 0, z: 0 });
  for (const d of Object.values(offsets)) push(d);
  return seeds;
}

/** Player-facing explanation for a failed ignition. Silence was the worst
 * part of the old behaviour: the item simply did nothing, every time. */
export function explainFailure(result) {
  switch (result.reason) {
    case "frame_gaps":
      return `§7The frame is incomplete - ${result.gaps} gold block${result.gaps === 1 ? "" : "s"} missing from the ring.`;
    case "not_enclosed":
      return "§7The frame isn't sealed - the space inside leaks out through a gap in the ring.";
    case "not_rectangular":
      return "§7The opening is not a clean rectangle - fill in the notches.";
    case "too_small":
      return `§7The opening is only ${result.width}x${result.height} - the veil needs at least ${MIN_WIDTH} wide and ${MIN_HEIGHT} tall.`;
    case "too_large":
      return `§7That opening is too large - keep it within ${MAX_WIDTH}x${MAX_HEIGHT}.`;
    default:
      return "§7Nothing here to ignite - strike a gold-block frame with an empty space inside it.";
  }
}
