import { world, system } from "@minecraft/server";
import { KEYS, getWorldFlag, setWorldFlag, getPlayerJson, setPlayerJson } from "../lib/state.js";
import { ensureWorldBuilt, HOLLOW_VEIL, ISLAND_CENTER } from "../world/build.js";
import { FRAME_BLOCK, findAnyFrame, seedsForClick, explainFailure } from "./frame.js";

export { FRAME_BLOCK };
const PORTAL_BLOCK = "hollowveil:veil_portal";
const ARRIVAL_POS = { x: ISLAND_CENTER.x, y: ISLAND_CENTER.y, z: ISLAND_CENTER.z + 20 };
const PORTAL_COOLDOWN_TICKS = 100; // 5s, long enough to clear the block
const RETURN_PORTAL_BUILT_FLAG = "hollowveil:return_portal_built";

/** Adapts a live dimension to the plain { isAir, isFrame } interface that
 * frame.js (and tools/test_portal.js) work against. */
function probe(dimension) {
  const get = (pos) => {
    try {
      return dimension.getBlock(pos);
    } catch {
      return undefined;      // unloaded chunk or outside the build height
    }
  };
  return {
    isAir: (pos) => {
      const b = get(pos);
      return !!b && b.isAir;
    },
    isFrame: (pos) => get(pos)?.typeId === FRAME_BLOCK,
  };
}

const NEIGHBOUR_OFFSETS = [
  { x: 1, y: 0, z: 0 }, { x: -1, y: 0, z: 0 },
  { x: 0, y: 1, z: 0 }, { x: 0, y: -1, z: 0 },
  { x: 0, y: 0, z: 1 }, { x: 0, y: 0, z: -1 },
];

/** Was the player plausibly trying to light a portal here? Only then is a
 * "your frame is wrong" message wanted - otherwise every swing of the
 * igniter at a torch would scold them about gold blocks. */
function looksLikeAnAttempt(world, pos) {
  if (world.isFrame(pos)) return true;
  return NEIGHBOUR_OFFSETS.some((d) =>
    world.isFrame({ x: pos.x + d.x, y: pos.y + d.y, z: pos.z + d.z }));
}

/**
 * Lights a portal from a click on `clickedPos`.
 *
 * Returns true if a portal was lit. When the click was clearly aimed at a
 * gold frame and still failed, the player is told what is wrong with it -
 * the old version returned silently, so "the tool does nothing" was the
 * entire symptom and there was no way to tell a broken frame from a broken
 * addon.
 */
export function tryIgnitePortal(dimension, clickedPos, player, blockFace) {
  const view = probe(dimension);
  const result = findAnyFrame(view, seedsForClick(clickedPos, blockFace));
  if (!result.ok) {
    if (looksLikeAnAttempt(view, clickedPos)) player?.sendMessage(explainFailure(result));
    return false;
  }
  fillPortal(dimension, result.frame);
  try {
    dimension.playSound("hollowveil.portal.ignite", clickedPos);
  } catch {
    /* cosmetic */
  }
  player?.sendMessage("§cThe veil splits — red light pours through...");
  return true;
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

// A "custom transition" within what the stable Script API actually exposes:
// no 3D logo overlay or reskinned inventory screen is possible (see
// README's Known limitations), but a held black-then-violet camera fade
// timed around the teleport, paired with a themed title card, reads as a
// real cinematic beat instead of an instant cut.
function crossingFade(player) {
  try {
    player.camera.fade({
      fadeColor: { red: 0.10, green: 0.01, blue: 0.01 },
      fadeTime: { fadeInTime: 0.5, holdTime: 0.6, fadeOutTime: 1.1 },
    });
  } catch {
    /* purely cosmetic */
  }
}

function showCrossingTitle(player, title, subtitle) {
  try {
    player.onScreenDisplay.setTitle(title, {
      subtitle,
      fadeInDuration: 10,
      stayDuration: 40,
      fadeOutDuration: 20,
    });
  } catch {
    /* purely cosmetic */
  }
}

async function sendPlayerToHollowVeil(player, pos) {
  setPlayerJson(player, KEYS.RETURN_POS, { dimension: player.dimension.id, pos: { x: pos.x, y: pos.y, z: pos.z } });
  crossingFade(player);
  player.sendMessage("§cYou step through into the Hollow Veil...");
  await ensureWorldBuilt();
  const dim = world.getDimension(HOLLOW_VEIL);
  buildReturnPortalFrame(dim);
  player.teleport({ x: ARRIVAL_POS.x + 0.5, y: ARRIVAL_POS.y, z: ARRIVAL_POS.z + 0.5 }, { dimension: dim });
  showCrossingTitle(player, "§l§4THE HOLLOW VEIL", "§7A grey country stitched between worlds");
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
        crossingFade(player);
        player.sendMessage("§7The veil releases you back to the world you know.");
        player.teleport(dest, { dimension: targetDim });
        showCrossingTitle(player, "§l§7Back to the Living World", "");
      } else {
        sendPlayerToHollowVeil(player, pos);
      }
    }
  }, 10);
}
