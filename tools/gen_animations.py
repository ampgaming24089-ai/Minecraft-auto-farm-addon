#!/usr/bin/env python3
"""
Generates per-archetype bone animations and wires each entity to the set
that matches how it actually moves.

There used to be exactly one shared idle + walk pair applied to every
creature, so a ghost, a hound, a spider and a dragon all moved identically -
which is why the roster read as "little to no unique animations". Now each
entity is assigned an archetype (ghost / biped / quadruped / crawler /
winged / boss), and each archetype gets its own idle and locomotion clips
built from its own bone list.

Bone names still vary across the roster, and Bedrock ignores animation
entries for bones a model doesn't have - the same mechanism vanilla uses to
share one humanoid animation set across differently-rigged mobs - so an
archetype clip can safely list every naming variant.

Run with: python3 tools/gen_animations.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "RP")

# Entities that are projectiles, not creatures.
SKIP = {"debris_projectile", "imp_fireball"}

ARCHETYPE = {
    # drift, never touch the ground, no leg cycle at all
    "wraith": "ghost", "banshee": "ghost", "poltergeist": "ghost",
    "shade": "ghost", "soul_wisp": "ghost", "city_wraithguard": "ghost",
    # walk on two legs, swing arms
    "fallen_knight": "biped", "bastion_sentinel": "biped",
    "occultist": "biped", "imp": "biped",
    # four legs, diagonal trot
    "hellhound": "quadruped", "bonehide_elk": "quadruped",
    "glimmershroom_toad": "quadruped",
    # many legs, travelling wave
    "marrow_crawler": "crawler",
    # wings do the work
    "ashwing_bat": "winged", "ashen_whelp": "winged", "veil_dragon": "winged",
    # bosses get their own heavier, slower presence
    "hollow_king": "boss", "weeping_widow": "boss", "malacoda": "boss",
}
DEFAULT_ARCHETYPE = "biped"

ARM_PAIRS = [("left_arm", "right_arm"), ("arm_l", "arm_r")]
LEG_PAIRS = [("leg_l", "leg_r")]
QUAD_LEGS = [("leg_fl", "leg_br"), ("leg_fr", "leg_bl")]  # diagonal pairs
ROOTS = ("body", "base", "core", "legs", "dress")
HEADS = ("head",)


def sin(expr, amp, phase=0.0, t="query.anim_time"):
    ph = f" + {phase}" if phase else ""
    return f"math.sin({t} * {expr}{ph}) * {amp}"


def build():
    anims = {}

    # ---- ghost: slow vertical drift, gentle roll, trailing hem ----------
    idle = {}
    for r in ROOTS:
        idle[r] = {"position": [0.0, sin(28.0, 1.6), 0.0],
                   "rotation": [0.0, sin(11.0, 3.0), 0.0]}
    idle["head"] = {"rotation": [sin(24.0, 5.0), 0.0, 0.0]}
    for l, r in ARM_PAIRS:
        idle[l] = {"rotation": [sin(20.0, 6.0), 0.0, sin(16.0, 8.0)]}
        idle[r] = {"rotation": [sin(20.0, 6.0, 40), 0.0, f"-{sin(16.0, 8.0)}"]}
    for n in ("tail", "hair", "veil", "cloak_a", "cloak_b", "cloak_c", "t1", "t2", "t3"):
        idle[n] = {"rotation": [sin(18.0, 9.0), 0.0, 0.0]}
    anims["animation.hv.ghost.idle"] = {"loop": True, "bones": idle}
    # moving: lean into the drift, hem streams back
    move = {}
    for r in ROOTS:
        move[r] = {"rotation": [-8.0, 0.0, 0.0], "position": [0.0, sin(46.0, 2.2), 0.0]}
    for n in ("tail", "hair", "veil", "cloak_a", "cloak_b", "cloak_c"):
        move[n] = {"rotation": [f"22.0 + {sin(40.0, 8.0)}", 0.0, 0.0]}
    anims["animation.hv.ghost.move"] = {
        "loop": True, "anim_time_update": "query.modified_distance_moved", "bones": move}

    # ---- biped: arm/leg counter-swing ----------------------------------
    idle = {r: {"position": [0.0, sin(38.0, 0.35), 0.0]} for r in ROOTS}
    idle["head"] = {"rotation": [sin(26.0, 4.0), sin(9.0, 6.0), 0.0]}
    for l, r in ARM_PAIRS:
        idle[l] = {"rotation": [0.0, 0.0, sin(22.0, 3.0)]}
        idle[r] = {"rotation": [0.0, 0.0, f"-{sin(22.0, 3.0)}"]}
    for n in ("pauldron_l", "pauldron_r", "staff", "tail"):
        idle[n] = {"rotation": [0.0, 0.0, sin(18.0, 2.5)]}
    anims["animation.hv.biped.idle"] = {"loop": True, "bones": idle}
    move = {}
    for l, r in ARM_PAIRS:
        move[l] = {"rotation": [sin(38.17, -38.0), 0.0, 0.0]}
        move[r] = {"rotation": [sin(38.17, 38.0), 0.0, 0.0]}
    for l, r in LEG_PAIRS:
        move[l] = {"rotation": [sin(38.17, 42.0), 0.0, 0.0]}
        move[r] = {"rotation": [sin(38.17, -42.0), 0.0, 0.0]}
    for r in ROOTS:
        move[r] = {"position": [0.0, f"math.abs({sin(76.34, 0.9)})", 0.0]}
    anims["animation.hv.biped.move"] = {
        "loop": True, "anim_time_update": "query.modified_distance_moved", "bones": move}

    # ---- quadruped: diagonal trot, head bob ----------------------------
    idle = {r: {"position": [0.0, sin(30.0, 0.3), 0.0]} for r in ROOTS}
    idle["head"] = {"rotation": [sin(20.0, 5.0), 0.0, 0.0]}
    idle["tail"] = {"rotation": [0.0, sin(26.0, 12.0), 0.0]}
    for n in ("ear_l", "antler_l", "eye_l"):
        idle[n] = {"rotation": [0.0, 0.0, sin(17.0, 4.0)]}
    for n in ("ear_r", "antler_r", "eye_r"):
        idle[n] = {"rotation": [0.0, 0.0, f"-{sin(17.0, 4.0)}"]}
    anims["animation.hv.quadruped.idle"] = {"loop": True, "bones": idle}
    move = {}
    for a, b in QUAD_LEGS:
        move[a] = {"rotation": [sin(38.17, 40.0), 0.0, 0.0]}
        move[b] = {"rotation": [sin(38.17, 40.0), 0.0, 0.0]}
    move["leg_fr"] = {"rotation": [sin(38.17, -40.0), 0.0, 0.0]}
    move["leg_bl"] = {"rotation": [sin(38.17, -40.0), 0.0, 0.0]}
    for r in ROOTS:
        move[r] = {"position": [0.0, f"math.abs({sin(76.34, 1.1)})", 0.0],
                   "rotation": [sin(76.34, 3.0), 0.0, 0.0]}
    move["head"] = {"rotation": [sin(76.34, 7.0), 0.0, 0.0]}
    move["tail"] = {"rotation": [sin(38.17, 16.0), 0.0, 0.0]}
    anims["animation.hv.quadruped.move"] = {
        "loop": True, "anim_time_update": "query.modified_distance_moved", "bones": move}

    # ---- crawler: travelling wave down the legs, low skittering body ----
    idle = {r: {"position": [0.0, sin(44.0, 0.25), 0.0]} for r in ROOTS}
    for i in range(1, 4):
        idle[f"leg{i}_l"] = {"rotation": [0.0, 0.0, sin(30.0, 4.0, i * 60)]}
        idle[f"leg{i}_r"] = {"rotation": [0.0, 0.0, f"-{sin(30.0, 4.0, i * 60)}"]}
    idle["fang_l"] = {"rotation": [0.0, sin(50.0, 6.0), 0.0]}
    idle["fang_r"] = {"rotation": [0.0, f"-{sin(50.0, 6.0)}", 0.0]}
    anims["animation.hv.crawler.idle"] = {"loop": True, "bones": idle}
    move = {}
    for i in range(1, 4):
        ph = (i - 1) * 120
        move[f"leg{i}_l"] = {"rotation": [sin(76.34, 26.0, ph), 0.0, sin(76.34, 16.0, ph)]}
        move[f"leg{i}_r"] = {"rotation": [sin(76.34, 26.0, ph + 180), 0.0, f"-{sin(76.34, 16.0, ph + 180)}"]}
    for r in ROOTS:
        move[r] = {"position": [0.0, f"math.abs({sin(152.0, 0.6)})", 0.0],
                   "rotation": [0.0, sin(76.34, 4.0), 0.0]}
    anims["animation.hv.crawler.move"] = {
        "loop": True, "anim_time_update": "query.modified_distance_moved", "bones": move}

    # ---- winged: real flap, driven by time (not distance) so it beats
    # while hovering too ------------------------------------------------
    idle = {}
    idle["wing_l"] = {"rotation": [0.0, 0.0, sin(110.0, 34.0)]}
    idle["wing_r"] = {"rotation": [0.0, 0.0, f"-{sin(110.0, 34.0)}"]}
    for r in ROOTS:
        idle[r] = {"position": [0.0, sin(110.0, 1.1, 90), 0.0]}
    idle["head"] = {"rotation": [sin(30.0, 5.0), 0.0, 0.0]}
    idle["neck"] = {"rotation": [sin(26.0, 4.0), 0.0, 0.0]}
    for n in ("tail", "tail1"):
        idle[n] = {"rotation": [sin(24.0, 8.0), 0.0, 0.0]}
    idle["tail2"] = {"rotation": [sin(24.0, 11.0, 40), 0.0, 0.0]}
    for n in ("leg_fl", "leg_fr", "leg_bl", "leg_br"):
        idle[n] = {"rotation": [22.0, 0.0, 0.0]}  # tucked while airborne
    anims["animation.hv.winged.idle"] = {"loop": True, "bones": idle}
    move = {}
    move["wing_l"] = {"rotation": [0.0, 0.0, sin(150.0, 52.0)]}
    move["wing_r"] = {"rotation": [0.0, 0.0, f"-{sin(150.0, 52.0)}"]}
    for r in ROOTS:
        move[r] = {"rotation": [-10.0, 0.0, 0.0]}
    move["neck"] = {"rotation": [8.0, 0.0, 0.0]}
    anims["animation.hv.winged.move"] = {"loop": True, "bones": move}

    # ---- boss: slow, heavy, deliberate ---------------------------------
    idle = {}
    for r in ROOTS:
        idle[r] = {"position": [0.0, sin(16.0, 1.2), 0.0], "rotation": [0.0, sin(7.0, 2.0), 0.0]}
    idle["head"] = {"rotation": [sin(14.0, 4.0), sin(6.0, 9.0), 0.0]}
    idle["torso"] = {"rotation": [0.0, sin(9.0, 3.0), 0.0]}
    for l, r in ARM_PAIRS:
        idle[l] = {"rotation": [sin(12.0, 5.0), 0.0, f"6.0 + {sin(10.0, 4.0)}"]}
        idle[r] = {"rotation": [sin(12.0, 5.0, 60), 0.0, f"-6.0 - {sin(10.0, 4.0)}"]}
    # Trailing cloth. The Hollow King's cloak and hem are five and four
    # separate panels now, each given a slightly different period so they
    # stream out of step instead of moving as one flat sheet.
    for i, n in enumerate(("cloak_a", "cloak_b", "cloak_c", "cloak_d", "cloak_e",
                           "hem_f", "hem_b", "hem_l", "hem_r",
                           "skirt_f", "skirt_l", "skirt_r",
                           "dress", "veil", "tail")):
        idle[n] = {"rotation": [sin(10.0 + i * 0.7, 7.0, i * 25), 0.0, 0.0]}
    for i, n in enumerate(("hair_l", "hair_r", "hair_c")):
        idle[n] = {"rotation": [sin(12.0 + i, 6.0, i * 40), 0.0, sin(9.0, 4.0, i * 30)]}
    for n in ("crown_a", "crown_b", "crown_c", "crown_d", "crown_e", "horn_l", "horn_r"):
        idle[n] = {"rotation": [0.0, 0.0, sin(13.0, 2.0)]}
    # The crown shards orbit the head rather than sitting still - it is the
    # King's most recognisable feature, so it should be the one that moves.
    for i, n in enumerate(("halo_f", "halo_b", "halo_l", "halo_r")):
        idle[n] = {
            "rotation": [sin(16.0, 8.0, i * 90), sin(11.0, 14.0, i * 90), 0.0],
            "position": [0.0, sin(19.0, 1.4, i * 90), 0.0],
        }
    idle["reaper"] = {"rotation": [sin(8.0, 3.0), 0.0, sin(11.0, 2.5)]}
    idle["wing_l"] = {"rotation": [0.0, 0.0, sin(34.0, 16.0)]}
    idle["wing_r"] = {"rotation": [0.0, 0.0, f"-{sin(34.0, 16.0)}"]}
    # The Widow's six three-segment legs. Each pair is driven a third of a
    # cycle apart so the set ripples front-to-back the way a spider's does,
    # and the tibia counter-rotates against the femur so the joint bends
    # instead of the whole leg swinging as one stick.
    for i in range(3):
        for side, sign in (("l", 1.0), ("r", -1.0)):
            ph = i * 60
            idle[f"spider_{side}{i}_femur"] = {
                "rotation": [sin(14.0, 6.0, ph), 0.0, f"{sign * 4.0} + {sin(12.0, 5.0, ph)}"],
            }
            idle[f"spider_{side}{i}_tibia"] = {
                "rotation": [sin(14.0, -9.0, ph), 0.0, f"{-sign * 3.0} - {sin(12.0, 7.0, ph)}"],
            }
            idle[f"spider_{side}{i}_tarsus"] = {"rotation": [sin(14.0, 5.0, ph + 30), 0.0, 0.0]}
    anims["animation.hv.boss.idle"] = {"loop": True, "bones": idle}
    move = {}
    for l, r in ARM_PAIRS:
        move[l] = {"rotation": [sin(24.0, -26.0), 0.0, 0.0]}
        move[r] = {"rotation": [sin(24.0, 26.0), 0.0, 0.0]}
    for l, r in LEG_PAIRS:
        move[l] = {"rotation": [sin(24.0, 30.0), 0.0, 0.0]}
        move[r] = {"rotation": [sin(24.0, -30.0), 0.0, 0.0]}
    for r in ROOTS:
        move[r] = {"position": [0.0, f"math.abs({sin(48.0, 1.6)})", 0.0]}
    # Walking: the spider legs stride, the cloth streams back.
    for i in range(3):
        for side, sign in (("l", 1.0), ("r", -1.0)):
            ph = i * 60 + (0 if sign > 0 else 90)
            move[f"spider_{side}{i}_femur"] = {"rotation": [sin(30.0, 26.0, ph), 0.0, sign * 6.0]}
            move[f"spider_{side}{i}_tibia"] = {"rotation": [sin(30.0, -34.0, ph), 0.0, 0.0]}
    for i, n in enumerate(("cloak_a", "cloak_b", "cloak_c", "cloak_d", "cloak_e",
                           "hem_f", "hem_b", "hem_l", "hem_r",
                           "skirt_f", "skirt_l", "skirt_r", "veil", "tail")):
        move[n] = {"rotation": [f"20.0 + {sin(38.0 + i, 9.0, i * 25)}", 0.0, 0.0]}
    anims["animation.hv.boss.move"] = {
        "loop": True, "anim_time_update": "query.modified_distance_moved", "bones": move}

    return anims


def write_animation_file(anims):
    data = {"format_version": "1.10.0", "animations": anims}
    p = os.path.join(RP, "animations", "hv_generic.animation.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {len(anims)} animations across {len(set(ARCHETYPE.values()))} archetypes")


def wire_entities():
    entity_dir = os.path.join(RP, "entity")
    count = 0
    for fname in sorted(os.listdir(entity_dir)):
        if not fname.endswith(".entity.json"):
            continue
        ident = fname[: -len(".entity.json")]
        if ident in SKIP:
            continue
        arch = ARCHETYPE.get(ident, DEFAULT_ARCHETYPE)
        p = os.path.join(entity_dir, fname)
        with open(p) as f:
            data = json.load(f)
        desc = data["minecraft:client_entity"]["description"]
        desc["animations"] = {
            "idle": f"animation.hv.{arch}.idle",
            "move": f"animation.hv.{arch}.move",
        }
        scripts = desc.setdefault("scripts", {})
        scripts["animate"] = ["idle", {"move": "query.modified_move_speed > 0.05"}]
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
        count += 1
    print(f"wired archetype animations into {count} entities")


if __name__ == "__main__":
    write_animation_file(build())
    wire_entities()
