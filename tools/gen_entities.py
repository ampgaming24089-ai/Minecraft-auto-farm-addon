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
import faces
from gen_assets import PAL, RP, EYE_GLOW, ENTITY_PATTERN, save, stable_seed

CUBE = tuple  # (origin(x,y,z), size(dx,dy,dz))


def _front_face_of(bone):
    """The atlas rectangle covering a bone's primary cube's front face."""
    if not bone or not bone.get("cubes"):
        return None, None
    cube = bone["cubes"][0]
    if "_uv" not in cube:
        return None, None
    u, v = cube["_uv"]
    dx, dy, dz = cube["size"]
    return boxuv.face_rects(u, v, dx, dy, dz)["front"], cube


def paint_features(draw, bones, identifier, palette, glow_color):
    """Paints a real face on the head and a marking on the chest.

    This replaced two flat dots. A pair of squares on a box is a domino, not
    a face - it was the biggest single reason these mobs read as "soulless
    blobs". Each creature now gets sockets with depth, a brow that sets an
    expression, a jaw/snout/visor appropriate to what it is, and something on
    the torso so the largest surface on the model is not a blank slab. See
    tools/faces.py for the styles and which creature wears which.
    """
    head, head_cube = _front_face_of(next((b for b in bones if b["name"] == "head"), None))
    if head:
        base = (head_cube.get("palette") or palette).get("front") or palette.get("side")
        faces.paint_face(draw, head, base, glow_color, faces.FACE_OF.get(identifier, "hollow"))

    torso_bone = next((b for b in bones if b["name"] in ("torso", "body")), None)
    chest, chest_cube = _front_face_of(torso_bone)
    if chest:
        base = (chest_cube.get("palette") or palette).get("front") or palette.get("side")
        faces.paint_chest(draw, chest, base, glow_color, faces.CHEST_OF.get(identifier, "none"))


def entity_geo(identifier, tex_name, bones, palette, atlas_width=64, visible_bounds=(2, 2.5, 1)):
    """bones: list of {name, parent, pivot, cubes:[{name, origin, size, part}]}
    part selects a palette sub-key ('top'/'side'/'front') for shading."""
    atlas = boxuv.Atlas(max_width=atlas_width)
    for bone in bones:
        for cube in bone["cubes"]:
            c = boxuv.Cube(cube["name"], cube["origin"], cube["size"])
            c.pattern = ENTITY_PATTERN.get(identifier)
            atlas.place(c)
            cube["_uv"] = c.uv

    w, h = atlas.finalize_size()
    img = boxuv.new_canvas(w, h)
    draw = ImageDraw.Draw(img)
    seed = stable_seed(identifier) % 10000
    for bone in bones:
        for i, cube in enumerate(bone["cubes"]):
            c = boxuv.Cube(cube["name"], cube["origin"], cube["size"])
            c.pattern = ENTITY_PATTERN.get(identifier)
            c.uv = cube["_uv"]
            pal = cube.get("palette", palette)
            boxuv.paint_cube(draw, c, pal, seed=seed + i)

    # Every creature gets features, not just the ones with a glow colour -
    # a skull's sockets and a sentinel's visor read fine without one.
    glow = EYE_GLOW.get(identifier) or (235, 235, 245, 255)
    paint_features(draw, bones, identifier, palette, glow)

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


def egg_colors(palette_key):
    """Spawn-egg base/overlay derived from the creature's own palette.
    Without a spawn_egg block Bedrock renders the egg solid black, which is
    why every one of these eggs was an unreadable black blob in the
    creative inventory."""
    pal = PAL.get(palette_key) or {}
    def hexof(c):
        return "#%02x%02x%02x" % (c[0], c[1], c[2])
    base = pal.get("side") or (140, 140, 150, 255)
    over = pal.get("top") or pal.get("front") or base
    # push the overlay away from the base so the speckles actually read
    over = tuple(min(255, int(v * 1.35)) for v in over[:3])
    return hexof(base), hexof(over)


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



def _bbox(c):
    ox, oy, oz = c["origin"]
    dx, dy, dz = c["size"]
    return ox, oy, oz, dx, dy, dz


def add_detail(identifier, bones):
    """Appends small detail cubes so creatures have a readable silhouette
    instead of a stack of plain boxes. Everything is positioned relative to
    the bone's existing primary cube, so it works for any rig: a brow ridge
    and jaw on the head, hands at the ends of arms, feet under legs,
    shoulder pads on the torso, a tip on the tail.

    This is what turns a six-box mob into something that reads as a
    creature at a glance - the "soulless blob" problem was as much missing
    silhouette as it was flat texture."""
    by_name = {b["name"]: b for b in bones}

    def primary(name):
        b = by_name.get(name)
        if not b or not b["cubes"]:
            return None, None
        return b, b["cubes"][0]

    # --- head: brow ridge + jaw ------------------------------------------
    b, c = primary("head")
    if b and c:
        ox, oy, oz, dx, dy, dz = _bbox(c)
        if dx >= 4 and dy >= 4:
            b["cubes"].append(cube("brow", [ox, oy + dy - 2, oz - 1], [dx, 2, 1]))
            b["cubes"].append(cube("jaw", [ox + 1, oy, oz - 1], [max(1, dx - 2), 2, 1]))

    # --- arms: hands ------------------------------------------------------
    for name in ("left_arm", "right_arm", "arm_l", "arm_r"):
        b, c = primary(name)
        if not (b and c):
            continue
        ox, oy, oz, dx, dy, dz = _bbox(c)
        b["cubes"].append(cube("hand", [ox - 1, oy - 2, oz - 1], [dx + 2, 2, dz + 2]))

    # --- legs: feet -------------------------------------------------------
    for name in ("leg_l", "leg_r", "leg_fl", "leg_fr", "leg_bl", "leg_br"):
        b, c = primary(name)
        if not (b and c):
            continue
        ox, oy, oz, dx, dy, dz = _bbox(c)
        b["cubes"].append(cube("foot", [ox, oy, oz - 2], [dx, 2, dz + 2]))

    # --- torso: shoulder ridge -------------------------------------------
    for name in ("torso", "body"):
        b, c = primary(name)
        if not (b and c):
            continue
        ox, oy, oz, dx, dy, dz = _bbox(c)
        if dx >= 6 and dy >= 6:
            b["cubes"].append(cube("collar", [ox - 1, oy + dy - 3, oz], [dx + 2, 3, dz]))
        break

    # --- tails / trailing pieces: a narrower tip --------------------------
    for name in ("tail", "tail2"):
        b, c = primary(name)
        if not (b and c):
            continue
        ox, oy, oz, dx, dy, dz = _bbox(c)
        b["cubes"].append(cube("tail_tip", [ox + 1, oy - 2, oz + dz], [max(1, dx - 2), max(2, dy - 2), 2]))

    return bones


# ---------------------------------------------------------------------------
# Cube helper shorthands
# ---------------------------------------------------------------------------
def cube(name, origin, size, part="side"):
    # Box UV allocates and paints atlas cells in whole pixels (it has to -
    # they're pixels), but Minecraft maps a cube's UVs from its ACTUAL size.
    # A fractional size like 1.5 therefore samples a different region than
    # the one that got painted, and the texture visibly smears/misaligns on
    # that cube. Snapping sizes to integers here - the single place every
    # cube is built - keeps geometry and atlas exactly in agreement and is
    # why vanilla box-UV models use whole-pixel cubes too.
    size = [max(1, int(round(v))) for v in size]
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
        bone("head", [0, 12, -9], [cube("head", [-3.5, 9, -12.5], [7, 6, 7]), cube("snout", [-2, 9, -15], [4, 3, 3])], parent="body"),
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
        bone("head", [0, 16, 0], [cube("head", [-3, 16, -3], [6, 6, 6])], parent="body"),
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

# --- New passive mobs ---
add(
    "ashwing_bat",
    "ashwing_bat",
    [
        bone("body", [0, 8, 0], [cube("body", [-2, 7, -2.5], [4, 3, 5])]),
        bone("head", [0, 10, -3], [cube("head", [-2.5, 8.5, -5.5], [5, 4, 4])], parent="body"),
        bone("ear_l", [1, 12, -3.5], [cube("ear_l", [0.5, 11.5, -4], [1, 1.5, 1])], parent="head"),
        bone("ear_r", [-1, 12, -3.5], [cube("ear_r", [-1.5, 11.5, -4], [1, 1.5, 1])], parent="head"),
        bone("wing_l", [2, 9, 0], [cube("wing_l", [2, 6, -2], [4, 4, 4])], parent="body"),
        bone("wing_r", [-2, 9, 0], [cube("wing_r", [-6, 6, -2], [4, 4, 4])], parent="body"),
    ],
    scale=0.5,
    visible_bounds=(1.2, 1.0, 0.6),
)

add(
    "bonehide_elk",
    "bonehide_elk",
    [
        bone("body", [0, 13, 0], [cube("body", [-5, 10, -9], [10, 8, 18])]),
        bone("head", [0, 16, -11], [cube("head", [-3, 14, -14], [6, 6, 6]), cube("snout", [-2, 14.5, -16.5], [4, 3, 2.5])], parent="body"),
        bone("antler_l", [2, 21, -12], [cube("antler_l", [1, 20, -13], [1, 6, 1])], parent="head"),
        bone("antler_r", [-2, 21, -12], [cube("antler_r", [-2, 20, -13], [1, 6, 1])], parent="head"),
        bone("tail", [0, 15, 9], [cube("tail", [-1, 12, 9], [2, 4, 2])], parent="body"),
        bone("leg_fl", [3.5, 10, -6], [cube("leg_fl", [1.5, 0, -7.5], [3, 10, 3])], parent="body"),
        bone("leg_fr", [-3.5, 10, -6], [cube("leg_fr", [-4.5, 0, -7.5], [3, 10, 3])], parent="body"),
        bone("leg_bl", [3.5, 10, 6], [cube("leg_bl", [1.5, 0, 4.5], [3, 10, 3])], parent="body"),
        bone("leg_br", [-3.5, 10, 6], [cube("leg_br", [-4.5, 0, 4.5], [3, 10, 3])], parent="body"),
    ],
    visible_bounds=(2.2, 2.2, 1.4),
)

add(
    "glimmershroom_toad",
    "glimmershroom_toad",
    [
        bone("body", [0, 4, 0], [cube("body", [-4, 2, -5], [8, 5, 10])]),
        bone("head", [0, 6, -5], [cube("head", [-3.5, 2.5, -8.5], [7, 5, 4])], parent="body"),
        bone("eye_l", [1.5, 8, -7.5], [cube("eye_l", [1, 6.5, -8.2], [1.5, 1.5, 1])], parent="head"),
        bone("eye_r", [-1.5, 8, -7.5], [cube("eye_r", [-2.5, 6.5, -8.2], [1.5, 1.5, 1])], parent="head"),
        bone("leg_fl", [3, 2, -3], [cube("leg_fl", [2, 0, -4], [2, 2, 2])], parent="body"),
        bone("leg_fr", [-3, 2, -3], [cube("leg_fr", [-4, 0, -4], [2, 2, 2])], parent="body"),
        bone("leg_bl", [3, 2, 3], [cube("leg_bl", [2, 0, 2], [2, 2, 2])], parent="body"),
        bone("leg_br", [-3, 2, 3], [cube("leg_br", [-4, 0, 2], [2, 2, 2])], parent="body"),
    ],
    scale=0.6,
    visible_bounds=(1.2, 0.8, 0.8),
)

# --- New hostile mobs ---
add(
    "bastion_sentinel",
    "bastion_sentinel",
    [
        bone("body", [0, 10, 0], [cube("body", [-5.5, 9, -3.5], [11, 13, 7])]),
        bone("pauldron_l", [6, 21, 0], [cube("pl", [4.5, 19.5, -4], [3, 3, 5], "front")], parent="body"),
        bone("pauldron_r", [-6, 21, 0], [cube("pr", [-7.5, 19.5, -4], [3, 3, 5], "front")], parent="body"),
        bone("head", [0, 23, 0], [cube("head", [-4, 22, -4], [8, 8, 8])], parent="body"),
        bone("arm_l", [7, 19, 0], [cube("arm_l", [5.5, 8, -2.5], [4, 13, 5])], parent="body"),
        bone("arm_r", [-7, 19, 0], [cube("arm_r", [-9.5, 8, -2.5], [4, 13, 5])], parent="body"),
        bone("leg_l", [2.5, 9, 0], [cube("leg_l", [0.5, -5, -2.5], [4, 14, 5])], parent="body"),
        bone("leg_r", [-2.5, 9, 0], [cube("leg_r", [-4.5, -5, -2.5], [4, 14, 5])], parent="body"),
    ],
    visible_bounds=(2.4, 3.0, 1.1),
)

add(
    "city_wraithguard",
    "city_wraithguard",
    [
        bone("body", [0, 12, 0], [cube("robe", [-5, 5, -3], [10, 12, 6])]),
        bone("torso", [0, 17, 0], [cube("torso", [-4, 17, -3], [8, 8, 6])], parent="body"),
        bone("head", [0, 25, 0], [cube("head", [-4, 25, -4], [8, 8, 8])], parent="torso"),
        bone("helm_spike", [0, 33, 0], [cube("spike", [-0.5, 33, -0.5], [1, 4, 1], "top")], parent="head"),
        bone("arm_l", [6, 21, 0], [cube("arm_l", [4.5, 12, -1.5], [3, 11, 3])], parent="torso"),
        bone("arm_r", [-6, 21, 0], [cube("arm_r", [-7.5, 12, -1.5], [3, 11, 3])], parent="torso"),
        bone("tail", [0, 5, 4], [cube("robe_tail", [-4, 0, 4], [8, 6, 2])], parent="body"),
    ],
    visible_bounds=(2.0, 2.8, 1.0),
)

add(
    "marrow_crawler",
    "marrow_crawler",
    [
        bone("body", [0, 5, 0], [cube("body", [-5, 3, -7], [10, 5, 14])]),
        bone("head", [0, 6, -8], [cube("head", [-3, 3.5, -11.5], [6, 5, 5])], parent="body"),
        bone("fang_l", [1, 5, -11], [cube("fang_l", [0.5, 4, -12], [1, 2, 1])], parent="head"),
        bone("fang_r", [-1, 5, -11], [cube("fang_r", [-1.5, 4, -12], [1, 2, 1])], parent="head"),
        bone("leg1_l", [5, 4, -5], [cube("leg1_l", [4, 2, -6.5], [4, 2, 2])], parent="body"),
        bone("leg1_r", [-5, 4, -5], [cube("leg1_r", [-8, 2, -6.5], [4, 2, 2])], parent="body"),
        bone("leg2_l", [5, 4, -1], [cube("leg2_l", [4, 2, -2], [4, 2, 2])], parent="body"),
        bone("leg2_r", [-5, 4, -1], [cube("leg2_r", [-8, 2, -2], [4, 2, 2])], parent="body"),
        bone("leg3_l", [5, 4, 3], [cube("leg3_l", [4, 2, 2], [4, 2, 2])], parent="body"),
        bone("leg3_r", [-5, 4, 3], [cube("leg3_r", [-8, 2, 2], [4, 2, 2])], parent="body"),
    ],
    scale=0.85,
    visible_bounds=(2.0, 1.2, 1.6),
)

add(
    "ashen_whelp",
    "ashen_whelp",
    [
        bone("body", [0, 6, 0], [cube("body", [-2, 4, -1.5], [4, 5, 3])]),
        bone("head", [0, 11, 0], [cube("head", [-3, 11, -3], [6, 6, 6])], parent="body"),
        bone("horn_l", [1, 15, 0], [cube("horn_l", [0.5, 15, -0.5], [1, 2, 1], "top")], parent="head"),
        bone("horn_r", [-1, 15, 0], [cube("horn_r", [-1.5, 15, -0.5], [1, 2, 1], "top")], parent="head"),
        bone("arm_l", [2.5, 9, 0], [cube("arm_l", [2, 5, -1], [1.5, 4, 2])], parent="body"),
        bone("arm_r", [-2.5, 9, 0], [cube("arm_r", [-3.5, 5, -1], [1.5, 4, 2])], parent="body"),
        bone("leg_l", [1, 4, 0], [cube("leg_l", [0.2, 0, -1], [1.6, 4, 2])], parent="body"),
        bone("leg_r", [-1, 4, 0], [cube("leg_r", [-1.8, 0, -1], [1.6, 4, 2])], parent="body"),
        bone("tail", [0, 5, 1.5], [cube("tail", [-0.5, 4, 1.5], [1, 1, 4])], parent="body"),
    ],
    scale=0.55,
    visible_bounds=(1.2, 1.4, 0.7),
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


DRAGON_BONES = [
    bone("body", [0, 14, 0], [cube("body", [-6, 11, -10], [12, 10, 20])]),
    bone("neck", [0, 20, -10], [cube("neck", [-3.5, 17, -15], [7, 7, 6])], parent="body"),
    bone("head", [0, 21, -16], [cube("head", [-4, 17, -21], [8, 7, 8]), cube("snout", [-2.5, 18, -25], [5, 4, 4])], parent="neck"),
    bone("horn_l", [1.5, 25, -18], [cube("horn_l", [1, 24, -19], [1, 4, 1], "top")], parent="head"),
    bone("horn_r", [-1.5, 25, -18], [cube("horn_r", [-2, 24, -19], [1, 4, 1], "top")], parent="head"),
    bone("tail1", [0, 14, 10], [cube("tail1", [-3, 11, 10], [6, 6, 10])], parent="body"),
    bone("tail2", [0, 13, 20], [cube("tail2", [-2, 11, 20], [4, 4, 9])], parent="tail1"),
    bone("wing_l", [6, 20, -2], [cube("wing_l", [6, 12, -8], [2, 14, 20], "front")], parent="body"),
    bone("wing_r", [-6, 20, -2], [cube("wing_r", [-8, 12, -8], [2, 14, 20], "front")], parent="body"),
    bone("leg_fl", [4, 11, -6], [cube("leg_fl", [1.5, 0, -8], [5, 11, 5])], parent="body"),
    bone("leg_fr", [-4, 11, -6], [cube("leg_fr", [-6.5, 0, -8], [5, 11, 5])], parent="body"),
    bone("leg_bl", [4, 11, 6], [cube("leg_bl", [1.5, 0, 4], [5, 11, 5])], parent="body"),
    bone("leg_br", [-4, 11, 6], [cube("leg_br", [-6.5, 0, 4], [5, 11, 5])], parent="body"),
]

DRAGON_COLOR_KEYS = ["dragon_0", "dragon_1", "dragon_2", "dragon_3", "dragon_4", "dragon_5"]


def build_dragon():
    """One geometry shared by 6 differently-painted textures, switched at
    runtime via minecraft:variant + a render-controller texture array - the
    same mechanism vanilla horses use for coat colors (verified against
    Mojang's horse.json/horse render controller)."""
    atlas = boxuv.Atlas(max_width=96)
    for b in DRAGON_BONES:
        for cube_def in b["cubes"]:
            c = boxuv.Cube(cube_def["name"], cube_def["origin"], cube_def["size"])
            c.pattern = ENTITY_PATTERN.get("veil_dragon")
            atlas.place(c)
            cube_def["_uv"] = c.uv
    w, h = atlas.finalize_size()

    for i, pal_key in enumerate(DRAGON_COLOR_KEYS):
        palette = PAL[pal_key]
        img = boxuv.new_canvas(w, h)
        draw = ImageDraw.Draw(img)
        for bi, b in enumerate(DRAGON_BONES):
            for ci, cube_def in enumerate(b["cubes"]):
                part = cube_def.get("part", "side")
                pal = palette if part == "side" else {**palette, "side": palette.get(part, palette.get("side"))}
                c = boxuv.Cube(cube_def["name"], cube_def["origin"], cube_def["size"])
                c.pattern = ENTITY_PATTERN.get("veil_dragon")
                c.uv = cube_def["_uv"]
                boxuv.paint_cube(draw, c, pal, seed=i * 100 + bi * 10 + ci)
        glow = EYE_GLOW.get("veil_dragon") or (255, 230, 150, 255)
        paint_features(draw, DRAGON_BONES, "veil_dragon", palette, glow)
        save(img, RP, "textures", "entity", f"veil_dragon_{i}.png")

    geo_bones = []
    for b in DRAGON_BONES:
        gb = {"name": b["name"], "pivot": list(b["pivot"])}
        if b.get("parent"):
            gb["parent"] = b["parent"]
        gb["cubes"] = [{"origin": list(c["origin"]), "size": list(c["size"]), "uv": list(c["_uv"])} for c in b["cubes"]]
        geo_bones.append(gb)

    geo = {
        "format_version": "1.16.0",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": "geometry.hv_veil_dragon",
                    "texture_width": w,
                    "texture_height": h,
                    "visible_bounds_width": 6,
                    "visible_bounds_height": 5,
                    "visible_bounds_offset": [0, 2, 0],
                },
                "bones": geo_bones,
            }
        ],
    }
    geo_path = os.path.join(RP, "models", "entity", "veil_dragon.geo.json")
    os.makedirs(os.path.dirname(geo_path), exist_ok=True)
    with open(geo_path, "w") as f:
        json.dump(geo, f, indent=2)

    render_controller = {
        "format_version": "1.10.0",
        "render_controllers": {
            "controller.render.hv_dragon": {
                "arrays": {"textures": {"Array.color": [f"Texture.variant{i}" for i in range(6)]}},
                "geometry": "Geometry.default",
                "materials": [{"*": "Material.default"}],
                "textures": ["Array.color[query.variant]"],
            }
        },
    }
    rc_path = os.path.join(RP, "render_controllers", "hv_dragon.render_controllers.json")
    with open(rc_path, "w") as f:
        json.dump(render_controller, f, indent=2)

    client_entity = {
        "format_version": "1.16.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": "hollowveil:veil_dragon",
                "materials": {"default": "entity_alphatest"},
                "textures": {f"variant{i}": f"textures/entity/veil_dragon_{i}" for i in range(6)},
                "geometry": {"default": "geometry.hv_veil_dragon"},
                "render_controllers": ["controller.render.hv_dragon"],
                "scripts": {"scale": "1.0"},
            }
        },
    }
    b, o = egg_colors("dragon_1")
    client_entity["minecraft:client_entity"]["description"]["spawn_egg"] = {
        "base_color": b, "overlay_color": o,
    }
    ce_path = os.path.join(RP, "entity", "veil_dragon.entity.json")
    with open(ce_path, "w") as f:
        json.dump(client_entity, f, indent=2)

    print("built entity veil_dragon (6 color variants)")


def run():
    write_shared_render_controller()
    build_dragon()
    for identifier, palette_key, bones, scale, vb in ENTITIES:
        palette = PAL[palette_key]
        # projectiles stay as bare shapes; everything else gets silhouette detail
        if identifier not in ("debris_projectile", "imp_fireball"):
            bones = add_detail(identifier, bones)
        resolved_bones = []
        for b in bones:
            cubes = []
            for c in b["cubes"]:
                part = c.get("part", "side")
                pal = palette if part == "side" else {**palette, "side": palette.get(part, palette.get("side"))}
                cubes.append({"name": c["name"], "origin": c["origin"], "size": c["size"], "palette": pal})
            resolved_bones.append({"name": b["name"], "parent": b.get("parent"), "pivot": b["pivot"], "cubes": cubes})
        entity_geo(identifier, identifier, resolved_bones, palette, visible_bounds=vb)
        # projectiles are not spawnable, so they get no egg
        eggs = None if identifier in ("debris_projectile", "imp_fireball") else egg_colors(palette_key)
        write_client_entity(identifier, identifier, f"geometry.hv_{identifier}",
                            spawn_egg_colors=eggs, scale=scale)
        print("built entity", identifier)


if __name__ == "__main__":
    run()
