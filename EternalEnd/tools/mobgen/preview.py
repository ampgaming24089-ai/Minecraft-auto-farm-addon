"""
Render the roster to a picture, so the models can be looked at.

Bedrock will happily load a model whose legs come out of its head, and a
texture atlas tells you nothing about what the mob looks like assembled. This
is a small software renderer - bone transforms, a z-buffer, and nearest-
neighbour texture sampling off the same face rectangles the painter used - so
every change to `roster.py` can be checked against the design sheets instead of
against a wall of JSON.

    python3 preview.py            # one contact sheet of all twenty
    python3 preview.py void_dragon ender_deer

It is a development tool. Nothing it writes ships in the pack.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402

from paint import paint_model  # noqa: E402
from roster import ROSTER, BY_ID  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "preview")

# Camera. A three-quarter view from slightly above, which is how the design
# sheets are drawn and the angle a player usually meets a mob at.
YAW = math.radians(-34)
PITCH = math.radians(18)

BACKGROUND = (13, 10, 20)

# Face normals, in model space, matching the box-UV face names.
NORMALS = {
    "up": (0, 1, 0),
    "down": (0, -1, 0),
    "north": (0, 0, -1),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
    "east": (1, 0, 0),
}

LIGHT = (-0.42, 0.78, -0.46)


def rotate_point(point, axis_angles):
    """Apply x, y, z rotations in Bedrock's order (z, y, x are applied x,y,z)."""
    x, y, z = point
    rx, ry, rz = (math.radians(a) for a in axis_angles)
    # X
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    # Y
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    # Z
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return x, y, z


def bone_transform(bone, bones_by_name):
    """
    The chain of (pivot, rotation) pairs from this bone up to the root.

    Returned outermost-last so a point can be pushed through them in order.
    """
    chain = []
    current = bone
    while current is not None:
        if current.rotation:
            chain.append((current.pivot, current.rotation))
        current = bones_by_name.get(current.parent)
    return chain


def apply_chain(point, chain):
    for pivot, rotation in chain:
        moved = (point[0] - pivot[0], point[1] - pivot[1], point[2] - pivot[2])
        moved = rotate_point(moved, rotation)
        point = (moved[0] + pivot[0], moved[1] + pivot[1], moved[2] + pivot[2])
    return point


def view(point):
    """Model space to camera space: yaw, then pitch."""
    x, y, z = point
    cx = x * math.cos(YAW) + z * math.sin(YAW)
    cz = -x * math.sin(YAW) + z * math.cos(YAW)
    cy = y * math.cos(PITCH) - cz * math.sin(PITCH)
    depth = y * math.sin(PITCH) + cz * math.cos(PITCH)
    return cx, cy, depth


CORNERS = {
    # (face) -> the four model-space corners, as (dx, dy, dz) in 0/1 of size,
    # ordered so (u, v) runs the same way the box-UV rectangle does.
    "up": ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)),
    "down": ((0, 0, 1), (1, 0, 1), (1, 0, 0), (0, 0, 0)),
    "north": ((1, 1, 0), (0, 1, 0), (0, 0, 0), (1, 0, 0)),
    "south": ((0, 1, 1), (1, 1, 1), (1, 0, 1), (0, 0, 1)),
    "west": ((0, 1, 0), (0, 1, 1), (0, 0, 1), (0, 0, 0)),
    "east": ((1, 1, 1), (1, 1, 0), (1, 0, 0), (1, 0, 1)),
}


def render(mob, size=320):
    model = mob.model()
    model.pack()
    texture, _ = paint_model(model, mob.id)
    tex = texture.load()
    tex_size = texture.size[0]

    bones_by_name = {bone.name: bone for bone in model.bones}

    quads = []
    for bone in model.bones:
        chain = bone_transform(bone, bones_by_name)
        for cube in bone.cubes:
            ox, oy, oz = cube.origin
            sx, sy, sz = cube.size
            inflate = cube.inflate or 0.0
            for face, corners in CORNERS.items():
                points = []
                for dx, dy, dz in corners:
                    point = (
                        ox - inflate + dx * (sx + 2 * inflate),
                        oy - inflate + dy * (sy + 2 * inflate),
                        oz - inflate + dz * (sz + 2 * inflate),
                    )
                    if cube.rotation:
                        point = apply_chain(point, [(cube.pivot, cube.rotation)])
                    points.append(view(apply_chain(point, chain)))
                normal = NORMALS[face]
                if cube.rotation:
                    normal = rotate_point(normal, cube.rotation)
                for pivot, rotation in chain:
                    normal = rotate_point(normal, rotation)
                quads.append((points, cube.face_rect(face), normal))

    # Fit the model to the frame.
    xs = [p[0] for quad in quads for p in quad[0]]
    ys = [p[1] for quad in quads for p in quad[0]]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0) * 1.12
    scale = size / span
    ox = size / 2 - (min(xs) + max(xs)) / 2 * scale
    oy = size / 2 + (min(ys) + max(ys)) / 2 * scale

    image = Image.new("RGB", (size, size), BACKGROUND)
    px = image.load()
    depth_buffer = [[1e9] * size for _ in range(size)]

    for points, rect, normal in quads:
        shade = 0.42 + 0.58 * max(0.0, sum(n * l for n, l in zip(normal, LIGHT)))
        _raster(px, depth_buffer, size, points, rect, tex, tex_size, scale, ox, oy,
                shade)

    return image


def _raster(px, depth_buffer, size, points, rect, tex, tex_size, scale, ox, oy,
            shade):
    """Draw one textured quad as two triangles, with a per-pixel depth test."""
    screen = [(ox + p[0] * scale, oy - p[1] * scale, p[2]) for p in points]
    uv = [(rect[0], rect[1]), (rect[0] + rect[2], rect[1]),
          (rect[0] + rect[2], rect[1] + rect[3]), (rect[0], rect[1] + rect[3])]

    for tri in ((0, 1, 2), (0, 2, 3)):
        a, b, c = (screen[i] for i in tri)
        ua, ub, uc = (uv[i] for i in tri)
        min_x = max(0, int(min(a[0], b[0], c[0])))
        max_x = min(size - 1, int(max(a[0], b[0], c[0])) + 1)
        min_y = max(0, int(min(a[1], b[1], c[1])))
        max_y = min(size - 1, int(max(a[1], b[1], c[1])) + 1)
        area = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(area) < 1e-6:
            continue
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                cx, cy = x + 0.5, y + 0.5
                w0 = ((b[0] - a[0]) * (cy - a[1]) - (cx - a[0]) * (b[1] - a[1])) / area
                w1 = ((cx - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (cy - a[1])) / area
                w2 = 1.0 - w0 - w1
                if w0 < -0.001 or w1 < -0.001 or w2 < -0.001:
                    continue
                depth = a[2] * w2 + b[2] * w1 + c[2] * w0
                if depth >= depth_buffer[y][x]:
                    continue
                u = ua[0] * w2 + ub[0] * w1 + uc[0] * w0
                v = ua[1] * w2 + ub[1] * w1 + uc[1] * w0
                tx = min(tex_size - 1, max(0, int(u)))
                ty = min(tex_size - 1, max(0, int(v)))
                r, g, b_, alpha = tex[tx, ty]
                # Emissive texels ignore the lighting term, which is exactly
                # what they do in game.
                lit = 1.0 if alpha != 255 else shade
                depth_buffer[y][x] = depth
                px[x, y] = (min(255, int(r * lit)), min(255, int(g * lit)),
                            min(255, int(b_ * lit)))


def main():
    os.makedirs(OUT, exist_ok=True)
    wanted = sys.argv[1:]
    mobs = [BY_ID[name] for name in wanted] if wanted else ROSTER

    images = []
    for mob in mobs:
        print(f"  rendering {mob.id}")
        image = render(mob)
        image.save(os.path.join(OUT, f"{mob.id}.png"))
        images.append((mob, image))

    cell = 320
    cols = 5
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), BACKGROUND)
    for index, (_, image) in enumerate(images):
        sheet.paste(image, ((index % cols) * cell, (index // cols) * cell))
    sheet.save(os.path.join(OUT, "roster.png"))
    print(f"  wrote {OUT}/roster.png")


if __name__ == "__main__":
    main()
