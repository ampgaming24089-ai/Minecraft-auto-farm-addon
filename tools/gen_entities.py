#!/usr/bin/env python3
"""
Generates BP client-independent geometry + matching RP textures for every
Hollow Veil creature from one shared cube list per entity (see boxuv.py).
Also writes the RP entity client-definition JSON + a shared render
controller/material so each mob actually renders once imported.

Run standalone: python3 tools/gen_entities.py
"""
import json
import os

from PIL import ImageDraw

import boxuv
from gen_assets import PAL, RP, save

CUBE = tuple  # (origin(x,y,z), size(dx,dy,dz))


def entity_geo(identifier, tex_name, bones, palette, atlas_width=64, visible_bounds=(2, 2.5, 1)):
    """bones: list of {name, parent, pivot, cubes:[{name, origin, size, part}]}
    part selects a palette sub-key ('top'/'side'/'front') for shading."""
    atlas = boxuv.Atlas(max_width=atlas_width)
    for bone in bones:
        for cube in bone["cubes"]:
            c = boxuv.Cube(cube["name"], cube["origin"], cube["size"])
            atlas.place(c)
            cube["_uv"] = c.uv

    w, h = atlas.finalize_size()
    img = boxuv.new_canvas(w, h)
    draw = ImageDraw.Draw(img)
    seed = abs(hash(identifier)) % 10000
    for bone in bones:
        for i, cube in enumerate(bone["cubes"]):
            c = boxuv.Cube(cube["name"], cube["origin"], cube["size"])
            c.uv = cube["_uv"]
            pal = cube.get("palette", palette)
            boxuv.paint_cube(draw, c, pal, seed=seed + i)

    save(img, RP, "textures", "entity", f"{tex_name}.png")

    geo_bones = []
    for bone in bones:
        b = {"name": bone["name"], "pivot": list(bone["pivot"])}
        if bone.get("parent"):
            b["parent"] = bone["parent"]
        b["cubes"] = [
            {"origin": list(c["origin"]), "size": list(c["size"]), "uv": list(c["_uv"])}
            for c in bone["cubes"]
        ]
        geo_bones.append(b)

    geo = {
        "format_version": "1.16.0",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": f"geometry.hv_{identifier}",
                    "texture_width": w,
                    "texture_height": h,
                    "visible_bounds_width": visible_bounds[0],
                    "visible_bounds_height": visible_bounds[1],
                    "visible_bounds_offset": [0, visible_bounds[2], 0],
                },
                "bones": geo_bones,
            }
        ],
    }
    geo_path = os.path.join(RP, "models", "entity", f"{identifier}.geo.json")
    os.makedirs(os.path.dirname(geo_path), exist_ok=True)
    with open(geo_path, "w") as f:
        json.dump(geo, f, indent=2)
    return geo_path


def write_client_entity(identifier, tex_name, geo_id, spawn_egg_colors=None, scale=1.0):
    data = {
        "format_version": "1.16.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": f"hollowveil:{identifier}",
                "materials": {"default": "entity_alphatest"},
                "textures": {"default": f"textures/entity/{tex_name}"},
                "geometry": {"default": f"geometry.hv_{identifier}"},
                "render_controllers": ["controller.render.hv_default"],
                "scripts": {"scale": str(scale)},
            }
        },
    }
    if spawn_egg_colors:
        data["minecraft:client_entity"]["description"]["spawn_egg"] = {
            "base_color": spawn_egg_colors[0],
            "overlay_color": spawn_egg_colors[1],
        }
    p = os.path.join(RP, "entity", f"{identifier}.entity.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2)
    return p


def write_shared_render_controller():
    data = {
        "format_version": "1.10.0",
        "render_controllers": {
            "controller.render.hv_default": {
                "geometry": "Geometry.default",
                "materials": [{"*": "Material.default"}],
                "textures": ["Texture.default"],
            }
        },
    }
    p = os.path.join(RP, "render_controllers", "hv_default.render_controllers.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Cube helper shorthands
# ---------------------------------------------------------------------------
def cube(name, origin, size, part="side"):
    return {"name": name, "origin": origin, "size": size, "part": part}


def bone(name, pivot, cubes, parent=None):
    return {"name": name, "parent": parent, "pivot": pivot, "cubes": cubes}


# ---------------------------------------------------------------------------
# Entity definitions
# ---------------------------------------------------------------------------
ENTITIES = []


def add(identifier, palette_key, bones, scale=1.0, visible_bounds=(2, 2.5, 1)):
    ENTITIES.append((identifier, palette_key, bones, scale, visible_bounds))


# Wraith: hooded floating robe
add(
    "wraith",
    "wraith",
    [
        bone("body", [0, 12, 0], [cube("robe_lower", [-6, 4, -4], [12, 10, 8])]),
        bone("torso", [0, 16, 0], [cube("robe_upper", [-5, 14, -3], [10, 8, 6])], parent="body"),
        bone("head", [0, 22, 0], [cube("hood", [-4, 22, -4], [8, 8, 8])], parent="torso"),
        bone("left_arm", [5, 20, 0], [cube("l_arm", [4, 8, -1.5], [3, 12, 3])], parent="torso"),
        bone("right_arm", [-5, 20, 0], [cube("r_arm", [-7, 8, -1.5], [3, 12, 3])], parent="torso"),
        bone("tail", [0, 4, 4], [cube("robe_tail", [-4, 0, 4], [8, 6, 2])], parent="body"),
    ],
)

# Banshee: wide dress, raised arms, trailing hair
add(
    "banshee",
    "banshee",
    [
        bone("body", [0, 12, 0], [cube("dress", [-7, 4, -4], [14, 10, 8])]),
        bone("torso", [0, 16, 0], [cube("torso", [-4.5, 15, -3], [9, 9, 6])], parent="body"),
        bone("head", [0, 24, 0], [cube("head", [-3.5, 24, -3.5], [7, 8, 7])], parent="torso"),
        bone("hair", [0, 26, -3.5], [cube("hair", [-4, 20, -5.5], [8, 6, 2])], parent="head"),
        bone("left_arm", [5.5, 22, 0], [cube("l_arm", [4.5, 12, -1.5], [3, 10, 3])], parent="torso"),
        bone("right_arm", [-5.5, 22, 0], [cube("r_arm", [-7.5, 12, -1.5], [3, 10, 3])], parent="torso"),
        bone("tail", [0, 4, 4], [cube("dress_tail", [-5, 0, 4], [10, 8, 2])], parent="body"),
    ],
    visible_bounds=(2.5, 2.8, 1.2),
)

# Poltergeist: floating debris cluster
add(
    "poltergeist",
    "poltergeist",
    [
        bone("core", [0, 10, 0], [cube("core", [-3, 7, -3], [6, 6, 6])]),
        bone("debris1", [4, 12, 0], [cube("d1", [3, 10, -1.5], [3, 3, 3])], parent="core"),
        bone("debris2", [-4, 9, 2], [cube("d2", [-6, 8, 1], [2, 2, 2])], parent="core"),
        bone("debris3", [0, 14, -3], [cube("d3", [-3, 13, -5], [4, 1, 2])], parent="core"),
    ],
    scale=0.8,
    visible_bounds=(1.4, 1.4, 0.7),
)

# Hellhound: quadruped
add(
    "hellhound",
    "hellhound",
    [
        bone("body", [0, 10, 0], [cube("body", [-4, 7, -7], [8, 7, 14])]),
        bone("head", [0, 12, -9], [cube("head", [-3, 9.5, -12], [6, 5, 6]), cube("snout", [-1.5, 9.5, -14.5], [3, 3, 2.5])], parent="body"),
        bone("ear_l", [2, 15, -11], [cube("ear_l", [1.5, 14.5, -12], [1, 2, 1])], parent="head"),
        bone("ear_r", [-2, 15, -11], [cube("ear_r", [-2.5, 14.5, -12], [1, 2, 1])], parent="head"),
        bone("tail", [0, 10, 7], [cube("tail", [-1, 8, 7], [2, 2, 8])], parent="body"),
        bone("leg_fl", [3, 7, -5], [cube("leg_fl", [1.5, 0, -6.5], [3, 7, 3])], parent="body"),
        bone("leg_fr", [-3, 7, -5], [cube("leg_fr", [-4.5, 0, -6.5], [3, 7, 3])], parent="body"),
        bone("leg_bl", [3, 7, 5], [cube("leg_bl", [1.5, 0, 3.5], [3, 7, 3])], parent="body"),
        bone("leg_br", [-3, 7, 5], [cube("leg_br", [-4.5, 0, 3.5], [3, 7, 3])], parent="body"),
    ],
    visible_bounds=(2.2, 1.4, 1.6),
)

# Imp: small biped flyer with wings
add(
    "imp",
    "imp",
    [
        bone("body", [0, 10, 0], [cube("body", [-2.5, 7, -2], [5, 6, 4])]),
        bone("head", [0, 16, 0], [cube("head", [-2.5, 16, -2.5], [5, 5, 5])], parent="body"),
        bone("arm_l", [3, 13, 0], [cube("arm_l", [2, 8, -1], [2, 5, 2])], parent="body"),
        bone("arm_r", [-3, 13, 0], [cube("arm_r", [-4, 8, -1], [2, 5, 2])], parent="body"),
        bone("leg_l", [1.5, 7, 0], [cube("leg_l", [0.5, 2, -1], [2, 5, 2])], parent="body"),
        bone("leg_r", [-1.5, 7, 0], [cube("leg_r", [-2.5, 2, -1], [2, 5, 2])], parent="body"),
        bone("wing_l", [2.5, 13, 1], [cube("wing_l", [2.5, 8, 1], [1, 6, 8])], parent="body"),
        bone("wing_r", [-2.5, 13, 1], [cube("wing_r", [-3.5, 8, 1], [1, 6, 8])], parent="body"),
        bone("tail", [0, 8, 2], [cube("tail", [-0.5, 6, 2], [1, 1, 6])], parent="body"),
    ],
    scale=0.7,
    visible_bounds=(1.6, 1.6, 0.9),
)

# Shade: smoky humanoid
add(
    "shade",
    "shade",
    [
        bone("body", [0, 10, 0], [cube("body", [-3, 8, -2], [6, 10, 4])]),
        bone("head", [0, 20, 0], [cube("head", [-3, 18, -3], [6, 6, 6])], parent="body"),
        bone("arm_l", [4, 17, 0], [cube("arm_l", [3, 7, -1], [2, 10, 2])], parent="body"),
        bone("arm_r", [-4, 17, 0], [cube("arm_r", [-5, 7, -1], [2, 10, 2])], parent="body"),
        bone("leg_l", [1.5, 8, 0], [cube("leg_l", [0.5, -2, -1], [2, 10, 2])], parent="body"),
        bone("leg_r", [-1.5, 8, 0], [cube("leg_r", [-2.5, -2, -1], [2, 10, 2])], parent="body"),
    ],
    visible_bounds=(1.8, 2.4, 0.9),
)

# Fallen Knight: heavy armoured biped
add(
    "fallen_knight",
    "knight",
    [
        bone("body", [0, 10, 0], [cube("body", [-5, 9, -3], [10, 12, 6])]),
        bone("pauldron_l", [5.5, 20, 0], [cube("pl", [4, 18.5, -3.5], [3, 3, 5])], parent="body"),
        bone("pauldron_r", [-5.5, 20, 0], [cube("pr", [-7, 18.5, -3.5], [3, 3, 5])], parent="body"),
        bone("head", [0, 22, 0], [cube("head", [-4, 21, -4], [8, 8, 8])], parent="body"),
        bone("arm_l", [6.5, 18, 0], [cube("arm_l", [5, 8, -2], [4, 12, 4])], parent="body"),
        bone("arm_r", [-6.5, 18, 0], [cube("arm_r", [-9, 8, -2], [4, 12, 4])], parent="body"),
        bone("leg_l", [2.5, 9, 0], [cube("leg_l", [0.5, -5, -2], [4, 14, 4])], parent="body"),
        bone("leg_r", [-2.5, 9, 0], [cube("leg_r", [-4.5, -5, -2], [4, 14, 4])], parent="body"),
    ],
    visible_bounds=(2.2, 2.9, 1.0),
)

# Soul Wisp: tiny orb with tendrils
add(
    "soul_wisp",
    "soulwisp",
    [
        bone("core", [0, 9, 0], [cube("core", [-2, 7, -2], [4, 4, 4])]),
        bone("t1", [2, 9, 0], [cube("t1", [2, 8, -0.5], [1, 4, 1])], parent="core"),
        bone("t2", [-2, 9, 1], [cube("t2", [-3, 8, 0.5], [1, 4, 1])], parent="core"),
        bone("t3", [0, 9, -2], [cube("t3", [-0.5, 8, -3], [1, 4, 1])], parent="core"),
    ],
    scale=0.5,
    visible_bounds=(1, 1, 0.5),
)

# Occultist: robed NPC trader
add(
    "occultist",
    "occultist",
    [
        bone("body", [0, 12, 0], [cube("robe", [-5, 3, -3], [10, 13, 6])]),
        bone("hood_back", [0, 22, 2], [cube("hb", [-4, 20, 1.5], [8, 4, 2])], parent="body"),
        bone("head", [0, 22, 0], [cube("head", [-4, 20, -4], [8, 8, 8])], parent="body"),
        bone("arm_l", [6, 18, 0], [cube("arm_l", [5, 6, -1.5], [3, 12, 3])], parent="body"),
        bone("arm_r", [-6, 18, 0], [cube("arm_r", [-8, 6, -1.5], [3, 12, 3])], parent="body"),
        bone("staff", [-8, 6, 0], [cube("staff", [-8.5, 0, -0.5], [1, 18, 1])], parent="arm_r"),
    ],
    visible_bounds=(2.2, 2.9, 1.1),
)

# --- Bosses ---

add(
    "hollow_king",
    "hollow_king",
    [
        bone("base", [0, 8, 0], [cube("robe_swirl", [-9, 0, -9], [18, 10, 18])]),
        bone("cloak_a", [0, 8, 9], [cube("cloak_a", [-8, 4, 9], [16, 20, 2])], parent="base"),
        bone("cloak_b", [6, 8, 9], [cube("cloak_b", [4, 2, 9.2], [4, 16, 2])], parent="base"),
        bone("cloak_c", [-6, 8, 9], [cube("cloak_c", [-8, 2, 9.2], [4, 16, 2])], parent="base"),
        bone("torso", [0, 18, 0], [cube("ribcage", [-7, 18, -4], [14, 16, 8], "front")], parent="base"),
        bone("head", [0, 36, 0], [cube("skull", [-5, 36, -5], [10, 10, 10])], parent="torso"),
        bone("crown_a", [0, 46, 0], [cube("crown_a", [-1, 46, -1], [2, 4, 2], "top")], parent="head"),
        bone("crown_b", [3, 46, 0], [cube("crown_b", [2, 46, -1], [2, 3, 2], "top")], parent="head"),
        bone("crown_c", [-3, 46, 0], [cube("crown_c", [-4, 46, -1], [2, 3, 2], "top")], parent="head"),
        bone("arm_l", [9, 30, 0], [cube("arm_l", [7, 14, -2.5], [5, 16, 5])], parent="torso"),
        bone("arm_r", [-9, 30, 0], [cube("arm_r", [-12, 14, -2.5], [5, 16, 5])], parent="torso"),
    ],
    scale=1.6,
    visible_bounds=(4.5, 5.5, 2.2),
)

add(
    "weeping_widow",
    "weeping_widow",
    [
        bone("dress", [0, 7, 0], [cube("dress_flare", [-11, 0, -9], [22, 14, 7])]),
        bone("torso", [0, 18, 0], [cube("torso", [-6, 15, -3.5], [12, 14, 7])], parent="dress"),
        bone("head", [0, 33, 0], [cube("head", [-4.5, 33, -4.5], [9, 10, 9])], parent="torso"),
        bone("veil", [0, 34, -4.5], [cube("veil", [-5, 28, -6.5], [10, 8, 2])], parent="head"),
        bone("arm_l", [7, 25, 0], [cube("arm_l", [5, 12, -2], [4, 14, 4])], parent="torso"),
        bone("arm_r", [-7, 25, 0], [cube("arm_r", [-9, 12, -2], [4, 14, 4])], parent="torso"),
        bone("spider_arm_l", [10, 16, 3], [cube("sa_l", [9, 8, 2], [2, 18, 2])], parent="torso"),
        bone("spider_arm_r", [-10, 16, 3], [cube("sa_r", [-11, 8, 2], [2, 18, 2])], parent="torso"),
        bone("tail", [0, 6, 7], [cube("dress_tail", [-7, 0, 7], [14, 10, 2])], parent="dress"),
    ],
    scale=1.5,
    visible_bounds=(4.2, 5.2, 2.4),
)

add(
    "malacoda",
    "malacoda",
    [
        bone("legs", [0, 8, 0], [cube("leg_l", [2, 0, -3], [6, 16, 6]), cube("leg_r", [-8, 0, -3], [6, 16, 6])]),
        bone("torso", [0, 24, 0], [cube("torso", [-8, 24, -4.5], [16, 18, 9])], parent="legs"),
        bone("head", [0, 42, 0], [cube("head", [-5, 42, -5], [10, 10, 10])], parent="torso"),
        bone("horn_l", [3, 52, -2], [cube("horn_l", [2, 52, -3], [2, 6, 2], "top")], parent="head"),
        bone("horn_r", [-3, 52, -2], [cube("horn_r", [-4, 52, -3], [2, 6, 2], "top")], parent="head"),
        bone("arm_l", [11, 36, 0], [cube("arm_l", [8, 18, -2.5], [5, 18, 5])], parent="torso"),
        bone("arm_r", [-11, 36, 0], [cube("arm_r", [-13, 18, -2.5], [5, 18, 5])], parent="torso"),
        bone("tail", [0, 22, 4], [cube("tail", [-1.5, 12, 4], [3, 3, 14])], parent="legs"),
        bone("wing_l", [8, 38, 4], [cube("wing_l", [8, 24, 4], [2, 18, 24], "front")], parent="torso"),
        bone("wing_r", [-8, 38, 4], [cube("wing_r", [-10, 24, 4], [2, 18, 24], "front")], parent="torso"),
    ],
    scale=1.8,
    visible_bounds=(5.5, 6.5, 3.5),
)

# --- Projectiles (tiny) ---
add(
    "debris_projectile",
    "poltergeist",
    [bone("core", [0, 0, 0], [cube("core", [-2, -2, -2], [4, 4, 4])])],
    scale=0.4,
    visible_bounds=(0.6, 0.6, 0.3),
)
add(
    "imp_fireball",
    "imp",
    [bone("core", [0, 0, 0], [cube("core", [-2.5, -2.5, -2.5], [5, 5, 5])])],
    scale=0.4,
    visible_bounds=(0.6, 0.6, 0.3),
)


def run():
    write_shared_render_controller()
    for identifier, palette_key, bones, scale, vb in ENTITIES:
        palette = PAL[palette_key]
        resolved_bones = []
        for b in bones:
            cubes = []
            for c in b["cubes"]:
                part = c.get("part", "side")
                pal = palette if part == "side" else {**palette, "side": palette.get(part, palette.get("side"))}
                cubes.append({"name": c["name"], "origin": c["origin"], "size": c["size"], "palette": pal})
            resolved_bones.append({"name": b["name"], "parent": b.get("parent"), "pivot": b["pivot"], "cubes": cubes})
        entity_geo(identifier, identifier, resolved_bones, palette, visible_bounds=vb)
        write_client_entity(identifier, identifier, f"geometry.hv_{identifier}", scale=scale)
        print("built entity", identifier)


if __name__ == "__main__":
    run()
