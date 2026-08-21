"""
Draw the pack icon.

The icon is how a player tells one pack from another in a list of twenty, so
the rename needs one of its own: a player who still has the old End Everlasting
build installed should be able to see at a glance which row is which.

So it draws the pack's actual subject rather than a logo - a column of floating
islands stacked through the frame against the new teal sky, with a violet spire
on the largest. That is what the addon does, and it is what the screenshots
look like.

    python3 build.py
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "mobgen"))

from PIL import Image  # noqa: E402

from paint import Rng, hex_to_rgb, mix, scale, string_seed  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

SIZE = 128

SKY_TOP = "#0B1F28"
SKY_BOTTOM = "#16414A"
ROCK = "#6E6455"
ROCK_DARK = "#4A4238"
GRASS = "#2E7A6E"
GRASS_LIT = "#49A891"
CRYSTAL = "#B04CFF"
CRYSTAL_LIT = "#E9B4FF"
STAR = "#BFE2EC"

# Each island: centre x, centre y, half-width, and how deep its keel hangs.
ISLANDS = [
    (64, 88, 34, 22),
    (30, 52, 17, 11),
    (96, 44, 20, 13),
    (56, 24, 13, 8),
    (104, 96, 12, 8),
]


def build():
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
    px = image.load()
    rng = Rng(string_seed("icon"))

    top = hex_to_rgb(SKY_TOP)
    bottom = hex_to_rgb(SKY_BOTTOM)
    for y in range(SIZE):
        row = mix(top, bottom, (y / (SIZE - 1)) ** 1.3)
        for x in range(SIZE):
            px[x, y] = (*row, 255)

    for _ in range(26):
        x, y = int(rng.between(0, SIZE)), int(rng.between(0, SIZE * 0.7))
        px[x, y] = (*hex_to_rgb(STAR), 255)

    for index, (cx, cy, half, keel) in enumerate(ISLANDS):
        _island(px, rng, cx, cy, half, keel, lit=index == 0)

    path = os.path.join(ROOT, "RP", "pack_icon.png")
    image.save(path, "PNG", optimize=True)
    image.save(os.path.join(ROOT, "BP", "pack_icon.png"), "PNG", optimize=True)
    print(f"  wrote {os.path.relpath(path, ROOT)} and the behaviour pack's copy")


def _island(px, rng, cx, cy, half, keel, lit):
    rock = hex_to_rgb(ROCK)
    rock_dark = hex_to_rgb(ROCK_DARK)
    grass = hex_to_rgb(GRASS)
    grass_lit = hex_to_rgb(GRASS_LIT)

    for dx in range(-half, half + 1):
        edge = abs(dx) / half
        # The keel: deepest under the middle, tapering to nothing at the rim.
        depth = max(1, int(keel * (1 - edge * edge) + rng.between(-1, 1)))
        for dy in range(0, depth):
            y = cy + dy
            if not (0 <= y < SIZE and 0 <= cx + dx < SIZE):
                continue
            shade = 1.0 - dy / max(1, depth) * 0.55
            px[cx + dx, y] = (*scale(mix(rock, rock_dark, edge * 0.5), shade), 255)

        # Two rows of surface on top.
        for dy in (-2, -1):
            y = cy + dy
            if 0 <= y < SIZE and 0 <= cx + dx < SIZE:
                tone = grass_lit if dy == -2 and rng.chance(0.65) else grass
                px[cx + dx, y] = (*tone, 255)

    if lit:
        _spire(px, rng, cx + 4, cy - 3)


def _spire(px, rng, x, base_y):
    """A crystal needle, which is the pack's one recognisable silhouette."""
    crystal = hex_to_rgb(CRYSTAL)
    crystal_lit = hex_to_rgb(CRYSTAL_LIT)
    height = 30
    for step in range(height):
        y = base_y - step
        if y < 0:
            break
        width = max(0, int(3 * (1 - step / height)))
        for dx in range(-width, width + 1):
            if not (0 <= x + dx < SIZE):
                continue
            lit = dx <= 0 or rng.chance(0.3)
            px[x + dx, y] = (*(crystal_lit if lit else crystal), 255)
        # A faint bloom to either side of the tip.
        if step > height * 0.6 and 0 <= y < SIZE:
            for dx in (-width - 1, width + 1):
                if 0 <= x + dx < SIZE:
                    current = px[x + dx, y]
                    px[x + dx, y] = (*mix(current[:3], crystal, 0.45), 255)


if __name__ == "__main__":
    print("Drawing the pack icon...")
    build()
