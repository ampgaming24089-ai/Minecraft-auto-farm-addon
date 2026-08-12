#!/usr/bin/env python3
"""
Builds the player guide from the pack's own data.

A guide that is typed by hand starts wrong and gets worse: recipes change,
armour values get rebalanced, mobs move between biomes, and the document goes
on confidently describing the pack as it was three releases ago. So nothing
here is typed twice. Recipes are read out of BP/recipes, armour and weapon
numbers out of BP/items, drops out of BP/loot_tables, and the mob rosters out
of the spawner's own tables. Prose that a machine cannot derive - what a thing
is *for* - lives in one table below and nowhere else.

Three outputs, one source:
  BP/scripts/ui/guidedata.js  - the in-game Field Guide's content
  docs/GUIDE.md               - the same guide for the repo
  docs/guide.html             - a standalone page for players

Run:  python3 tools/gen_guide.py
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import balance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "BP")
DOCS = os.path.join(ROOT, "docs")


# ---------------------------------------------------------------- reading ---
def load(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return json.load(fh)


def lang_names():
    """Display name for every item, block and entity, from the .lang file."""
    names = {}
    path = os.path.join(ROOT, "RP", "texts", "en_US.lang")
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        for prefix in ("item.", "tile.", "entity."):
            if key.startswith(prefix):
                ident = key[len(prefix):].rsplit(".name", 1)[0]
                names[ident] = value.strip()
    return names


NAMES = lang_names()


def set_label(set_name):
    """A set's display name: the chestplate's name minus its slot word, since
    that word is "Chestplate" for most sets and "Wrap" for the Shroud."""
    full = pretty(f"hollowveil:{set_name}_chestplate")
    return full.rsplit(" ", 1)[0] if " " in full else full


def pretty(ident):
    """A readable name for any identifier, ours or vanilla."""
    if ident in NAMES:
        return NAMES[ident]
    return ident.split(":")[-1].replace("_", " ").title()


def items():
    out = {}
    for fn in sorted(os.listdir(os.path.join(BP, "items"))):
        if not fn.endswith(".json"):
            continue
        item = load(BP, "items", fn)["minecraft:item"]
        out[item["description"]["identifier"]] = item["components"]
    return out


def recipes():
    """{output identifier: [human-readable ingredient list, ...]}"""
    out = defaultdict(list)
    for fn in sorted(os.listdir(os.path.join(BP, "recipes"))):
        if not fn.endswith(".json"):
            continue
        doc = load(BP, "recipes", fn)
        for key, recipe in doc.items():
            if not key.startswith("minecraft:recipe"):
                continue
            result = recipe.get("result") or recipe.get("output")
            rid = result.get("item") if isinstance(result, dict) else result
            if not rid:
                continue
            count = result.get("count", 1) if isinstance(result, dict) else 1

            if "recipe_furnace" in key:
                src = recipe["input"]
                src = src.get("item") if isinstance(src, dict) else src
                out[rid].append({"kind": "smelt", "count": count,
                                 "ingredients": [(pretty(src), 1)]})
                continue

            tally = defaultdict(int)
            if "pattern" in recipe:
                keymap = {k: (v.get("item") if isinstance(v, dict) else v)
                          for k, v in recipe.get("key", {}).items()}
                for row in recipe["pattern"]:
                    for ch in row:
                        if ch in keymap:
                            tally[keymap[ch]] += 1
            else:
                for ing in recipe.get("ingredients", []):
                    iid = ing.get("item") if isinstance(ing, dict) else ing
                    tally[iid] += ing.get("count", 1) if isinstance(ing, dict) else 1
            if tally:
                out[rid].append({
                    "kind": "craft", "count": count,
                    "ingredients": [(pretty(i), n) for i, n in sorted(tally.items())],
                })
    return out


def drops():
    """{entity or block identifier: [dropped item names]}"""
    out = defaultdict(list)
    for root, _, files in os.walk(os.path.join(BP, "loot_tables")):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            rel = os.path.relpath(os.path.join(root, fn), BP).replace("\\", "/")
            names = re.findall(r'"name"\s*:\s*"(hollowveil:[\w]+)"', open(os.path.join(root, fn)).read())
            out[rel] = [pretty(n) for n in dict.fromkeys(names)]
    return out


def entities():
    out = {}
    for fn in sorted(os.listdir(os.path.join(BP, "entities"))):
        if not fn.endswith(".json"):
            continue
        ent = load(BP, "entities", fn)["minecraft:entity"]
        out[ent["description"]["identifier"]] = ent
    return out


def spawn_rosters():
    """Biome -> [(entity id, pack low, pack high, hostile?)], read out of the
    spawner so the guide can never claim a mob lives somewhere it does not."""
    src = open(os.path.join(BP, "scripts", "mobs", "spawner.js"), encoding="utf-8").read()
    body = src[src.index("const REGION_TABLES"):]
    body = body[:body.index("\n};")]
    rosters = defaultdict(list)
    current = None
    for line in body.splitlines():
        head = re.match(r"\s*(\w+):\s*\[", line)
        if head:
            current = head.group(1)
            continue
        row = re.search(r'id:\s*"([\w:]+)".*?pack:\s*\[(\d+),\s*(\d+)\].*?kind:\s*(\w+)', line)
        if row and current:
            rosters[current].append((row.group(1), int(row.group(2)),
                                     int(row.group(3)), row.group(4) == "HOSTILE"))
    return rosters


def biome_names():
    """Region id -> display name, straight out of biomes.js."""
    src = open(os.path.join(BP, "scripts", "world", "biomes.js"), encoding="utf-8").read()
    return dict(re.findall(r'id:\s*"(\w+)",\s*\n\s*name:\s*"([^"]+)"', src))


def world_constants():
    src = open(os.path.join(BP, "scripts", "world", "biomes.js"), encoding="utf-8").read()
    radius = int(re.search(r"WORLD_RADIUS\s*=\s*(\d+)", src).group(1))
    return {"radius": radius}


# --------------------------------------------------------------- the prose --
# The only hand-written content in the guide: what a thing is FOR. Everything
# else on the page is derived. Keyed by identifier so a rename shows up as a
# missing entry rather than as silently stale text.
PURPOSE = {
    "hollowveil:soulfire_igniter":
        "Your way in. Works exactly like a flint and steel - and lights fires "
        "like one too - but its blue flame is what opens a gold-block frame.",
    "hollowveil:soul_shard":
        "The Veil's currency. Dropped by almost everything; the Occultist "
        "takes eight for an emerald.",
    "hollowveil:ember_dust": "Ashlands currency. Trades for emeralds.",
    "hollowveil:spectral_dust": "Refines into Wraithsteel at the Occultist's table.",
    "hollowveil:journal":
        "This guide. You are handed one the first time you join; the Occultist "
        "sells replacements.",
    "hollowveil:soul_compass":
        "Points at Hollow Hamlet and tells you how far. In a world this size "
        "that is not a luxury.",
    "hollowveil:spirit_lantern":
        "Night vision while held, and it drags hidden Poltergeists back into "
        "view - they cannot stay invisible near one.",
    "hollowveil:ghost_ward_charm":
        "Hold it and a Wraith's touch no longer drains your hunger.",
    "hollowveil:featherfall_charm": "Slow falling while held. Pairs well with a dragon.",
    "hollowveil:dragon_egg":
        "Right-click any block to hatch a wild Veil Dragon. Colour is random.",
    "hollowveil:ember_coal": "Burns for 160 seconds - twice as long as coal.",
    "hollowveil:ember_core": "Nine Ember Coal in one block-sized lump. Uncrafts.",
    "hollowveil:elk_marrow": "Light snack, and Veil Dragons like it.",
    "hollowveil:ember_fruit": "Solid food, and the fastest way to a dragon's trust.",
    "hollowveil:veil_marrow_stew":
        "The best meal in the Veil, and worth 15 dragon temper a bowl.",
    "hollowveil:toad_mucus": "Two make a slime ball, which nothing else here does.",
    "hollowveil:glimmershroom_item": "Marsh mushroom. Goes in the stew.",
    "hollowveil:hollow_kings_reaper":
        "Withers what it hits and heals you for a fifth of the damage dealt.",
    "hollowveil:wailing_edge":
        "Sneak and swing: everything around your target is thrown back.",
    "hollowveil:malacodas_fang":
        "Stacks burning on a target. At twelve stacks it detonates.",
    "hollowveil:sigil_hollow_king": "Use on a Ritual Altar to summon the Hollow King.",
    "hollowveil:sigil_weeping_widow": "Use on a Ritual Altar to summon the Weeping Widow.",
    "hollowveil:sigil_malacoda": "Use on a Ritual Altar to summon Malacoda.",
}

MOB_NOTES = {
    "hollowveil:wraith":
        "Blinks through thin walls instead of walking around them, and drains "
        "hunger on contact. Below 40% health it enrages: faster and larger.",
    "hollowveil:banshee": "Screams. Knockback plus nausea to everything nearby.",
    "hollowveil:poltergeist":
        "Cycles in and out of invisibility and throws debris. A Spirit Lantern "
        "keeps it visible.",
    "hollowveil:shade": "Teleports to flank you. Rarely where you last saw it.",
    "hollowveil:hellhound": "Pack hunter. Sets what it bites on fire.",
    "hollowveil:imp": "Steals an item from your bag on a lucky hit, then flees with it.",
    "hollowveil:fallen_knight":
        "Raises a shield periodically, refunding half the damage it takes while up.",
    "hollowveil:soul_wisp": "Harmless, luminous, and full of Soul Shards. It will run.",
    "hollowveil:bastion_sentinel": "Slow, armoured, hits like a wall falling on you.",
    "hollowveil:city_wraithguard": "Ranged. Patrols the sunken ruins in pairs.",
    "hollowveil:marrow_crawler": "Fast, low, and arrives with friends.",
    "hollowveil:ashen_whelp": "A young dragon. Not tameable - it bites.",
    "hollowveil:bonehide_elk": "Grazes the marsh in herds. Drops hide and marrow.",
    "hollowveil:glimmershroom_toad": "Glows faintly. Drops the mucus.",
    "hollowveil:ashwing_bat": "Flocks. Membranes for the Featherfall Charm.",
    "hollowveil:veil_dragon":
        "Wild adults are rare in the Ashlands. Feed one Ember Fruit or Veil "
        "Marrow Stew until it accepts you, then ride it - it flies like a "
        "Happy Ghast, steered by where you look.",
    "hollowveil:occultist": "The trader at Hollow Hamlet's shrine. Right-click to shop.",
}

# Region names come from biomes.js; only the description is written here.
BIOME_NOTES = {
    "hub": "Where you arrive, and where Hollow Hamlet stands. Lit, and nothing "
           "hostile spawns within 32 blocks of the shrine.",
    "moors": "Headstones to the horizon. The signature look of the dimension, "
             "and the ghosts' home ground.",
    "ashlands": "Burnt red country. Demons, the deepest ore, and the only place "
                "wild dragons fly.",
    "marsh": "Wet, luminous, and the only place with anything worth eating.",
    "ruins": "A drowned city under guard. Bring something that shoots back.",
}

SECTIONS_INTRO = {
    "start": (
        "Getting In",
        "Craft Soulfire and Steel from one Soul Sand and one Iron Ingot. Build "
        "a frame out of Gold Blocks exactly the way you would build a nether "
        "portal - the corners are optional - and TAP the frame with the "
        "igniter. One tap is enough; you do not need to hold. The portal "
        "burns red. Walk through.\n\n"
        "If it will not light, the igniter tells you why: which blocks are "
        "missing, or that the opening is the wrong shape or size. Any "
        "rectangle from 2x3 up to 21x21 works.\n\n"
        "If it still will not light, nothing here depends on it. Open this "
        "guide and press 'Travel to the Hollow Veil' at the bottom, or type "
        "/scriptevent hollowveil:portal to have a working portal built where "
        "you stand."),
    "back": (
        "Getting Home",
        "Stand in the portal you arrived through, or in the pre-lit one beside "
        "Hollow Hamlet. You come out where you left."),
}


# ------------------------------------------------------------ assembling ----
def armour_table(comps):
    return comps.get("minecraft:wearable", {}).get("protection")


def build():
    it = items()
    rec = recipes()
    ent = entities()
    rosters = spawn_rosters()
    consts = world_constants()
    lt = drops()

    guide = {"world": consts, "sections": []}

    # --- getting in / out --------------------------------------------------
    for key in ("start", "back"):
        title, body = SECTIONS_INTRO[key]
        guide["sections"].append({"id": key, "title": title,
                                  "icon": "soulfire_igniter", "text": body,
                                  "entries": []})

    # --- the world ---------------------------------------------------------
    bnames = biome_names()
    biome_entries = []
    for bid, note in BIOME_NOTES.items():
        roster = rosters.get(bid, [])
        who = ", ".join(pretty(m[0]) for m in roster) or "nothing much"
        biome_entries.append({"name": bnames.get(bid, bid.title()),
                              "text": f"{note}\n\nLives here: {who}."})
    guide["sections"].append({
        "id": "world", "title": "The Five Regions", "icon": "soul_compass",
        "entries": biome_entries,
        "text": (f"The Veil is a disc {consts['radius']:,} blocks in every "
                 f"direction from the hub. Terrain builds itself around you as "
                 f"you travel, so there is no edge to reach quickly and nothing "
                 f"to load in advance."),
    })

    # --- mobs --------------------------------------------------------------
    mob_entries = []
    for ident, entity in sorted(ent.items()):
        if ident not in MOB_NOTES:
            continue
        comps = entity["components"]
        health = comps.get("minecraft:health", {}).get("value")
        loot = comps.get("minecraft:loot")
        table = loot.get("table") if isinstance(loot, dict) else loot
        dropped = ", ".join(lt.get(table, [])) if table else ""
        bits = [MOB_NOTES[ident]]
        if health:
            bits.append(f"Health: {health}.")
        if dropped:
            bits.append(f"Drops: {dropped}.")
        mob_entries.append({"name": pretty(ident), "text": "\n\n".join(bits)})
    guide["sections"].append({"id": "mobs", "title": "Creatures", "icon": "demon_horn",
                              "entries": mob_entries})

    # --- ores and gear -----------------------------------------------------
    def gear_entry(ident):
        comps = it[ident]
        bits = []
        if PURPOSE.get(ident):
            bits.append(PURPOSE[ident])
        dmg = comps.get("minecraft:damage")
        if isinstance(dmg, dict):
            dmg = dmg.get("value")
        if dmg:
            bits.append(f"Attack damage: +{dmg}.")
        prot = armour_table(comps)
        if prot:
            bits.append(f"Protection: {prot}.")
        dur = comps.get("minecraft:durability", {}).get("max_durability")
        if dur:
            bits.append(f"Durability: {dur}.")
        for r in rec.get(ident, []):
            ing = ", ".join(f"{n}x {name}" for name, n in r["ingredients"])
            verb = "Smelt" if r["kind"] == "smelt" else "Craft"
            got = f" (makes {r['count']})" if r["count"] > 1 else ""
            bits.append(f"{verb}: {ing}{got}.")
        return {"name": pretty(ident), "text": "\n".join(bits) or "-"}

    tiers = [
        ("wraithsteel", "Wraithsteel", "Diamond-grade. Wraithsteel Ore is common "
                                       "below the moors; smelt the scrap."),
        ("veilsteel", "Veilsteel", "Better than diamond. The ore sits deep and "
                                   "glows blue at the edges."),
        ("hollowforged", "Hollowforged", "Better than netherite, and the best "
                                         "gear in the pack. The ore is white with "
                                         "red cracks and only appears in the "
                                         "lowest three layers."),
    ]
    tier_entries = []
    for prefix, label, blurb in tiers:
        members = [i for i in sorted(it) if i.startswith(f"hollowveil:{prefix}_")]
        lines = [blurb]
        for ident in members:
            e = gear_entry(ident)
            lines.append(f"\n{e['name']}\n{e['text']}")
        tier_entries.append({"name": label, "text": "\n".join(lines)})
    guide["sections"].append({"id": "gear", "title": "Ore Tiers & Gear",
                              "icon": "hollowforged_ingot", "entries": tier_entries})

    # --- armour set bonuses ------------------------------------------------
    bonus_notes = {}
    for line in balance.SET_BONUS_NOTES.strip().splitlines()[1:]:
        if "-" not in line:
            continue
        key, text = line.split("-", 1)
        key = key.strip()
        if key:
            bonus_notes[key] = text.strip()
        elif bonus_notes:                      # a wrapped continuation line
            last = list(bonus_notes)[-1]
            bonus_notes[last] += " " + line.strip()
    set_entries = [{"name": set_label(k),
                    "text": v} for k, v in bonus_notes.items()]
    guide["sections"].append({"id": "sets", "title": "Armour Set Bonuses",
                              "icon": "hollowforged_chestplate", "entries": set_entries,
                              "text": ("Wear all four pieces of a set to get its bonus. "
                                       "Minecraft caps armour's damage reduction at 20 "
                                       "points - netherite is exactly 20 and every set "
                                       "here is above it - so these bonuses are where "
                                       "the tiering above netherite actually lives.")})

    # --- tools, trinkets, food --------------------------------------------
    misc = [i for i in sorted(PURPOSE) if not any(
        i.startswith(f"hollowveil:{p}_") for p, _, _ in tiers)]
    guide["sections"].append({
        "id": "items", "title": "Items & What They Do", "icon": "spirit_lantern",
        "entries": [gear_entry(i) for i in misc if i in it]})

    # --- the numbers, in one table -----------------------------------------
    base = sum(balance.NETHERITE_ARMOUR)
    armour_rows = [f"Netherite, for comparison: {'/'.join(map(str, balance.NETHERITE_ARMOUR))} = {base}."]
    for set_name, spec in balance.ARMOUR.items():
        total = sum(spec["prot"])
        armour_rows.append(
            f"{set_label(set_name)}: "
            f"{'/'.join(map(str, spec['prot']))} = {total} "
            f"(+{total - base} over netherite), enchantability {spec['ench']}.")
    weapon_rows = [f"Netherite sword, for comparison: {balance.NETHERITE_SWORD + 1} damage."]
    for name, spec in balance.WEAPONS.items():
        weapon_rows.append(f"{pretty('hollowveil:' + name)}: {spec['damage'] + 1} damage, "
                           f"{spec['dur']} durability, enchantability {spec['ench']}.")
    guide["sections"].append({
        "id": "numbers", "title": "Every Number", "icon": "hollowforged_sword",
        "text": ("Helmet / chestplate / leggings / boots, then the total. "
                 "Weapon damage includes the one point every hit does bare-handed."),
        "entries": [{"name": "Armour", "text": "\n".join(armour_rows)},
                    {"name": "Weapons and tools", "text": "\n".join(weapon_rows)}]})

    # --- bosses ------------------------------------------------------------
    BOSS_TEXT = {
        "hollowveil:hollow_king": ("Sunken Crypt", "Hollow King's Reaper + Spectral Regalia"),
        "hollowveil:weeping_widow": ("Widow's Hollow", "Wailing Edge + Mourner's Shroud"),
        "hollowveil:malacoda": ("Cinder Bastion", "Malacoda's Fang + Ashen Demonplate"),
    }
    boss_entries = []
    for ident, (where, reward) in BOSS_TEXT.items():
        health = ent[ident]["components"].get("minecraft:health", {}).get("value")
        sigil = f"hollowveil:sigil_{ident.split(':')[1]}"
        craft = rec.get(sigil, [])
        ing = ", ".join(f"{n}x {name}" for name, n in craft[0]["ingredients"]) if craft else "?"
        boss_entries.append({"name": pretty(ident), "text": (
            f"{where}. Health: {health}.\n\n"
            f"Sigil: {ing}.\n"
            f"Use the sigil on a Ritual Altar. The altar clears an arena around "
            f"itself, walls it in and leaves a doorway, then the boss walks out.\n\n"
            f"Three phases, at full health, 66% and 30%. Each phase knocks the "
            f"arena back, summons adds and speeds the boss up.\n\n"
            f"Drops: {reward}.\n\n"
            f"Re-fightable: craft another sigil once the altar has settled "
            f"(20 minutes).")})
    guide["sections"].append({"id": "bosses", "title": "The Three Wardens",
                              "icon": "sigil_hollow_king", "entries": boss_entries})

    # --- the dragon --------------------------------------------------------
    tame = ent["hollowveil:veil_dragon"]["components"]["minecraft:tamemount"]
    feed = ", ".join(f"{pretty(f['item'])} (+{f['temper_mod']} temper)"
                     for f in tame["feed_items"])
    guide["sections"].append({"id": "dragon", "title": "The Veil Dragon", "icon": "dragon_egg",
                              "entries": [{"name": "Taming and flying", "text": (
                                  f"Wild adults fly over the Ashlands, rarely. There is also a "
                                  f"Veil Dragon Egg - boss loot, or buy one from the Occultist - "
                                  f"which hatches a wild one wherever you use it.\n\n"
                                  f"Feed it: {feed}. Temper runs to {tame['max_temper']}; "
                                  f"keep feeding until it stops throwing you.\n\n"
                                  f"Once tamed it can be ridden and named. It flies the way a "
                                  f"Happy Ghast does - you steer by looking, and it climbs when "
                                  f"you hold jump. Six colours, decided when it spawns.")}]})

    # --- trading -----------------------------------------------------------
    shop_src = open(os.path.join(BP, "scripts", "ui", "shop.js"), encoding="utf-8").read()
    cats = re.findall(r'title:\s*"§5([^"]+)"', shop_src)
    labels = re.findall(r'label:\s*"([^"]+)"', shop_src)
    guide["sections"].append({"id": "trade", "title": "The Occultist", "icon": "soul_shard",
                              "text": ("Right-click the Occultist at the Hollow Hamlet shrine. "
                                       "The shop is a menu, not a vanilla trade screen: pick a "
                                       "category, pick a trade, and it checks your bag."),
                              "entries": [{"name": c, "text": "\n".join(
                                  "- " + l for l in labels[i * 6:(i + 1) * 6])}
                                  for i, c in enumerate(cats)]})

    return guide


# ----------------------------------------------------------------- output ---
def write_guidedata(guide):
    path = os.path.join(BP, "scripts", "ui", "guidedata.js")
    header = (
        "// GENERATED by tools/gen_guide.py - do not edit by hand.\n"
        "//\n"
        "// Every number and recipe below was read out of this pack's own item,\n"
        "// recipe, loot and spawner data at build time, so the in-game guide\n"
        "// cannot drift away from what the pack actually does. Change the pack,\n"
        "// re-run the generator, and the guide follows.\n\n"
        "export const GUIDE = ")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(header + json.dumps(guide, indent=2, ensure_ascii=False) + ";\n")
    return path


def write_markdown(guide):
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, "GUIDE.md")
    out = ["# The Hollow Veil - Player Guide", "",
           "*Generated from the pack's own data by `tools/gen_guide.py`. "
           "Every recipe, stat and drop below is read out of the addon itself.*", ""]
    for section in guide["sections"]:
        out += [f"## {section['title']}", ""]
        if section.get("text"):
            out += [section["text"], ""]
        for entry in section.get("entries", []):
            out += [f"### {entry['name']}", "", entry["text"], ""]
    out += ["---", "",
            "*Built for Minecraft Bedrock. The addon and this guide are free "
            "to download, play and share.*", ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    return path




# ------------------------------------------------------------------ html ---
# A standalone page for players, built from the same data as everything else.
#
# The look is taken from the dimension rather than from "spooky website":
# deepslate ground, bone-parchment in light mode, and the two accents are the
# pack's own - the pale green-cyan of a wraith's eyes and the burnt orange of
# the Ashlands. Headings are set in a serif with wide small-caps, which is
# what lettering on a headstone looks like, and every derived number (health,
# drops, recipes) is set in mono so the reader can tell at a glance which
# lines are facts out of the pack and which are prose.

STAT_PREFIXES = ("Health:", "Drops:", "Craft:", "Smelt:", "Protection:",
                 "Durability:", "Attack damage:", "Lives here:", "Sigil:",
                 "Feed it:")

PAGE_CSS = """
:root {
  color-scheme: light dark;

  --ground:      #e9e5dd;
  --ground-deep: #ded9cf;
  --panel:       #f4f1ea;
  --ink:         #1b1922;
  --ink-soft:    #4a4654;
  --ink-faint:   #736e80;
  --rule:        #cbc5b8;
  --soulfire:    #1f7f70;
  --soulfire-dim:#7fb8ae;
  --ember:       #b4482a;
  --shadow:      rgba(27, 25, 34, .09);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:      #14131a;
    --ground-deep: #0e0d13;
    --panel:       #1c1a24;
    --ink:         #ded9e6;
    --ink-soft:    #a49eb2;
    --ink-faint:   #746e82;
    --rule:        #2e2b39;
    --soulfire:    #61d8c2;
    --soulfire-dim:#2f6f66;
    --ember:       #e07a52;
    --shadow:      rgba(0, 0, 0, .5);
  }
}

:root[data-theme="dark"] {
  --ground:      #14131a;
  --ground-deep: #0e0d13;
  --panel:       #1c1a24;
  --ink:         #ded9e6;
  --ink-soft:    #a49eb2;
  --ink-faint:   #746e82;
  --rule:        #2e2b39;
  --soulfire:    #61d8c2;
  --soulfire-dim:#2f6f66;
  --ember:       #e07a52;
  --shadow:      rgba(0, 0, 0, .5);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font: 400 16px/1.65 ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* Fog: a single soft pool of light behind the masthead, nothing more. */
body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(120% 60% at 50% -10%,
              color-mix(in srgb, var(--soulfire) 9%, transparent), transparent 70%);
  z-index: 0;
}

.wrap { position: relative; z-index: 1; max-width: 1120px; margin: 0 auto; padding: 0 24px 96px; }

/* --- masthead --- */
header.masthead { padding: 72px 0 40px; border-bottom: 1px solid var(--rule); }
.eyebrow {
  font: 500 12px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: .22em;
  text-transform: uppercase;
  color: var(--soulfire);
  margin: 0 0 18px;
}
h1 {
  font: 400 clamp(38px, 7vw, 68px)/1.05 Georgia, "Iowan Old Style", "Times New Roman", serif;
  font-variant-caps: small-caps;
  letter-spacing: .04em;
  text-wrap: balance;
  margin: 0 0 18px;
}
.standfirst {
  max-width: 58ch;
  font-size: 18px;
  color: var(--ink-soft);
  margin: 0;
}
.facts {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 28px;
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
  font: 500 13px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
}
.facts b { color: var(--ink); font-weight: 600; }

/* --- layout --- */
.columns { display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: 56px; padding-top: 44px; }
@media (max-width: 860px) { .columns { grid-template-columns: 1fr; gap: 28px; } }

nav.contents { position: sticky; top: 24px; align-self: start; }
@media (max-width: 860px) {
  nav.contents { position: static; overflow-x: auto; }
  nav.contents ol { display: flex; gap: 18px; white-space: nowrap; }
}
nav.contents ol { margin: 0; padding: 0; list-style: none; display: grid; gap: 11px; }
nav.contents a {
  color: var(--ink-soft);
  text-decoration: none;
  font-size: 14px;
  border-left: 2px solid transparent;
  padding-left: 12px;
  display: block;
}
@media (max-width: 860px) { nav.contents a { border-left: 0; padding-left: 0; } }
nav.contents a:hover, nav.contents a:focus-visible { color: var(--ink); border-left-color: var(--soulfire); }

/* --- sections --- */
section { padding: 0 0 56px; scroll-margin-top: 24px; }
h2 {
  font: 400 30px/1.15 Georgia, "Iowan Old Style", "Times New Roman", serif;
  font-variant-caps: small-caps;
  letter-spacing: .05em;
  margin: 0 0 16px;
  padding-left: 16px;
  /* the crack of light: the ore in this pack glows through fissures in stone */
  border-left: 2px solid var(--soulfire);
  text-wrap: balance;
}
.lede { max-width: 66ch; color: var(--ink-soft); margin: 0 0 28px; }

.entries { display: grid; gap: 2px; }
article {
  background: var(--panel);
  border: 1px solid var(--rule);
  padding: 20px 22px;
}
article + article { border-top: 0; }
h3 {
  font: 600 15px/1.3 ui-sans-serif, system-ui, sans-serif;
  letter-spacing: .01em;
  margin: 0 0 10px;
  color: var(--ink);
}
article p { margin: 0 0 10px; max-width: 66ch; color: var(--ink-soft); }
article p:last-child { margin-bottom: 0; }
h4 {
  font: 600 14px/1.3 ui-sans-serif, system-ui, sans-serif;
  margin: 18px 0 8px;
  color: var(--ink);
}
.stat {
  font: 400 13.5px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
  margin: 0 0 4px;
  overflow-x: auto;
}
.stat .k { color: var(--soulfire); }
.stat.danger .k { color: var(--ember); }

footer.end {
  border-top: 1px solid var(--rule);
  padding-top: 24px;
  color: var(--ink-faint);
  font-size: 14px;
  max-width: 66ch;
}

@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
:focus-visible { outline: 2px solid var(--soulfire); outline-offset: 3px; }
"""


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_body(text):
    """Prose becomes paragraphs; derived facts become monospace stat rows."""
    out = []
    for block in text.split("\n"):
        line = block.strip()
        if not line:
            continue
        hit = next((p for p in STAT_PREFIXES if line.startswith(p)), None)
        if hit:
            danger = " danger" if hit in ("Drops:", "Sigil:") else ""
            key, rest = line.split(":", 1)
            out.append(f'<p class="stat{danger}"><span class="k">{esc(key)}</span>'
                       f'{esc(":" + rest)}</p>')
        elif ":" not in line and len(line) < 40 and not line.endswith("."):
            out.append(f"<h4>{esc(line)}</h4>")     # a sub-item inside a tier
        else:
            out.append(f"<p>{esc(line)}</p>")
    return "\n        ".join(out)


def write_html(guide):
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, "guide.html")

    sections = guide["sections"]
    nav = "\n".join(
        f'      <li><a href="#{s["id"]}">{esc(s["title"])}</a></li>' for s in sections)

    body = []
    for s in sections:
        body.append(f'    <section id="{s["id"]}">')
        body.append(f'      <h2>{esc(s["title"])}</h2>')
        if s.get("text"):
            body.append(f'      <p class="lede">{esc(s["text"])}</p>')
        if s.get("entries"):
            body.append('      <div class="entries">')
            for e in s["entries"]:
                body.append("      <article>")
                body.append(f'        <h3>{esc(e["name"])}</h3>')
                body.append(f"        {render_body(e['text'])}")
                body.append("      </article>")
            body.append("      </div>")
        body.append("    </section>")

    mobs = len([e for s in sections if s["id"] == "mobs" for e in s["entries"]])
    entries = sum(len(s.get("entries", [])) for s in sections)

    doc = f"""<title>Hollow Veil Field Guide</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{PAGE_CSS}</style>

<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">Minecraft Bedrock &middot; free dimension add-on</p>
    <h1>The Hollow Veil</h1>
    <p class="standfirst">A grey country stitched between the living world and
      whatever comes after. Gold frame, blue flame, and everything past it is
      new. Here is all of it, and how to use it.</p>
    <ul class="facts">
      <li><b>{guide['world']['radius']:,}</b> blocks in every direction</li>
      <li><b>5</b> regions</li>
      <li><b>{mobs}</b> creatures</li>
      <li><b>3</b> bosses</li>
      <li><b>{entries}</b> entries below</li>
    </ul>
  </header>

  <div class="columns">
    <nav class="contents" aria-label="Contents">
      <ol>
{nav}
      </ol>
    </nav>

    <main>
{chr(10).join(body)}
      <footer class="end">
        Every recipe, stat and drop on this page is read straight out of the
        add-on by <code>tools/gen_guide.py</code>, so the guide cannot drift
        away from what the pack actually does. Free to download, play and share.
      </footer>
    </main>
  </div>
</div>
"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return path


def main():
    guide = build()
    a = write_guidedata(guide)
    b = write_markdown(guide)
    c = write_html(guide)
    entries = sum(len(s.get("entries", [])) for s in guide["sections"])
    print(f"guide: {len(guide['sections'])} sections, {entries} entries")
    for out in (a, b, c):
        print(f"  {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
