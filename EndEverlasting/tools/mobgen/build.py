"""
Emit every file the twenty Eternal End mobs need.

Run from this directory:

    python3 build.py

and it writes geometry, textures, client entities, behaviour entities,
animations, loot tables, spawn rules, the projectiles the ranged mobs fire, the
food and taming items the passive mobs justify, and the language strings that
name all of it. Everything it writes lives under `eternal_end:` or in a file
named after a mob, so it never touches the hand-written `voidbound:` half of
the pack.

The generator is the source of truth. If a mob needs a different silhouette or
five more health, change `roster.py` and rebuild; hand-editing the output means
the next build silently reverts it.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paint import paint_model  # noqa: E402
from roster import ROSTER, GOLD, MAGENTA, VIOLET, CYAN, EMBER  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
BP = os.path.join(ROOT, "BP")
RP = os.path.join(ROOT, "RP")

NS = "eternal_end"

# Where mob art lives. Kept in its own folder so the twenty new textures never
# collide with the pack's existing entity art.
TEXTURE_DIR = f"textures/entity/{NS}"


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def write_png(path, image):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, "PNG", optimize=True)


# ===========================================================================
# Animations
# ===========================================================================

# Vanilla's walk-cycle constant: distance moved times this puts one full leg
# swing on roughly one block of travel.
STRIDE = "query.modified_distance_moved * 38.17"
SPEED = "query.modified_move_speed"


def _idle_animation(mob):
    """The at-rest loop: breathing, a head that looks around, a live tail."""
    gait = mob.gait
    bones = {}

    if gait["head"]:
        bones[gait["head"]] = {
            "rotation": [
                "math.sin(query.anim_time * 44) * 3",
                "math.sin(query.anim_time * 31) * 5",
                0,
            ]
        }

    for index, bone in enumerate(gait["tail"]):
        phase = index * 35
        bones[bone] = {
            "rotation": [
                f"math.sin(query.anim_time * 48 - {phase}) * {4 + index * 2}",
                f"math.sin(query.anim_time * 37 - {phase}) * {8 + index * 3}",
                0,
            ]
        }

    for index, bone in enumerate(gait["extra"]):
        phase = (index * 47) % 360
        bones[bone] = {
            "rotation": [
                f"math.sin(query.anim_time * 40 - {phase}) * 6",
                0,
                f"math.sin(query.anim_time * 33 - {phase}) * 5",
            ]
        }

    if gait["hover"]:
        for bone, sign in gait["wings"]:
            amount = gait["flap"]
            bones[bone] = {
                "rotation": [0, 0,
                             f"{sign} * math.cos(query.anim_time * 190) * {amount}"]
            }

    if gait["spin"]:
        bones[gait["spin"]] = {"rotation": [0, "query.anim_time * 110", 0]}

    if gait["jaw"]:
        bones[gait["jaw"]] = {
            "rotation": ["4 + math.sin(query.anim_time * 88) * 4", 0, 0]
        }

    if gait["bob"]:
        bones.setdefault("body", {})["position"] = [
            0, f"math.sin(query.anim_time * 42) * {gait['bob']}", 0
        ]

    if not bones:
        bones["body"] = {"position": [0, "math.sin(query.anim_time * 40) * 0.3", 0]}

    return {"loop": True, "animation_length": 4.0, "bones": bones}


def _move_animation(mob):
    """The travelling loop. Everything is scaled by move speed, so a stopped
    mob plays this and stands perfectly still."""
    gait = mob.gait
    bones = {}
    swing = gait["swing"]

    for bone, sign in gait["legs"]:
        sign_text = "" if sign > 0 else "-"
        bones[bone] = {
            "rotation": [f"{sign_text}math.cos({STRIDE}) * {swing} * {SPEED}", 0, 0]
        }

    for bone, sign in gait["arms"]:
        sign_text = "" if sign > 0 else "-"
        bones[bone] = {
            "rotation": [
                f"{sign_text}math.cos({STRIDE}) * {max(14, swing - 12)} * {SPEED}",
                0, 0,
            ]
        }

    for bone, sign in gait["wings"]:
        amount = gait["flap"]
        bones[bone] = {
            "rotation": [
                0, 0,
                f"{sign} * math.cos(query.anim_time * 340) * {amount} * "
                f"math.max({SPEED}, 0.35)",
            ]
        }

    if gait.get("hop"):
        bones.setdefault("body", {})["position"] = [
            0, f"math.abs(math.sin({STRIDE} * 0.5)) * 3.5 * {SPEED}", 0
        ]
        bones.setdefault("body", {})["scale"] = [
            f"1 + math.sin({STRIDE}) * 0.08 * {SPEED}",
            f"1 - math.sin({STRIDE}) * 0.10 * {SPEED}",
            f"1 + math.sin({STRIDE}) * 0.08 * {SPEED}",
        ]
    elif gait["legs"]:
        bones.setdefault("body", {})["position"] = [
            0, f"math.cos({STRIDE} * 2) * 0.6 * {SPEED}", 0
        ]

    for index, bone in enumerate(gait["tail"]):
        bones.setdefault(bone, {})["rotation"] = [
            0, f"math.cos({STRIDE} - {index * 40}) * {18 + index * 6} * {SPEED}", 0
        ]

    if not bones:
        bones["body"] = {"position": [0, f"math.cos({STRIDE} * 2) * 0.4 * {SPEED}", 0]}

    return {"loop": True, "bones": bones}


def _attack_animation(mob):
    """
    One swing, keyframed.

    Whatever the mob leads with - a jaw, a blade, a pair of arms, or the whole
    body - gets thrown forward and comes back to rest, so the clip can be
    stopped at any point without leaving the mob stuck in a pose.
    """
    gait = mob.gait
    bones = {}

    if gait["lunge"]:
        bones[gait["lunge"]] = {
            "rotation": {"0.0": [0, 0, 0], "0.15": [-60, 0, 0],
                         "0.35": [70, 0, 0], "0.7": [0, 0, 0]}
        }
    if gait["jaw"]:
        bones[gait["jaw"]] = {
            "rotation": {"0.0": [0, 0, 0], "0.12": [34, 0, 0],
                         "0.3": [6, 0, 0], "0.6": [0, 0, 0]}
        }
    for bone, sign in gait["arms"]:
        bones[bone] = {
            "rotation": {"0.0": [0, 0, 0], "0.15": [-70, 0, 0],
                         "0.32": [46, 0, 0], "0.65": [0, 0, 0]}
        }
    if gait["head"] and not gait["jaw"]:
        bones.setdefault(gait["head"], {})["rotation"] = {
            "0.0": [0, 0, 0], "0.14": [-18, 0, 0], "0.3": [22, 0, 0],
            "0.6": [0, 0, 0],
        }
    if not bones:
        bones["body"] = {
            "position": {"0.0": [0, 0, 0], "0.15": [0, 0, -4],
                         "0.35": [0, 0, 2], "0.6": [0, 0, 0]}
        }
    else:
        bones.setdefault("body", {})["position"] = {
            "0.0": [0, 0, 0], "0.18": [0, 0, -2.5], "0.6": [0, 0, 0]
        }

    return {"loop": False, "animation_length": 0.7, "bones": bones}


def _hurt_animation(mob):
    """A short flinch. Never longer than the invulnerability window."""
    return {
        "loop": False,
        "animation_length": 0.4,
        "bones": {
            "body": {
                "rotation": {"0.0": [0, 0, 0], "0.08": [-12, 0, 7],
                             "0.24": [5, 0, -3], "0.4": [0, 0, 0]},
                "position": {"0.0": [0, 0, 0], "0.08": [0, 0.8, 1.6],
                             "0.4": [0, 0, 0]},
            }
        },
    }


def _death_animation(mob):
    """Falls onto its side and sinks. Holds the last frame, which is the pose
    the corpse should be in when the entity is removed."""
    drop = -6 if mob.gait["hover"] else -3
    return {
        "loop": "hold_on_last_frame",
        "animation_length": 1.2,
        "bones": {
            "body": {
                "rotation": {"0.0": [0, 0, 0], "0.35": [0, 0, -32],
                             "1.2": [0, 0, -88]},
                "position": {"0.0": [0, 0, 0], "1.2": [0, drop, 0]},
            }
        },
    }


def _alert_animation(mob):
    """The pose it holds while it has a target: lowered, wound up, watching."""
    gait = mob.gait
    bones = {
        "body": {
            "rotation": ["-6 + math.sin(query.anim_time * 130) * 2", 0, 0],
        }
    }
    if gait["head"]:
        bones[gait["head"]] = {
            "rotation": ["8 + math.sin(query.anim_time * 150) * 3", 0, 0]
        }
    if gait["jaw"]:
        bones[gait["jaw"]] = {
            "rotation": ["14 + math.sin(query.anim_time * 240) * 6", 0, 0]
        }
    for bone, sign in gait["wings"]:
        bones[bone] = {
            "rotation": [0, 0,
                         f"{sign} * (22 + math.cos(query.anim_time * 260) * 14)"]
        }
    return {"loop": True, "animation_length": 2.0, "bones": bones}


# ===========================================================================
# Behaviour pack entities
# ===========================================================================

def _families(mob):
    families = [mob.id, NS, "mob"]
    if mob.category == "boss":
        families += ["monster", "boss"]
    elif mob.category == "hostile":
        families.append("monster")
    else:
        families.append("passive")
    return families


def _movement_components(stats):
    """Ground or hover locomotion, using the idiom the pack already ships."""
    if stats.get("flying"):
        return {
            "minecraft:can_fly": {},
            "minecraft:movement.hover": {},
            "minecraft:navigation.hover": {
                "can_path_over_water": True,
                "can_sink": False,
                "can_pass_doors": False,
                "can_path_from_air": True,
                "avoid_water": True,
                "avoid_damage_blocks": True,
            },
            "minecraft:behavior.random_hover": {
                "priority": 8,
                "xz_dist": 10,
                "y_dist": 6,
                "y_offset": -1,
                "interval": 60,
                "hover_height": [2, 8],
            },
            "minecraft:physics": {"has_gravity": False, "has_collision": True},
        }
    return {
        "minecraft:movement.basic": {},
        "minecraft:navigation.walk": {
            "can_path_over_water": False,
            "avoid_water": True,
            "can_pass_doors": False,
            "avoid_damage_blocks": True,
        },
        "minecraft:jump.static": {},
        "minecraft:physics": {},
    }


def _common_components(mob):
    stats = mob.stats
    components = {
        "minecraft:type_family": {"family": _families(mob)},
        "minecraft:collision_box": {
            "width": stats["width"],
            "height": stats["height"],
        },
        "minecraft:health": {"value": stats["health"], "max": stats["health"]},
        "minecraft:movement": {"value": stats["speed"]},
        "minecraft:knockback_resistance": {"value": stats.get("knockback", 0.0)},
        "minecraft:nameable": {},
        "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
        "minecraft:conditional_bandwidth_optimization": {},
        "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0},
        "minecraft:experience_reward": {
            "on_death": f"query.last_hit_by_player ? {stats['xp']} : 0"
        },
        "minecraft:loot": {"table": f"loot_tables/entities/{mob.id}.json"},
    }
    components.update(_movement_components(stats))
    if stats.get("scale", 1.0) != 1.0:
        components["minecraft:scale"] = {"value": stats["scale"]}
    if stats.get("fire_immune"):
        components["minecraft:fire_immune"] = True
    if stats.get("armour"):
        # Bedrock has no armour stat for mobs, so a plated one takes a fraction
        # of what it is hit for instead. Only `cause` and `damage_multiplier`
        # are set: they are the two fields of this component that have meant
        # the same thing across every version, and a damage sensor that fails
        # to parse takes the whole pack down with it.
        components["minecraft:damage_sensor"] = {
            "triggers": [{
                "cause": "all",
                "damage_multiplier": round(1.0 - stats["armour"] * 0.04, 2),
            }]
        }
    if stats.get("climbs"):
        components["minecraft:can_climb"] = {}
    if stats.get("teleports"):
        components["minecraft:teleport"] = {
            "random_teleports": True,
            "max_random_teleport_time": 20,
            "random_teleport_cube": [24, 12, 24],
            "target_distance": 14,
            "target_teleport_chance": 0.06,
            "light_teleport_chance": 0.01,
        }
    return components


def _combat_components(mob, priority_offset=0):
    stats = mob.stats
    components = {
        "minecraft:attack": {"damage": stats["damage"]},
        "minecraft:behavior.hurt_by_target": {"priority": 1},
        "minecraft:behavior.nearest_attackable_target": {
            "priority": 2,
            "must_see": True,
            "must_see_forget_duration": 10.0,
            "reselect_targets": True,
            "within_radius": 28 if mob.category == "boss" else 22,
            "entity_types": [{
                "filters": {"test": "is_family", "subject": "other", "value": "player"},
                "max_dist": 40 if mob.category == "boss" else 24,
            }],
        },
        "minecraft:behavior.melee_attack": {
            "priority": 3 + priority_offset,
            "speed_multiplier": 1.25,
            "track_target": True,
        },
    }
    if stats.get("ranged"):
        components["minecraft:shooter"] = {"def": stats["projectile"]}
        components["minecraft:behavior.ranged_attack"] = {
            "priority": 3,
            "attack_interval_min": 1.6 if mob.category == "boss" else 2.4,
            "attack_interval_max": 3.0 if mob.category == "boss" else 4.5,
            "attack_radius": 24,
            "burst_shots": 3 if mob.category == "boss" else 1,
            "burst_interval": 0.3,
        }
        components["minecraft:behavior.melee_attack"]["priority"] = 4
    return components


def _idle_behaviours(start=6):
    return {
        "minecraft:behavior.random_stroll": {
            "priority": start, "speed_multiplier": 0.8,
        },
        "minecraft:behavior.look_at_player": {
            "priority": start + 1, "look_distance": 10,
        },
        "minecraft:behavior.random_look_around": {"priority": start + 2},
    }


def _boss_entity(mob):
    components = _common_components(mob)
    components.update(_combat_components(mob))
    components.update(_idle_behaviours(start=7))
    components["minecraft:boss"] = {
        "should_darken_sky": True,
        "hud_range": 64,
        "name": mob.stats["boss_name"],
    }
    components["minecraft:persistent"] = {}
    components["minecraft:despawn"] = {"despawn_from_distance": {}}
    del components["minecraft:despawn"]  # bosses never despawn
    components["minecraft:knockback_resistance"] = {"value": 1.0}
    if mob.stats.get("summons"):
        components["minecraft:behavior.summon_entity"] = _summon(mob.stats["summons"])
    entity = {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {
                "identifier": f"{NS}:{mob.id}",
                "is_spawnable": True,
                "is_summonable": True,
                "is_experimental": False,
            },
            "components": components,
        },
    }
    return entity


def _summon(what):
    return {
        "priority": 5,
        "summon_choices": [{
            "min_activation_range": 0,
            "max_activation_range": 20,
            "cooldown_time": 12.0,
            "weight": 3,
            "sequence": [{
                "shape": "circle",
                "target": "self",
                "base_delay": 0.5,
                "delay": 0.2,
                "num_entities_spawned": 2,
                "entity_type": what,
                "size": 3,
                "entity_lifespan": 120,
            }],
        }],
    }


def _hostile_entity(mob):
    components = _common_components(mob)
    components.update(_combat_components(mob))
    components.update(_idle_behaviours())
    components["minecraft:despawn"] = {"despawn_from_distance": {}}
    if mob.stats.get("hops"):
        components["minecraft:jump.static"] = {}
        components["minecraft:movement.jump"] = {"jump_delay": [0.3, 0.9]}
        components.pop("minecraft:movement.basic", None)
    if mob.stats.get("sprint"):
        components["minecraft:behavior.melee_attack"]["speed_multiplier"] = 1.6
    if mob.stats.get("summons"):
        components["minecraft:behavior.summon_entity"] = _summon(mob.stats["summons"])
    return {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {
                "identifier": f"{NS}:{mob.id}",
                "is_spawnable": True,
                "is_summonable": True,
                "is_experimental": False,
            },
            "components": components,
        },
    }


def _passive_entity(mob):
    """
    A tameable animal.

    Three component groups do the work: `wild` carries the taming offer,
    `tamed` carries everything an owned animal gets, and `baby` carries the
    growing-up state so a bred pair actually produces young. The events wire
    them together, which is the whole of Bedrock's taming contract.
    """
    stats = mob.stats
    components = _common_components(mob)
    components.update(_idle_behaviours(start=6))
    components["minecraft:despawn"] = {"despawn_from_distance": {
        "min_distance": 96, "max_distance": 160,
    }}
    components["minecraft:behavior.float"] = {"priority": 0}
    if stats.get("panics"):
        components["minecraft:behavior.panic"] = {
            "priority": 1, "speed_multiplier": 1.4,
        }
    components["minecraft:behavior.tempt"] = {
        "priority": 3,
        "speed_multiplier": 1.1,
        "items": [stats["tame_item"], stats["breed_item"]],
    }
    if stats["damage"]:
        components["minecraft:attack"] = {"damage": stats["damage"]}
    components["minecraft:behavior.avoid_mob_type"] = {
        "priority": 2,
        "entity_types": [{
            "filters": {"test": "is_family", "subject": "other", "value": "monster"},
            "max_dist": 10,
            "walk_speed_multiplier": 1.5,
            "sprint_speed_multiplier": 1.5,
        }],
    }

    wild = {
        "minecraft:tameable": {
            "probability": 0.34,
            "tame_items": [stats["tame_item"]],
            "tame_event": {"event": f"{NS}:on_tame", "target": "self"},
        }
    }

    tamed = {
        "minecraft:is_tamed": {},
        "minecraft:persistent": {},
        "minecraft:health": {"value": stats["health"] + 8,
                             "max": stats["health"] + 8},
        "minecraft:behavior.follow_owner": {
            "priority": 4, "speed_multiplier": 1.2,
            "start_distance": 10, "stop_distance": 3,
        },
        "minecraft:behavior.owner_hurt_by_target": {"priority": 1},
        "minecraft:behavior.owner_hurt_target": {"priority": 2},
        "minecraft:breedable": {
            "require_tame": True,
            "breeds_with": [{
                "mate_type": f"{NS}:{mob.id}",
                "baby_type": f"{NS}:{mob.id}",
                "breed_event": {"event": "minecraft:entity_born", "target": "baby"},
            }],
            "breed_items": [stats["breed_item"]],
        },
    }
    if stats.get("sits"):
        tamed["minecraft:sittable"] = {}
        tamed["minecraft:behavior.stay_while_sitting"] = {"priority": 3}
    if stats.get("rideable"):
        tamed["minecraft:rideable"] = {
            "seat_count": 1,
            "family_types": ["player"],
            "interact_text": "action.interact.ride.horse",
            "seats": {"position": [0.0, 1.1, -0.2], "lock_rider_rotation": 0},
        }
        tamed["minecraft:behavior.player_ride_tamed"] = {"priority": 0}
    if stats.get("milkable"):
        tamed["minecraft:interact"] = {
            "interactions": [{
                "on_interact": {
                    "filters": {
                        "all_of": [
                            {"test": "is_family", "subject": "other", "value": "player"},
                            {"test": "has_equipment", "domain": "hand",
                             "subject": "other", "value": "bucket"},
                        ]
                    }
                },
                "use_item": True,
                "transform_to_item": "minecraft:milk_bucket",
                "play_sounds": "milk",
                "interact_text": "action.interact.milk",
                "cooldown": 4.0,
            }]
        }

    baby = {
        "minecraft:is_baby": {},
        "minecraft:scale": {"value": 0.55},
        "minecraft:ageable": {
            "duration": 1200,
            "feed_items": [stats["tame_item"]],
            "grow_up": {"event": "minecraft:ageable_grow_up", "target": "self"},
        },
        "minecraft:behavior.follow_parent": {"priority": 5, "speed_multiplier": 1.1},
    }

    return {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {
                "identifier": f"{NS}:{mob.id}",
                "is_spawnable": True,
                "is_summonable": True,
                "is_experimental": False,
            },
            "component_groups": {
                f"{NS}:wild": wild,
                f"{NS}:tamed": tamed,
                f"{NS}:baby": baby,
                f"{NS}:adult": {},
            },
            "components": components,
            "events": {
                "minecraft:entity_spawned": {
                    "add": {"component_groups": [f"{NS}:wild", f"{NS}:adult"]}
                },
                "minecraft:entity_born": {
                    "add": {"component_groups": [f"{NS}:tamed", f"{NS}:baby"]}
                },
                "minecraft:ageable_grow_up": {
                    "remove": {"component_groups": [f"{NS}:baby"]},
                    "add": {"component_groups": [f"{NS}:adult"]},
                },
                f"{NS}:on_tame": {
                    "remove": {"component_groups": [f"{NS}:wild"]},
                    "add": {"component_groups": [f"{NS}:tamed"]},
                },
            },
        },
    }


BUILDERS = {
    "boss": _boss_entity,
    "hostile": _hostile_entity,
    "passive_tame": _passive_entity,
}


# ===========================================================================
# Spawn rules, loot
# ===========================================================================

SPAWN_BLOCKS = [
    "minecraft:end_stone",
    "voidbound:shattered_end_stone",
    "voidbound:verdant_end_stone",
    "voidbound:crystalline_end_stone",
    "voidbound:glowspore_soil",
    "voidbound:ashen_end_stone",
    "voidbound:bonespire_stone",
    "voidbound:aurora_stone",
    "voidbound:mossy_end_stone",
]


def _spawn_rule(mob):
    spawn = mob.spawn
    condition = {
        "minecraft:spawns_on_surface": {},
        "minecraft:biome_filter": {
            "test": "has_biome_tag", "operator": "==", "value": "the_end",
        },
        "minecraft:height_filter": {"min": 0, "max": 250},
        "minecraft:density_limit": {"surface": 3 if spawn.get("passive") else 2},
        "minecraft:herd": {
            "min_size": spawn["herd"][0], "max_size": spawn["herd"][1],
        },
        "minecraft:weight": {"default": spawn["weight"]},
        "minecraft:spawns_on_block_filter": SPAWN_BLOCKS,
    }
    if spawn["light"] == "dark":
        condition["minecraft:brightness_filter"] = {
            "min": 0, "max": 8, "adjust_for_weather": False,
        }
    if not spawn.get("passive"):
        condition["minecraft:difficulty_filter"] = {"min": "easy", "max": "hard"}
    if mob.stats.get("flying"):
        # Flyers are sited off the ground, so they need the airborne pass as
        # well as a block under them to have been found in the first place.
        condition["minecraft:spawns_underground"] = {}

    return {
        "format_version": "1.8.0",
        "minecraft:spawn_rules": {
            "description": {
                "identifier": f"{NS}:{mob.id}",
                "population_control": "animal" if spawn.get("passive") else "monster",
            },
            "conditions": [condition],
        },
    }


def _loot_table(mob):
    pools = []
    for name, low, high in mob.loot:
        entry = {"type": "item", "name": name, "weight": 1}
        if low == high:
            if low > 1:
                entry["functions"] = [{"function": "set_count", "count": low}]
            pools.append({"rolls": 1, "entries": [entry]})
            continue
        entry["functions"] = [
            {"function": "set_count", "count": {"min": low, "max": high}}
        ]
        pool = {"rolls": 1, "entries": [entry]}
        if low == 0:
            # A zero-minimum drop should sometimes give nothing at all rather
            # than an item stack of zero, which reads as a bug in the drop feed.
            pool["entries"].append({"type": "empty", "weight": 1})
        pools.append(pool)
    return {"pools": pools}


# ===========================================================================
# Client entities
# ===========================================================================

def _client_entity(mob):
    animations = {
        "idle": f"animation.{NS}.{mob.id}.idle",
        "move": f"animation.{NS}.{mob.id}.move",
        "ee_alert": f"animation.{NS}.{mob.id}.alert",
        "ee_death": f"animation.{NS}.{mob.id}.death",
        "ee_state": f"controller.animation.{NS}.mob.state",
    }
    return {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": f"{NS}:{mob.id}",
                # Emissive alpha lets the violet crystals and eyes light
                # themselves straight out of the texture's alpha channel.
                "materials": {"default": "entity_emissive_alpha"},
                "textures": {"default": f"{TEXTURE_DIR}/{mob.id}"},
                "geometry": {"default": f"geometry.{NS}.{mob.id}"},
                "animations": animations,
                "scripts": {"animate": ["idle", "move", "ee_state"]},
                "render_controllers": [f"controller.render.{NS}.default"],
                "spawn_egg": {
                    "base_color": mob.egg[0],
                    "overlay_color": mob.egg[1],
                },
            }
        },
    }


# ===========================================================================
# Projectiles the ranged mobs fire
# ===========================================================================

PROJECTILES = [
    ("void_breath", "Void Breath", 12, "#2A1140", MAGENTA, 1.4, 0.0),
    ("void_lance", "Void Lance", 7, "#1E1030", VIOLET, 2.0, 0.0),
    ("royal_bolt", "Royal Bolt", 9, "#3A2A08", GOLD, 2.2, 0.0),
    ("wisp_flame", "Wisp Flame", 5, "#1B0A3A", VIOLET, 1.5, 0.0),
]


def _projectile_entity(ident, damage, power, gravity):
    return {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {
                "identifier": f"{NS}:{ident}",
                "is_spawnable": False,
                "is_summonable": True,
                "is_experimental": False,
            },
            "components": {
                "minecraft:collision_box": {"width": 0.4, "height": 0.4},
                "minecraft:physics": {"has_gravity": gravity > 0},
                "minecraft:conditional_bandwidth_optimization": {},
                "minecraft:projectile": {
                    "on_hit": {
                        "impact_damage": {
                            "damage": damage,
                            "knockback": True,
                            "semi_random_diff_damage": False,
                            "destroy_on_hit": True,
                        },
                        "remove_on_hit": {},
                        "particle_on_hit": {
                            "particle_type": "basic_crit_particle",
                            "on_other_hit": True,
                            "on_entity_hit": True,
                        },
                    },
                    "power": power,
                    "gravity": gravity,
                    "uncertainty_base": 4,
                    "uncertainty_multiplier": 0,
                    "anchor": 1,
                    "should_bounce": False,
                    "offset": [0, -0.1, 0],
                },
            },
        },
    }


def _projectile_client(ident):
    return {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": f"{NS}:{ident}",
                "materials": {"default": "entity_emissive_alpha"},
                "textures": {"default": f"{TEXTURE_DIR}/{ident}"},
                "geometry": {"default": f"geometry.{NS}.projectile"},
                "render_controllers": [f"controller.render.{NS}.default"],
            }
        },
    }


def _projectile_geometry():
    """One shard, shared by every projectile - only the texture differs."""
    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": f"geometry.{NS}.projectile",
                "texture_width": 16,
                "texture_height": 16,
                "visible_bounds_width": 1,
                "visible_bounds_height": 1,
                "visible_bounds_offset": [0, 0, 0],
            },
            "bones": [{
                "name": "shard",
                "pivot": [0, 0, 0],
                "cubes": [
                    {"origin": [-2, -2, -3], "size": [4, 4, 6], "uv": [0, 0]},
                    {"origin": [-1, -1, -5], "size": [2, 2, 3], "uv": [0, 10]},
                ],
            }],
        }],
    }


def _projectile_texture(core_hex, glow_hex):
    from PIL import Image
    from paint import GLOW_ALPHA, hex_to_rgb, mix

    core = hex_to_rgb(core_hex)
    glow = hex_to_rgb(glow_hex)
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = image.load()
    for y in range(16):
        for x in range(16):
            t = ((x % 4) + (y % 4)) / 6.0
            lit = (x + y) % 3 != 0
            px[x, y] = (*(glow if lit else mix(core, glow, t)),
                        GLOW_ALPHA if lit else 255)
    return image


# ===========================================================================
# Items: the meat the passive mobs drop, and what tames them
# ===========================================================================

MEATS = [
    ("ender_venison", "Ender Venison", 3, 0.4, 8, 0.8, "#5A2438", "#8A3A54"),
    ("chorus_beef", "Chorus Beef", 3, 0.3, 8, 0.8, "#5E2A50", "#8E4A78"),
    ("void_pork", "Void Pork", 3, 0.3, 8, 0.8, "#54263A", "#864056"),
    ("ray_meat", "Ray Meat", 2, 0.2, 6, 0.6, "#2E3A66", "#4A5C94"),
    ("ender_poultry", "Ender Poultry", 2, 0.2, 6, 0.7, "#3A3060", "#5C4E8E"),
]


def _food_item(ident, name, nutrition, saturation, raw):
    return {
        "format_version": "1.21.100",
        "minecraft:item": {
            "description": {
                "identifier": f"{NS}:{ident}",
                "menu_category": {"category": "nature"},
            },
            "components": {
                "minecraft:icon": {"textures": {"default": f"{NS}_{ident}"}},
                "minecraft:display_name": {"value": f"item.{NS}:{ident}.name"},
                "minecraft:max_stack_size": 64,
                "minecraft:food": {
                    "nutrition": nutrition,
                    "saturation_modifier": saturation,
                    "can_always_eat": False,
                },
                "minecraft:use_modifiers": {"use_duration": 1.6, "movement_modifier": 0.35},
                "minecraft:use_animation": "eat",
            },
        },
    }


def _lumen_feed_item():
    return {
        "format_version": "1.21.100",
        "minecraft:item": {
            "description": {
                "identifier": f"{NS}:lumen_feed",
                "menu_category": {"category": "nature"},
            },
            "components": {
                "minecraft:icon": {"textures": {"default": f"{NS}_lumen_feed"}},
                "minecraft:display_name": {"value": f"item.{NS}:lumen_feed.name"},
                "minecraft:max_stack_size": 64,
            },
        },
    }


DROP_ITEMS = [
    ("void_scale", "Void Scale", "#2A1140", VIOLET, "scale"),
    ("void_ember", "Void Ember", "#1B0A3A", MAGENTA, "spark"),
    ("void_chitin_plate", "Void Chitin Plate", "#2A1038", VIOLET, "plate"),
    ("void_heart", "Void Heart", "#3A0A2A", MAGENTA, "heart"),
    ("overlord_eye", "Overlord Eye", "#1E1030", MAGENTA, "eye"),
    ("crown_shard", "Crown Shard", "#4A3208", GOLD, "shard"),
]


def _material_item(ident):
    return {
        "format_version": "1.21.100",
        "minecraft:item": {
            "description": {
                "identifier": f"{NS}:{ident}",
                "menu_category": {"category": "items"},
            },
            "components": {
                "minecraft:icon": {"textures": {"default": f"{NS}_{ident}"}},
                "minecraft:display_name": {"value": f"item.{NS}:{ident}.name"},
                "minecraft:max_stack_size": 64,
            },
        },
    }


def _item_icon(shape, dark_hex, bright_hex):
    """A 16x16 pixel-art icon, drawn from two colours and a silhouette."""
    from PIL import Image
    from paint import Rng, hex_to_rgb, mix, scale, string_seed

    dark = hex_to_rgb(dark_hex)
    bright = hex_to_rgb(bright_hex)
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = image.load()
    rng = Rng(string_seed(shape + dark_hex))

    def inside(x, y):
        cx, cy = x - 7.5, y - 7.5
        if shape == "scale":
            return abs(cx) / 5.0 + abs(cy) / 6.5 <= 1.0
        if shape == "spark":
            return abs(cx) + abs(cy) <= 6.5
        if shape == "plate":
            return abs(cx) <= 5 and abs(cy) <= 5.5
        if shape == "heart":
            return (cx * cx + (cy - 1) ** 2) <= 30 and abs(cx) - cy * 0.4 <= 5
        if shape == "eye":
            return (cx / 6.5) ** 2 + (cy / 4.2) ** 2 <= 1.0
        if shape == "shard":
            return abs(cx) <= 4.5 - abs(cy) * 0.25
        if shape == "meat":
            return (cx / 5.5) ** 2 + (cy / 4.5) ** 2 <= 1.0
        if shape == "feed":
            return abs(cx) / 5.5 + abs(cy) / 5.5 <= 1.0
        return abs(cx) <= 5 and abs(cy) <= 5

    for y in range(16):
        for x in range(16):
            if not inside(x, y):
                continue
            edge = not (inside(x - 1, y) and inside(x + 1, y)
                        and inside(x, y - 1) and inside(x, y + 1))
            if edge:
                tone = scale(dark, 0.6)
            else:
                t = max(0.0, 1.0 - ((x - 6) ** 2 + (y - 5) ** 2) / 60.0)
                tone = mix(dark, bright, min(1.0, t + rng.next() * 0.22))
            px[x, y] = (*tone, 255)
    return image


COOK_TIME = 200


def _furnace_recipe(raw, cooked):
    return {
        "format_version": "1.20.10",
        "minecraft:recipe_furnace": {
            "description": {"identifier": f"{NS}:cook_{cooked}"},
            "tags": ["furnace", "smoker", "campfire", "soul_campfire"],
            "input": f"{NS}:{raw}",
            "output": f"{NS}:{cooked}",
        },
    }


def _feed_recipe():
    """Lumen Feed: the End's answer to wheat, made from what the End grows."""
    return {
        "format_version": "1.20.10",
        "minecraft:recipe_shapeless": {
            "description": {"identifier": f"{NS}:lumen_feed"},
            "tags": ["crafting_table"],
            "ingredients": [
                {"item": "minecraft:chorus_fruit"},
                {"item": "voidbound:lumen_berry"},
                {"item": "voidbound:bloom_pod"},
            ],
            "result": {"item": f"{NS}:lumen_feed", "count": 3},
        },
    }


# ===========================================================================
# Driver
# ===========================================================================

def build():
    animations = {}
    actions = {}
    lang = []
    written = 0

    lang.append("## Eternal End mobs")
    for mob in ROSTER:
        model = mob.model()
        model.pack()

        write_json(os.path.join(RP, "models", "entity", f"{mob.id}.geo.json"),
                   model.to_json())

        colour, mer = paint_model(model, mob.id)
        write_png(os.path.join(RP, TEXTURE_DIR, f"{mob.id}.png"), colour)
        write_png(os.path.join(RP, TEXTURE_DIR, f"{mob.id}_mer.png"), mer)
        write_json(os.path.join(RP, TEXTURE_DIR, f"{mob.id}.texture_set.json"), {
            "format_version": "1.16.100",
            "minecraft:texture_set": {
                "color": mob.id,
                "metalness_emissive_roughness": f"{mob.id}_mer",
            },
        })

        write_json(os.path.join(RP, "entity", f"{mob.id}.entity.json"),
                   _client_entity(mob))
        write_json(os.path.join(BP, "entities", f"{mob.id}.json"),
                   BUILDERS[mob.category](mob))
        write_json(os.path.join(BP, "loot_tables", "entities", f"{mob.id}.json"),
                   _loot_table(mob))
        if mob.spawn:
            write_json(os.path.join(BP, "spawn_rules", f"{mob.id}.json"),
                       _spawn_rule(mob))

        animations[f"animation.{NS}.{mob.id}.idle"] = _idle_animation(mob)
        animations[f"animation.{NS}.{mob.id}.move"] = _move_animation(mob)
        animations[f"animation.{NS}.{mob.id}.alert"] = _alert_animation(mob)
        animations[f"animation.{NS}.{mob.id}.death"] = _death_animation(mob)
        actions[f"animation.{NS}.{mob.id}.attack"] = _attack_animation(mob)
        actions[f"animation.{NS}.{mob.id}.hurt"] = _hurt_animation(mob)

        lang.append(f"entity.{NS}:{mob.id}.name={mob.name}")
        lang.append(f"item.spawn_egg.entity.{NS}:{mob.id}.name=Spawn {mob.name}")
        written += 1
        print(f"  {mob.id:22} {model.texture_width}x{model.texture_height} "
              f"{sum(len(b.cubes) for b in model.bones):2} cubes")

    write_json(os.path.join(RP, "animations", f"{NS}.animation.json"),
               {"format_version": "1.10.0", "animations": animations})
    write_json(os.path.join(RP, "animations", f"{NS}.actions.animation.json"),
               {"format_version": "1.10.0", "animations": actions})

    write_json(
        os.path.join(RP, "animation_controllers",
                     f"{NS}.mob.animation_controllers.json"),
        {
            "format_version": "1.10.0",
            "animation_controllers": {
                f"controller.animation.{NS}.mob.state": {
                    "initial_state": "calm",
                    "states": {
                        "calm": {
                            "blend_transition": 0.3,
                            "transitions": [
                                {"dying": "!query.is_alive"},
                                {"alert": "query.has_target"},
                            ],
                        },
                        "alert": {
                            "animations": ["ee_alert"],
                            "blend_transition": 0.25,
                            "transitions": [
                                {"dying": "!query.is_alive"},
                                {"calm": "!query.has_target"},
                            ],
                        },
                        "dying": {
                            "animations": ["ee_death"],
                            "blend_transition": 0.15,
                            "transitions": [{"calm": "query.is_alive"}],
                        },
                    },
                }
            },
        },
    )

    write_json(os.path.join(RP, "render_controllers",
                            f"{NS}.render_controllers.json"),
               {
                   "format_version": "1.10.0",
                   "render_controllers": {
                       f"controller.render.{NS}.default": {
                           "geometry": "Geometry.default",
                           "materials": [{"*": "Material.default"}],
                           "textures": ["Texture.default"],
                       }
                   },
               })

    # Projectiles.
    write_json(os.path.join(RP, "models", "entity", f"{NS}_projectile.geo.json"),
               _projectile_geometry())
    lang.append("")
    lang.append("## Eternal End projectiles")
    for ident, name, damage, core, glow, power, gravity in PROJECTILES:
        write_json(os.path.join(BP, "entities", f"{ident}.json"),
                   _projectile_entity(ident, damage, power, gravity))
        write_json(os.path.join(RP, "entity", f"{ident}.entity.json"),
                   _projectile_client(ident))
        write_png(os.path.join(RP, TEXTURE_DIR, f"{ident}.png"),
                  _projectile_texture(core, glow))
        lang.append(f"entity.{NS}:{ident}.name={name}")

    # Items.
    lang.append("")
    lang.append("## Eternal End items")
    icons = {}
    for ident, name, nutrition, saturation, cooked_n, cooked_s, dark, bright \
            in MEATS:
        raw_id = f"raw_{ident}"
        cooked_id = f"cooked_{ident}"
        write_json(os.path.join(BP, "items", f"{raw_id}.json"),
                   _food_item(raw_id, name, nutrition, saturation, raw=True))
        write_json(os.path.join(BP, "items", f"{cooked_id}.json"),
                   _food_item(cooked_id, name, cooked_n, cooked_s, raw=False))
        write_json(os.path.join(BP, "recipes", f"cook_{cooked_id}.json"),
                   _furnace_recipe(raw_id, cooked_id))
        write_png(os.path.join(RP, "textures", "items", f"{NS}_{raw_id}.png"),
                  _item_icon("meat", dark, bright))
        write_png(os.path.join(RP, "textures", "items", f"{NS}_{cooked_id}.png"),
                  _item_icon("meat", bright, "#F0C890"))
        icons[f"{NS}_{raw_id}"] = f"textures/items/{NS}_{raw_id}"
        icons[f"{NS}_{cooked_id}"] = f"textures/items/{NS}_{cooked_id}"
        lang.append(f"item.{NS}:{raw_id}.name=Raw {name}")
        lang.append(f"item.{NS}:{cooked_id}.name=Cooked {name}")

    write_json(os.path.join(BP, "items", "lumen_feed.json"), _lumen_feed_item())
    write_json(os.path.join(BP, "recipes", "lumen_feed.json"), _feed_recipe())
    write_png(os.path.join(RP, "textures", "items", f"{NS}_lumen_feed.png"),
              _item_icon("feed", "#2C4A2A", CYAN))
    icons[f"{NS}_lumen_feed"] = f"textures/items/{NS}_lumen_feed"
    lang.append(f"item.{NS}:lumen_feed.name=Lumen Feed")

    for ident, name, dark, bright, shape in DROP_ITEMS:
        write_json(os.path.join(BP, "items", f"{ident}.json"),
                   _material_item(ident))
        write_png(os.path.join(RP, "textures", "items", f"{NS}_{ident}.png"),
                  _item_icon(shape, dark, bright))
        icons[f"{NS}_{ident}"] = f"textures/items/{NS}_{ident}"
        lang.append(f"item.{NS}:{ident}.name={name}")

    _merge_item_texture_atlas(icons)
    _merge_lang(lang)
    _register_mob_action_clips()

    print(f"\n  {written} mobs, {len(PROJECTILES)} projectiles, "
          f"{len(icons)} items")


def _merge_item_texture_atlas(icons):
    """Add the new icons to the resource pack's item atlas, in place."""
    path = os.path.join(RP, "textures", "item_texture.json")
    with open(path, encoding="utf-8") as handle:
        atlas = json.load(handle)
    data = atlas.setdefault("texture_data", {})
    for ident, texture in icons.items():
        data[ident] = {"textures": texture}
    write_json(path, atlas)


LANG_MARKER = "## --- generated by tools/mobgen ---"


def _merge_lang(lines):
    """
    Rewrite the generated block of the language file, leaving the rest alone.

    Everything after the marker belongs to this script; everything before it is
    hand-written and must survive a rebuild untouched.
    """
    path = os.path.join(RP, "texts", "en_US.lang")
    with open(path, encoding="utf-8") as handle:
        existing = handle.read()
    head = existing.split(LANG_MARKER)[0].rstrip() + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(head)
        handle.write("\n" + LANG_MARKER + "\n")
        handle.write("\n".join(lines).rstrip() + "\n")


def _register_mob_action_clips():
    """
    Write the Eternal End half of the attack/hurt clip table.

    `mobActions.js` keeps its identifiers written out in full so the identifier
    checker can read them straight out of the source rather than guessing at
    names assembled at runtime. That has to stay true for the generated mobs
    too, so this emits a sibling module of literal strings and `mobActions.js`
    merges it in - which also means a rebuild rewrites one generated file
    instead of surgically editing a hand-written one.
    """
    entries = "\n".join(
        f'  ["{NS}:{mob.id}", {{\n'
        f'    attack: "animation.{NS}.{mob.id}.attack",\n'
        f'    hurt: "animation.{NS}.{mob.id}.hurt",\n'
        f'  }}],'
        for mob in ROSTER
    )
    source = (
        "/**\n"
        " * Attack and hurt clips for the Eternal End roster.\n"
        " *\n"
        " * Generated by tools/mobgen/build.py - do not edit by hand. Merged\n"
        " * into the clip table in mobActions.js, which is what plays them.\n"
        " */\n\n"
        "export const ETERNAL_END_CLIPS = [\n" + entries + "\n];\n"
    )
    path = os.path.join(BP, "scripts", "content", "eternalEndClips.js")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(source)


if __name__ == "__main__":
    print("Building the Eternal End roster...")
    build()
