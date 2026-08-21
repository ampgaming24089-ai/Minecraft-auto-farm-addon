"""
Geometry construction and UV packing for the Eternal End mobs.

A Bedrock model is a tree of bones holding axis-aligned cubes, and every cube
needs a rectangle of the texture reserved for it. Doing that by hand for twenty
mobs is where hand-authored packs go wrong: one mistyped UV origin and a leg
wears a face. So the model is described in Python - bones, pivots, cubes, and
the *material* each cube is painted in - and the atlas is packed from that.

The packer lays cubes out on shelves, largest first, into the smallest
power-of-two atlas they fit in. Because the packer owns the layout, the painter
in `paint.py` can be handed the exact rectangle of every face, which is what
makes it possible to put eyes on a head and crystals on a spine without anyone
ever writing a UV coordinate down.

Box UV, for reference. A cube of size (w, h, d) placed at atlas (u, v) covers
2*(w+d) by (d+h) pixels, laid out as:

        u   u+d       u+d+w     u+2d+w    u+2d+2w
    v   +---+---------+---------+
        |   |   up    |  down   |
    v+d +---+---------+---------+---------+
        |wst|  north  |  east   |  south  |
   v+d+h+---+---------+---------+---------+
"""

from __future__ import annotations

# The six faces of a cube, in the order Bedrock lays them out in box UV.
FACES = ("up", "down", "west", "north", "east", "south")


class Cube:
    """One box in a bone, plus the material it is painted in."""

    def __init__(self, origin, size, mat, inflate=0.0, mirror=False, pivot=None,
                 rotation=None):
        self.origin = [float(v) for v in origin]
        self.size = [int(round(v)) for v in size]
        self.mat = mat
        self.inflate = inflate
        self.mirror = mirror
        self.pivot = pivot
        self.rotation = rotation
        self.uv = None  # filled in by pack()

    @property
    def atlas_size(self):
        """The (width, height) this cube needs on the texture."""
        w, h, d = self.size
        return 2 * (w + d), d + h

    def face_rect(self, face):
        """The (x, y, w, h) rectangle of one face, in atlas pixels."""
        w, h, d = self.size
        u, v = self.uv
        return {
            "up": (u + d, v, w, d),
            "down": (u + d + w, v, w, d),
            "west": (u, v + d, d, h),
            "north": (u + d, v + d, w, h),
            "east": (u + d + w, v + d, d, h),
            "south": (u + 2 * d + w, v + d, w, h),
        }[face]

    def to_json(self):
        cube = {
            "origin": self.origin,
            "size": self.size,
            "uv": list(self.uv),
        }
        if self.inflate:
            cube["inflate"] = self.inflate
        if self.mirror:
            cube["mirror"] = True
        if self.rotation:
            cube["rotation"] = self.rotation
            cube["pivot"] = self.pivot or [
                self.origin[0] + self.size[0] / 2,
                self.origin[1] + self.size[1] / 2,
                self.origin[2] + self.size[2] / 2,
            ]
        return cube


class Bone:
    """A named joint. Animations address these, so the names are the API."""

    def __init__(self, name, pivot, parent=None, rotation=None):
        self.name = name
        self.pivot = [float(v) for v in pivot]
        self.parent = parent
        self.rotation = rotation
        self.cubes: list[Cube] = []

    def cube(self, origin, size, mat, **kwargs):
        cube = Cube(origin, size, mat, **kwargs)
        self.cubes.append(cube)
        return cube

    def to_json(self):
        bone = {"name": self.name, "pivot": self.pivot}
        if self.parent:
            bone["parent"] = self.parent
        if self.rotation:
            bone["rotation"] = self.rotation
        if self.cubes:
            bone["cubes"] = [c.to_json() for c in self.cubes]
        return bone


class Model:
    """A whole mob: bones, cubes, and the atlas they were packed into."""

    def __init__(self, identifier, visible_width=2.0, visible_height=2.0,
                 visible_offset=(0, 1, 0)):
        self.identifier = identifier
        self.visible_width = visible_width
        self.visible_height = visible_height
        self.visible_offset = list(visible_offset)
        self.bones: list[Bone] = []
        self.texture_width = 0
        self.texture_height = 0

    def bone(self, name, pivot, parent=None, rotation=None):
        bone = Bone(name, pivot, parent, rotation)
        self.bones.append(bone)
        return bone

    @property
    def cubes(self):
        for bone in self.bones:
            yield from bone.cubes

    def pack(self, min_size=64, max_size=256):
        """
        Reserve a rectangle for every cube, in the smallest square atlas that
        holds them all.

        Shelf packing, tallest-first. Mob cubes are small and similar in size,
        so the fancier bin packers buy nothing here - what matters is that the
        result is deterministic, because a texture that shuffles between builds
        would make every rebuild a full re-diff of twenty PNGs.
        """
        # Tallest first, ties broken by width then by declaration order, so the
        # layout is a pure function of the model.
        order = sorted(
            enumerate(self.cubes),
            key=lambda pair: (-pair[1].atlas_size[1], -pair[1].atlas_size[0], pair[0]),
        )

        size = min_size
        while size <= max_size:
            if self._try_pack(order, size):
                self.texture_width = size
                self.texture_height = size
                return size
            size *= 2
        raise ValueError(
            f"{self.identifier}: cubes do not fit in a {max_size}x{max_size} atlas"
        )

    def _try_pack(self, order, size):
        shelf_y = 0
        shelf_height = 0
        cursor_x = 0
        placed = []
        for _, cube in order:
            w, h = cube.atlas_size
            if w > size:
                return False
            if cursor_x + w > size:
                # New shelf.
                shelf_y += shelf_height
                shelf_height = 0
                cursor_x = 0
            if shelf_y + h > size:
                return False
            placed.append((cube, (cursor_x, shelf_y)))
            cursor_x += w
            shelf_height = max(shelf_height, h)
        for cube, uv in placed:
            cube.uv = uv
        return True

    def to_json(self):
        if not self.texture_width:
            self.pack()
        return {
            "format_version": "1.12.0",
            "minecraft:geometry": [
                {
                    "description": {
                        "identifier": f"geometry.eternal_end.{self.identifier}",
                        "texture_width": self.texture_width,
                        "texture_height": self.texture_height,
                        "visible_bounds_width": self.visible_width,
                        "visible_bounds_height": self.visible_height,
                        "visible_bounds_offset": self.visible_offset,
                    },
                    "bones": [b.to_json() for b in self.bones],
                }
            ],
        }
