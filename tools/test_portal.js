/**
 * Regression tests for portal frame detection.
 *
 * "Portal tool doesn't light the gold blocks and create a portal" was reported
 * twice. The second time the cause was that detection required gold at the
 * four corners, so a frame built the way the game teaches you to build a
 * nether portal - ten blocks, corners left empty - was rejected outright.
 *
 * The first test below builds exactly that frame. It fails against the old
 * code and passes against the new, which is the only reason to trust the fix
 * without a device in hand.
 *
 *   node tools/test_portal.js
 *
 * validate.py runs this, so ./build_addon.sh will not package a pack whose
 * portal cannot be lit.
 */
import {
  findAnyFrame,
  seedsForClick,
  explainFailure,
  FRAME_BLOCK,
} from "../BP/scripts/portal/frame.js";

const GOLD = FRAME_BLOCK;

/** A tiny stub world: a map of "x,y,z" -> block id, everything else air. */
function makeWorld(blocks) {
  const key = (p) => `${p.x},${p.y},${p.z}`;
  return {
    blocks,
    isAir: (p) => !blocks.has(key(p)),
    isFrame: (p) => blocks.get(key(p)) === GOLD,
    set: (p, id) => blocks.set(key(p), id),
  };
}

/**
 * Builds a portal frame in the z=0 plane running along x.
 * `corners` mirrors how nether portals are actually built: false leaves the
 * four corner blocks out, which is the normal, correct shape.
 */
function buildFrame(interiorWidth, interiorHeight, { corners = false, omit = [] } = {}) {
  const blocks = new Map();
  const world = makeWorld(blocks);
  const x0 = 10, y0 = 64, z = 0;
  const place = (x, y) => {
    if (omit.some((o) => o.x === x && o.y === y)) return;
    world.set({ x, y, z }, GOLD);
  };
  for (let x = x0; x < x0 + interiorWidth; x++) {
    place(x, y0 - 1);                       // bottom row
    place(x, y0 + interiorHeight);          // top row
  }
  for (let y = y0; y < y0 + interiorHeight; y++) {
    place(x0 - 1, y);                       // left column
    place(x0 + interiorWidth, y);           // right column
  }
  if (corners) {
    place(x0 - 1, y0 - 1);
    place(x0 + interiorWidth, y0 - 1);
    place(x0 - 1, y0 + interiorHeight);
    place(x0 + interiorWidth, y0 + interiorHeight);
  }
  return {
    world,
    // The block a player actually hits: the bottom-left frame block, struck
    // on its top face, standing in the doorway.
    click: { pos: { x: x0, y: y0 - 1, z }, face: "Up" },
    bottomLeftInterior: { x: x0, y: y0, z },
  };
}

let failures = 0;
function check(name, condition, detail) {
  if (condition) {
    console.log(`  ok   ${name}`);
  } else {
    console.log(`  FAIL ${name}${detail ? ` - ${detail}` : ""}`);
    failures++;
  }
}

function ignite(built) {
  const seeds = seedsForClick(built.click.pos, built.click.face);
  return findAnyFrame(built.world, seeds);
}

console.log("portal frame detection");

// The reported bug: a nether-shaped frame with no corner blocks.
{
  const built = buildFrame(2, 3);
  const r = ignite(built);
  check("4x5 nether-shaped frame, no corners, lights", r.ok,
        r.ok ? "" : `${r.reason} (${explainFailure(r)})`);
  if (r.ok) {
    check("  detects the 2x3 interior",
          r.frame.width === 2 && r.frame.height === 3,
          `got ${r.frame.width}x${r.frame.height}`);
  }
}

// Corners present must keep working - plenty of players fill them in.
{
  const r = ignite(buildFrame(2, 3, { corners: true }));
  check("4x5 frame WITH corners still lights", r.ok, r.ok ? "" : r.reason);
}

// Larger frames, both orientations, and a click from inside the doorway.
{
  const r = ignite(buildFrame(4, 5));
  check("6x7 frame lights", r.ok, r.ok ? "" : r.reason);
}
{
  const built = buildFrame(3, 4);
  const seeds = seedsForClick(built.bottomLeftInterior, "Up");
  const r = findAnyFrame(built.world, seeds);
  check("clicking from inside the opening lights", r.ok, r.ok ? "" : r.reason);
}
{
  // Same frame rotated into the x=0 plane running along z.
  const blocks = new Map();
  const world = makeWorld(blocks);
  const z0 = 10, y0 = 64, x = 0;
  for (let z = z0; z < z0 + 2; z++) {
    world.set({ x, y: y0 - 1, z }, GOLD);
    world.set({ x, y: y0 + 3, z }, GOLD);
  }
  for (let y = y0; y < y0 + 3; y++) {
    world.set({ x, y, z: z0 - 1 }, GOLD);
    world.set({ x, y, z: z0 + 2 }, GOLD);
  }
  const r = findAnyFrame(world, seedsForClick({ x, y: y0 - 1, z: z0 }, "Up"));
  check("frame running along z lights", r.ok, r.ok ? "" : r.reason);
}

// Genuinely broken frames must still be refused, and must say why.
{
  const r = ignite(buildFrame(2, 3, { omit: [{ x: 11, y: 63 }] }));
  check("frame with a hole in the bottom is refused", !r.ok, r.ok ? "lit anyway" : "");
  check("  and the message points at the gap",
        !r.ok && /missing|gap/.test(explainFailure(r)), explainFailure(r));
}
{
  const r = ignite(buildFrame(2, 1));
  check("frame too short is refused", !r.ok, r.ok ? "lit anyway" : "");
}
{
  // No frame at all: a lone gold block in the open.
  const blocks = new Map();
  const world = makeWorld(blocks);
  world.set({ x: 0, y: 64, z: 0 }, GOLD);
  const r = findAnyFrame(world, seedsForClick({ x: 0, y: 64, z: 0 }, "Up"));
  check("bare gold block in the open is refused", !r.ok, r.ok ? "lit anyway" : "");
  check("  without scanning the whole world",
        !r.ok && r.reason !== "no_air", r.reason);
}

console.log(failures ? `\n${failures} portal test(s) failed` : "\nall portal tests passed");
process.exit(failures ? 1 : 0);
