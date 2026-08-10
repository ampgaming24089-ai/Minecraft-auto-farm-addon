"""
Minimal Minecraft "Box UV" allocator + texture atlas painter.

Given a list of named cuboids (size in model units), this assigns each cuboid
a non-overlapping region in a texture atlas using the standard Minecraft box-UV
face layout, so a hand-authored geometry.json and its texture PNG always agree
with each other. This is the same face-layout algorithm Minecraft/Blockbench
use for "Box UV" mode:

    texture strip per cube, given uv=(u,v) and size=(dx,dy,dz):
        top    -> x=u+dz,           y=v,       w=dx, h=dz
        bottom -> x=u+dz+dx,        y=v,       w=dx, h=dz
        right  -> x=u,              y=v+dz,    w=dz, h=dy
        front  -> x=u+dz,           y=v+dz,    w=dx, h=dy
        left   -> x=u+dz+dx,        y=v+dz,    w=dz, h=dy
        back   -> x=u+dz+dx+dz,     y=v+dz,    w=dx, h=dy

    total cell footprint: width = 2*dz + 2*dx, height = dz + dy
"""
from PIL import Image, ImageDraw
import math, random


class Cube:
    def __init__(self, name, origin, size, pivot=None, rotation=None, inflate=0.0, mirror=False):
        self.name = name
        self.origin = origin
        self.size = size
        self.pivot = pivot
        self.rotation = rotation
        self.inflate = inflate
        self.mirror = mirror
        self.uv = None  # assigned by atlas packer


class Atlas:
    def __init__(self, max_width=128):
        self.max_width = max_width
        self.cursor_x = 0
        self.cursor_y = 0
        self.row_h = 0
        self.width = 0
        self.height = 0

    def place(self, cube: Cube):
        dx, dy, dz = cube.size
        dx, dy, dz = math.ceil(dx), math.ceil(dy), math.ceil(dz)
        cell_w = 2 * dz + 2 * dx
        cell_h = dz + dy
        if self.cursor_x + cell_w > self.max_width and self.cursor_x > 0:
            self.cursor_x = 0
            self.cursor_y += self.row_h
            self.row_h = 0
        cube.uv = [self.cursor_x, self.cursor_y]
        self.cursor_x += cell_w
        self.row_h = max(self.row_h, cell_h)
        self.width = max(self.width, self.cursor_x)
        self.height = max(self.height, self.cursor_y + self.row_h)
        return cube.uv

    def finalize_size(self):
        # pad a couple pixels so nothing touches the hard edge
        return self.width + 1, self.height + 1


FACE_ORDER = ["top", "bottom", "right", "front", "left", "back"]


def face_rects(u, v, dx, dy, dz):
    dx, dy, dz = math.ceil(dx), math.ceil(dy), math.ceil(dz)
    return {
        "top":    (u + dz,          v,           dx, dz),
        "bottom": (u + dz + dx,     v,           dx, dz),
        "right":  (u,                v + dz,      dz, dy),
        "front":  (u + dz,          v + dz,      dx, dy),
        "left":   (u + dz + dx,     v + dz,      dz, dy),
        "back":   (u + dz + dx + dz, v + dz,      dx, dy),
    }


def paint_cube(draw: ImageDraw.ImageDraw, cube: Cube, palette, seed=0):
    """palette: dict of face-group -> base RGBA color. face-groups: 'top','bottom','side','front','back'
    Adds simple per-pixel value noise + a darker outline so shapes read at a distance."""
    u, v = cube.uv
    dx, dy, dz = cube.size
    rects = face_rects(u, v, dx, dy, dz)
    rnd = random.Random(seed)
    face_color = {
        "top": palette.get("top", palette.get("side")),
        "bottom": palette.get("bottom", palette.get("side")),
        "right": palette.get("side"),
        "left": palette.get("side"),
        "front": palette.get("front", palette.get("side")),
        "back": palette.get("back", palette.get("side")),
    }
    for face, (x, y, w, h) in rects.items():
        base = face_color[face]
        for px in range(w):
            for py in range(h):
                jitter = rnd.randint(-12, 12)
                # a light diagonal sheen so flat faces don't read as a
                # single flat color from a distance
                sheen = 10 if (px + py) % 5 == 0 else 0
                col = tuple(max(0, min(255, c + jitter + sheen)) if i < 3 else c for i, c in enumerate(base))
                draw.point((x + px, y + py), fill=col)
        # a softer outline than before - a hard -60 read as near-black on
        # already-dark palettes and made mobs look like flat silhouettes
        outline = tuple(max(0, c - 35) if i < 3 else 255 for i, c in enumerate(base))
        draw.rectangle([x, y, x + w - 1, y + h - 1], outline=outline)


def new_canvas(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))
