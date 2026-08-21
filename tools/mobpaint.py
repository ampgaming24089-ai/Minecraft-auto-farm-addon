#!/usr/bin/env python3
"""Paint an entity texture from its own geometry.

Hand-laying UVs for a sixty-cube model is where the time goes and where the
bugs live. Since mobkit already knows exactly which rectangle every cube was
given, the texture can be painted *from the model* instead: walk the cubes,
work out each face's footprint, and hand it to a painter that decides colour
from the bone's name and the face's direction.

That means the art and the model can never drift out of alignment, and adding
a limb costs one line rather than a UV rethink.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from artlib import Canvas, mix, shade  # noqa: E402


def box_rects(uv, size):
    """The six face rectangles of a box unwrap: (face, x, y, w, h)."""
    u, v = uv
    w, h, d = (int(math.ceil(s)) for s in size)
    return [
        ("up", u + d, v, w, d),
        ("down", u + d + w, v, w, d),
        ("east", u, v + d, d, h),
        ("north", u + d, v + d, w, h),
        ("west", u + d + w, v + d, d, h),
        ("south", u + d + w + d, v + d, w, h),
    ]


def paint(canvas, geometry, painter):
    """Fill every cube's footprint using `painter(bone, face, fx, fy, fw, fh)`."""
    for bone in geometry["bones"]:
        for cube in bone.get("cubes", []) or []:
            uv = cube.get("uv", [0, 0])
            if isinstance(uv, dict):
                continue                     # per-face uv: not produced by mobkit
            for face, ox, oy, fw, fh in box_rects(uv, cube["size"]):
                for fy in range(fh):
                    for fx in range(fw):
                        colour = painter(bone["name"], face, fx, fy, fw, fh)
                        if colour is not None:
                            canvas.set(ox + fx, oy + fy, colour)


def ridged(base, high, fx, fy, fw, fh, period=3, strength=0.22):
    """A banded shade across a face - the cheapest way to stop a flat panel
    reading as a flat panel."""
    t = (fy % period) / float(max(1, period - 1))
    return mix(base, high, t * strength)


def edge_light(colour, fx, fy, fw, fh, amount=0.22):
    """Lighten the top and one side of a face so cubes have visible corners."""
    if fy == 0:
        return shade(colour, amount)
    if fx == 0:
        return shade(colour, amount * 0.6)
    if fy == fh - 1 or fx == fw - 1:
        return shade(colour, -amount * 0.7)
    return colour
