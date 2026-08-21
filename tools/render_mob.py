#!/usr/bin/env python3
"""Render a Bedrock entity model to a PNG, so designs can be looked at.

    python3 tools/render_mob.py void_dragon --angle 35 --size 640

Every model in this pack has, until now, been authored blind: numbers typed
into a .geo.json and judged in game an hour later. That is a terrible way to
design a creature. This is a small software rasteriser - no dependencies, same
rules as the rest of the toolchain - that takes the geometry and its texture
and draws the thing, so a silhouette can be fixed in seconds instead of after
a build, an import and a flight out to find one.

It implements the parts of the Bedrock model format that affect what a model
*looks* like: the bone tree, pivots, bone rotations, cube origins and sizes,
inflate, per-cube uv (both box and per-face), and mirroring. It is a preview,
not the engine - it does not do animation, attachables or render controllers.
"""

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from artlib import Canvas, canvas_from_png, save_png  # noqa: E402

ROOT = os.path.dirname(HERE)


# --------------------------------------------------------------------------
# Small vector helpers. Kept local and explicit; a matrix library would be
# more code than the six operations actually needed here.
# --------------------------------------------------------------------------

def rotate_xyz(point, degrees):
    """Rotate a point by Bedrock's XYZ bone rotation, in Bedrock's order."""
    x, y, z = point
    rx, ry, rz = (math.radians(d) for d in degrees)
    # X
    cy, sy = math.cos(rx), math.sin(rx)
    y, z = y * cy - z * sy, y * sy + z * cy
    # Y
    cy, sy = math.cos(ry), math.sin(ry)
    x, z = x * cy + z * sy, -x * sy + z * cy
    # Z
    cy, sy = math.cos(rz), math.sin(rz)
    x, y = x * cy - y * sy, x * sy + y * cy
    return (x, y, z)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def normalise(v):
    length = math.sqrt(sum(c * c for c in v)) or 1.0
    return (v[0] / length, v[1] / length, v[2] / length)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

# Face order and the corner winding Bedrock uses, plus each face's box-UV slot.
# Corners are given in unit cube space; they are scaled by the cube size.
FACES = {
    "north": ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, -1)),
    "south": ((1, 0, 1), (0, 0, 1), (0, 1, 1), (1, 1, 1), (0, 0, 1)),
    "west":  ((0, 0, 1), (0, 0, 0), (0, 1, 0), (0, 1, 1), (-1, 0, 0)),
    "east":  ((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0), (1, 0, 0)),
    "up":    ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1), (0, 1, 0)),
    "down":  ((0, 0, 1), (1, 0, 1), (1, 0, 0), (0, 0, 0), (0, -1, 0)),
}


def box_uv(uv, size, face):
    """The rectangle in texture space a face samples, for box-style uv.

    Bedrock's box unwrap: top and bottom sit on the first `depth` rows, then
    east / north / west / south run across the next `height` rows.
    """
    u, v = uv
    w, h, d = size
    rects = {
        "up":    (u + d,         v,     w, d),
        "down":  (u + d + w,     v,     w, d),
        "east":  (u,             v + d, d, h),
        "north": (u + d,         v + d, w, h),
        "west":  (u + d + w,     v + d, d, h),
        "south": (u + d + w + d, v + d, w, h),
    }
    return rects[face]


def collect_quads(geometry):
    """Flatten a geometry's bone tree into world-space textured quads."""
    bones = {b["name"]: b for b in geometry.get("bones", [])}

    def world_of(bone_name, point):
        """Apply this bone's rotation and every ancestor's, in order."""
        chain = []
        name = bone_name
        seen = set()
        while name and name in bones and name not in seen:
            seen.add(name)
            chain.append(bones[name])
            name = bones[name].get("parent")
        for bone in chain:
            rotation = bone.get("rotation")
            if not rotation:
                continue
            pivot = bone.get("pivot", [0, 0, 0])
            point = add(rotate_xyz(sub(point, pivot), rotation), pivot)
        return point

    quads = []
    for bone in geometry.get("bones", []):
        for cube in bone.get("cubes", []) or []:
            origin = cube["origin"]
            size = cube["size"]
            inflate = cube.get("inflate", 0.0)
            mirror = cube.get("mirror", False)
            uv = cube.get("uv", [0, 0])
            per_face = isinstance(uv, dict)

            lo = [origin[i] - inflate for i in range(3)]
            span = [size[i] + inflate * 2 for i in range(3)]

            # A cube can carry its own rotation about its own pivot.
            cube_rotation = cube.get("rotation")
            cube_pivot = cube.get("pivot", [lo[0] + span[0] / 2,
                                            lo[1] + span[1] / 2,
                                            lo[2] + span[2] / 2])

            for face, (c0, c1, c2, c3, normal) in FACES.items():
                if per_face:
                    entry = uv.get(face)
                    if entry is None:
                        continue
                    rect = (entry["uv"][0], entry["uv"][1],
                            entry["uv_size"][0], entry["uv_size"][1])
                else:
                    rect = box_uv(uv, size, face)

                corners = []
                for corner in (c0, c1, c2, c3):
                    point = [lo[i] + corner[i] * span[i] for i in range(3)]
                    if cube_rotation:
                        point = add(rotate_xyz(sub(point, cube_pivot), cube_rotation),
                                    cube_pivot)
                    corners.append(world_of(bone["name"], tuple(point)))

                # Texture corners follow the same winding as the geometry.
                u0, v0, uw, vh = rect
                if uw < 0:
                    u0, uw = u0 + uw, -uw
                if vh < 0:
                    v0, vh = v0 + vh, -vh
                texel = [(u0, v0 + vh), (u0 + uw, v0 + vh), (u0 + uw, v0), (u0, v0)]
                if face in ("up", "down"):
                    texel = [(u0, v0), (u0 + uw, v0), (u0 + uw, v0 + vh), (u0, v0 + vh)]
                if mirror:
                    texel = [texel[1], texel[0], texel[3], texel[2]]

                world_normal = normalise(world_of(bone["name"], normal)) \
                    if bone.get("rotation") else normalise(normal)
                quads.append((corners, texel, world_normal, bone["name"]))
    return quads


# --------------------------------------------------------------------------
# Rasteriser
# --------------------------------------------------------------------------

def render(quads, texture, emissive, size, yaw, pitch, margin=0.10,
           background=(18, 14, 28, 255)):
    """Z-buffered render of the quads, lit by one key light plus ambient."""
    canvas = Canvas(size, size)
    canvas.fill(background)
    depth = [[1e30] * size for _ in range(size)]

    yaw_r, pitch_r = math.radians(yaw), math.radians(pitch)

    def view(point):
        x, y, z = point
        # Yaw about Y, then pitch about X. Model space is Bedrock's: +Y up.
        cx, sx = math.cos(yaw_r), math.sin(yaw_r)
        x, z = x * cx + z * sx, -x * sx + z * cx
        cy, sy = math.cos(pitch_r), math.sin(pitch_r)
        y, z = y * cy - z * sy, y * sy + z * cy
        return (x, y, z)

    viewed = [[view(c) for c in corners] for corners, _, _, _ in quads]
    if not viewed:
        return canvas

    xs = [p[0] for q in viewed for p in q]
    ys = [p[1] for q in viewed for p in q]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    scale = size * (1.0 - margin * 2) / span
    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2

    def project(p):
        return (size / 2 + (p[0] - cx) * scale,
                size / 2 - (p[1] - cy) * scale,
                p[2])

    key = normalise((-0.45, 0.8, -0.42))

    for index, (corners, texel, normal, _bone) in enumerate(quads):
        screen = [project(p) for p in viewed[index]]
        lit = 0.42 + 0.58 * max(0.0, dot(normalise(view(normal)), key))

        # Two triangles per quad, barycentric fill with a depth test.
        for tri in ((0, 1, 2), (0, 2, 3)):
            pts = [screen[i] for i in tri]
            uvs = [texel[i] for i in tri]
            min_x = max(0, int(min(p[0] for p in pts)))
            max_x = min(size - 1, int(max(p[0] for p in pts)) + 1)
            min_y = max(0, int(min(p[1] for p in pts)))
            max_y = min(size - 1, int(max(p[1] for p in pts)) + 1)
            (x0, y0, _), (x1, y1, _), (x2, y2, _) = pts
            area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
            if abs(area) < 1e-9:
                continue

            for py in range(min_y, max_y + 1):
                for px in range(min_x, max_x + 1):
                    sx, sy = px + 0.5, py + 0.5
                    w0 = ((x1 - sx) * (y2 - sy) - (x2 - sx) * (y1 - sy)) / area
                    w1 = ((x2 - sx) * (y0 - sy) - (x0 - sx) * (y2 - sy)) / area
                    w2 = 1.0 - w0 - w1
                    if w0 < 0 or w1 < 0 or w2 < 0:
                        continue
                    z = w0 * pts[0][2] + w1 * pts[1][2] + w2 * pts[2][2]
                    if z >= depth[py][px]:
                        continue

                    u = w0 * uvs[0][0] + w1 * uvs[1][0] + w2 * uvs[2][0]
                    v = w0 * uvs[0][1] + w1 * uvs[1][1] + w2 * uvs[2][1]
                    tx = max(0, min(texture.w - 1, int(u)))
                    ty = max(0, min(texture.h - 1, int(v)))
                    colour = texture.get(tx, ty)
                    if colour[3] < 24:
                        continue

                    glow = 0.0
                    if emissive is not None:
                        ex = max(0, min(emissive.w - 1, int(u * emissive.w / texture.w)))
                        ey = max(0, min(emissive.h - 1, int(v * emissive.h / texture.h)))
                        glow = emissive.get(ex, ey)[1] / 255.0

                    shade = lit + (1.0 - lit) * glow
                    boost = 1.0 + glow * 0.9
                    pixel = tuple(
                        max(0, min(255, int(colour[i] * shade * boost))) for i in range(3)
                    ) + (255,)
                    depth[py][px] = z
                    canvas.set(px, py, pixel)
    return canvas


def load_geometry(path, identifier=None):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    entries = data.get("minecraft:geometry")
    if entries:
        for entry in entries:
            if identifier is None or entry["description"]["identifier"] == identifier:
                return entry
        return entries[0]
    # 1.8 format: geometry keyed by identifier at the top level.
    for key, value in data.items():
        if key.startswith("geometry.") and isinstance(value, dict):
            if identifier is None or key == identifier:
                return value
    raise SystemExit(f"no geometry found in {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="model name under RP/models/entity, without .geo.json")
    parser.add_argument("--texture", help="texture name under RP/textures/entity")
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--angle", type=float, default=34.0, help="yaw in degrees")
    parser.add_argument("--pitch", type=float, default=14.0)
    parser.add_argument("--out", help="output png")
    parser.add_argument("--turnaround", type=int, default=0,
                        help="render N views around the model into one sheet")
    args = parser.parse_args()

    geo_path = os.path.join(ROOT, "RP", "models", "entity", args.name + ".geo.json")
    geometry = load_geometry(geo_path)
    quads = collect_quads(geometry)

    tex_name = args.texture or ("voidbound_" + args.name)
    tex_path = os.path.join(ROOT, "RP", "textures", "entity", tex_name + ".png")
    texture = canvas_from_png(tex_path)
    mer_path = os.path.join(ROOT, "RP", "textures", "entity", tex_name + "_mer.png")
    emissive = canvas_from_png(mer_path) if os.path.exists(mer_path) else None

    out = args.out or os.path.join(ROOT, "dist", "model_%s.png" % args.name)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if args.turnaround:
        views = args.turnaround
        sheet = Canvas(args.size * views, args.size)
        sheet.fill((18, 14, 28, 255))
        for i in range(views):
            frame = render(quads, texture, emissive, args.size,
                           args.angle + i * (360.0 / views), args.pitch)
            for y in range(args.size):
                for x in range(args.size):
                    sheet.set(i * args.size + x, y, frame.get(x, y))
        sheet.save(out)
    else:
        render(quads, texture, emissive, args.size, args.angle, args.pitch).save(out)

    print("%s  (%d quads) -> %s" % (args.name, len(quads), os.path.relpath(out, ROOT)))


if __name__ == "__main__":
    main()
