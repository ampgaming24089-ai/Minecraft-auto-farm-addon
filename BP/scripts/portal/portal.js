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
  let result;
  try {
    const view = probe(dimension);
    result = findAnyFrame(view, seedsForClick(clickedPos, blockFace));
    if (!result.ok) {
      if (looksLikeAnAttempt(view, clickedPos)) player?.sendMessage(explainFailure(result));
      return false;
    }
    if (!fillPortal(dimension, result.frame)) {
      player?.sendMessage("§cThe frame is right, but the blocks wouldn't take. Try again where the chunk is loaded.");
      return false;
    }
  } catch (err) {
    // Never fail silently again. Three rounds of "the tool does nothing" were
    // a TypeError thrown right here with nothing to show for it in-game.
    console.error(`[Hollow Veil] portal ignition failed: ${err}`);
    player?.sendMessage(`§cThe igniter faltered: §7${err}`);
    return false;
  }
  try {
    dimension.playSound("hollowveil.portal.ignite", clickedPos);
  } catch {
    /* cosmetic */
  }
  player?.sendMessage("§cThe veil splits — red light pours through...");
  return true;
}

/**
 * Places a box of blocks one block at a time.
 *
 * Deliberately NOT a command. This is the last step of lighting a portal, and
 * it is where every previous attempt died: it called
 * `dimension.runCommandAsync`, which does not exist in @minecraft/server 2.x,
 * so it threw `TypeError` after the frame had already been found. Nothing
 * about filling a doorway needs the command parser - `setBlockType` is a
 * direct native call, it is on the 2.9.0 Dimension bindings, and it cannot be
 * defeated by a command being disabled or a permission level.
 *
 * Returns how many blocks were actually placed, so the caller can tell a real
 * portal from a no-op in an unloaded chunk.
 */
export function setBox(dimension, from, to, typeId) {
  let placed = 0;
  for (let x = Math.min(from.x, to.x); x <= Math.max(from.x, to.x); x++) {
    for (let y = Math.min(from.y, to.y); y <= Math.max(from.y, to.y); y++) {
      for (let z = Math.min(from.z, to.z); z <= Math.max(from.z, to.z); z++) {
        try {
          dimension.setBlockType({ x, y, z }, typeId);
          placed += 1;
        } catch {
          // unloaded chunk or outside the build height - skip this one block
        }
      }
    }
  }
  return placed;
}

function fillPortal(dimension, frame) {
  const { axis, fixedVal, minA, maxA, minY, maxY } = frame;
  const from = axis === "x" ? { x: minA, y: minY, z: fixedVal } : { x: fixedVal, y: minY, z: minA };
  const to = axis === "x" ? { x: maxA, y: maxY, z: fixedVal } : { x: fixedVal, y: maxY, z: maxA };
  return setBox(dimension, from, to, PORTAL_BLOCK) > 0;
}

function buildReturnPortalFrame(dim) {
  if (getWorldFlag(RETURN_PORTAL_BUILT_FLAG)) return;
  setWorldFlag(RETURN_PORTAL_BUILT_FLAG, true);
  const { x, y, z } = ARRIVAL_POS;
  // a pre-built, pre-lit return portal frame (4 wide x 5 tall, facing +x) at
  // the edge of Hollow Hamlet
  const zf = z + 2;
  setBox(dim, { x: x - 1, y, z: zf }, { x: x + 2, y, z: zf }, FRAME_BLOCK);
  setBox(dim, { x: x - 1, y: y + 4, z: zf }, { x: x + 2, y: y + 4, z: zf }, FRAME_BLOCK);
  setBox(dim, { x: x - 1, y: y + 1, z: zf }, { x: x - 1, y: y + 3, z: zf }, FRAME_BLOCK);
  setBox(dim, { x: x + 2, y: y + 1, z: zf }, { x: x + 2, y: y + 3, z: zf }, FRAME_BLOCK);
  setBox(dim, { x, y: y + 1, z: zf }, { x: x + 1, y: y + 3, z: zf }, PORTAL_BLOCK);
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

/**
 * Where to actually put someone who has just crossed over.
 *
 * The old code teleported to a hard-coded y and trusted it. On any world whose
 * hub build had failed, the terrain streamer had since filled that spot with
 * solid ground, and players arrived encased in rock with a stone ceiling -
 * which is exactly what the owner photographed. Now the arrival column is
 * cleared and the standing height is read off the world rather than assumed.
 */
function safeArrival(dim) {
  const { x, z } = ARRIVAL_POS;
  // Guarantee a pocket to stand in no matter what is there now.
  setBox(dim, { x: x - 1, y: ARRIVAL_POS.y + 1, z: z - 1 },
              { x: x + 1, y: ARRIVAL_POS.y + 4, z: z + 1 }, "minecraft:air");
  let y = ARRIVAL_POS.y;
  try {
    const top = dim.getTopmostBlock({ x, z }, ARRIVAL_POS.y + 40);
    if (top && !top.isAir) y = top.location.y;
  } catch {
    /* fall back to the hub's surface height */
  }
  // Something solid underfoot, so a gap in the floor cannot drop them.
  setBox(dim, { x: x - 1, y, z: z - 1 }, { x: x + 1, y, z: z + 1 }, "hollowveil:bonestone");
  return { x: x + 0.5, y: y + 1, z: z + 0.5 };
}

export async function sendPlayerToHollowVeil(player, pos) {
  setPlayerJson(player, KEYS.RETURN_POS, { dimension: player.dimension.id, pos: { x: pos.x, y: pos.y, z: pos.z } });
  crossingFade(player);
  player.sendMessage("§cYou step through into the Hollow Veil...");
  await ensureWorldBuilt();
  const dim = world.getDimension(HOLLOW_VEIL);
  buildReturnPortalFrame(dim);
  player.teleport(safeArrival(dim), { dimension: dim });
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
