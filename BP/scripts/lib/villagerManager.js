import { BlockPermutation } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";

/**
 * Villager Manager Wand
 * ======================
 * A companion tool for the Librarian Trading Hall (and any other villager).
 * Right-click a villager while holding it to:
 *
 *  - Reroll trades: finds the nearest lectern within 8 blocks, breaks it,
 *    and places an identical one back. This is the real, verified vanilla
 *    mechanic for re-rolling a villager's enchanted-book offer — but it
 *    ONLY affects trades the villager hasn't sold yet. Once you've made a
 *    first trade with a villager, its whole trade list locks permanently;
 *    rerolling after that does nothing (harmless, just a no-op).
 *  - Replace villager: removes the targeted villager and spawns a fresh,
 *    unemployed one in its place, so it can claim a job site from scratch.
 *    Use this on a villager you've already traded with and don't want.
 *
 * What this can't do, and why: Script API has no documented way to read a
 * villager's currently-offered trades before you commit to one, so there's
 * no way to script "check if the offer is Mending, auto-keep or
 * auto-reroll" — you still have to open the trade screen yourself and look.
 * This wand just makes acting on what you see nearly instant.
 */

const TOOL_ID = "autofarm:villager_wand";
const LECTERN_SEARCH_RADIUS = 8;

function findNearestLectern(dimension, location) {
  let nearest = null;
  let nearestDist = Infinity;
  for (let dx = -LECTERN_SEARCH_RADIUS; dx <= LECTERN_SEARCH_RADIUS; dx++) {
    for (let dy = -2; dy <= 2; dy++) {
      for (let dz = -LECTERN_SEARCH_RADIUS; dz <= LECTERN_SEARCH_RADIUS; dz++) {
        const pos = { x: Math.floor(location.x) + dx, y: Math.floor(location.y) + dy, z: Math.floor(location.z) + dz };
        let block;
        try {
          block = dimension.getBlock(pos);
        } catch {
          continue;
        }
        if (block?.typeId !== "minecraft:lectern") continue;
        const dist = dx * dx + dy * dy + dz * dz;
        if (dist < nearestDist) {
          nearestDist = dist;
          nearest = block;
        }
      }
    }
  }
  return nearest;
}

function rerollLectern(player, villager) {
  const block = findNearestLectern(villager.dimension, villager.location);
  if (!block) {
    player.sendMessage("§c[Villager Manager] No lectern found within 8 blocks of that villager.");
    return;
  }
  const permutation = block.permutation;
  block.setPermutation(BlockPermutation.resolve("minecraft:air"));
  block.setPermutation(permutation);
  player.sendMessage(
    "§a[Villager Manager] Lectern reset. If this villager hasn't traded with you yet, its book offer just re-rolled — open its trades to check."
  );
}

function replaceVillager(player, villager) {
  const location = villager.location;
  const dimension = villager.dimension;
  try {
    villager.remove();
  } catch {
    player.sendMessage("§c[Villager Manager] Couldn't remove that villager.");
    return;
  }
  dimension.spawnEntity("minecraft:villager", location);
  player.sendMessage("§a[Villager Manager] Replaced with a fresh, unemployed villager.");
}

export function registerVillagerManager(world) {
  world.afterEvents.playerInteractWithEntity.subscribe((event) => {
    const { player, target } = event;
    const held = player.getComponent("minecraft:inventory")?.container?.getItem(player.selectedSlotIndex);
    if (held?.typeId !== TOOL_ID) return;
    if (target.typeId !== "minecraft:villager") return;

    const form = new ActionFormData()
      .title("Villager Manager")
      .body("This villager's trades can only be inspected in-game — this tool just acts on what you decide.")
      .button("Reroll trades (break/replace lectern)")
      .button("Replace villager (fresh, unemployed)")
      .button("Cancel");

    form.show(player).then((response) => {
      if (response.canceled || response.selection === undefined || response.selection === 2) return;
      if (response.selection === 0) rerollLectern(player, target);
      else replaceVillager(player, target);
    });
  });
}
