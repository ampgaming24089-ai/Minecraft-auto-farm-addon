import { world, system } from "@minecraft/server";
import { KEYS, getWorldFlag, setWorldFlag, getPlayerJson, setPlayerJson } from "../lib/state.js";
import { ensureWorldBuilt, HOLLOW_VEIL, ISLAND_CENTER } from "../world/build.js";

const FRAME_BLOCK = "hollowveil:soulforged_obsidian";
const PORTAL_BLOCK = "hollowveil:veil_portal";
const ARRIVAL_POS = { x: ISLAND_CENTER.x, y: ISLAND_CENTER.y, z: ISLAND_CENTER.z + 20 };
const PORTAL_COOLDOWN_TICKS = 100; // 5s, long enough to clear the block
const RETURN_PORTAL_BUILT_FLAG = "hollowveil:return_portal_built";

function isFrameBlock(dimension, pos) {
  try {
    return dimension.getBlock(pos)?.typeId === FRAME_BLOCK;
  } catch {
    return false;
  }
}

function isAir(dimension, pos) {
  try {
    const b = dimension.getBlock(pos);
    return !!b && b.isAir;
  } catch {
    return false;
  }
}

/** Flood-fills an air pocket along `axis` (+y), keeping the perpendicular
 * horizontal axis fixed, mirroring vanilla nether-portal frame detection:
 * a filled rectangle of air, 2-21 wide, 3-21 tall, fully bordered by frame
 * blocks on all four sides (front/back stay open). */
function tryOrientation(dimension, seed, axis) {
  const fixedAxis = axis === "x" ? "z" : "x";
  const fixedVal = seed[fixedAxis];
  const visited = new Set();
  const queue = [seed];
  const cells = [];
  const MAX_CELLS = 21 * 21;

  while (queue.length) {
    const cur = queue.pop();
    const key = `${cur[axis]},${cur.y}`;
    if (visited.has(key)) continue;
    visited.add(key);
    if (cur[fixedAxis] !== fixedVal) continue;
    if (!isAir(dimension, cur)) continue;
    cells.push(cur);
    if (cells.length > MAX_CELLS) return null;

    const neighbors = [
      { ...cur, [axis]: cur[axis] + 1 },
      { ...cur, [axis]: cur[axis] - 1 },
      { ...cur, y: cur.y + 1 },
      { ...cur, y: cur.y - 1 },
    ];
    for (const n of neighbors) {
      const k = `${n[axis]},${n.y}`;
      if (!visited.has(k)) queue.push(n);
    }
  }

  if (cells.length === 0) return null;
  let minA = Infinity, maxA = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const c of cells) {
    minA = Math.min(minA, c[axis]);
    maxA = Math.max(maxA, c[axis]);
    minY = Math.min(minY, c.y);
    maxY = Math.max(maxY, c.y);
  }
  const width = maxA - minA + 1;
  const height = maxY - minY + 1;
  if (width < 2 || width > 21 || height < 3 || height > 21) return null;
  if (cells.length !== width * height) return null; // must be a solid rectangle, no notches

  for (let a = minA - 1; a <= maxA + 1; a++) {
    const top = { [axis]: a, y: maxY + 1, [fixedAxis]: fixedVal };
    const bottom = { [axis]: a, y: minY - 1, [fixedAxis]: fixedVal };
    if (!isFrameBlock(dimension, top) || !isFrameBlock(dimension, bottom)) return null;
  }
  for (let y = minY; y <= maxY; y++) {
    const left = { [axis]: minA - 1, y, [fixedAxis]: fixedVal };
    const right = { [axis]: maxA + 1, y, [fixedAxis]: fixedVal };
    if (!isFrameBlock(dimension, left) || !isFrameBlock(dimension, right)) return null;
  }

  return { axis, fixedAxis, fixedVal, minA, maxA, minY, maxY };
}

export function tryIgnitePortal(dimension, clickedPos, player) {
  const seedCandidates = [
    clickedPos,
    { ...clickedPos, y: clickedPos.y + 1 },
    { ...clickedPos, x: clickedPos.x + 1 },
    { ...clickedPos, x: clickedPos.x - 1 },
    { ...clickedPos, z: clickedPos.z + 1 },
    { ...clickedPos, z: clickedPos.z - 1 },
  ];
  for (const seed of seedCandidates) {
    if (!isAir(dimension, seed)) continue;
    for (const axis of ["x", "z"]) {
      const frame = tryOrientation(dimension, seed, axis);
      if (frame) {
        fillPortal(dimension, frame);
        dimension.playSound("hollowveil.portal.ignite", clickedPos);
        player?.sendMessage("§5The veil tears open before you...");
        return true;
      }
    }
  }
  return false;
}

function fillPortal(dimension, frame) {
  const { axis, fixedAxis, fixedVal, minA, maxA, minY, maxY } = frame;
  const from = axis === "x" ? { x: minA, y: minY, z: fixedVal } : { x: fixedVal, y: minY, z: minA };
  const to = axis === "x" ? { x: maxA, y: maxY, z: fixedVal } : { x: fixedVal, y: maxY, z: maxA };
  dimension.runCommandAsync(`fill ${from.x} ${from.y} ${from.z} ${to.x} ${to.y} ${to.z} ${PORTAL_BLOCK}`);
}

function buildReturnPortalFrame(dim) {
  if (getWorldFlag(RETURN_PORTAL_BUILT_FLAG)) return;
  setWorldFlag(RETURN_PORTAL_BUILT_FLAG, true);
  const { x, y, z } = ARRIVAL_POS;
  // a pre-built, pre-lit return portal frame (4 wide x 5 tall, facing +x) at
  // the edge of Hollow Hamlet
  dim.runCommandAsync(`fill ${x - 1} ${y} ${z + 2} ${x + 2} ${y} ${z + 2} ${FRAME_BLOCK}`);
  dim.runCommandAsync(`fill ${x - 1} ${y + 4} ${z + 2} ${x + 2} ${y + 4} ${z + 2} ${FRAME_BLOCK}`);
  dim.runCommandAsync(`fill ${x - 1} ${y + 1} ${z + 2} ${x - 1} ${y + 3} ${z + 2} ${FRAME_BLOCK}`);
  dim.runCommandAsync(`fill ${x + 2} ${y + 1} ${z + 2} ${x + 2} ${y + 3} ${z + 2} ${FRAME_BLOCK}`);
  dim.runCommandAsync(`fill ${x} ${y + 1} ${z + 2} ${x + 1} ${y + 3} ${z + 2} ${PORTAL_BLOCK}`);
}

async function sendPlayerToHollowVeil(player, pos) {
  setPlayerJson(player, KEYS.RETURN_POS, { dimension: player.dimension.id, pos: { x: pos.x, y: pos.y, z: pos.z } });
  player.sendMessage("§5You step through into the Hollow Veil...");
  await ensureWorldBuilt();
  const dim = world.getDimension(HOLLOW_VEIL);
  buildReturnPortalFrame(dim);
  player.teleport({ x: ARRIVAL_POS.x + 0.5, y: ARRIVAL_POS.y, z: ARRIVAL_POS.z + 0.5 }, { dimension: dim });
}

export function startPortalTicking() {
  system.runInterval(() => {
    for (const player of world.getAllPlayers()) {
      const cooldownUntil = getPlayerJson(player, KEYS.PORTAL_COOLDOWN, 0);
      if (system.currentTick < cooldownUntil) continue;
      const loc = player.location;
      const pos = { x: Math.floor(loc.x), y: Math.floor(loc.y), z: Math.floor(loc.z) };
      let block;
      try {
        block = player.dimension.getBlock(pos);
      } catch {
        continue;
      }
      if (block?.typeId !== PORTAL_BLOCK) continue;

      setPlayerJson(player, KEYS.PORTAL_COOLDOWN, system.currentTick + PORTAL_COOLDOWN_TICKS);
      if (player.dimension.id === HOLLOW_VEIL) {
        const ret = getPlayerJson(player, KEYS.RETURN_POS, null);
        const targetDim = world.getDimension(ret?.dimension ?? "minecraft:overworld");
        const dest = ret?.pos ?? world.getDefaultSpawnLocation();
        player.sendMessage("§7The veil releases you back to the world you know.");
        player.teleport(dest, { dimension: targetDim });
      } else {
        sendPlayerToHollowVeil(player, pos);
      }
    }
  }, 10);
}
