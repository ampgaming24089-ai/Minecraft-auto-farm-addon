/**
 * The End Reawakened set bonus.
 *
 * Raw numbers alone would make this armour a slightly better netherite, which
 * is not a reason to grind for it. Wearing the whole set in the End instead
 * changes how the dimension is played: slow falling makes the gaps between
 * islands survivable, and resistance takes the edge off the mobs that live
 * out there. Take one piece off, or leave the End, and it stops.
 *
 * The Crown is the other half of that idea. It occupies the helmet slot, so
 * wearing it costs you the set bonus and four points of protection - it has to
 * be worth that trade on its own, which is why it grants night vision and
 * strength rather than another defensive stat. Both effects are End-only, so
 * the Crown is a reason to go back rather than a permanent upgrade you carry
 * into every other dimension.
 */

import { EquipmentSlot, system, world } from "@minecraft/server";
import { END_DIMENSION } from "../world/generator.js";

const PIECES = [
  { slot: EquipmentSlot.Head, id: "voidbound:void_helmet" },
  { slot: EquipmentSlot.Chest, id: "voidbound:void_chestplate" },
  { slot: EquipmentSlot.Legs, id: "voidbound:void_leggings" },
  { slot: EquipmentSlot.Feet, id: "voidbound:void_boots" },
];

const CROWN_ID = "voidbound:sovereign_crown";

const CHECK_INTERVAL_TICKS = 40;

/** Longer than the check interval so the effect never visibly lapses. */
const EFFECT_DURATION_TICKS = 120;

/** playerId -> whether the bonus was active last check, for the notification. */
const active = new Map();

function wearsFullSet(player) {
  const equippable = player.getComponent("minecraft:equippable");
  if (!equippable) return false;
  for (const piece of PIECES) {
    let worn;
    try {
      worn = equippable.getEquipment(piece.slot);
    } catch {
      return false;
    }
    if (worn?.typeId !== piece.id) return false;
  }
  return true;
}

function wearsCrown(player) {
  const equippable = player.getComponent("minecraft:equippable");
  if (!equippable) return false;
  try {
    return equippable.getEquipment(EquipmentSlot.Head)?.typeId === CROWN_ID;
  } catch {
    return false;
  }
}

function check() {
  for (const player of world.getAllPlayers()) {
    const inEnd = player.dimension.id === END_DIMENSION;

    if (inEnd && wearsCrown(player)) {
      try {
        player.addEffect("night_vision", EFFECT_DURATION_TICKS, {
          amplifier: 0, showParticles: false,
        });
        player.addEffect("strength", EFFECT_DURATION_TICKS, {
          amplifier: 0, showParticles: false,
        });
      } catch (error) {
        console.warn(`[End Reawakened] could not apply crown powers: ${error}`);
      }
    }

    const eligible = inEnd && wearsFullSet(player);
    const wasActive = active.get(player.id) ?? false;

    if (eligible) {
      try {
        player.addEffect("slow_falling", EFFECT_DURATION_TICKS, {
          amplifier: 0,
          showParticles: false,
        });
        player.addEffect("resistance", EFFECT_DURATION_TICKS, {
          amplifier: 0,
          showParticles: false,
        });
      } catch (error) {
        console.warn(`[End Reawakened] could not apply set bonus: ${error}`);
      }
      if (!wasActive) {
        try {
          player.onScreenDisplay.setActionBar("§dEnd Reawakened set §7- slow falling, resistance");
          player.playSound("beacon.activate", { volume: 0.4, pitch: 1.5 });
        } catch {
          // Cosmetic only.
        }
      }
    }
    active.set(player.id, eligible);
  }
}

export function startArmorSet() {
  system.runInterval(check, CHECK_INTERVAL_TICKS);
  world.afterEvents.playerLeave.subscribe((event) => {
    active.delete(event.playerId);
  });
}
