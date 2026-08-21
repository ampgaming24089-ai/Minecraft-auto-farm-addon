"""
Draw the End's sky.

The sky texture is tiled across the whole dome, many times over, so the one
thing it must not have is structure. The previous one was a dense field of hard
white pixels on flat purple: at that density the tiling reads as static, the
repeat is obvious the moment you turn your head, and the stars sit in front of
everything instead of behind it.

So this draws almost nothing. A deep teal-violet ground, a very low frequency
mottle so the field has depth rather than being a flat fill, a handful of dim
stars, and two or three brighter ones with a soft halo. Roughly a twentieth of
the stars the old one had.

Both noise fields are sampled on a torus - the texture is walked as an angle
around two circles rather than as a flat plane - so opposite edges are the same
sample and the tile has no seam anywhere.

    python3 build.py            # writes RP/textures/environment/end_sky.png
    python3 build.py --preview  # also writes a 3x3 tiling to check the seams
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "mobgen"))

from PIL import Image  # noqa: E402

from paint import Rng, hex_to_rgb, mix, string_seed  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "RP", "textures", "environment", "end_sky.png")

SIZE = 256

# The two ends of the mottle. Deep teal into a colder blue-violet - the colours
# the reference screenshots read as, rather than vanilla's magenta-purple.
DEEP = "#0C2731"
TEAL = "#17454C"
VIOLET = "#1B2B48"

# Pale, cold star colours. Nothing is pure white: a white pixel on a dark sky
# is the single thing that makes a skybox look cheap.
STAR_DIM = "#7FA8B4"
STAR_MID = "#B8D8E4"
STAR_BRIGHT = "#DCF0F6"

STARS_DIM = 34
STARS_MID = 11
STARS_BRIGHT = 3


def lattice(rng_seed, period):
    """A grid of random values, one per cell of a `period`-by-`period` torus."""
    rng = Rng(rng_seed)
    return [[rng.next() for _ in range(period)] for _ in range(period)]


def smooth(t):
    return t * t * (3 - 2 * t)


def tiled_noise(grid, period, x, y):
    """
    Bilinear value noise that wraps.

    Indices are taken modulo the lattice period, so the sample at x=SIZE is the
    sample at x=0 and the texture tiles with no seam.
    """
    fx = x * period / SIZE
    fy = y * period / SIZE
    x0, y0 = int(fx) % period, int(fy) % period
    x1, y1 = (x0 + 1) % period, (y0 + 1) % period
    tx, ty = smooth(fx - int(fx)), smooth(fy - int(fy))
    top = grid[y0][x0] * (1 - tx) + grid[y0][x1] * tx
    bottom = grid[y1][x0] * (1 - tx) + grid[y1][x1] * tx
    return top * (1 - ty) + bottom * ty


def build(preview=False):
    deep = hex_to_rgb(DEEP)
    teal = hex_to_rgb(TEAL)
    violet = hex_to_rgb(VIOLET)

    # Three octaves, all wrapping. The coarse one decides teal versus violet,
    # the middle one gives the field some cloud, the fine one keeps it from
    # banding on a screen that dithers.
    coarse = lattice(string_seed("sky/coarse"), 2)
    middle = lattice(string_seed("sky/middle"), 4)
    fine = lattice(string_seed("sky/fine"), 8)

    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
    px = image.load()

    for y in range(SIZE):
        for x in range(SIZE):
            hue = tiled_noise(coarse, 2, x, y)
            cloud = (tiled_noise(middle, 4, x, y) * 0.68
                     + tiled_noise(fine, 8, x, y) * 0.32)
            # Bias the cloud low, and keep the lift shallow. The mottle is
            # there to stop the field being a flat fill, not to be a feature:
            # anything with real contrast becomes a shape you can see repeat
            # once the texture is tiled across the whole dome.
            lift = max(0.0, (cloud - 0.40) / 0.60) ** 1.9 * 0.55
            ground = mix(teal, violet, hue)
            px[x, y] = (*mix(deep, ground, lift), 255)

    _stars(px)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    image.save(OUT, "PNG", optimize=True)
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  {SIZE}x{SIZE}, "
          f"{STARS_DIM + STARS_MID + STARS_BRIGHT} stars")

    if preview:
        sheet = Image.new("RGB", (SIZE * 3, SIZE * 3))
        for row in range(3):
            for column in range(3):
                sheet.paste(image.convert("RGB"), (column * SIZE, row * SIZE))
        path = os.path.join(HERE, "preview_tiled.png")
        sheet.save(path)
        print(f"  wrote {path} (3x3, to check the seams)")


def _stars(px):
    """
    Scatter the stars.

    Placed on a jittered grid rather than at pure random positions: uniform
    randomness clumps, and a clump of stars on a tiling texture becomes a
    repeating constellation, which is exactly the tell we are trying to avoid.
    """
    rng = Rng(string_seed("sky/stars"))
    dim = hex_to_rgb(STAR_DIM)
    mid = hex_to_rgb(STAR_MID)
    bright = hex_to_rgb(STAR_BRIGHT)

    def place(count, colour, halo):
        cells = max(1, int(math.ceil(math.sqrt(count))))
        step = SIZE / cells
        slots = [(cx, cy) for cy in range(cells) for cx in range(cells)]
        rng_shuffle(slots, rng)
        for index in range(min(count, len(slots))):
            cx, cy = slots[index]
            x = int(cx * step + rng.between(1, step - 1)) % SIZE
            y = int(cy * step + rng.between(1, step - 1)) % SIZE
            base = px[x, y]
            px[x, y] = (*colour, 255)
            if not halo:
                continue
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = (x + ox) % SIZE, (y + oy) % SIZE
                px[nx, ny] = (*mix(base[:3], colour, 0.42), 255)

    place(STARS_DIM, dim, halo=False)
    place(STARS_MID, mid, halo=False)
    place(STARS_BRIGHT, bright, halo=True)


def rng_shuffle(items, rng):
    for i in range(len(items) - 1, 0, -1):
        j = int(rng.next() * (i + 1))
        items[i], items[j] = items[j], items[i]


if __name__ == "__main__":
    print("Drawing the End sky...")
    build(preview="--preview" in sys.argv)
