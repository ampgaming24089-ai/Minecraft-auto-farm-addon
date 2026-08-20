/**
 * The Rift Charm and the Echo Horn.
 *
 * Both exist because the End is hostile to navigation. Vanilla's compass spins,
 * its maps are blank, and every island looks like the last one, so the two
 * problems worth solving are "I cannot get back to where I was" and "I cannot
 * tell what is out there". The Charm answers the first, the Horn the second.
 *
 * Neither works outside the End. That is deliberate: they are tools for one
 * dimension, not a general upgrade to travel.
 */

import { system, world } from "@minecraft/server";
import { END_DIMENSION } from "../world/generator.js";
import { distanceTo, sitesNear } from "../world/sites.js";

const CHARM_ID = "voidbound:rift_charm";
const HORN_ID = "voidbound:echo_horn";

const ANCHOR_X = "voidbound.anchor_x";
const ANCHOR_Y = "voidbound.anchor_y";
const ANCHOR_Z = "voidbound.anchor_z";

/** Ticks between uses, so neither item can be spammed. */
const CHARM_COOLDOWN = 100;
const HORN_COOLDOWN = 160;

/** How far the Horn's echo reaches, in cells (272 blocks each). */
const HORN_CELLS = 3;

/** Radius the Horn reports mobs within. */
const HORN_MOB_RANGE = 48;

const lastUsed = new Map();

function onCooldown(player, key, ticks) {
    const id = `${player.id}:${key}`;
    const now = system.currentTick;
    if (now - (lastUsed.get(id) ?? -Infinity) < ticks) return true;
    lastUsed.set(id, now);
    return false;
}

function readAnchor(player) {
  try {
    const x = player.getDynamicProperty(ANCHOR_X);
    const y = player.getDynamicProperty(ANCHOR_Y);
    const z = player.getDynamicProperty(ANCHOR_Z);
    if (typeof x === "number" && typeof y === "number" && typeof z === "number") {
      return { x, y, z };
    }
  } catch {
    // Treat as unset.
  }
  return undefined;
}

function setAnchor(player) {
  const at = player.location;
  try {
    player.setDynamicProperty(ANCHOR_X, Math.floor(at.x) + 0.5);
    player.setDynamicProperty(ANCHOR_Y, Math.floor(at.y));
    player.setDynamicProperty(ANCHOR_Z, Math.floor(at.z) + 0.5);
  } catch (error) {
    player.sendMessage("§cThe charm will not hold that place.");
    console.warn(`[End Reawakened] could not store anchor: ${error}`);
    return;
  }
  player.sendMessage(
    `§dAnchor set. §7${Math.floor(at.x)}, ${Math.floor(at.y)}, ${Math.floor(at.z)}`
  );
  player.playSound("beacon.activate", { volume: 0.5, pitch: 1.5 });
  burst(player, player.location);
}

function burst(player, at) {
  for (let i = 0; i < 8; i++) {
    const angle = (i / 8) * Math.PI * 2;
    try {
      player.dimension.spawnParticle("voidbound:rift_burst", {
        x: at.x + Math.cos(angle) * 0.8,
        y: at.y + 1,
        z: at.z + Math.sin(angle) * 0.8,
      });
    } catch {
      // Cosmetic.
    }
  }
}

function recall(player) {
  const anchor = readAnchor(player);
  if (!anchor) {
    player.sendMessage("§8The charm is unbound. Sneak and use it to set an anchor.");
    player.playSound("note.bass", { volume: 0.5, pitch: 0.7 });
    return;
  }
  burst(player, player.location);
  try {
    player.teleport(anchor, { dimension: player.dimension });
  } catch {
    player.sendMessage("§cSomething is standing where your anchor was.");
    return;
  }
  burst(player, anchor);
  player.playSound("mob.endermen.portal", { volume: 0.7, pitch: 1.1 });
  player.sendMessage("§5The charm pulls you back.");
}

function sound(player) {
  const position = player.location;
  const sites = sitesNear(position.x, position.z, HORN_CELLS);

  try {
    player.playSound("mob.warden.sonic_boom", { volume: 0.6, pitch: 1.4 });
  } catch {
    // Sound id unavailable on this version; the reading still works.
  }
  for (let ring = 1; ring <= 3; ring++) {
    try {
      player.dimension.spawnParticle("voidbound:rift_shockwave", {
        x: position.x, y: position.y + ring * 0.6, z: position.z,
      });
    } catch {
      // Cosmetic.
    }
  }

  if (sites.length === 0) {
    player.sendMessage("§8The echo returns empty.");
    return;
  }

  player.sendMessage("§5The echo returns:");
  for (const site of sites.slice(0, 3)) {
    const distance = Math.round(distanceTo(site, position));
    player.sendMessage(`  §7${site.blueprint.name} §f${distance}§7 blocks`);
  }

  let hostile = 0;
  try {
    hostile = player.dimension
      .getEntities({ location: position, maxDistance: HORN_MOB_RANGE, families: ["monster"] })
      .length;
  } catch {
    hostile = -1;
  }
  if (hostile > 0) {
    player.onScreenDisplay.setActionBar(`§c${hostile} hostile nearby`);
  } else if (hostile === 0) {
    player.onScreenDisplay.setActionBar("§aNothing hostile nearby");
  }
}

export function startUtilityItems() {
  world.afterEvents.itemUse.subscribe((event) => {
    const { source: player, itemStack } = event;
    const typeId = itemStack.typeId;
    if (typeId !== CHARM_ID && typeId !== HORN_ID) return;

    if (player.dimension.id !== END_DIMENSION) {
      player.sendMessage("§8It is inert outside the End.");
      return;
    }

    try {
      if (typeId === CHARM_ID) {
        if (onCooldown(player, "charm", CHARM_COOLDOWN)) return;
        // Sneaking rebinds the anchor; a plain use returns to it.
        if (player.isSneaking) setAnchor(player);
        else recall(player);
        return;
      }
      if (onCooldown(player, "horn", HORN_COOLDOWN)) return;
      sound(player);
    } catch (error) {
      console.warn(`[End Reawakened] utility item failed: ${error}`);
    }
  });

  world.afterEvents.playerLeave.subscribe((event) => {
    for (const key of [...lastUsed.keys()]) {
      if (key.startsWith(`${event.playerId}:`)) lastUsed.delete(key);
    }
  });
}
