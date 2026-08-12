// Does the terrain frontier outrun a player?
//
// The owner's report was "it's not an open world, it has an edge you can fall
// off of", with a screenshot of exactly that. The cause was policy, not a
// crash: the builder kept a radius of 3 sectors - 96 blocks - around each
// player, while Bedrock renders up to ~256, so the edge of the generated world
// was permanently inside what you could see.
//
// This simulates a player sprinting in a straight line and then turning, runs
// the real scheduling policy from BP/scripts/world/frontier.js against a
// budgeted builder, and asserts that no sector within view distance is ever
// missing. Run: node tools/test_terrain.js
//
// Verified to FAIL at radius 3 and lookahead 0 before the fix was applied.

import {
  SECTOR, VIEW_BLOCKS, BUILD_RADIUS, LOOKAHEAD,
  sectorCandidates, headingFrom, sectorsWithin,
} from "../BP/scripts/world/frontier.js";

let failures = 0;
function ok(label, cond, detail = "") {
  console.log(`  ${cond ? "ok  " : "FAIL"}   ${label}${detail ? ` - ${detail}` : ""}`);
  if (!cond) failures += 1;
}

// Measured by tools/bench_terrain.mjs against the real generator, decoration
// passes included: 208 native fills for an average sector, 473 for the worst
// sampled - a mountain sector, where the surface changes height almost every
// block so the rectangle merge has least to work with. The runtime budget is
// 900 writes per pass and a pass runs every 2 ticks.
const AVG_SECTOR_COST = 208;
const WORST_SECTOR_COST = 473;
const WRITE_BUDGET = 900;
const TICK_INTERVAL = 2;

const SPRINT_BPS = 5.6;      // Bedrock sprint speed, blocks per second
const TICKS_PER_SEC = 20;

/**
 * Runs the real policy over a simulated walk.
 * Returns the worst "how many sectors inside view distance were missing".
 */
function simulate({ radius, lookahead, path, sectorCost = AVG_SECTOR_COST }) {
  const built = new Set();
  const key = (sx, sz) => `${sx},${sz}`;
  let prev = null;
  let worstMissing = 0;
  let worstAt = null;
  let filledAtPass = null;      // first pass with nothing missing in view
  let pass = -1;

  for (const now of path) {
    pass += 1;
    const heading = headingFrom(prev, now);
    prev = now;

    let budget = WRITE_BUDGET;
    const candidates = sectorCandidates(now.x, now.z, heading, {
      radius, lookahead, isBuilt: (sx, sz) => built.has(key(sx, sz)),
    });
    for (const c of candidates) {
      if (budget <= 0) break;
      budget -= sectorCost;
      built.add(key(c.sx, c.sz));
    }

    // Everything the player can see must exist.
    let missing = 0;
    for (const s of sectorsWithin(now.x, now.z, VIEW_BLOCKS)) {
      if (!built.has(key(s.sx, s.sz))) missing += 1;
    }
    if (missing === 0 && filledAtPass === null) filledAtPass = pass;
    // Arriving in an ungenerated world and watching it fill for a few seconds
    // is inherent - the dimension has no engine generator and every block is
    // placed by script. What must never happen is a frontier that persists
    // once the world around you has caught up, which is the edge that was
    // photographed. So the worst case is measured from the moment the disc
    // first completes.
    if (filledAtPass !== null && missing > worstMissing) {
      worstMissing = missing;
      worstAt = now;
    }
  }
  const secondsToFill = filledAtPass === null
    ? Infinity
    : (filledAtPass * TICK_INTERVAL) / TICKS_PER_SEC;
  return { worstMissing, worstAt, secondsToFill };
}

/** A player who arrives, stands a moment, sprints east, then turns north. */
function walkPath(seconds) {
  const path = [];
  const passes = Math.floor((seconds * TICKS_PER_SEC) / TICK_INTERVAL);
  const perPass = (SPRINT_BPS * TICK_INTERVAL) / TICKS_PER_SEC;
  let x = 0;
  let z = 20;
  for (let i = 0; i < passes; i++) {
    if (i < 40) {
      // standing still just after arrival, letting the disc fill
    } else if (i < passes * 0.6) {
      x += perPass;
    } else {
      z += perPass;
    }
    path.push({ x, z });
  }
  return path;
}

console.log("terrain frontier");

const path = walkPath(180);

// 1. The shipped policy: once the world has caught up, a sprinting player
//    never outruns it again.
{
  const r = simulate({ radius: BUILD_RADIUS, lookahead: LOOKAHEAD, path });
  ok("a sprinting player never outruns the frontier", r.worstMissing === 0,
     r.worstMissing ? `${r.worstMissing} sector(s) missing at x=${r.worstAt.x.toFixed(0)} z=${r.worstAt.z.toFixed(0)}` : "");
  ok("the world around a new arrival fills quickly", r.secondsToFill <= 8,
     `${r.secondsToFill.toFixed(1)}s to fill view distance`);
}

// 2. Same policy, worst-case sector cost - the frontier must still hold when
//    every sector is as expensive as the most expensive one measured.
{
  const r = simulate({
    radius: BUILD_RADIUS, lookahead: LOOKAHEAD, path, sectorCost: WORST_SECTOR_COST,
  });
  ok("still holds when every sector costs the worst measured price", r.worstMissing === 0,
     r.worstMissing ? `${r.worstMissing} sector(s) missing` : "");
}

// 3. The check has to be able to fail, or it proves nothing. This is the old
//    shipped policy, and it is the bug the owner photographed: at radius 3 the
//    frontier never reaches view distance at all, so it never even completes.
{
  const r = simulate({ radius: 3, lookahead: 0, path });
  ok("the old radius-3 policy is caught by this test",
     r.secondsToFill === Infinity || r.worstMissing > 0,
     "never generated out to view distance at all");
}

// 4. The build radius must clear view distance by construction, not by luck.
ok("build radius clears render distance",
   BUILD_RADIUS * SECTOR > VIEW_BLOCKS,
   `${BUILD_RADIUS * SECTOR} blocks vs ${VIEW_BLOCKS}`);

console.log(failures ? `\n${failures} terrain test(s) failed` : "\nall terrain tests passed");
process.exit(failures ? 1 : 0);
