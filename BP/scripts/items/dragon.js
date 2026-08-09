import { world } from "@minecraft/server";

const HATCH_ITEM = "hollowveil:dragon_egg";

export function registerDragonEgg() {
  world.afterEvents.itemUseOn.subscribe((ev) => {
    const { source, itemStack, block } = ev;
    if (!source || !itemStack || itemStack.typeId !== HATCH_ITEM) return;
    const dim = block.dimension;
    const spot = { x: block.location.x + 0.5, y: block.location.y + 1, z: block.location.z + 0.5 };
    try {
      const dragon = dim.spawnEntity("hollowveil:veil_dragon", spot);
      dim.spawnParticle("hollowveil:soul_wisp_particle", spot);
      dim.playSound("hollowveil.portal.ignite", spot);
      source.sendMessage("§5The egg cracks open - a wild Veil Dragon takes flight!");
      void dragon;
    } catch {
      source.sendMessage("§7There's no room for a dragon to hatch here.");
      return;
    }
    consumeOneEgg(source);
  });
}

function consumeOneEgg(player) {
  try {
    const equip = player.getComponent("minecraft:equippable");
    const held = equip?.getEquipment("Mainhand");
    if (held?.typeId === HATCH_ITEM) {
      if (held.amount <= 1) equip.setEquipment("Mainhand", undefined);
      else {
        held.amount -= 1;
        equip.setEquipment("Mainhand", held);
      }
      return;
    }
    const inv = player.getComponent("minecraft:inventory")?.container;
    if (!inv) return;
    for (let i = 0; i < inv.size; i++) {
      const it = inv.getItem(i);
      if (it?.typeId === HATCH_ITEM) {
        if (it.amount <= 1) inv.setItem(i, undefined);
        else {
          it.amount -= 1;
          inv.setItem(i, it);
        }
        return;
      }
    }
  } catch {
    /* if this fails the egg just isn't consumed - not fatal */
  }
}
