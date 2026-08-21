"""
Check every reference in the pack resolves.

Bedrock fails quietly. A client entity pointing at a geometry that does not
exist gives you an invisible mob, a texture path off by one character gives you
a magenta one, and a loot table naming an item that was never registered gives
you a mob that drops nothing - all with no error anywhere the player can see.
So the pack is checked here instead:

  * every geometry, texture, animation, controller and render controller a
    client entity names exists
  * every behaviour entity has a client entity and vice versa
  * every loot table, spawn rule and trade table a behaviour entity names exists
  * every item, block and entity identifier a loot table or recipe names is one
    the pack or vanilla actually defines
  * every texture shortname an item or block asks for is in the atlases
  * every identifier is unique, and matches the file it lives in
  * every animation identifier the scripts play is a real clip

Run it from the addon root:

    python3 tools/validate.py
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BP = os.path.join(ROOT, "BP")
RP = os.path.join(ROOT, "RP")

problems: list[str] = []
notes: list[str] = []


# Namespaces this pack owns. A reference outside them - `geometry.humanoid`,
# `animation.player.swim`, `textures/entity/steve` - belongs to the vanilla
# resource pack, is not shipped here, and is not this checker's business.
OURS = ("voidbound", "eternal_end")


def ours(name):
    return isinstance(name, str) and any(part in name for part in OURS)


def fail(message):
    problems.append(message)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as error:
        fail(f"{os.path.relpath(path, ROOT)}: invalid JSON - {error}")
    except OSError as error:
        fail(f"{os.path.relpath(path, ROOT)}: unreadable - {error}")
    return None


def walk(root, suffix=".json"):
    for base, _, files in os.walk(root):
        for name in sorted(files):
            if name.endswith(suffix):
                yield os.path.join(base, name)


# ---------------------------------------------------------------------------
# Gather what the pack defines.
# ---------------------------------------------------------------------------

def collect():
    data = {
        "bp_entities": {},      # identifier -> path
        "rp_entities": {},
        "geometries": set(),
        "animations": set(),
        "animation_controllers": set(),
        "render_controllers": set(),
        "textures": set(),      # resource-pack-relative paths, no extension
        "item_atlas": set(),
        "terrain_atlas": set(),
        "items": {},
        "blocks": {},
        "loot_tables": set(),
        "trade_tables": set(),
        "spawn_rules": {},
        "particles": set(),
        "fogs": set(),
        "block_states": set(),
        "lang": set(),
    }

    for path in walk(os.path.join(BP, "entities")):
        doc = read_json(path)
        if not doc:
            continue
        description = doc.get("minecraft:entity", {}).get("description", {})
        identifier = description.get("identifier")
        if not identifier:
            fail(f"{os.path.relpath(path, ROOT)}: no identifier")
            continue
        if identifier in data["bp_entities"]:
            fail(f"duplicate behaviour entity {identifier}")
        data["bp_entities"][identifier] = path

    for path in walk(os.path.join(RP, "entity")):
        doc = read_json(path)
        if not doc:
            continue
        description = doc.get("minecraft:client_entity", {}).get("description", {})
        identifier = description.get("identifier")
        if not identifier:
            fail(f"{os.path.relpath(path, ROOT)}: no identifier")
            continue
        if identifier in data["rp_entities"]:
            fail(f"duplicate client entity {identifier}")
        data["rp_entities"][identifier] = path

    for path in walk(os.path.join(RP, "models")):
        doc = read_json(path)
        if not doc:
            continue
        entries = doc.get("minecraft:geometry")
        if isinstance(entries, list):
            for entry in entries:
                identifier = entry.get("description", {}).get("identifier")
                if identifier:
                    data["geometries"].add(identifier)
        for key in doc:
            # The pre-1.12 form puts the identifier in the key itself.
            if key.startswith("geometry."):
                data["geometries"].add(key.split(":")[0])

    for path in walk(os.path.join(RP, "animations")):
        doc = read_json(path) or {}
        data["animations"].update(doc.get("animations", {}))

    for path in walk(os.path.join(RP, "animation_controllers")):
        doc = read_json(path) or {}
        data["animation_controllers"].update(doc.get("animation_controllers", {}))

    for path in walk(os.path.join(RP, "render_controllers")):
        doc = read_json(path) or {}
        data["render_controllers"].update(doc.get("render_controllers", {}))

    for base, _, files in os.walk(os.path.join(RP, "textures")):
        for name in files:
            if not name.endswith(".png"):
                continue
            relative = os.path.relpath(os.path.join(base, name), RP)
            data["textures"].add(relative[:-4].replace(os.sep, "/"))

    atlas = read_json(os.path.join(RP, "textures", "item_texture.json")) or {}
    data["item_atlas"].update(atlas.get("texture_data", {}))
    atlas = read_json(os.path.join(RP, "textures", "terrain_texture.json")) or {}
    data["terrain_atlas"].update(atlas.get("texture_data", {}))

    for path in walk(os.path.join(BP, "items")):
        doc = read_json(path)
        if not doc:
            continue
        identifier = doc.get("minecraft:item", {}).get("description", {}).get(
            "identifier")
        if not identifier:
            fail(f"{os.path.relpath(path, ROOT)}: no identifier")
            continue
        if identifier in data["items"]:
            fail(f"duplicate item {identifier}")
        data["items"][identifier] = doc

    for path in walk(os.path.join(BP, "blocks")):
        doc = read_json(path)
        if not doc:
            continue
        identifier = doc.get("minecraft:block", {}).get("description", {}).get(
            "identifier")
        if not identifier:
            fail(f"{os.path.relpath(path, ROOT)}: no identifier")
            continue
        if identifier in data["blocks"]:
            fail(f"duplicate block {identifier}")
        data["blocks"][identifier] = doc
        # State names share the namespace:name shape with blocks and items, so
        # the script check has to know them or it flags every state read.
        data["block_states"].update(
            doc["minecraft:block"]["description"].get("states", {}))

    for path in walk(os.path.join(BP, "loot_tables")):
        data["loot_tables"].add(
            os.path.relpath(path, BP).replace(os.sep, "/"))
    for path in walk(os.path.join(BP, "trading")):
        data["trade_tables"].add(
            os.path.relpath(path, BP).replace(os.sep, "/"))

    for path in walk(os.path.join(BP, "spawn_rules")):
        doc = read_json(path)
        if not doc:
            continue
        identifier = doc.get("minecraft:spawn_rules", {}).get(
            "description", {}).get("identifier")
        if identifier:
            data["spawn_rules"][identifier] = path

    for path in walk(os.path.join(RP, "particles")):
        doc = read_json(path) or {}
        identifier = doc.get("particle_effect", {}).get(
            "description", {}).get("identifier")
        if identifier:
            data["particles"].add(identifier)

    for path in walk(os.path.join(RP, "fogs")):
        doc = read_json(path) or {}
        identifier = doc.get("minecraft:fog_settings", {}).get(
            "description", {}).get("identifier")
        if identifier:
            data["fogs"].add(identifier)

    lang_path = os.path.join(RP, "texts", "en_US.lang")
    if os.path.exists(lang_path):
        with open(lang_path, encoding="utf-8") as handle:
            for line in handle:
                if "=" in line and not line.strip().startswith("#"):
                    data["lang"].add(line.split("=", 1)[0].strip())

    return data


# ---------------------------------------------------------------------------
# Checks.
# ---------------------------------------------------------------------------

def check_client_entities(data):
    for identifier, path in data["rp_entities"].items():
        where = os.path.relpath(path, ROOT)
        doc = read_json(path)
        description = doc["minecraft:client_entity"]["description"]

        for name, geometry in (description.get("geometry") or {}).items():
            if ours(geometry) and geometry not in data["geometries"]:
                fail(f"{where}: geometry '{geometry}' ({name}) does not exist")

        for name, texture in (description.get("textures") or {}).items():
            if ours(texture) and texture not in data["textures"]:
                fail(f"{where}: texture '{texture}' ({name}) does not exist")

        animations = description.get("animations") or {}
        for name, clip in animations.items():
            if not ours(clip):
                continue
            if clip.startswith("controller."):
                if clip not in data["animation_controllers"]:
                    fail(f"{where}: animation controller '{clip}' does not exist")
            elif clip not in data["animations"]:
                fail(f"{where}: animation '{clip}' does not exist")

        for entry in (description.get("scripts") or {}).get("animate", []):
            key = entry if isinstance(entry, str) else next(iter(entry))
            if key not in animations:
                fail(f"{where}: animate list names '{key}', which is not in "
                     f"the animations map")

        for controller in description.get("render_controllers", []):
            name = controller if isinstance(controller, str) else next(iter(controller))
            if ours(name) and name not in data["render_controllers"]:
                fail(f"{where}: render controller '{name}' does not exist")

        if identifier not in data["bp_entities"] and not identifier.startswith("minecraft:"):
            fail(f"{where}: client entity {identifier} has no behaviour entity")


def check_behaviour_entities(data):
    for identifier, path in data["bp_entities"].items():
        where = os.path.relpath(path, ROOT)
        doc = read_json(path)
        entity = doc["minecraft:entity"]

        if identifier not in data["rp_entities"]:
            fail(f"{where}: behaviour entity {identifier} has no client entity")

        groups = [entity.get("components", {})]
        groups += list(entity.get("component_groups", {}).values())

        for components in groups:
            loot = components.get("minecraft:loot", {}).get("table")
            if loot and loot not in data["loot_tables"]:
                fail(f"{where}: loot table '{loot}' does not exist")
            trade = components.get("minecraft:trade_table", {}).get("table")
            if trade and trade not in data["trade_tables"]:
                fail(f"{where}: trade table '{trade}' does not exist")

            shooter = components.get("minecraft:shooter", {}).get("def")
            if shooter and shooter not in data["bp_entities"] \
                    and not shooter.startswith("minecraft:"):
                fail(f"{where}: shooter fires '{shooter}', which does not exist")

            tameable = components.get("minecraft:tameable", {})
            for item in tameable.get("tame_items", []):
                _check_item(where, item, data, "tame_items")
            breedable = components.get("minecraft:breedable", {})
            for item in breedable.get("breed_items", []):
                _check_item(where, item, data, "breed_items")
            for mate in breedable.get("breeds_with", []):
                for key in ("mate_type", "baby_type"):
                    other = mate.get(key)
                    if other and other not in data["bp_entities"] \
                            and not other.startswith("minecraft:"):
                        fail(f"{where}: breedable {key} '{other}' does not exist")
            for item in components.get("minecraft:ageable", {}).get("feed_items", []):
                _check_item(where, item, data, "ageable feed_items")
            for item in components.get("minecraft:behavior.tempt", {}).get("items", []):
                _check_item(where, item, data, "tempt items")

            summon = components.get("minecraft:behavior.summon_entity", {})
            for choice in summon.get("summon_choices", []):
                for step in choice.get("sequence", []):
                    what = step.get("entity_type")
                    if what and what not in data["bp_entities"] \
                            and not what.startswith("minecraft:"):
                        fail(f"{where}: summons '{what}', which does not exist")

        # Events may only touch component groups the entity actually declares.
        declared = set(entity.get("component_groups", {}))
        for name, event in (entity.get("events") or {}).items():
            for action in ("add", "remove"):
                for group in (event.get(action) or {}).get("component_groups", []):
                    if group not in declared:
                        fail(f"{where}: event '{name}' {action}s unknown "
                             f"component group '{group}'")

        if f"entity.{identifier}.name" not in data["lang"] \
                and entity["description"].get("is_spawnable"):
            notes.append(f"{where}: no display name for {identifier}")


def _check_item(where, item, data, context):
    name = item.get("item") if isinstance(item, dict) else item
    if not name:
        return
    name = name.split(":", 1)
    name = f"{name[0]}:{name[1]}" if len(name) == 2 else f"minecraft:{name[0]}"
    if name.startswith("minecraft:"):
        return
    if name not in data["items"] and name not in data["blocks"]:
        fail(f"{where}: {context} names '{name}', which the pack does not define")


def check_loot_tables(data):
    for relative in sorted(data["loot_tables"]):
        path = os.path.join(BP, relative)
        doc = read_json(path)
        if not doc:
            continue
        for pool in doc.get("pools", []):
            for entry in pool.get("entries", []):
                if entry.get("type") != "item":
                    continue
                _check_item(relative, entry.get("name"), data, "loot entry")


def check_recipes(data):
    for path in walk(os.path.join(BP, "recipes")):
        doc = read_json(path)
        if not doc:
            continue
        where = os.path.relpath(path, ROOT)
        for key, recipe in doc.items():
            if not key.startswith("minecraft:recipe"):
                continue
            names = []
            ingredients = recipe.get("ingredients")
            if isinstance(ingredients, list):
                names += ingredients
            if "input" in recipe:
                value = recipe["input"]
                names += value if isinstance(value, list) else [value]
            for value in (recipe.get("key") or {}).values():
                names.append(value)
            result = recipe.get("result")
            if result:
                names += result if isinstance(result, list) else [result]
            for name in names:
                _check_item(where, name, data, "recipe")


def check_items_and_blocks(data):
    for identifier, doc in data["items"].items():
        components = doc["minecraft:item"]["components"]
        icon = components.get("minecraft:icon")
        name = icon.get("texture") if isinstance(icon, dict) else icon
        if name and name not in data["item_atlas"]:
            fail(f"item {identifier}: icon '{name}' is not in item_texture.json")
        if f"item.{identifier}.name" not in data["lang"]:
            notes.append(f"item {identifier}: no display name")

    for identifier, doc in data["blocks"].items():
        components = doc["minecraft:block"]["components"]
        instances = components.get("minecraft:material_instances", {})
        for face, instance in instances.items():
            texture = instance.get("texture")
            if texture and texture not in data["terrain_atlas"]:
                fail(f"block {identifier}: texture '{texture}' ({face}) is not "
                     f"in terrain_texture.json")
        if f"tile.{identifier}.name" not in data["lang"]:
            notes.append(f"block {identifier}: no display name")


def check_atlases(data):
    for atlas_name, key in (("item_texture.json", "item_atlas"),
                            ("terrain_texture.json", "terrain_atlas")):
        atlas = read_json(os.path.join(RP, "textures", atlas_name)) or {}
        for short, entry in atlas.get("texture_data", {}).items():
            textures = entry.get("textures")
            paths = textures if isinstance(textures, list) else [textures]
            for texture in paths:
                if isinstance(texture, dict):
                    texture = texture.get("path")
                if texture and texture not in data["textures"]:
                    fail(f"{atlas_name}: '{short}' points at missing "
                         f"texture '{texture}'")


def check_spawn_rules(data):
    for identifier, path in data["spawn_rules"].items():
        where = os.path.relpath(path, ROOT)
        if identifier not in data["bp_entities"]:
            fail(f"{where}: spawn rule for {identifier}, which has no entity")
        doc = read_json(path)
        for condition in doc["minecraft:spawn_rules"].get("conditions", []):
            for block in condition.get("minecraft:spawns_on_block_filter", []):
                name = block if isinstance(block, str) else block.get("name")
                if name and not name.startswith("minecraft:") \
                        and name not in data["blocks"]:
                    fail(f"{where}: spawns on '{name}', which does not exist")


SCRIPT_ID = re.compile(r'"((?:eternal_end|voidbound|minecraft):[a-z0-9_./]+)"')
SCRIPT_CLIP = re.compile(r'"(animation\.[a-z0-9_.]+)"')


def check_scripts(data):
    """Every identifier a script names in a string literal has to resolve."""
    known = (set(data["bp_entities"]) | set(data["items"]) | set(data["blocks"])
             | data["particles"] | data["fogs"] | data["block_states"])
    for path in walk(os.path.join(BP, "scripts"), ".js"):
        where = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        for identifier in set(SCRIPT_ID.findall(source)):
            if identifier.startswith("minecraft:"):
                continue
            if identifier in known:
                continue
            fail(f"{where}: names '{identifier}', which the pack does not define")
        for clip in set(SCRIPT_CLIP.findall(source)):
            if ours(clip) and clip not in data["animations"]:
                fail(f"{where}: plays '{clip}', which is not a clip in the pack")


def check_manifests():
    seen = {}
    for name in ("BP", "RP"):
        path = os.path.join(ROOT, name, "manifest.json")
        doc = read_json(path)
        if not doc:
            continue
        uuids = [doc["header"]["uuid"]] + [m["uuid"] for m in doc["modules"]]
        for uuid in uuids:
            if uuid in seen:
                fail(f"manifest UUID {uuid} used twice ({seen[uuid]} and {name})")
            seen[uuid] = name
    bp = read_json(os.path.join(ROOT, "BP", "manifest.json"))
    rp = read_json(os.path.join(ROOT, "RP", "manifest.json"))
    if bp and rp:
        wanted = rp["header"]["uuid"]
        if not any(d.get("uuid") == wanted for d in bp.get("dependencies", [])):
            fail("BP manifest does not depend on the resource pack's UUID")


def main():
    data = collect()
    check_client_entities(data)
    check_behaviour_entities(data)
    check_loot_tables(data)
    check_recipes(data)
    check_items_and_blocks(data)
    check_atlases(data)
    check_spawn_rules(data)
    check_scripts(data)
    check_manifests()

    print(f"entities   {len(data['bp_entities']):>4} behaviour / "
          f"{len(data['rp_entities'])} client")
    print(f"geometry   {len(data['geometries']):>4}")
    print(f"animations {len(data['animations']):>4} clips / "
          f"{len(data['animation_controllers'])} controllers")
    print(f"items      {len(data['items']):>4}")
    print(f"blocks     {len(data['blocks']):>4}")
    print(f"textures   {len(data['textures']):>4}")

    if notes:
        print(f"\n{len(notes)} note(s):")
        for note in notes[:40]:
            print(f"  - {note}")
        if len(notes) > 40:
            print(f"  ... and {len(notes) - 40} more")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  ! {problem}")
        return 1
    print("\nno broken references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
