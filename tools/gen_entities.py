#!/usr/bin/env python3
"""Emit every file a mob needs from one line of spec.

A Bedrock mob is five files that have to agree with each other: a behaviour
entity, a spawn rule, a loot table, a client entity, and a lang line. Written
by hand across twenty-two mobs that is a hundred-odd files and a guaranteed
drift - a texture renamed here, an identifier mistyped there, and the mob is
an invisible white box in game with nothing in the content log to say why.

So they are generated. The table below is the whole roster; everything else is
derived from it, which means the five files for a mob cannot disagree, and
adding a mob is one entry rather than five files.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------------------------------------------------------
# The roster
# --------------------------------------------------------------------------
# kind:      passive | hostile | boss
# size:      (width, height) collision box in blocks
# move:      walk | fly | hover  - decides navigation and movement components
# hp/dmg/spd: the numbers
# spawn:     None, or (weight, herd_min, herd_max, brightness_max, density)
# drops:     list of (item, weight, min, max); an ("", w, 0, 0) entry is a miss
# egg:       (base, overlay) spawn-egg colours
# extra:     components merged in last, for anything the shape above cannot say

VOID_STONE = ["minecraft:end_stone", "voidbound:shattered_end_stone",
              "voidbound:verdant_end_stone", "voidbound:crystalline_end_stone",
              "voidbound:glowspore_soil", "voidbound:bonespire_stone",
              "voidbound:mossy_end_stone", "voidbound:ashen_end_stone"]

MOBS = {}


def mob(name, title, kind, size, move, hp, dmg, spd, egg, drops,
        spawn=None, extra=None, tame=None, ride=False, scale=1.0):
    MOBS[name] = dict(title=title, kind=kind, size=size, move=move, hp=hp,
                      dmg=dmg, spd=spd, egg=egg, drops=drops, spawn=spawn,
                      extra=extra or {}, tame=tame, ride=ride, scale=scale)


# ---- bosses ---------------------------------------------------------------
mob("void_dragon", "Void Dragon", "boss", (4.5, 3.4), "fly", 320, 18, 0.42,
    ("#0B0714", "#FF3DFF"),
    [("voidbound:void_crystal", 1, 3, 6), ("voidbound:titan_core", 1, 1, 1),
     ("minecraft:dragon_breath", 1, 1, 2)],
    extra={"minecraft:fire_immune": {}, "minecraft:knockback_resistance": {"value": 1.0}})
mob("ender_overlord", "Ender Overlord", "boss", (3.6, 5.0), "hover", 400, 16, 0.30,
    ("#120826", "#FF6BFF"),
    [("voidbound:void_crystal", 1, 4, 8), ("voidbound:sovereign_crown", 1, 1, 1),
     ("minecraft:ender_pearl", 1, 4, 8)],
    extra={"minecraft:fire_immune": {}, "minecraft:knockback_resistance": {"value": 1.0}})
mob("end_king", "End King", "boss", (1.6, 3.6), "walk", 360, 20, 0.34,
    ("#1A0A2E", "#FFC65A"),
    [("voidbound:voidsteel_ingot", 1, 3, 6), ("voidbound:sovereign_crown", 1, 1, 1),
     ("voidbound:echo_shard", 1, 4, 9)],
    extra={"minecraft:knockback_resistance": {"value": 0.9}})

# ---- hostiles -------------------------------------------------------------
mob("void_stalker", "Void Stalker", "hostile", (1.4, 1.5), "walk", 34, 7, 0.34,
    ("#0D0718", "#C77BFF"),
    [("voidbound:void_chitin", 4, 1, 3), ("minecraft:ender_pearl", 2, 0, 1),
     ("", 3, 0, 0)],
    spawn=(6, 1, 2, 7, 2))
mob("purpur_golem", "Purpur Golem", "hostile", (1.6, 2.6), "walk", 60, 9, 0.22,
    ("#3A1152", "#E0A8FF"),
    [("minecraft:purpur_block", 5, 2, 5), ("voidbound:void_crystal", 1, 0, 1)],
    spawn=(4, 1, 1, 15, 1),
    extra={"minecraft:knockback_resistance": {"value": 0.8}})
mob("shulker_beast", "Shulker Beast", "hostile", (1.5, 1.7), "walk", 46, 8, 0.24,
    ("#2A1140", "#B27BFF"),
    [("minecraft:shulker_shell", 3, 1, 2), ("voidbound:void_chitin", 4, 1, 3)],
    spawn=(5, 1, 2, 7, 2),
    extra={"minecraft:knockback_resistance": {"value": 0.6}})
mob("corrupted_enderman", "Corrupted Enderman", "hostile", (0.9, 2.9), "walk", 44, 8, 0.32,
    ("#0A0612", "#FF3DFF"),
    [("minecraft:ender_pearl", 4, 1, 2), ("voidbound:void_crystal", 2, 0, 1)],
    spawn=(6, 1, 2, 7, 2))
mob("end_spider", "End Spider", "hostile", (1.6, 1.1), "walk", 28, 6, 0.36,
    ("#140828", "#A640FF"),
    [("minecraft:string", 5, 1, 3), ("voidbound:void_chitin", 3, 1, 2)],
    spawn=(7, 1, 3, 7, 3),
    extra={"minecraft:can_climb": {}})
mob("chorus_fiend", "Chorus Fiend", "hostile", (1.2, 2.6), "walk", 38, 7, 0.26,
    ("#2A0B44", "#D46BFF"),
    [("minecraft:chorus_fruit", 5, 2, 4), ("voidbound:lumen_berry", 2, 1, 2)],
    spawn=(5, 1, 2, 9, 2))
mob("obsidian_beast", "Obsidian Beast", "hostile", (1.9, 2.1), "walk", 72, 11, 0.28,
    ("#08060E", "#FF7A2E"),
    [("minecraft:obsidian", 5, 1, 3), ("voidbound:void_crystal", 2, 0, 1)],
    spawn=(3, 1, 1, 7, 1),
    extra={"minecraft:fire_immune": {},
           "minecraft:knockback_resistance": {"value": 0.85}})
mob("endermite_hive", "Endermite Hive", "hostile", (1.5, 1.0), "walk", 30, 5, 0.30,
    ("#170A2B", "#FF3DFF"),
    [("voidbound:void_chitin", 5, 1, 3), ("minecraft:ender_pearl", 2, 0, 1)],
    spawn=(6, 1, 2, 7, 2))
mob("void_wisp", "Void Wisp", "hostile", (0.8, 1.2), "hover", 16, 4, 0.36,
    ("#070510", "#6FF0FF"),
    [("voidbound:echo_shard", 4, 1, 2), ("voidbound:void_crystal", 1, 0, 1)],
    spawn=(7, 1, 3, 7, 3))
mob("void_slime", "Void Slime", "hostile", (1.3, 1.7), "walk", 32, 6, 0.24,
    ("#0A0714", "#A640FF"),
    [("minecraft:slime_ball", 5, 1, 3), ("voidbound:void_crystal", 1, 0, 1)],
    spawn=(6, 1, 3, 9, 3))
mob("teleporter", "Teleporter", "hostile", (1.0, 2.8), "walk", 40, 8, 0.33,
    ("#080611", "#63E8FF"),
    [("minecraft:ender_pearl", 5, 2, 3), ("voidbound:echo_shard", 2, 1, 2)],
    spawn=(5, 1, 1, 7, 2))
mob("end_crab", "End Crab", "hostile", (1.7, 1.0), "walk", 34, 7, 0.24,
    ("#0B0714", "#5BE9FF"),
    [("voidbound:void_chitin", 5, 2, 4), ("voidbound:void_crystal", 2, 0, 1)],
    spawn=(5, 1, 2, 11, 2),
    extra={"minecraft:knockback_resistance": {"value": 0.5}})
mob("ender_ghost", "Ender Ghost", "hostile", (1.1, 2.9), "hover", 36, 9, 0.30,
    ("#070510", "#7CF2FF"),
    [("voidbound:echo_shard", 4, 1, 3), ("minecraft:ender_pearl", 2, 0, 1)],
    spawn=(4, 1, 1, 5, 1))

# ---- passives -------------------------------------------------------------
mob("astral_whale", "Astral Whale", "passive", (4.0, 3.0), "fly", 120, 0, 0.22,
    ("#0E0A1C", "#FFC65A"),
    [("voidbound:astral_shard", 4, 1, 3), ("voidbound:void_crystal", 2, 1, 2)],
    spawn=(2, 1, 1, 15, 1), scale=1.0)
mob("sky_ray", "Sky Ray", "passive", (2.2, 0.9), "fly", 30, 0, 0.30,
    ("#150B26", "#8AF3FF"),
    [("voidbound:astral_shard", 3, 1, 2), ("minecraft:phantom_membrane", 3, 1, 2)],
    spawn=(6, 1, 3, 15, 3))
mob("ender_deer", "Ender Deer", "passive", (1.2, 2.0), "walk", 24, 0, 0.32,
    ("#1A0C31", "#8AF3FF"),
    [("voidbound:void_chitin", 3, 1, 2), ("minecraft:leather", 4, 1, 2)],
    spawn=(6, 2, 4, 15, 3),
    tame=dict(food=["voidbound:lumen_berry"], breed=["voidbound:lumen_berry"]))
mob("chorus_cow", "Chorus Cow", "passive", (1.4, 1.8), "walk", 28, 0, 0.24,
    ("#37294A", "#C060E8"),
    [("minecraft:chorus_fruit", 5, 1, 3), ("minecraft:leather", 4, 1, 2)],
    spawn=(6, 2, 4, 15, 3),
    tame=dict(food=["minecraft:chorus_fruit"], breed=["minecraft:chorus_fruit"]))
mob("void_hog", "Void Hog", "passive", (1.5, 1.3), "walk", 26, 3, 0.28,
    ("#1B1229", "#FF5CE8"),
    [("voidbound:void_chitin", 4, 1, 2), ("minecraft:leather", 3, 0, 1)],
    spawn=(6, 2, 3, 15, 3),
    tame=dict(food=["voidbound:ender_fruit"], breed=["voidbound:ender_fruit"]))
mob("ender_bird", "Ender Bird", "passive", (1.4, 1.6), "fly", 20, 0, 0.34,
    ("#150B26", "#7BEEFF"),
    [("minecraft:feather", 5, 1, 3), ("voidbound:astral_shard", 1, 0, 1)],
    spawn=(6, 1, 3, 15, 3),
    tame=dict(food=["voidbound:lumen_berry"], breed=["voidbound:lumen_berry"]))


# --------------------------------------------------------------------------
# Emitters
# --------------------------------------------------------------------------

def movement_components(spec):
    """Navigation and movement for a mob that walks, flies or hovers.

    A flier given walk navigation stands on the ground looking confused, and a
    walker given fly navigation sinks through the island, so this is the one
    part of the spec that has to be got right per mob rather than shared."""
    move = spec["move"]
    if move == "fly":
        return {
            "minecraft:movement": {"value": spec["spd"]},
            "minecraft:movement.fly": {},
            "minecraft:navigation.fly": {"can_path_over_water": True,
                                         "can_path_from_air": True,
                                         "avoid_damage_blocks": True},
            "minecraft:can_fly": {},
            "minecraft:behavior.float_wander": {"priority": 6, "xz_dist": 14,
                                                "y_dist": 8, "y_offset": 1.0,
                                                "random_reselect": True,
                                                "float_duration": [0.2, 1.2]},
        }
    if move == "hover":
        return {
            "minecraft:movement": {"value": spec["spd"]},
            "minecraft:movement.hover": {},
            "minecraft:navigation.hover": {"can_path_over_water": True,
                                           "can_path_from_air": True,
                                           "avoid_damage_blocks": True},
            "minecraft:can_fly": {},
            "minecraft:behavior.float_wander": {"priority": 6, "xz_dist": 10,
                                                "y_dist": 5, "y_offset": 0.6,
                                                "random_reselect": True},
        }
    return {
        "minecraft:movement": {"value": spec["spd"]},
        "minecraft:movement.basic": {},
        "minecraft:navigation.walk": {"can_path_over_water": False,
                                      "avoid_water": True,
                                      "can_pass_doors": False,
                                      "avoid_damage_blocks": True},
        "minecraft:jump.static": {},
        "minecraft:behavior.random_stroll": {"priority": 6,
                                             "speed_multiplier": 0.8},
    }


def behaviour_entity(name, spec):
    kind = spec["kind"]
    width, height = spec["size"]
    families = [name, "voidbound", "mob"]
    families.insert(2, "monster" if kind != "passive" else "passive")
    if kind == "boss":
        families.insert(2, "boss")

    components = {
        "minecraft:type_family": {"family": families},
        "minecraft:collision_box": {"width": width, "height": height},
        "minecraft:health": {"value": spec["hp"], "max": spec["hp"]},
        "minecraft:physics": {},
        "minecraft:nameable": {},
        "minecraft:pushable": {"is_pushable": kind != "boss",
                               "is_pushable_by_piston": kind != "boss"},
        "minecraft:conditional_bandwidth_optimization": {},
    }
    if spec["scale"] != 1.0:
        components["minecraft:scale"] = {"value": spec["scale"]}
    components.update(movement_components(spec))

    if spec["dmg"]:
        components["minecraft:attack"] = {"damage": spec["dmg"]}
    if kind == "passive":
        components["minecraft:despawn"] = {"despawn_from_distance": {}}
        components["minecraft:behavior.panic"] = {"priority": 1,
                                                  "speed_multiplier": 1.4}
        components["minecraft:behavior.avoid_mob_type"] = {
            "priority": 2,
            "entity_types": [{"filters": {"test": "is_family", "subject": "other",
                                          "value": "monster"},
                              "max_dist": 10, "walk_speed_multiplier": 1.5,
                              "sprint_speed_multiplier": 1.5}],
        }
    else:
        components["minecraft:behavior.hurt_by_target"] = {"priority": 1}
        components["minecraft:behavior.nearest_attackable_target"] = {
            "priority": 2, "must_see": True, "must_see_forget_duration": 8.0,
            "reselect_targets": True,
            "within_radius": 32 if kind == "boss" else 24,
            "entity_types": [{"filters": {"test": "is_family", "subject": "other",
                                          "value": "player"},
                              "max_dist": 32 if kind == "boss" else 24}],
        }
        components["minecraft:behavior.melee_attack"] = {
            "priority": 3, "speed_multiplier": 1.2, "track_target": True}
        if kind == "hostile":
            components["minecraft:despawn"] = {"despawn_from_distance": {}}
        else:
            components["minecraft:persistent"] = {}

    if spec["tame"]:
        # A passive worth keeping: it can be fed, healed and bred, and it has
        # a baby form, because a breedable mob with no calf is a dead end.
        components["minecraft:breedable"] = {
            "require_tame": False,
            "breeds_with": [{"mate_type": "voidbound:" + name,
                             "baby_type": "voidbound:" + name,
                             "breed_event": {"event": "minecraft:entity_born"}}],
            "love_filters": {"test": "has_component", "subject": "self",
                             "operator": "!=", "value": "minecraft:is_baby"},
            "food": [{"item": item} for item in spec["tame"]["breed"]],
        }
        components["minecraft:behavior.breed"] = {"priority": 3,
                                                  "speed_multiplier": 1.0}
        components["minecraft:behavior.follow_parent"] = {"priority": 4,
                                                          "speed_multiplier": 1.1}
        components["minecraft:behavior.tempt"] = {
            "priority": 4, "speed_multiplier": 1.2,
            "items": spec["tame"]["food"]}
        components["minecraft:interact"] = {
            "interactions": [{
                "on_interact": {
                    "filters": {"all_of": [
                        {"test": "is_family", "subject": "other", "value": "player"},
                        {"test": "has_equipment", "subject": "other",
                         "domain": "hand", "value": spec["tame"]["food"][0]},
                    ]},
                    "event": "voidbound:fed",
                },
                "use_item": True,
                "hurt_item": 0,
                "play_sounds": "eat",
                "particle_on_start": {"particle_type": "heart",
                                      "particle_y_offset": 1.0},
            }],
        }

    components["minecraft:behavior.look_at_player"] = {"priority": 7,
                                                       "look_distance": 10}
    components["minecraft:behavior.random_look_around"] = {"priority": 8}
    reward = {"passive": 3, "hostile": 8, "boss": 60}[kind]
    components["minecraft:experience_reward"] = {
        "on_death": "query.last_hit_by_player ? %d : 0" % reward}
    components["minecraft:loot"] = {
        "table": "loot_tables/entities/%s.json" % name}
    components.update(spec["extra"])

    entity = {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {
                "identifier": "voidbound:" + name,
                "is_spawnable": True,
                "is_summonable": True,
                "is_experimental": False,
            },
            "components": components,
        },
    }
    if spec["tame"]:
        # Being fed heals; being born makes a smaller one that grows up.
        entity["minecraft:entity"]["component_groups"] = {
            "voidbound:baby": {
                "minecraft:is_baby": {},
                "minecraft:scale": {"value": 0.55 * spec["scale"]},
                "minecraft:ageable": {
                    "duration": 1200,
                    "feed_items": spec["tame"]["food"],
                    "grow_up": {"event": "minecraft:ageable_grow_up"},
                },
            },
            "voidbound:adult": {
                "minecraft:scale": {"value": spec["scale"]},
            },
        }
        entity["minecraft:entity"]["events"] = {
            "minecraft:entity_spawned": {"add": {"component_groups": ["voidbound:adult"]}},
            "minecraft:entity_born": {"add": {"component_groups": ["voidbound:baby"]}},
            "minecraft:ageable_grow_up": {
                "remove": {"component_groups": ["voidbound:baby"]},
                "add": {"component_groups": ["voidbound:adult"]},
            },
            "voidbound:fed": {"add": {"component_groups": ["voidbound:adult"]}},
        }
    return entity


def spawn_rule(name, spec):
    if not spec["spawn"]:
        return None
    weight, herd_min, herd_max, brightness, density = spec["spawn"]
    passive = spec["kind"] == "passive"
    condition = {
        "minecraft:spawns_on_surface": {},
        "minecraft:brightness_filter": {"min": 0, "max": brightness,
                                        "adjust_for_weather": False},
        "minecraft:biome_filter": {"test": "has_biome_tag", "operator": "==",
                                   "value": "the_end"},
        "minecraft:height_filter": {"min": 0, "max": 160},
        "minecraft:difficulty_filter": {"min": "easy", "max": "hard"},
        "minecraft:density_limit": {"surface": density},
        "minecraft:herd": {"min_size": herd_min, "max_size": herd_max},
        "minecraft:weight": {"default": weight},
        "minecraft:spawns_on_block_filter": VOID_STONE,
    }
    if spec["move"] in ("fly", "hover"):
        # A flier that has to stand on a block to spawn never spawns over the
        # gaps between islands, which is the only place it should be.
        condition.pop("minecraft:spawns_on_block_filter")
        condition["minecraft:spawns_underground"] = {}
        condition["minecraft:height_filter"] = {"min": 40, "max": 200}
    return {
        "format_version": "1.8.0",
        "minecraft:spawn_rules": {
            "description": {
                "identifier": "voidbound:" + name,
                "population_control": "animal" if passive else "monster",
            },
            "conditions": [condition],
        },
    }


def loot_table(spec):
    pools = []
    entries = []
    for item, weight, low, high in spec["drops"]:
        if not item:
            entries.append({"type": "empty", "weight": weight})
            continue
        entry = {"type": "item", "name": item, "weight": weight}
        if (low, high) != (1, 1):
            entry["functions"] = [{"function": "set_count",
                                   "count": {"min": low, "max": high}}]
        entries.append(entry)
    pools.append({"rolls": 1, "entries": entries})
    return {"pools": pools}


def client_entity(name, spec):
    # Only the clips the controller reaches are declared here. Attack and hurt
    # are played from script by their *full* identifier, so listing them in
    # this map would declare two clips nothing ever plays through it - which is
    # exactly what check:ids flags, and it is right to.
    animations = {
        "idle": "animation.voidbound.%s.idle" % name,
        "move": "animation.voidbound.%s.move" % name,
        "death": "animation.voidbound.%s.death" % name,
        "vb_state": "controller.animation.voidbound.mob.full",
    }
    return {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": "voidbound:" + name,
                "materials": {"default": "entity_alphatest"},
                "textures": {"default": "textures/entity/voidbound_" + name},
                "geometry": {"default": "geometry.voidbound." + name},
                "animations": animations,
                "scripts": {"animate": ["vb_state"]},
                "render_controllers": ["controller.render.voidbound.default"],
                "spawn_egg": {"base_color": spec["egg"][0],
                              "overlay_color": spec["egg"][1]},
            },
        },
    }


def write(path, data):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def main():
    lang = []
    for name, spec in MOBS.items():
        write("BP/entities/%s.json" % name, behaviour_entity(name, spec))
        rule = spawn_rule(name, spec)
        if rule:
            write("BP/spawn_rules/%s.json" % name, rule)
        write("BP/loot_tables/entities/%s.json" % name, loot_table(spec))
        write("RP/entity/%s.entity.json" % name, client_entity(name, spec))
        lang.append("entity.voidbound:%s.name=%s" % (name, spec["title"]))
        lang.append("item.spawn_egg.entity.voidbound:%s.name=Spawn %s"
                    % (name, spec["title"]))
    print("%d mobs -> %d files" % (len(MOBS), len(MOBS) * 4))
    return lang


if __name__ == "__main__":
    for line in main():
        print("  " + line)
