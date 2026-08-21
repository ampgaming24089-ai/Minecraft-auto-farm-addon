#!/usr/bin/env python3
"""Animate every mob from its own skeleton.

Hand-authoring five clips for twenty-two rigs with sixty to a hundred bones
each is not work anyone finishes, and the half of it that does get finished
drives three bones and leaves the other ninety rigid - which is exactly what
"the mobs look flat and animation-less" meant.

So the clips are generated from the geometry. Every bone the kit produces is
named for what it is (`leg_l2_shin`, `wing_r_rib_1`, `tatter_4_end`,
`mote_3`), and that name is enough to know how it should move: legs swing
opposed front to back, wings beat, rags trail with a phase delay down their
length, motes orbit, jaws open on the attack. A bone the classifier does not
recognise is left alone rather than guessed at.

The result is that adding a limb to a model animates it too, with no second
edit anywhere.
"""

import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "RP", "models", "entity")
OUT = os.path.join(ROOT, "RP", "animations", "voidbound.mobs.animation.json")
CONTROLLERS = os.path.join(ROOT, "RP", "animation_controllers",
                           "voidbound.mob.animation_controllers.json")

# Which mobs get generated clips. Kept explicit so the older hand-written
# mobs keep the animations they already have.
ROSTER = [
    "void_dragon", "ender_overlord", "end_king",
    "void_stalker", "purpur_golem", "shulker_beast", "corrupted_enderman",
    "end_spider", "chorus_fiend", "obsidian_beast", "endermite_hive",
    "void_wisp", "void_slime", "teleporter", "end_crab", "ender_ghost",
    "astral_whale", "sky_ray", "ender_deer", "chorus_cow", "void_hog",
    "ender_bird", "echo_warden",
]

# Mobs that hold themselves in the air. Their idle gets a hover bob and their
# "walk" is a swim rather than a step.
AIRBORNE = {"void_dragon", "ender_overlord", "void_wisp", "ender_ghost",
            "astral_whale", "sky_ray", "ender_bird"}


def classify(bone):
    """What kind of thing is this bone, for animation purposes?

    Returns (kind, index) where index phases a bone against its siblings - the
    third link of a tail should lag the second, and the left legs should be
    half a cycle off the right.
    """
    b = bone
    trailing = re.findall(r"(\d+)", b)
    index = int(trailing[-1]) if trailing else 0

    if "_jaw" in b:
        return "jaw", index
    if "_tooth_" in b or "_maw" in b or "_nostril" in b or "_brow" in b:
        return "skip", index
    if b.startswith(("mote", "ring0", "ring1", "orbit", "satellite")):
        return "orbit", index
    if b.startswith(("wing", "primary", "covert", "fin_", "membrane")):
        return "wing", index
    if b.startswith(("tail", "trail", "wisp", "tatter", "rag", "shroud",
                     "drip", "tentacle", "frond")):
        return "trail", index
    if b.startswith(("leg", "fore_", "hind_", "thigh", "shank", "arm_",
                     "upper_", "claw_", "hand_", "digit", "talon", "toe")):
        # Side is what decides the phase: left legs lead, right legs follow.
        side = 1 if re.search(r"(^|_)l(\d|_|$)", b) else 0
        return "leg", index * 2 + side
    if b.startswith(("neck", "head", "face", "skull", "muzzle")):
        return "head", index
    if b.startswith(("shard", "spine", "spike", "quill", "bristle", "crest",
                     "splinter", "stem", "bud", "fruit", "antler", "horn",
                     "crystal", "brood", "cell", "rift", "flare")):
        return "ornament", index
    if b.startswith(("body", "chest", "torso", "hips", "rump", "abdomen",
                     "thorax", "shell", "seg", "blob", "core", "hump",
                     "shoulder", "waist", "pelvis", "breast", "mantle")):
        return "body", index
    return "other", index


def sway(amount, speed, phase, term="query.anim_time"):
    return "math.sin(%s * %d + %d) * %s" % (term, speed, phase, amount)


def build(name, bones, airborne):
    """The five clips for one skeleton."""
    idle, move, attack, hurt, death = {}, {}, {}, {}, {}

    for bone in bones:
        kind, index = classify(bone)
        if kind == "skip":
            continue
        phase = (index * 47) % 360
        opposite = (phase + 180) % 360

        if kind == "leg":
            # A walk cycle: swing about X, with the two sides opposed. The
            # amplitude is small on idle so a standing mob shifts rather than
            # marches on the spot.
            idle[bone] = {"rotation": [sway(1.5, 60, phase), 0, 0]}
            move[bone] = {"rotation": [sway(26, 260, phase), 0,
                                       sway(3, 260, opposite)]}
            attack[bone] = {"rotation": [sway(10, 400, phase), 0, 0]}
        elif kind == "wing":
            # The beat. Rolling the spar is what reads as a wingbeat; pitching
            # it only makes the wing nod.
            idle[bone] = {"rotation": [0, 0, sway(6, 70, phase)]}
            move[bone] = {"rotation": [sway(4, 150, phase), 0,
                                       sway(22, 150, phase)]}
            attack[bone] = {"rotation": [0, 0, sway(30, 260, phase)]}
        elif kind == "trail":
            # A wave travelling outward: each link lags the one before it, so
            # a tail whips rather than swinging as one stick.
            lag = index * 38
            idle[bone] = {"rotation": [sway(2.5, 55, lag),
                                       sway(4.0, 45, lag), 0]}
            move[bone] = {"rotation": [sway(4, 120, lag),
                                       sway(9, 110, lag), 0]}
            attack[bone] = {"rotation": [sway(6, 200, lag),
                                        sway(14, 190, lag), 0]}
        elif kind == "orbit":
            # Free-floating pieces: they keep turning regardless of state.
            spin = "query.anim_time * %d" % (60 + index * 17)
            for clip in (idle, move, attack):
                clip[bone] = {"rotation": [0, spin, 0]}
        elif kind == "jaw":
            idle[bone] = {"rotation": [sway(2.5, 40, phase), 0, 0]}
            move[bone] = {"rotation": [sway(4, 90, phase), 0, 0]}
            attack[bone] = {"rotation": ["math.sin(query.anim_time * 300) * 18 + 14",
                                         0, 0]}
        elif kind == "head":
            idle[bone] = {"rotation": [sway(2, 35, phase), sway(3, 28, phase), 0]}
            move[bone] = {"rotation": [sway(3, 110, phase), sway(4, 90, phase), 0]}
            attack[bone] = {"rotation": [sway(7, 220, phase), 0, 0]}
        elif kind == "ornament":
            idle[bone] = {"rotation": [sway(1.5, 50, phase), 0, sway(2, 44, phase)]}
            move[bone] = {"rotation": [sway(2.5, 130, phase), 0,
                                       sway(3, 120, phase)]}
        elif kind == "body":
            if airborne:
                idle[bone] = {"position": [0, sway(1.2, 45, phase), 0],
                              "rotation": [sway(2, 40, phase), 0,
                                           sway(2.5, 34, phase)]}
                move[bone] = {"position": [0, sway(2.0, 110, phase), 0],
                              "rotation": [sway(4, 100, phase), 0,
                                           sway(5, 90, phase)]}
            else:
                idle[bone] = {"position": [0, sway(0.35, 40, phase), 0],
                              "rotation": [0, 0, sway(1.2, 36, phase)]}
                move[bone] = {"position": [0, sway(0.9, 240, phase), 0],
                              "rotation": [sway(2, 240, phase), 0,
                                           sway(2.5, 120, phase)]}
            attack[bone] = {"rotation": [sway(5, 240, phase), 0, 0]}

    # Hurt is a whole-body flinch rather than a per-bone pose: it has to read
    # in the fifth of a second it is on screen, and it must not fight whatever
    # clip it interrupts.
    root = bones[0]
    hurt[root] = {
        "rotation": ["math.sin(query.anim_time * 900) * 9", 0,
                     "math.sin(query.anim_time * 1200) * 7"],
        "position": [0, "math.sin(query.anim_time * 900) * 0.8", 0],
    }

    # Death: fall onto one side and sink. Bedrock plays this once, so it is
    # written against anim_time directly rather than as a loop.
    death[root] = {
        "rotation": [0, 0, "math.min(query.anim_time * 110, 88)"],
        "position": [0, "-math.min(query.anim_time * 9, 7)", 0],
    }
    for bone in bones[1:]:
        kind, index = classify(bone)
        if kind in ("trail", "wing", "leg"):
            death[bone] = {"rotation": [
                "math.min(query.anim_time * %d, %d)" % (40 + index * 5,
                                                        18 + index * 3),
                0, 0]}

    return {
        "animation.voidbound.%s.idle" % name: {
            "loop": True, "animation_length": 4.0, "bones": idle},
        "animation.voidbound.%s.move" % name: {
            "loop": True, "animation_length": 2.0, "bones": move},
        "animation.voidbound.%s.attack" % name: {
            "loop": True, "animation_length": 0.75, "bones": attack},
        "animation.voidbound.%s.hurt" % name: {
            "loop": "hold_on_last_frame", "animation_length": 0.3,
            "bones": hurt},
        "animation.voidbound.%s.death" % name: {
            "loop": "hold_on_last_frame", "animation_length": 1.6,
            "bones": death},
    }


def full_controller():
    """One controller every generated mob shares: standing, moving, dying.

    Attack and hurt are deliberately *not* states here. No Molang query can see
    a swing land, so those two are fired from `mobActions.js` through
    /playanimation the moment the hit lands - and a controller state that also
    drove them would be fighting the same bones from the other direction, with
    the blend deciding the winner frame by frame. One system owns a bone at a
    time.

    `query.modified_move_speed` is what separates standing from moving:
    `query.is_moving` stays true for a tick after a mob stops, which shows up
    as a step taken on the spot.
    """
    return {
        "controller.animation.voidbound.mob.full": {
            "initial_state": "idle",
            "states": {
                "idle": {
                    "animations": ["idle"],
                    "blend_transition": 0.25,
                    "transitions": [
                        {"dying": "!query.is_alive"},
                        {"moving": "query.modified_move_speed > 0.05"},
                    ],
                },
                "moving": {
                    "animations": ["move"],
                    "blend_transition": 0.25,
                    "transitions": [
                        {"dying": "!query.is_alive"},
                        {"idle": "query.modified_move_speed <= 0.05"},
                    ],
                },
                "dying": {
                    "animations": ["death"],
                    "blend_transition": 0.1,
                    "transitions": [{"idle": "query.is_alive"}],
                },
            },
        },
    }


def main():
    animations = {}
    for name in ROSTER:
        path = os.path.join(MODELS, "%s.geo.json" % name)
        geo = json.load(open(path))["minecraft:geometry"][0]
        bones = [b["name"] for b in geo["bones"]]
        animations.update(build(name, bones, name in AIRBORNE))
        print("%-18s %3d bones" % (name, len(bones)))

    with open(OUT, "w") as handle:
        json.dump({"format_version": "1.10.0", "animations": animations},
                  handle, indent=1)
        handle.write("\n")

    existing = json.load(open(CONTROLLERS))
    existing["animation_controllers"].update(full_controller())
    with open(CONTROLLERS, "w") as handle:
        json.dump(existing, handle, indent=2)
        handle.write("\n")
    print("%d clips -> %s" % (len(animations), os.path.relpath(OUT, ROOT)))


if __name__ == "__main__":
    main()
