#!/usr/bin/env python3
"""Generate attack, hurt, death and alert clips for every pack mob.

    python3 tools/gen_mob_actions.py

The idle and move clips in RP/animations/voidbound.animation.json are authored
by hand, because each one is a specific idea about how that creature carries
itself. Action clips are not like that: an attack is a lunge, a hurt is a
recoil, a death is a collapse, and what changes between mobs is which bones
those map onto and how far they travel. That is a rule, so it is written as
one, and the output goes to its own file so the hand-authored one stays
readable.

Every mob uses the same short names - ea_alert, ea_death - so a single shared
animation controller drives all of them. Attack and hurt are one-shots fired
from script, because no client-side query can see a swing land.
"""

import json
import os
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "RP", "animations", "voidbound.actions.animation.json")

OD = OrderedDict


# ---------------------------------------------------------------------------
# Which bones each creature moves, and how hard.
#
# `scale` is a single dial for how far everything travels: a whale that
# recoils as sharply as a beetle looks weightless, and a beetle that recoils
# as slowly as a whale looks broken.
# ---------------------------------------------------------------------------

MOBS = {
    "lumen_wisp": dict(
        body="body", limbs=["shard_left", "shard_right", "shard_top"],
        kind="float", scale=0.8),
    "rift_stalker": dict(
        body="body", head="head", jaw="jaw", tail="tail",
        limbs=["leg_front_left", "leg_front_right", "leg_back_left", "leg_back_right"],
        kind="quadruped", scale=1.15),
    "void_moth": dict(
        body="body", head="head",
        limbs=["wing_upper_left", "wing_upper_right", "wing_lower_left", "wing_lower_right"],
        kind="flyer", scale=0.9),
    "echo_sentinel": dict(
        root="root", body="body", head="head", limbs=["arm_left", "arm_right"],
        kind="float", scale=1.1),
    "rift_sovereign": dict(
        root="root", body="shell_upper", head="crown",
        limbs=["shard_a", "shard_b", "shard_c", "shard_d"],
        kind="float", scale=1.0),
    "chorus_hopper": dict(
        body="body", head="head", limbs=["leg_left", "leg_right"],
        extra=["frond_left", "frond_right"], kind="biped", scale=0.85),
    "shard_wraith": dict(
        body="shroud", head="hood", limbs=["tatter_left", "tatter_right"],
        kind="float", scale=1.0),
    "crystal_crawler": dict(
        body="body", head="head", limbs=["leg_%d" % i for i in range(6)],
        kind="insect", scale=1.2),
    "void_serpent": dict(
        body="segment_0", head="head", jaw="jaw", tail="tail",
        limbs=["fin_left", "fin_right"], kind="serpent", scale=1.05),
    "glimmerfin": dict(
        body="body", tail="tail", limbs=["wing_left", "wing_right"],
        kind="ray", scale=0.75),
    "endstone_golem": dict(
        root="root", body="body", head="head", limbs=["arm_left", "arm_right"],
        legs=["leg_left", "leg_right"], kind="golem", scale=1.25),
    "astral_whale": dict(
        body="body", head="head", tail="tail", limbs=["fin_left", "fin_right"],
        kind="whale", scale=0.55),
    "voidling": dict(
        body="body", head="head", limbs=["arm_left", "arm_right"],
        kind="biped", scale=0.9),
    "ender_beetle": dict(
        body="body", head="head", limbs=["leg_%d" % i for i in range(6)],
        kind="insect", scale=1.15),
    # The Warden wears the Sentinel's skeleton. Same bones, more weight behind
    # every one of them, which is what makes it read as the boss version.
    "echo_warden": dict(
        root="root", body="body", head="head", limbs=["arm_left", "arm_right"],
        kind="float", scale=1.45),
    # The Titan wears the golem's skeleton, so it moves on the golem's bones -
    # slower and heavier, which is the whole difference between them.
    "void_titan": dict(
        root="root", body="body", head="head", limbs=["arm_left", "arm_right"],
        legs=["leg_left", "leg_right"], kind="golem", scale=1.6),
}

# Limbs that hang off the sides mirror; limbs in a row take a phase offset so
# they do not all move as one plank.
def side(name, index, total):
    if name.endswith("_left") or name.endswith("_right"):
        return -1.0 if name.endswith("_left") else 1.0
    if total <= 1:
        return 0.0
    # A row of legs: front pair one way, back pair the other.
    return 1.0 if index % 2 == 0 else -1.0


def k(*pairs):
    """Keyframe map from (time, value) pairs."""
    return OD((("%.2f" % t), v) for t, v in pairs)


def once(length, bones):
    return OD([
        ("loop", False),
        ("animation_length", round(length, 3)),
        ("override_previous_animation", False),
        ("bones", bones),
    ])


def looping(bones):
    return OD([("loop", True), ("bones", bones)])


def attack_clip(spec):
    s = spec["scale"]
    kind = spec["kind"]
    bones = OD()
    length = 0.55 if kind not in ("whale", "golem") else 0.9
    wind, hit, end = length * 0.32, length * 0.52, length

    # Wind up away from the target, then drive through it. The hold at the end
    # is what makes a swing land rather than merely pass by.
    body = spec.get("body")
    if body:
        bones[body] = {"rotation": k((0, [0, 0, 0]), (wind, [-14 * s, 0, 0]),
                                     (hit, [20 * s, 0, 0]), (end, [0, 0, 0]))}
    head = spec.get("head")
    if head:
        bones[head] = {"rotation": k((0, [0, 0, 0]), (wind, [-18 * s, 0, 0]),
                                     (hit, [26 * s, 0, 0]), (end, [0, 0, 0]))}
    jaw = spec.get("jaw")
    if jaw:
        # The jaw opens on the wind-up and snaps shut on contact.
        bones[jaw] = {"rotation": k((0, [0, 0, 0]), (wind, [34 * s, 0, 0]),
                                    (hit, [-4 * s, 0, 0]), (end, [0, 0, 0]))}
    limbs = spec.get("limbs", [])
    for i, limb in enumerate(limbs):
        d = side(limb, i, len(limbs))
        bones[limb] = {"rotation": k(
            (0, [0, 0, 0]),
            (wind, [-40 * s, 0, 14 * s * d]),
            (hit, [48 * s, 0, -8 * s * d]),
            (end, [0, 0, 0]))}
    root = spec.get("root")
    if root:
        bones[root] = {"position": k((0, [0, 0, 0]), (wind, [0, 0.6 * s, -0.8 * s]),
                                     (hit, [0, -0.4 * s, 1.6 * s]), (end, [0, 0, 0]))}
    return once(length, bones)


def hurt_clip(spec):
    s = spec["scale"]
    bones = OD()
    length = 0.34 if spec["kind"] != "whale" else 0.6
    peak = length * 0.28

    body = spec.get("body")
    if body:
        bones[body] = {"rotation": k((0, [0, 0, 0]), (peak, [-22 * s, 6 * s, 9 * s]),
                                     (length, [0, 0, 0]))}
    head = spec.get("head")
    if head:
        bones[head] = {"rotation": k((0, [0, 0, 0]), (peak, [-26 * s, -9 * s, 0]),
                                     (length, [0, 0, 0]))}
    limbs = spec.get("limbs", [])
    for i, limb in enumerate(limbs):
        d = side(limb, i, len(limbs))
        bones[limb] = {"rotation": k((0, [0, 0, 0]), (peak, [-16 * s, 0, 30 * s * d]),
                                     (length, [0, 0, 0]))}
    tail = spec.get("tail")
    if tail:
        bones[tail] = {"rotation": k((0, [0, 0, 0]), (peak, [18 * s, 22 * s, 0]),
                                     (length, [0, 0, 0]))}
    root = spec.get("root")
    if root:
        bones[root] = {"position": k((0, [0, 0, 0]), (peak, [0, 0, -1.4 * s]),
                                     (length, [0, 0, 0]))}
    return once(length, bones)


# Bedrock keeps a dead entity around for about twenty ticks and then removes
# it. A collapse longer than that is a collapse nobody ever sees the end of, so
# every death clip finishes inside the window whatever the creature's weight.
DEATH_SECONDS = 0.95


def death_clip(spec):
    """The collapse. Held at the end, because it is the last thing it does."""
    s = spec["scale"]
    kind = spec["kind"]
    bones = OD()
    length = DEATH_SECONDS
    mid = length * 0.45

    # Fliers sink; everything else falls over sideways.
    sinks = kind in ("float", "flyer", "whale", "ray", "serpent")
    body = spec.get("body")
    if body:
        tip = [14 * s, 0, 0] if sinks else [0, 0, 74]
        bones[body] = {"rotation": k((0, [0, 0, 0]), (mid, [v * 0.5 for v in tip]),
                                     (length, tip))}
    head = spec.get("head")
    if head:
        bones[head] = {"rotation": k((0, [0, 0, 0]), (mid, [16 * s, 0, 0]),
                                     (length, [30 * s, 0, 0]))}
    limbs = spec.get("limbs", [])
    for i, limb in enumerate(limbs):
        d = side(limb, i, len(limbs))
        bones[limb] = {"rotation": k((0, [0, 0, 0]),
                                     (mid, [18 * s, 0, 22 * s * d]),
                                     (length, [34 * s, 0, 40 * s * d]))}
    legs = spec.get("legs", [])
    for i, leg in enumerate(legs):
        d = -1.0 if leg.endswith("_left") else 1.0
        bones[leg] = {"rotation": k((0, [0, 0, 0]), (length, [26 * s, 0, 12 * s * d]))}
    tail = spec.get("tail")
    if tail:
        bones[tail] = {"rotation": k((0, [0, 0, 0]), (length, [-24 * s, 0, 0]))}
    root = spec.get("root")
    if root:
        drop = -3.0 * s if sinks else -1.4 * s
        bones[root] = {"position": k((0, [0, 0, 0]), (mid, [0, drop * 0.4, 0]),
                                     (length, [0, drop, 0]))}
    return once(length, bones)


def alert_clip(spec):
    """The stance it takes while it has something to kill.

    A held pose plus a fast tremor: the pose says "it has seen you", the
    tremor says "it is about to do something about it".
    """
    s = spec["scale"]
    bones = OD()
    tense = "math.sin(query.life_time * 340) * %.2f" % (1.6 * s)

    body = spec.get("body")
    if body:
        bones[body] = {"rotation": [-7 * s, 0, tense]}
    head = spec.get("head")
    if head:
        bones[head] = {"rotation": [10 * s, tense, 0]}
    limbs = spec.get("limbs", [])
    for i, limb in enumerate(limbs):
        d = side(limb, i, len(limbs))
        bones[limb] = {"rotation": [-12 * s, 0, "%.2f + %s" % (10 * s * d, tense)]}
    root = spec.get("root")
    if root:
        bones[root] = {"position": [0, "math.sin(query.life_time * 170) * %.2f" % (0.3 * s), 0]}
    return looping(bones)


def tidy(value):
    """Round every number in the tree.

    Degrees carry no meaning past two decimals, and unrounded floats leave
    -16.099999999999998 all over a file people have to read.
    """
    if isinstance(value, float):
        rounded = round(value, 2)
        return int(rounded) if rounded == int(rounded) else rounded
    if isinstance(value, list):
        return [tidy(v) for v in value]
    if isinstance(value, dict):
        return OD((key, tidy(v)) for key, v in value.items())
    return value


def main():
    animations = OD()
    for name in sorted(MOBS):
        spec = MOBS[name]
        base = "animation.voidbound.%s" % name
        animations["%s.attack" % base] = attack_clip(spec)
        animations["%s.hurt" % base] = hurt_clip(spec)
        animations["%s.death" % base] = death_clip(spec)
        animations["%s.alert" % base] = alert_clip(spec)

    with open(OUT, "w") as fh:
        json.dump(tidy(OD([("format_version", "1.8.0"), ("animations", animations)])), fh, indent=2)
        fh.write("\n")
    print("%d action clips across %d mobs -> %s"
          % (len(animations), len(MOBS), os.path.relpath(OUT, ROOT)))


if __name__ == "__main__":
    main()
