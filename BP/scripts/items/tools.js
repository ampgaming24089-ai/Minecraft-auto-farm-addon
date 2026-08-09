import { world, system } from "@minecraft/server";
import { openJournal } from "../ui/journal.js";
import { tryIgnitePortal } from "../portal/portal.js";
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

  world.afterEvents.itemUseOn.subscribe((ev) => {
    const { source, itemStack, block } = ev;
    if (!itemStack || !source) return;
    if (itemStack.typeId === "hollowveil:wraithfire_igniter" && block?.typeId === "hollowveil:soulforged_obsidian") {
      tryIgnitePortal(block.dimension, block.location, source);
    } else if (itemStack.typeId?.startsWith("hollowveil:sigil_") && block?.typeId === "hollowveil:ritual_altar") {
      const consumed = useSigilOnAltar(source, block.dimension, block.location, itemStack.typeId, system.currentTick);
      if (consumed) consumeOneItem(source, itemStack);
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
