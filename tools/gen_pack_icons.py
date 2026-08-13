#!/usr/bin/env python3
"""Generates the 128x128 pack_icon.png for each of the three Aurora packs.

Each icon shares the same dark-slate plate and cyan/violet aurora ribbon so the
three packs read as one family in the pack list, with a distinct glyph per pack.
"""
import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packs")
SIZE = 128

BG_TOP = (18, 21, 29)
BG_BOTTOM = (10, 12, 18)
CYAN = (77, 227, 208)
VIOLET = (139, 107, 255)
WARM = (255, 186, 120)


def lerp(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def plate():
    """Dark rounded plate with a vertical gradient and a cyan rim."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(SIZE):
        d.line([(0, y), (SIZE, y)], fill=lerp(BG_TOP, BG_BOTTOM, y / (SIZE - 1)))

    # Round off the corners by punching an alpha mask.
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=18, fill=255)
    img.putalpha(mask)

    d = ImageDraw.Draw(img)
    d.rounded_rectangle([1, 1, SIZE - 2, SIZE - 2], radius=17, outline=(64, 86, 96, 255), width=2)
    d.rounded_rectangle([4, 4, SIZE - 5, SIZE - 5], radius=14, outline=(38, 50, 58, 160), width=1)
    return img


def aurora_ribbon(img, y_base, amp, phase, color, thickness=7, alpha=190):
    """A soft sine ribbon, drawn as stacked translucent strokes."""
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = []
    for x in range(6, SIZE - 5):
        t = (x - 6) / (SIZE - 12)
        y = y_base + math.sin(t * math.pi * 2.1 + phase) * amp
        pts.append((x, y))
    for i, width in enumerate(range(thickness, 0, -2)):
        a = int(alpha * (0.30 + 0.70 * (i / max(1, thickness // 2))))
        d.line(pts, fill=color + (min(255, a),), width=width, joint="curve")
    img.alpha_composite(layer)


def glyph_visuals(img):
    """Sun disc over layered aurora bands."""
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([46, 30, 82, 66], fill=WARM + (235,))
    d.ellipse([40, 24, 88, 72], outline=WARM + (70,), width=3)
    aurora_ribbon(img, 86, 11, 0.0, CYAN, thickness=9)
    aurora_ribbon(img, 98, 8, 1.4, VIOLET, thickness=7, alpha=160)


def glyph_ui(img):
    """A 3x3 slot grid, the signature shape of the inventory restyle."""
    d = ImageDraw.Draw(img, "RGBA")
    aurora_ribbon(img, 104, 7, 0.6, VIOLET, thickness=7, alpha=120)
    cell, gap, n = 22, 6, 3
    total = n * cell + (n - 1) * gap
    ox = (SIZE - total) // 2
    oy = 26
    for r in range(n):
        for c in range(n):
            x, y = ox + c * (cell + gap), oy + r * (cell + gap)
            d.rounded_rectangle([x, y, x + cell, y + cell], radius=4, fill=(8, 10, 15, 255))
            lit = (r * n + c) in (0, 4, 8)
            d.rounded_rectangle(
                [x, y, x + cell, y + cell],
                radius=4,
                outline=(CYAN if lit else (70, 84, 96)) + (255,),
                width=2,
            )


def glyph_animations(img):
    """A running figure, echoing the sprint cycle."""
    d = ImageDraw.Draw(img, "RGBA")
    aurora_ribbon(img, 102, 7, 0.3, CYAN, thickness=7, alpha=120)

    # Motion trails behind the runner.
    for i, a in enumerate((60, 100, 150)):
        x = 26 + i * 9
        d.line([(x, 52), (x + 12, 52)], fill=CYAN + (a,), width=3)
        d.line([(x + 4, 68), (x + 14, 68)], fill=CYAN + (a,), width=3)

    body = (233, 240, 245, 255)
    d.ellipse([70, 24, 88, 42], fill=body)              # head
    d.line([(78, 42), (72, 70)], fill=body, width=8)    # torso
    d.line([(74, 50), (94, 42)], fill=body, width=7)    # lead arm
    d.line([(76, 52), (58, 62)], fill=body, width=7)    # trail arm
    d.line([(72, 70), (88, 92)], fill=body, width=8)    # lead leg
    d.line([(72, 70), (56, 88)], fill=body, width=8)    # trail leg
    d.line([(88, 92), (96, 96)], fill=body, width=7)    # lead foot
    d.line([(56, 88), (48, 94)], fill=body, width=7)    # trail foot


BUILDERS = {
    "aurora_visuals": glyph_visuals,
    "aurora_ui": glyph_ui,
    "aurora_animations": glyph_animations,
}


def main():
    for pack, glyph in BUILDERS.items():
        img = plate()
        glyph(img)
        out = os.path.join(ROOT, pack, "pack_icon.png")
        img.save(out)
        print("wrote", os.path.relpath(out, os.path.join(ROOT, "..")))


if __name__ == "__main__":
    main()
