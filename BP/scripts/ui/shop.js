import { world, ItemStack } from "@minecraft/server";
import { ActionFormData, MessageFormData } from "@minecraft/server-ui";

const ICON = "textures/items/";

/** A real bespoke shop UI - replaces the vanilla trade-screen chrome
 * entirely. Occultist no longer carries minecraft:trade_table; this
 * listens for the player interacting with it directly
 * (world.afterEvents.playerInteractWithEntity) and drives the whole
 * transaction (cost check, item removal, reward grant) in script. */
const CATEGORIES = [
  {
    id: "currency",
    title: "§5Currency Exchange",
    icon: ICON + "soul_shard",
    items: [
      { label: "Soul Shards x8 -> Emerald", costs: [{ item: "hollowveil:soul_shard", count: 8 }], gives: [{ item: "minecraft:emerald", count: 1 }] },
      { label: "Ember Dust x8 -> Emerald", costs: [{ item: "hollowveil:ember_dust", count: 8 }], gives: [{ item: "minecraft:emerald", count: 1 }] },
      { label: "Diamonds x3 -> 32 Soul Shards", costs: [{ item: "minecraft:diamond", count: 3 }], gives: [{ item: "hollowveil:soul_shard", count: 32 }] },
      { label: "Emeralds x20 -> 6 Wraithsteel Ingots", costs: [{ item: "minecraft:emerald", count: 20 }], gives: [{ item: "hollowveil:wraithsteel_ingot", count: 6 }] },
    ],
  },
  {
    id: "supplies",
    title: "§5Supplies & Trinkets",
    icon: ICON + "spirit_lantern",
    items: [
      { label: "Emerald x3 -> Journal", costs: [{ item: "minecraft:emerald", count: 3 }], gives: [{ item: "hollowveil:journal", count: 1 }] },
      { label: "Emerald x5 -> Soul Compass", costs: [{ item: "minecraft:emerald", count: 5 }], gives: [{ item: "hollowveil:soul_compass", count: 1 }] },
      { label: "Emerald x10 -> Spirit Lantern", costs: [{ item: "minecraft:emerald", count: 10 }], gives: [{ item: "hollowveil:spirit_lantern", count: 1 }] },
      { label: "Emerald x14 -> Ghost Ward Charm", costs: [{ item: "minecraft:emerald", count: 14 }], gives: [{ item: "hollowveil:ghost_ward_charm", count: 1 }] },
      { label: "Emerald x4 -> 8 Ashwood Logs", costs: [{ item: "minecraft:emerald", count: 4 }], gives: [{ item: "hollowveil:ashwood_log", count: 8 }] },
      { label: "Emerald x2 -> 3 Ember Fruit", costs: [{ item: "minecraft:emerald", count: 2 }], gives: [{ item: "hollowveil:ember_fruit", count: 3 }] },
    ],
  },
  {
    id: "materials",
    title: "§5Refined Materials",
    icon: ICON + "veilsteel_ingot",
    items: [
      { label: "Spectral Dust x6 -> 2 Wraithsteel Ingots", costs: [{ item: "hollowveil:spectral_dust", count: 6 }], gives: [{ item: "hollowveil:wraithsteel_ingot", count: 2 }] },
      { label: "Sentinel Core + Plating x2 -> 4 Veilsteel Ingots", costs: [{ item: "hollowveil:sentinel_core", count: 2 }, { item: "hollowveil:veilsteel_plating", count: 2 }], gives: [{ item: "hollowveil:veilsteel_ingot", count: 4 }] },
    ],
  },
  {
    id: "enchants",
    title: "§5Warded Knowledge",
    icon: ICON + "spectral_dust",
    items: [
      { label: "Demon Horn x4 + Emerald x6 -> Enchanted Book", costs: [{ item: "hollowveil:demon_horn", count: 4 }, { item: "minecraft:emerald", count: 6 }], gives: [{ item: "minecraft:enchanted_book", count: 1 }] },
      { label: "Banshee Vocal Cord x3 + Emerald x10 -> Enchanted Book", costs: [{ item: "hollowveil:banshee_vocal_cord", count: 3 }, { item: "minecraft:emerald", count: 10 }], gives: [{ item: "minecraft:enchanted_book", count: 1 }] },
    ],
  },
  {
    id: "rare",
    title: "§5Rare Goods",
    icon: ICON + "dragon_egg",
    items: [
      { label: "Diamond x6 + Embered Scale x4 -> Veil Dragon Egg", costs: [{ item: "minecraft:diamond", count: 6 }, { item: "hollowveil:embered_scale", count: 4 }], gives: [{ item: "hollowveil:dragon_egg", count: 1 }] },
    ],
  },
];

export function registerShop() {
  world.afterEvents.playerInteractWithEntity.subscribe((ev) => {
    if (ev.target.typeId !== "hollowveil:occultist") return;
    openShopMenu(ev.player);
  });
}

function openShopMenu(player) {
  const form = new ActionFormData()
    .title("§l§5The Occultist's Wares")
    .body("§7A hooded figure spreads their hands over a table of relics.\n§7\"The Veil provides, for a price.\"");
  for (const cat of CATEGORIES) {
    form.button(cat.title, cat.icon);
  }
  form.show(player).then((res) => {
    if (res.canceled || res.selection === undefined) return;
    openCategory(player, CATEGORIES[res.selection]);
  });
}

function openCategory(player, category) {
  const form = new ActionFormData().title(category.title).body("§7Choose a trade:");
  for (const item of category.items) {
    const costText = item.costs.map((c) => `${itemName(c.item)} x${c.count}`).join(" + ");
    form.button(`${item.label}\n§8${costText}`, ICON + item.gives[0].item.split(":")[1]);
  }
  form.show(player).then((res) => {
    if (res.canceled || res.selection === undefined) {
      openShopMenu(player);
      return;
    }
    attemptPurchase(player, category.items[res.selection], category);
  });
}

function itemName(typeId) {
  return typeId.split(":")[1].replace(/_/g, " ");
}

function attemptPurchase(player, entry, category) {
  const inv = player.getComponent("minecraft:inventory")?.container;
  if (!inv) return;

  for (const cost of entry.costs) {
    if (countItem(inv, cost.item) < cost.count) {
      new MessageFormData()
        .title("§5The Occultist's Wares")
        .body(`§cYou don't have enough ${itemName(cost.item)}.`)
        .button1("Back")
        .button2("Close")
        .show(player)
        .then((res) => {
          if (!res.canceled && res.selection === 0) openCategory(player, category);
        });
      return;
    }
  }

  for (const cost of entry.costs) removeItem(inv, cost.item, cost.count);
  for (const give of entry.gives) giveItem(player, inv, give.item, give.count);

  player.playSound("random.orb");
  new MessageFormData()
    .title("§5The Occultist's Wares")
    .body(`§aTraded successfully.\n§7"${flavorLine()}"`)
    .button1("Continue Trading")
    .button2("Close")
    .show(player)
    .then((res) => {
      if (!res.canceled && res.selection === 0) openCategory(player, category);
    });
}

const FLAVOR_LINES = [
  "The Veil remembers this exchange.",
  "Spend it well, wanderer.",
  "Careful what you carry back through the portal.",
  "Every shard has a story. I won't ask about yours.",
];

function flavorLine() {
  return FLAVOR_LINES[Math.floor(Math.random() * FLAVOR_LINES.length)];
}

function countItem(inv, typeId) {
  let total = 0;
  for (let i = 0; i < inv.size; i++) {
    const stack = inv.getItem(i);
    if (stack?.typeId === typeId) total += stack.amount;
  }
  return total;
}

function removeItem(inv, typeId, count) {
  let remaining = count;
  for (let i = 0; i < inv.size && remaining > 0; i++) {
    const stack = inv.getItem(i);
    if (stack?.typeId !== typeId) continue;
    if (stack.amount <= remaining) {
      remaining -= stack.amount;
      inv.setItem(i, undefined);
    } else {
      stack.amount -= remaining;
      inv.setItem(i, stack);
      remaining = 0;
    }
  }
}

function giveItem(player, inv, typeId, count) {
  const stack = new ItemStack(typeId, count);
  const leftover = inv.addItem(stack);
  if (leftover) {
    try {
      player.dimension.spawnItem(leftover, player.location);
    } catch {
      /* inventory full and drop failed - player still got most of the trade */
    }
  }
}
