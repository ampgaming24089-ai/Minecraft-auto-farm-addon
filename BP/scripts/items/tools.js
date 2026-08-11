import { world, system, ItemStack } from "@minecraft/server";
import { openJournal } from "../ui/journal.js";
import { tryIgnitePortal } from "../portal/portal.js";
import { useSigilOnAltar } from "../bosses/chambers.js";
import { getWorldJson, KEYS } from "../lib/state.js";
import { nearestSite, SITE_LABELS } from "../world/sites.js";
import { regionAt, HOLLOW_VEIL } from "../world/build.js";
import { BIOMES } from "../world/biomes.js";

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
    const { player, itemStack, block, isFirstEvent, blockFace } = ev;
    if (!itemStack || !player || !block) return;
    if (isFirstEvent === false) return; // fires twice per interaction otherwise
    if (itemStack.typeId === "hollowveil:soulfire_igniter") {
      useIgniter(player, block, blockFace, itemStack);
    } else if (itemStack.typeId?.startsWith("hollowveil:sigil_") && block.typeId === "hollowveil:ritual_altar") {
      const consumed = useSigilOnAltar(player, block.dimension, block.location, itemStack.typeId, system.currentTick);
      if (consumed) consumeOneItem(player, itemStack);
    }
  });
}

// Soul fire only survives on soul soil and soul sand; anywhere else it winks
// out the instant it is placed. Everywhere else gets ordinary fire, which is
// exactly how vanilla behaves.
const SOUL_FIRE_BASES = new Set(["minecraft:soul_soil", "minecraft:soul_sand"]);

const FACE_OFFSETS = {
  Up: { x: 0, y: 1, z: 0 },
  Down: { x: 0, y: -1, z: 0 },
  North: { x: 0, y: 0, z: -1 },
  South: { x: 0, y: 0, z: 1 },
  West: { x: -1, y: 0, z: 0 },
  East: { x: 1, y: 0, z: 0 },
};

/**
 * Soulfire and Steel: a portal lighter first, a flint and steel second.
 *
 * The old handler only ran when the clicked block was gold, so clicking any
 * other part of the build did nothing whatsoever. It now runs on every block
 * - portal detection reads the surroundings, not the block under the cursor -
 * and falls back to lighting a fire so the tool behaves the way its name and
 * its recipe promise.
 */
function useIgniter(player, block, blockFace, itemStack) {
  if (tryIgnitePortal(block.dimension, block.location, player, blockFace)) {
    damageIgniter(player, itemStack, 1);
    return;
  }
  if (lightFire(block, blockFace)) damageIgniter(player, itemStack, 1);
}

function lightFire(block, blockFace) {
  const offset = FACE_OFFSETS[blockFace] ?? FACE_OFFSETS.Up;
  const pos = {
    x: block.location.x + offset.x,
    y: block.location.y + offset.y,
    z: block.location.z + offset.z,
  };
  try {
    const target = block.dimension.getBlock(pos);
    if (!target?.isAir) return false;
    const base = block.dimension.getBlock({ ...pos, y: pos.y - 1 })?.typeId;
    target.setType(SOUL_FIRE_BASES.has(base) ? "minecraft:soul_fire" : "minecraft:fire");
    return true;
  } catch {
    return false;   // unloaded chunk, or the fire had nothing to burn on
  }
}

/** Spends durability the way a real tool does, and breaks when spent. */
function damageIgniter(player, itemStack, amount) {
  try {
    const equip = player.getComponent("minecraft:equippable");
    const held = equip?.getEquipment("Mainhand");
    if (!held || held.typeId !== itemStack.typeId) return;
    const durability = held.getComponent("minecraft:durability");
    if (!durability) return;
    if (durability.damage + amount >= durability.maxDurability) {
      equip.setEquipment("Mainhand", undefined);
      player.dimension.playSound("random.break", player.location);
      return;
    }
    durability.damage += amount;
    equip.setEquipment("Mainhand", held);
  } catch {
    /* cosmetic - a tool that never wears out is better than a thrown error */
  }
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

/**
 * The Soul Compass.
 *
 * It used to report one thing: how far Hollow Hamlet was. That was adequate
 * when the world was 1,000 blocks across. At 50,000 in every direction, "the
 * hub is 31,402m away" is not navigation - it is a number. So it now also
 * names the region you are standing in and points at the nearest structure,
 * which is what actually gets you somewhere out here.
 *
 * Both extra readings are pure functions of your coordinates (see
 * world/biomes.js and world/sites.js), so this costs one hash lookup and a
 * short grid search, not a world scan.
 */
function pointToShrine(player) {
  const here = player.location;
  const lines = [];

  if (player.dimension.id === HOLLOW_VEIL) {
    const biome = BIOMES[regionAt(here)];
    if (biome) lines.push(`§d${biome.name ?? biome.id}`);

    const site = nearestSite(here.x, here.z);
    if (site) {
      const label = SITE_LABELS[site.type] ?? site.type.replace(/_/g, " ");
      lines.push(`§7${label} ${Math.round(site.dist)}m ` +
                 `${compassDirection(site.x - here.x, site.z - here.z)}`);
    }
  }

  const shrine = getWorldJson(KEYS.VILLAGE_SHRINE_POS, null);
  if (shrine) {
    const dist = Math.round(Math.hypot(shrine.x - here.x, shrine.z - here.z));
    lines.push(`§5Hamlet ${dist}m ${compassDirection(shrine.x - here.x, shrine.z - here.z)}`);
  } else {
    lines.push("§7The needle spins - Hollow Hamlet hasn't been found yet.");
  }

  player.onScreenDisplay.setActionBar(lines.join("  §8|  "));
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
    revealPoltergeists(player);
  }
  if (items.some((i) => i.typeId === "hollowveil:featherfall_charm")) {
    try {
      player.addEffect("slow_falling", LANTERN_INTERVAL + 5, { amplifier: 0, showParticles: false });
    } catch {
      /* ignore */
    }
  }
}

/**
 * The Spirit Lantern's whole point: poltergeists cycle in and out of
 * invisibility, and holding the lantern drags them back into view.
 *
 * This used to call `addEffect("glowing")`, which does nothing at all -
 * Glowing is a Java effect. Bedrock ships 37 effects and Glowing is not among
 * them (checked against mojang-effects.json), so the call threw every time
 * and the catch block swallowed it. The lantern's headline ability had never
 * worked in any released version of this pack.
 *
 * Stripping the poltergeist's invisibility outright is better anyway: it is
 * the actual thing the player wants, it is visible immediately, and it uses
 * the same dynamic property the mob's own visibility cycle reads, so the two
 * do not fight each other.
 */
const LANTERN_REVEAL_RANGE = 12;

function revealPoltergeists(player) {
  let ghosts;
  try {
    ghosts = player.dimension.getEntities({
      location: player.location,
      maxDistance: LANTERN_REVEAL_RANGE,
      type: "hollowveil:poltergeist",
    });
  } catch {
    return;
  }
  for (const ghost of ghosts) {
    try {
      ghost.removeEffect("invisibility");
      ghost.setDynamicProperty("hollowveil:hidden", false);
      ghost.dimension.spawnParticle("hollowveil:soul_burst_particle", {
        x: ghost.location.x,
        y: ghost.location.y + 1,
        z: ghost.location.z,
      });
    } catch {
      /* the ghost may have died or unloaded mid-sweep */
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
