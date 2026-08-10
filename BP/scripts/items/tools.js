import { world, system, ItemStack } from "@minecraft/server";
import { openJournal } from "../ui/journal.js";
import { tryIgnitePortal, FRAME_BLOCK } from "../portal/portal.js";
import { useSigilOnAltar } from "../bosses/chambers.js";
import { getWorldJson, KEYS } from "../lib/state.js";

export function registerItemHandlers() {
  world.afterEvents.itemUse.subscribe((ev) => {
    const { source, itemStack } = ev;
    if (itemStack.typeId === "hollowveil:journal") {
      openJournal(source);
    } else if (itemStack.typeId === "hollowveil:soul_compass") {
      pointToShrine(source);
    }
  });

  // NOTE: there is no `itemUseOn` event in @minecraft/server 2.x - the
  // right-click-a-block event is `playerInteractWithBlock` (verified against
  // the 2.8.0 bindings). Subscribing to the non-existent one threw on load
  // and took every subsystem registered after this one down with it, which
  // is why the igniter, sigils, dragon egg and shop all did nothing in-game.
  world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
    const { player, itemStack, block, isFirstEvent } = ev;
    if (!itemStack || !player || !block) return;
    if (isFirstEvent === false) return; // fires twice per interaction otherwise
    if (itemStack.typeId === "hollowveil:soulfire_igniter" && block.typeId === FRAME_BLOCK) {
      tryIgnitePortal(block.dimension, block.location, player);
    } else if (itemStack.typeId?.startsWith("hollowveil:sigil_") && block.typeId === "hollowveil:ritual_altar") {
      const consumed = useSigilOnAltar(player, block.dimension, block.location, itemStack.typeId, system.currentTick);
      if (consumed) consumeOneItem(player, itemStack);
    }
  });
}

function consumeOneItem(player, stack) {
  try {
    const inv = player.getComponent("minecraft:inventory")?.container;
    const equip = player.getComponent("minecraft:equippable");
    const held = equip?.getEquipment("Mainhand");
    if (held && held.typeId === stack.typeId) {
      if (held.amount <= 1) equip.setEquipment("Mainhand", undefined);
      else {
        held.amount -= 1;
        equip.setEquipment("Mainhand", held);
      }
      return;
    }
    // fall back to scanning the hotbar/inventory if it wasn't held in the main hand
    if (!inv) return;
    for (let i = 0; i < inv.size; i++) {
      const it = inv.getItem(i);
      if (it?.typeId === stack.typeId) {
        if (it.amount <= 1) inv.setItem(i, undefined);
        else {
          it.amount -= 1;
          inv.setItem(i, it);
        }
        return;
      }
    }
  } catch {
    /* if this fails the sigil just isn't consumed - not fatal */
  }
}

function pointToShrine(player) {
  const shrine = getWorldJson(KEYS.VILLAGE_SHRINE_POS, null);
  if (!shrine) {
    player.sendMessage("§7The compass needle spins - Hollow Hamlet hasn't been found yet.");
    return;
  }
  const dx = shrine.x - player.location.x;
  const dz = shrine.z - player.location.z;
  const dist = Math.round(Math.hypot(dx, dz));
  const dir = compassDirection(dx, dz);
  player.onScreenDisplay.setActionBar(`§5Hollow Hamlet: ${dist}m ${dir}`);
}

function compassDirection(dx, dz) {
  const angle = (Math.atan2(dx, -dz) * 180) / Math.PI;
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  const idx = Math.round(((angle % 360) + 360) % 360 / 45) % 8;
  return dirs[idx];
}

const LANTERN_INTERVAL = 20;

export function startPassiveItemEffects() {
  system.runInterval(() => {
    for (const player of world.getAllPlayers()) {
      applyLanternEffects(player);
    }
  }, LANTERN_INTERVAL);
}

function heldItems(player) {
  const equip = player.getComponent("minecraft:equippable");
  if (!equip) return [];
  try {
    return [equip.getEquipment("Mainhand"), equip.getEquipment("Offhand")].filter(Boolean);
  } catch {
    return [];
  }
}

function applyLanternEffects(player) {
  const items = heldItems(player);
  if (items.some((i) => i.typeId === "hollowveil:spirit_lantern")) {
    try {
      player.addEffect("night_vision", LANTERN_INTERVAL + 5, { amplifier: 0, showParticles: false });
    } catch {
      /* ignore */
    }
    const hidden = player.dimension.getEntities({ location: player.location, maxDistance: 10, type: "hollowveil:poltergeist" });
    for (const p of hidden) {
      try {
        p.addEffect("glowing", LANTERN_INTERVAL + 5, { amplifier: 0, showParticles: false });
      } catch {
        /* ignore */
      }
    }
  }
  if (items.some((i) => i.typeId === "hollowveil:featherfall_charm")) {
    try {
      player.addEffect("slow_falling", LANTERN_INTERVAL + 5, { amplifier: 0, showParticles: false });
    } catch {
      /* ignore */
    }
  }
}

export function hasGhostWard(player) {
  return heldItems(player).some((i) => i.typeId === "hollowveil:ghost_ward_charm");
}

// The stew's "give the bowl back" behaviour. It used to be a
// `using_converts_to` field on minecraft:food, but no vanilla item uses that
// field at a modern format_version - only legacy 1.10-format ones do - so
// rather than ship an unverified field (the exact class of guess that broke
// these food items in the first place) it's done here on the verified
// itemCompleteUse event instead.
const CONVERTS_TO = {
  "hollowveil:veil_marrow_stew": "minecraft:bowl",
};

export function registerFoodConversions() {
  world.afterEvents.itemCompleteUse.subscribe((ev) => {
    const give = CONVERTS_TO[ev.itemStack?.typeId];
    if (!give || !ev.source) return;
    try {
      const inv = ev.source.getComponent("minecraft:inventory")?.container;
      const leftover = inv?.addItem(new ItemStack(give, 1));
      if (leftover) ev.source.dimension.spawnItem(leftover, ev.source.location);
    } catch {
      /* inventory full and no room to drop; the bowl is simply lost */
    }
  });
}
