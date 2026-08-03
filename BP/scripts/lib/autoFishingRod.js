import { system, ItemStack } from "@minecraft/server";

/**
 * Auto Fishing Rod
 * ================
 * A deliberately SCRIPTED convenience item, not a recreation of real
 * vanilla fishing. Checked, not assumed: Bedrock's fishing_hook/bobber
 * cycle requires real player input to cast and reel, and there is no
 * stable @minecraft/server event that exposes "bobber hooked something,
 * awaiting reel-in" for a script to drive on its own — true unattended
 * auto-fishing isn't something the platform supports. So instead of faking
 * that specific mechanic, this rolls the SAME real odds as vanilla's actual
 * fishing loot table (85% fish / 10% junk / 5% treasure, the documented
 * vanilla split) on a timer, while you're standing near open water holding
 * it — an honest scripted stand-in, not a claim that it's "real" fishing.
 *
 * Right-click (item use) toggles it on/off for that player. While on, it
 * waits a randomized 5-30s (matching an unenchanted rod's real bobber
 * timing window) between catches, same as actually fishing, rather than
 * spamming instant loot.
 */

const TOOL_ID = "autofarm:auto_fishing_rod";

/** @type {Map<string, boolean>} playerId -> whether the loop is currently running */
const activeFishers = new Map();

const FISH_TABLE = [
  { itemId: "minecraft:cod", weight: 60 },
  { itemId: "minecraft:salmon", weight: 25 },
  { itemId: "minecraft:tropical_fish", weight: 13 },
  { itemId: "minecraft:pufferfish", weight: 2 },
];

// Approximate junk/treasure pools (the 85/10/5 top-level split is the
// verified real vanilla ratio; these sub-lists are a representative subset
// rather than an exact reproduction of every sub-weight on the wiki).
const JUNK_TABLE = [
  { itemId: "minecraft:leather", weight: 20 },
  { itemId: "minecraft:bone", weight: 20 },
  { itemId: "minecraft:string", weight: 20 },
  { itemId: "minecraft:bowl", weight: 15 },
  { itemId: "minecraft:stick", weight: 15 },
  { itemId: "minecraft:rotten_flesh", weight: 10 },
];

const TREASURE_TABLE = [
  { itemId: "minecraft:enchanted_book", weight: 25 },
  { itemId: "minecraft:name_tag", weight: 25 },
  { itemId: "minecraft:nautilus_shell", weight: 25 },
  { itemId: "minecraft:saddle", weight: 25 },
];

function weightedPick(table) {
  const total = table.reduce((sum, e) => sum + e.weight, 0);
  let roll = Math.random() * total;
  for (const entry of table) {
    roll -= entry.weight;
    if (roll <= 0) return entry.itemId;
  }
  return table[table.length - 1].itemId;
}

function rollCatch() {
  const roll = Math.random() * 100;
  if (roll < 85) return weightedPick(FISH_TABLE);
  if (roll < 95) return weightedPick(JUNK_TABLE);
  return weightedPick(TREASURE_TABLE);
}

/** A generous water check: any water block within 2 blocks of the player's feet. */
function isNearWater(player) {
  const loc = player.location;
  const dimension = player.dimension;
  for (let dx = -2; dx <= 2; dx++) {
    for (let dz = -2; dz <= 2; dz++) {
      try {
        const b = dimension.getBlock({ x: Math.floor(loc.x) + dx, y: Math.floor(loc.y) - 1, z: Math.floor(loc.z) + dz });
        if (b && b.typeId === "minecraft:water") return true;
      } catch {
        // Unloaded chunk edge — treat as "not water" and keep checking others.
      }
    }
  }
  return false;
}

function scheduleNextCatch(player) {
  if (!activeFishers.get(player.id)) return;
  const delayTicks = 100 + Math.floor(Math.random() * 500); // 5-30s

  system.runTimeout(() => {
    if (!activeFishers.get(player.id)) return;
    let stillHolding = false;
    try {
      const held = player.getComponent("minecraft:inventory")?.container?.getItem(player.selectedSlotIndex);
      stillHolding = held?.typeId === TOOL_ID;
    } catch {
      stillHolding = false;
    }
    if (!stillHolding || !player.isValid) {
      activeFishers.delete(player.id);
      return;
    }

    if (isNearWater(player)) {
      const itemId = rollCatch();
      try {
        const inv = player.getComponent("minecraft:inventory").container;
        const stack = new ItemStack(itemId, 1);
        if (inv.emptySlotsCount > 0) {
          inv.addItem(stack);
        } else {
          player.dimension.spawnItem(stack, player.location);
        }
        player.dimension.spawnEntity("minecraft:xp_orb", player.location);
        player.playSound("random.splash", { location: player.location });
        player.sendMessage(`§b[Auto Fishing Rod] §fCaught: §a${itemId.replace("minecraft:", "")}`);
      } catch {
        // Best effort — player may have moved dimensions/logged off mid-cycle.
      }
    }

    scheduleNextCatch(player);
  }, delayTicks);
}

export function registerAutoFishingRod(world) {
  world.afterEvents.itemUse.subscribe((event) => {
    const { source: player, itemStack } = event;
    if (itemStack.typeId !== TOOL_ID) return;

    const isActive = activeFishers.get(player.id) ?? false;
    if (isActive) {
      activeFishers.set(player.id, false);
      player.sendMessage("§7[Auto Fishing Rod] Stopped.");
    } else {
      activeFishers.set(player.id, true);
      player.sendMessage("§a[Auto Fishing Rod] Started — stand near open water. Use again to stop.");
      scheduleNextCatch(player);
    }
  });
}
