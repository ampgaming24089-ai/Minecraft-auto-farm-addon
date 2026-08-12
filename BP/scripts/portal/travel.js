import { world, system } from "@minecraft/server";
import { HOLLOW_VEIL } from "../world/build.js";
import { sendPlayerToHollowVeil } from "./portal.js";
import { KEYS, getPlayerJson } from "../lib/state.js";

/**
 * A way into the dimension that cannot fail.
 *
 * The portal has been reported broken three times. Each round I found a real
 * bug, fixed it, and it still did not work on the device - which means the
 * remaining fault is in a layer I cannot see from here. What I can do is stop
 * making the only entrance depend on it.
 *
 * These paths share nothing with the igniter: no item component, no block
 * detection, no interaction event. `scriptEventReceive` is the engine handing
 * a chat command straight to the script, and it is as close to a guarantee as
 * this API offers.
 *
 *   /scriptevent hollowveil:travel   - go to the Hollow Veil
 *   /scriptevent hollowveil:home     - come back
 *   /scriptevent hollowveil:portal   - build AND light a portal where you stand
 *   /scriptevent hollowveil:check    - report whether the scripts are running
 *
 * The Field Guide has buttons for the first two, so nobody has to type
 * anything. If the guide opens, the scripts are alive; if the guide does not
 * open either, the whole script module failed to load and that is the thing
 * to report.
 */
export function registerTravelCommands() {
  system.afterEvents.scriptEventReceive.subscribe((ev) => {
    const player = ev.sourceEntity;
    if (!player || player.typeId !== "minecraft:player") return;

    switch (ev.id) {
      case "hollowveil:travel":
        travelToVeil(player);
        break;
      case "hollowveil:home":
        returnHome(player);
        break;
      case "hollowveil:portal":
        buildPortalHere(player);
        break;
      case "hollowveil:check":
        report(player);
        break;
      default:
        break;
    }
  });
}

/** Straight into the dimension, from anywhere. */
export function travelToVeil(player) {
  if (player.dimension.id === HOLLOW_VEIL) {
    player.sendMessage("§7You are already in the Hollow Veil.");
    return;
  }
  const here = player.location;
  player.sendMessage("§5Stepping through...");
  sendPlayerToHollowVeil(player, {
    x: Math.floor(here.x), y: Math.floor(here.y), z: Math.floor(here.z),
  });
}

/** Back to wherever you left from, or world spawn if there is no record. */
export function returnHome(player) {
  if (player.dimension.id !== HOLLOW_VEIL) {
    player.sendMessage("§7You are not in the Hollow Veil.");
    return;
  }
  const ret = getPlayerJson(player, KEYS.RETURN_POS, null);
  try {
    const dim = world.getDimension(ret?.dimension ?? "minecraft:overworld");
    player.teleport(ret?.pos ?? world.getDefaultSpawnLocation(), { dimension: dim });
    player.sendMessage("§7The veil releases you.");
  } catch {
    player.sendMessage("§cCouldn't find the way back - try /scriptevent hollowveil:home again.");
  }
}

/**
 * Builds a correct gold frame in front of the player and fills it with portal
 * blocks directly. No igniter, no frame detection, no interaction event -
 * this is the escape hatch for exactly the failure being reported.
 */
function buildPortalHere(player) {
  const dim = player.dimension;
  const loc = player.location;
  const x = Math.floor(loc.x);
  const y = Math.floor(loc.y);
  const z = Math.floor(loc.z) + 3;          // a few blocks ahead, not underfoot
  const run = (cmd) => {
    try {
      dim.runCommand(cmd);
    } catch {
      /* one failed fill should not abandon the rest of the frame */
    }
  };
  // A 4x5 nether-shaped frame running along x, corners left out like vanilla.
  run(`fill ${x - 1} ${y - 1} ${z} ${x + 2} ${y - 1} ${z} minecraft:gold_block`);
  run(`fill ${x - 1} ${y + 3} ${z} ${x + 2} ${y + 3} ${z} minecraft:gold_block`);
  run(`fill ${x - 2} ${y} ${z} ${x - 2} ${y + 2} ${z} minecraft:gold_block`);
  run(`fill ${x + 3} ${y} ${z} ${x + 3} ${y + 2} ${z} minecraft:gold_block`);
  run(`fill ${x - 1} ${y} ${z} ${x + 2} ${y + 2} ${z} hollowveil:veil_portal`);
  player.sendMessage("§5A portal opens in front of you. Walk into it.");
}

/** Proof of life, so "nothing happens" can be told apart from "the scripts
 * are not running at all". */
function report(player) {
  const inVeil = player.dimension.id === HOLLOW_VEIL;
  player.sendMessage("§aHollow Veil scripts are running.");
  player.sendMessage(`§7Dimension: ${player.dimension.id}${inVeil ? " §a(you are in the Veil)" : ""}`);
  player.sendMessage("§7/scriptevent hollowveil:travel §8- go to the Veil");
  player.sendMessage("§7/scriptevent hollowveil:portal §8- build a working portal here");
  player.sendMessage("§7/scriptevent hollowveil:home §8- return");
}
