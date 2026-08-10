#!/usr/bin/env python3
"""
Generates one shared idle/walk animation pair and wires it into every
living-mob entity file, so mobs stop being static "blank outline" models.

Bone names vary a lot across this pack's roster (humanoid arm_l/arm_r vs
left_arm/right_arm, quadruped leg_fl/fr/bl/br, crawler leg1_l/leg2_l/...,
wings, tails, accessory bones like horns/antlers/ears/pauldrons/cloaks). A
single shared animation file just lists every bone name any entity in the
roster uses; Bedrock silently ignores bone names an entity's geometry
doesn't have (this is the same mechanism vanilla uses to share one
"humanoid" animation set across differently-rigged mobs), so one generic
pair works for all of them without per-entity authoring.

Verified against Mojang's bedrock-samples: spider.animation.json for the
anim_time_update + math.sin(query.anim_time * ...) leg-swing pattern, and
fox.animation.json for a plain query.anim_time idle sway with no
anim_time_update override (defaults to real elapsed seconds). The
description.animations / scripts.animate wiring mirrors horse_v2 and
chicken.animation.json (mixing unconditional and {name: condition} entries
in the same array).

Run with: python3 tools/gen_animations.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "RP")

# Entities that are projectiles, not living mobs - no idle/walk motion.
SKIP_ENTITIES = {"debris_projectile", "imp_fireball"}

IDLE_BONES = {}
WALK_BONES = {}


def idle(name, expr_by_axis):
    IDLE_BONES.setdefault(name, {}).update(expr_by_axis)


def walk(name, expr_by_axis):
    WALK_BONES.setdefault(name, {}).update(expr_by_axis)


# --- head: a slow nod ------------------------------------------------------
idle("head", {"rotation": ["math.sin(query.anim_time * 30.0) * 4.0", 0.0, 0.0]})

# --- root bones: gentle breathing bob --------------------------------------
for root in ("body", "base", "core", "legs"):
    idle(root, {"position": [0.0, "math.sin(query.anim_time * 40.0) * 0.4", 0.0]})

# --- secondary torso-ish bones: slight sway --------------------------------
for i, name in enumerate(("torso", "hair", "veil", "dress", "hood_back", "staff", "neck")):
    phase = i * 25
    idle(name, {"rotation": [0.0, 0.0, f"math.sin(query.anim_time * 14.0 + {phase}) * 2.5"]})

# --- triple accessory sets (cloak_a/b/c, crown_a/b/c): staggered sway ------
for group in ("cloak", "crown"):
    for i, suffix in enumerate("abc"):
        phase = i * 40
        idle(f"{group}_{suffix}", {"rotation": [0.0, 0.0, f"math.sin(query.anim_time * 12.0 + {phase}) * 3.0"]})

# --- arm pairs: idle sway, walk counter-swing with the legs ----------------
ARM_PAIRS = [("left_arm", "right_arm"), ("arm_l", "arm_r"), ("spider_arm_l", "spider_arm_r")]
for left, right in ARM_PAIRS:
    idle(left, {"rotation": [0.0, 0.0, "math.sin(query.anim_time * 25.0) * 3.0"]})
    idle(right, {"rotation": [0.0, 0.0, "-math.sin(query.anim_time * 25.0) * 3.0"]})
    walk(left, {"rotation": ["-math.sin(query.anim_time * 38.17) * 15.0", 0.0, 0.0]})
    walk(right, {"rotation": ["math.sin(query.anim_time * 38.17) * 15.0", 0.0, 0.0]})

# --- simple biped leg pair: idle weight-shift, walk full swing ------------
idle("leg_l", {"rotation": ["math.sin(query.anim_time * 18.0) * 2.0", 0.0, 0.0]})
idle("leg_r", {"rotation": ["-math.sin(query.anim_time * 18.0) * 2.0", 0.0, 0.0]})
walk("leg_l", {"rotation": ["math.sin(query.anim_time * 38.17) * 25.0", 0.0, 0.0]})
walk("leg_r", {"rotation": ["-math.sin(query.anim_time * 38.17) * 25.0", 0.0, 0.0]})

# --- quadruped legs: still at idle, diagonal trot gait on walk ------------
walk("leg_fl", {"rotation": ["math.sin(query.anim_time * 38.17) * 22.0", 0.0, 0.0]})
walk("leg_br", {"rotation": ["math.sin(query.anim_time * 38.17) * 22.0", 0.0, 0.0]})
walk("leg_fr", {"rotation": ["-math.sin(query.anim_time * 38.17) * 22.0", 0.0, 0.0]})
walk("leg_bl", {"rotation": ["-math.sin(query.anim_time * 38.17) * 22.0", 0.0, 0.0]})

# --- many-legged crawler: still at idle, spider-style wave gait on walk ---
for i in range(1, 4):
    phase = (i - 1) * 90
    walk(f"leg{i}_l", {"rotation": [f"math.sin(query.anim_time * 38.17 + {phase}) * 20.0", 0.0, 0.0]})
    walk(f"leg{i}_r", {"rotation": [f"-math.sin(query.anim_time * 38.17 + {phase}) * 20.0", 0.0, 0.0]})

# --- tails: a slow, slightly out-of-phase sway -----------------------------
idle("tail", {"rotation": ["math.sin(query.anim_time * 16.0) * 6.0", 0.0, 0.0]})
idle("tail1", {"rotation": ["math.sin(query.anim_time * 16.0) * 6.0", 0.0, 0.0]})
idle("tail2", {"rotation": ["math.sin(query.anim_time * 16.0 - 30.0) * 8.0", 0.0, 0.0]})

# --- wings: a slow resting flap, not a full flight flap --------------------
idle("wing_l", {"rotation": [0.0, 0.0, "math.sin(query.anim_time * 20.0) * 4.0"]})
idle("wing_r", {"rotation": [0.0, 0.0, "-math.sin(query.anim_time * 20.0) * 4.0"]})

# --- small paired accessories: a subtle twitch -----------------------------
ACCESSORY_PAIRS = [
    ("ear_l", "ear_r"), ("antler_l", "antler_r"), ("horn_l", "horn_r"),
    ("fang_l", "fang_r"), ("eye_l", "eye_r"), ("pauldron_l", "pauldron_r"),
]
for left, right in ACCESSORY_PAIRS:
    idle(left, {"rotation": [0.0, 0.0, "math.sin(query.anim_time * 15.0) * 2.0"]})
    idle(right, {"rotation": [0.0, 0.0, "-math.sin(query.anim_time * 15.0) * 2.0"]})

# --- helm spike: tiny bob ---------------------------------------------------
idle("helm_spike", {"position": [0.0, "math.sin(query.anim_time * 18.0) * 0.2", 0.0]})

# --- floating motes/debris (soul_wisp, poltergeist): orbiting bob ---------
for i, name in enumerate(("t1", "t2", "t3", "debris1", "debris2", "debris3")):
    phase = i * 120
    idle(name, {"position": [0.0, f"math.sin(query.anim_time * 25.0 + {phase}) * 3.0", 0.0]})


def gen_animation_file():
    data = {
        "format_version": "1.10.0",
        "animations": {
            "animation.hv.idle": {"loop": True, "bones": IDLE_BONES},
            "animation.hv.walk": {
                "loop": True,
                "anim_time_update": "query.modified_distance_moved",
                "bones": WALK_BONES,
            },
        },
    }
    p = os.path.join(RP, "animations", "hv_generic.animation.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2)
    print("wrote", p)


def wire_entities():
    entity_dir = os.path.join(RP, "entity")
    count = 0
    for fname in sorted(os.listdir(entity_dir)):
        if not fname.endswith(".entity.json"):
            continue
        identifier = fname[: -len(".entity.json")]
        if identifier in SKIP_ENTITIES:
            continue
        p = os.path.join(entity_dir, fname)
        with open(p) as f:
            data = json.load(f)
        desc = data["minecraft:client_entity"]["description"]
        desc["animations"] = {"idle": "animation.hv.idle", "walk": "animation.hv.walk"}
        scripts = desc.setdefault("scripts", {})
        scripts["animate"] = ["idle", {"walk": "query.modified_move_speed > 0.05"}]
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
        count += 1
    print(f"wired idle/walk animations into {count} entities")


if __name__ == "__main__":
    gen_animation_file()
    wire_entities()
