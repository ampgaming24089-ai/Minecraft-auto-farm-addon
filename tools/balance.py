#!/usr/bin/env python3
"""
The single source of truth for every weapon and armour number in the pack.

Why this file exists: the stats had drifted into mush. The entry-tier sword
did exactly netherite damage, the entry-tier armour was exactly netherite's
20 points, one boss set (Mourner's Shroud, 18) was *worse* than netherite, and
two boss weapons hit softer than the craftable sword you could make without
fighting anything. For a dimension you only reach after finishing the base
game, all of that is backwards.

The curve below fixes it, and applying it from one table means the guide, the
items and this document can never disagree.

  python3 tools/balance.py          # apply to BP/items
  python3 tools/balance.py --check  # report drift without writing

A NOTE ON THE ARMOUR CAP, because it changes what these numbers mean.
Minecraft's damage formula is  damage x (1 - min(20, armour) / 25).  The
min(20, ...) is a hard cap: 20 armour points is 80% reduction and no set of
plate in any edition of the game does better. Netherite is exactly 20. So the
totals below - up to 43 - cannot all turn into damage reduction, and it would
be dishonest to present them as if they did.

They are not decorative either. Points above the cap buy three real things:
  * partial sets. A 15-point chestplate alone puts you at 75% of the cap
    wearing one piece; netherite's 8 puts you at 40%.
  * broken gear. You stay at the cap far longer as pieces wear out.
  * mixing. A boss helmet over craftable plate still adds.
The scaling that survives *past* the cap is the set bonuses in
BP/scripts/armor/setBonuses.js, which is where the real tiering lives - see
SET_BONUS_NOTES at the bottom of this file.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = os.path.join(ROOT, "BP", "items")

# Vanilla, for reference in one place instead of in comments everywhere.
# netherite armour 3/8/6/3 = 20 points; netherite sword 7 (8 with the base
# punch); netherite axe 9; enchantability 15; chestplate durability 592.
NETHERITE_ARMOUR = (3, 8, 6, 3)
NETHERITE_SWORD = 7

# --- armour ---------------------------------------------------------------
# (helmet, chestplate, leggings, boots) protection, then durability in the
# same order, then enchantability. Every set beats netherite's 20; the shape
# of each set is as important as the total.
ARMOUR = {
    # craftable ladder
    "wraithsteel":       {"prot": (4, 9, 7, 4),    "dur": (550, 800, 750, 650),      "ench": 16},
    "veilsteel":         {"prot": (5, 11, 9, 5),   "dur": (800, 1150, 1080, 940),    "ench": 20},
    "hollowforged":      {"prot": (7, 14, 11, 7),  "dur": (1200, 1750, 1640, 1420),  "ench": 25},
    # boss rewards, each a different shape rather than a different colour
    "mourners_shroud":   {"prot": (5, 10, 8, 5),   "dur": (950, 1380, 1300, 1120),   "ench": 28},
    "spectral_regalia":  {"prot": (6, 12, 9, 6),   "dur": (1100, 1600, 1500, 1300),  "ench": 30},
    "ashen_demonplate":  {"prot": (8, 15, 12, 8),  "dur": (1400, 2000, 1880, 1620),  "ench": 20},
}
SLOTS = ("helmet", "chestplate", "leggings", "boots")

# --- weapons and tools ----------------------------------------------------
# `damage` is what goes in minecraft:damage - the bonus over the 1-point bare
# fist, so the tooltip reads damage + 1. Netherite sword is 7 (8 shown).
#
# Axes out-damage swords, as in vanilla. Boss weapons sit between the mid and
# top craftable tiers on raw damage and make up the difference with the
# effects in BP/scripts/items/weapons.js - which is what makes them worth
# carrying instead of just worth more.
WEAPONS = {
    "wraithsteel_sword":    {"damage": 9,  "dur": 1200, "ench": 16},
    "wraithsteel_axe":      {"damage": 11, "dur": 1200, "ench": 16},
    "wraithsteel_pickaxe":  {"damage": 5,  "dur": 1200, "ench": 16},

    "veilsteel_sword":      {"damage": 12, "dur": 2000, "ench": 20},
    "veilsteel_axe":        {"damage": 14, "dur": 2000, "ench": 20},
    "veilsteel_pickaxe":    {"damage": 7,  "dur": 2000, "ench": 20},

    "hollowforged_sword":   {"damage": 17, "dur": 3200, "ench": 25},
    "hollowforged_axe":     {"damage": 19, "dur": 3200, "ench": 25},
    "hollowforged_pickaxe": {"damage": 9,  "dur": 3200, "ench": 25},

    # Weeping Widow: lowest of the three, but the only one that hits a crowd.
    "wailing_edge":         {"damage": 13, "dur": 2200, "ench": 30},
    # Hollow King: wither plus a fifth of the damage back as health.
    "hollow_kings_reaper":  {"damage": 14, "dur": 2400, "ench": 28},
    # Malacoda: stacking burn that detonates. The hardest boss, the hardest hit.
    "malacodas_fang":       {"damage": 15, "dur": 2500, "ench": 26},
}

SET_BONUS_NOTES = """
Where the tiering continues once armour points stop counting:
  wraithsteel       - none. It is the entry suit; its 24 points are the point.
  veilsteel         - Resistance I.
  hollowforged      - Resistance I, Haste I, permanent fire resistance, and
                      Absorption II below 30% health.
  mourners_shroud   - permanent Speed I, Speed II below 30% health, and fall
                      damage refunds half of itself as health.
  spectral_regalia  - Resistance I, plus invisibility and water breathing
                      below 30% health.
  ashen_demonplate  - Resistance II and permanent fire resistance. The tank.
"""


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _save(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")


def apply(check_only=False):
    changes = []

    def touch(item_id, comps, key, path, value):
        node = comps
        for part in path[:-1]:
            node = node.setdefault(part, {})
        if node.get(path[-1]) != value:
            changes.append(f"{item_id}: {'.'.join(path)} {node.get(path[-1])} -> {value}")
            if not check_only:
                node[path[-1]] = value

    for set_name, spec in ARMOUR.items():
        for slot, prot, dur in zip(SLOTS, spec["prot"], spec["dur"]):
            path = os.path.join(ITEMS, f"{set_name}_{slot}.json")
            if not os.path.exists(path):
                changes.append(f"MISSING {set_name}_{slot}.json")
                continue
            doc = _load(path)
            comps = doc["minecraft:item"]["components"]
            ident = f"{set_name}_{slot}"
            touch(ident, comps, "prot", ["minecraft:wearable", "protection"], prot)
            touch(ident, comps, "dur", ["minecraft:durability", "max_durability"], dur)
            touch(ident, comps, "ench", ["minecraft:enchantable", "value"], spec["ench"])
            if not check_only:
                _save(path, doc)

    for name, spec in WEAPONS.items():
        path = os.path.join(ITEMS, f"{name}.json")
        if not os.path.exists(path):
            changes.append(f"MISSING {name}.json")
            continue
        doc = _load(path)
        comps = doc["minecraft:item"]["components"]
        touch(name, comps, "damage", ["minecraft:damage"], spec["damage"])
        touch(name, comps, "dur", ["minecraft:durability", "max_durability"], spec["dur"])
        touch(name, comps, "ench", ["minecraft:enchantable", "value"], spec["ench"])
        if not check_only:
            _save(path, doc)

    return changes


def report():
    print(f"{'SET':20s} {'helm':>5s} {'chest':>6s} {'legs':>5s} {'boots':>6s} "
          f"{'total':>6s} {'vs netherite':>13s}")
    base = sum(NETHERITE_ARMOUR)
    print(f"{'(netherite)':20s} {NETHERITE_ARMOUR[0]:5d} {NETHERITE_ARMOUR[1]:6d} "
          f"{NETHERITE_ARMOUR[2]:5d} {NETHERITE_ARMOUR[3]:6d} {base:6d} {'-':>13s}")
    for name, spec in ARMOUR.items():
        total = sum(spec["prot"])
        print(f"{name:20s} {spec['prot'][0]:5d} {spec['prot'][1]:6d} {spec['prot'][2]:5d} "
              f"{spec['prot'][3]:6d} {total:6d} {f'+{total - base}':>13s}")
    print(f"\n{'WEAPON':22s} {'damage':>7s} {'shown':>6s} {'vs netherite sword':>19s}")
    for name, spec in WEAPONS.items():
        d = spec["damage"]
        print(f"{name:22s} {d:7d} {d + 1:6d} {f'+{d - NETHERITE_SWORD}':>19s}")
    print(SET_BONUS_NOTES)


if __name__ == "__main__":
    check = "--check" in sys.argv
    edits = apply(check_only=check)
    if "--quiet" not in sys.argv:
        report()
    if check and edits:
        print(f"\n{len(edits)} item(s) drifted from tools/balance.py:")
        for c in edits:
            print("  " + c)
        sys.exit(1)
    print(f"\n{len(edits)} value(s) {'would change' if check else 'updated'}")
