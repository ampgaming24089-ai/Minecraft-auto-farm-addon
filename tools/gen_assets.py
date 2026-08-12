#!/usr/bin/env python3
"""
Procedural asset generator for the Hollow Veil addon.
Regenerates every PNG in BP/RP from code so geometry and textures always
agree, and the whole art pass is reproducible. Run with: python3 tools/gen_assets.py

NOTE ON ART STYLE: these are stylised, low-poly / flat-shaded placeholder
textures generated algorithmically (silhouette + palette + noise), not
hand-painted art. They are fully functional in-game (correct UVs, correct
sizes, no missing-texture pink/black checkerboards) but a professional pack
would replace them with bespoke Blockbench models / hand-painted textures.
"""
import colorsys
import math
import random
import os
import zlib

from PIL import Image, ImageDraw, ImageFilter

import boxuv
import icons


def stable_seed(value):
    """A random seed derived from `value` that's the same on every run.
    Python's built-in hash() is salted per-process for str/tuples-of-str
    (hash randomization), so using it to seed noise made textures that
    depend on a name (block/item/tier names) come out different on every
    regeneration - the opposite of this pipeline's whole point."""
    return zlib.crc32(repr(value).encode())

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "BP")
RP = os.path.join(ROOT, "RP")


def path(*parts):
    p = os.path.join(*parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def save(img, *parts):
    p = path(*parts)
    img.save(p)
    return p


# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
# Brightness floor: nothing in this table should read as "black" at a
# glance. Bedrock's own directional/ambient shading darkens flat-shaded
# textures further once they're on a real mob outdoors, so the source
# palette needs real headroom - "side" values stay >= ~110, "front"
# (the darkest of the three) stays >= ~80. Learned the hard way from a
# real screenshot where a (70,75,80) knight rendered as a black silhouette.
PAL = {
    "wraith":        {"side": (160, 220, 200, 255), "top": (205, 245, 230, 255), "front": (130, 195, 175, 255)},
    "wraith_glow":   (220, 255, 240, 255),
    "banshee":       {"side": (210, 190, 230, 255), "top": (235, 215, 250, 255), "front": (180, 160, 205, 255)},
    "banshee_glow":  (255, 240, 255, 255),
    "poltergeist":   {"side": (165, 165, 178, 255), "top": (195, 195, 208, 255), "front": (135, 135, 148, 255)},
    "hellhound":     {"side": (150, 55, 40, 255), "top": (185, 80, 55, 255), "front": (110, 35, 25, 255)},
    "hellhound_fire": (255, 140, 40, 255),
    "imp":           {"side": (190, 60, 55, 255), "top": (215, 85, 75, 255), "front": (150, 40, 35, 255)},
    "shade":         {"side": (95, 95, 145, 255), "top": (130, 130, 185, 255), "front": (70, 70, 115, 255)},
    "knight":        {"side": (135, 140, 150, 255), "top": (170, 175, 185, 255), "front": (100, 105, 115, 255)},
    "knight_trim":   (200, 60, 55, 255),
    "soulwisp":      {"side": (255, 240, 190, 255), "top": (255, 250, 220, 255), "front": (245, 215, 155, 255)},
    "occultist":     {"side": (140, 95, 165, 255), "top": (170, 120, 195, 255), "front": (105, 65, 130, 255)},
    "occultist_trim": (230, 190, 100, 255),
    # bosses
    "hollow_king":   {"side": (230, 230, 240, 255), "top": (250, 250, 255, 255), "front": (200, 200, 215, 255)},
    "hollow_king_cloak": {"side": (95, 55, 125, 255), "top": (120, 75, 150, 255), "front": (65, 35, 90, 255)},
    "hollow_king_gold": (230, 195, 100, 255),
    "weeping_widow": {"side": (215, 200, 230, 255), "top": (235, 225, 245, 255), "front": (185, 170, 205, 255)},
    "weeping_widow_dress": {"side": (100, 65, 130, 255), "top": (125, 85, 155, 255), "front": (70, 42, 95, 255)},
    "malacoda":      {"side": (200, 60, 40, 255), "top": (225, 85, 55, 255), "front": (155, 40, 25, 255)},
    "malacoda_wing": {"side": (80, 40, 40, 255), "top": (100, 52, 50, 255), "front": (55, 25, 25, 255)},
    "malacoda_horn": (55, 45, 45, 255),
    # new mobs
    "ashwing_bat":   {"side": (110, 90, 120, 255), "top": (140, 115, 150, 255), "front": (80, 65, 90, 255)},
    "bonehide_elk":  {"side": (210, 200, 180, 255), "top": (230, 220, 200, 255), "front": (180, 170, 152, 255)},
    "glimmershroom_toad": {"side": (120, 185, 165, 255), "top": (155, 220, 200, 255), "front": (90, 150, 132, 255)},
    "bastion_sentinel": {"side": (165, 110, 75, 255), "top": (195, 135, 95, 255), "front": (125, 78, 52, 255)},
    "bastion_sentinel_trim": (240, 170, 70, 255),
    "city_wraithguard": {"side": (110, 140, 170, 255), "top": (140, 170, 200, 255), "front": (80, 105, 132, 255)},
    "marrow_crawler": {"side": (130, 105, 85, 255), "top": (155, 128, 105, 255), "front": (95, 75, 60, 255)},
    "ashen_whelp":   {"side": (200, 85, 55, 255), "top": (225, 105, 75, 255), "front": (160, 55, 35, 255)},
    # dragon color variants (index order matches minecraft:variant value)
    "dragon_0": {"side": (195, 60, 55, 255), "top": (220, 85, 75, 255), "front": (150, 40, 35, 255)},    # ember red
    "dragon_1": {"side": (70, 115, 220, 255), "top": (100, 145, 240, 255), "front": (45, 80, 175, 255)}, # veil blue
    "dragon_2": {"side": (75, 195, 120, 255), "top": (105, 220, 145, 255), "front": (45, 150, 90, 255)}, # marsh green
    "dragon_3": {"side": (180, 95, 225, 255), "top": (205, 125, 245, 255), "front": (135, 65, 180, 255)}, # spectral purple
    "dragon_4": {"side": (240, 205, 80, 255), "top": (255, 228, 115, 255), "front": (200, 165, 50, 255)}, # gold
    "dragon_5": {"side": (85, 85, 95, 255), "top": (110, 110, 122, 255), "front": (58, 58, 66, 255)},    # obsidian black
}

# Glow-eye accents, painted onto the head bone's front face after the base
# noise pass - see paint_face_highlight() in gen_entities.py. None = skip
# (poltergeist/soul_wisp are already ambient light sources; toad already
# has hand-modeled eye cubes).
EYE_GLOW = {
    "wraith": (225, 255, 245, 255), "banshee": (255, 245, 255, 255), "shade": (190, 190, 255, 255),
    "hollow_king": (120, 255, 225, 255), "weeping_widow": (255, 245, 255, 255), "city_wraithguard": (200, 230, 255, 255),
    "hellhound": (255, 170, 60, 255), "imp": (255, 170, 60, 255), "malacoda": (255, 190, 80, 255),
    "ashen_whelp": (255, 170, 60, 255), "bastion_sentinel": (255, 190, 100, 255),
    "occultist": (255, 210, 120, 255), "fallen_knight": (200, 60, 55, 255),
    "ashwing_bat": (210, 130, 230, 255), "bonehide_elk": (255, 210, 140, 255), "marrow_crawler": (255, 90, 70, 255),
    "veil_dragon": (255, 230, 150, 255),
}


# Surface pattern per creature, consumed by boxuv.paint_cube. This is what
# stops every mob reading as the same painted box: a wraith's robe gets
# cloth folds, a knight gets banded plate with rivets, an elk gets bone
# striping, a dragon gets scale rows.
ENTITY_PATTERN = {
    "wraith": "cloth", "banshee": "cloth", "weeping_widow": "cloth",
    "occultist": "cloth", "shade": "cloth", "poltergeist": "cloth",
    "hollow_king": "plate", "fallen_knight": "plate",
    "bastion_sentinel": "plate", "city_wraithguard": "plate",
    "bonehide_elk": "bone", "marrow_crawler": "bone", "soul_wisp": "bone",
    "veil_dragon": "scale", "ashen_whelp": "scale", "malacoda": "scale",
    "imp": "scale", "glimmershroom_toad": "scale",
    "hellhound": "fur", "ashwing_bat": "fur",
}


def noise_fill(size, base, variance=14, seed=0):
    w, h = size
    img = Image.new("RGBA", (w, h), base)
    px = img.load()
    rnd = random.Random(seed)
    for x in range(w):
        for y in range(h):
            j = rnd.randint(-variance, variance)
            r, g, b, a = base
            px[x, y] = (
                max(0, min(255, r + j)),
                max(0, min(255, g + j)),
                max(0, min(255, b + j)),
                a,
            )
    return img


def vignette_edge(img, color=(0, 0, 0, 255), width=1):
    d = ImageDraw.Draw(img)
    w, h = img.size
    d.rectangle([0, 0, w - 1, h - 1], outline=color, width=width)
    return img


# ---------------------------------------------------------------------------
# Pack icons
# ---------------------------------------------------------------------------
def gen_pack_icons():
    for pack, ring, core in [
        (os.path.join(BP, "pack_icon.png"), (35, 10, 45, 255), (150, 60, 210, 255)),
        (os.path.join(RP, "pack_icon.png"), (20, 45, 40, 255), (90, 220, 180, 255)),
    ]:
        img = Image.new("RGBA", (128, 128), (10, 5, 15, 255))
        d = ImageDraw.Draw(img)
        cx, cy = 64, 64
        for r in range(60, 0, -1):
            t = r / 60
            col = tuple(int(ring[i] * t + core[i] * (1 - t)) for i in range(3)) + (255,)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        # torn veil / rip through the middle
        rnd = random.Random(7)
        pts = [(20 + rnd.randint(-6, 6), y) for y in range(10, 118, 10)]
        pts2 = [(x + 18 + rnd.randint(-4, 4), y) for x, y in pts]
        d.line(pts, fill=(5, 2, 8, 255), width=6, joint="curve")
        # a pair of glowing "eyes" for a ghostly face motif
        d.ellipse([46, 54, 58, 66], fill=(230, 255, 240, 255))
        d.ellipse([70, 54, 82, 66], fill=(230, 255, 240, 255))
        d.ellipse([49, 57, 55, 63], fill=(20, 60, 45, 255))
        d.ellipse([73, 57, 79, 63], fill=(20, 60, 45, 255))
        img = img.filter(ImageFilter.SMOOTH)
        img.save(pack)
        print("wrote", pack)


# ---------------------------------------------------------------------------
# Item icons — 32x32 procedural silhouettes on transparent backgrounds
# ---------------------------------------------------------------------------
IS = 32  # icon size
ICON_SS = 4  # supersampling factor for icons: draw at IS*ICON_SS, then
# downsample with LANCZOS so edges come out anti-aliased instead of PIL's
# hard 1px rasterization, which is what read as "choppy" at 32x32.


class ScaledDraw:
    """Wraps ImageDraw.Draw and multiplies every coordinate/width/radius by
    a fixed factor, so the existing draw_* functions below can keep
    authoring shapes in the same 0..32 coordinate space while actually
    rendering at higher resolution."""

    _SCALED_METHODS = ("polygon", "ellipse", "rectangle", "rounded_rectangle", "line", "pieslice", "chord", "arc", "point")

    def __init__(self, draw, scale):
        self._draw = draw
        self._scale = scale

    def _scale_xy(self, xy):
        s = self._scale
        if isinstance(xy[0], (int, float)):
            return [c * s for c in xy]
        return [(x * s, y * s) for x, y in xy]

    def _wrap(self, name):
        def method(xy, *args, **kwargs):
            xy = self._scale_xy(xy)
            if "width" in kwargs and kwargs["width"] is not None:
                kwargs["width"] = max(1, round(kwargs["width"] * self._scale))
            if "radius" in kwargs and kwargs["radius"] is not None:
                kwargs["radius"] = kwargs["radius"] * self._scale
            return getattr(self._draw, name)(xy, *args, **kwargs)
        return method

    def __getattr__(self, name):
        if name in self._SCALED_METHODS:
            return self._wrap(name)
        return getattr(self._draw, name)


def icon_canvas():
    return Image.new("RGBA", (IS, IS), (0, 0, 0, 0))


def render_icon(draw_fn):
    """Runs draw_fn(scaled_draw) at ICON_SS x resolution then downsamples
    for anti-aliasing. draw_fn is any of the draw_* functions below, which
    are authored against the normal 0..IS coordinate space."""
    big = Image.new("RGBA", (IS * ICON_SS, IS * ICON_SS), (0, 0, 0, 0))
    raw = ImageDraw.Draw(big)
    draw_fn(ScaledDraw(raw, ICON_SS))
    return big.resize((IS, IS), Image.LANCZOS)


def shade(color, amt):
    return tuple(max(0, min(255, c + amt)) if i < 3 else c for i, c in enumerate(color))


def draw_gem(draw, color, cx=16, cy=17, r=9):
    pts = [(cx, cy - r), (cx + r * 0.8, cy - r * 0.2), (cx + r * 0.55, cy + r), (cx - r * 0.55, cy + r), (cx - r * 0.8, cy - r * 0.2)]
    draw.polygon(pts, fill=color, outline=shade(color, -70))
    draw.polygon([(cx, cy - r), (cx + r * 0.8, cy - r * 0.2), (cx, cy - r * 0.1)], fill=shade(color, 45))


def draw_shard(draw, color):
    pts = [(16, 4), (22, 14), (18, 28), (14, 20), (9, 15)]
    draw.polygon(pts, fill=color, outline=shade(color, -70))
    draw.line([(16, 4), (16, 22)], fill=shade(color, 60), width=1)


def draw_dust_pile(draw, color):
    # single-pixel speckle is the right look for a powder/dust material, but
    # isolated 1px features get almost entirely blended away by the LANCZOS
    # downsample used for supersampled icons - so this one is rendered raw,
    # see RAW_ICONS below.
    rnd = random.Random(stable_seed(color) % 1000)
    for _ in range(70):
        x = 16 + rnd.randint(-11, 11)
        y = 22 + rnd.randint(-6, 4)
        if (x - 16) ** 2 / 121 + (y - 20) ** 2 / 36 <= 1:
            draw.point((x, y), fill=shade(color, rnd.randint(-30, 30)))


def draw_nugget(draw, color):
    draw.ellipse([9, 12, 23, 23], fill=color, outline=shade(color, -70))
    draw.ellipse([11, 13, 17, 18], fill=shade(color, 50))


# endpoints each vein is drawn between, per icon shape - keeps the glow
# confined to the shape's own footprint instead of wandering into blank space
VEIN_SPANS = {
    "sword": ((11, 19), (26, 7)),
    "pickaxe": ((7, 17), (17, 8)),
    "axe": ((9, 8), (18, 15)),
    "nugget": ((11, 15), (21, 20)),
    "helmet": ((10, 10), (22, 18)),
    "chestplate": ((11, 10), (21, 24)),
    "leggings": ((11, 8), (21, 24)),
    "boots": ((10, 8), (22, 20)),
}


def draw_glow_veins(draw, color, span, seed=1, n=2, spread=2.2):
    """A couple of thin glowing crack lines that stay within the given
    (p0, p1) span - the icon-scale equivalent of the ore blocks' crack
    texture, so the three new-tier materials read as the same material at
    any size, without the glow spilling outside the drawn shape."""
    p0, p1 = span
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = max(1e-6, (dx ** 2 + dy ** 2) ** 0.5)
    perp = (-dy / length, dx / length)
    rnd = random.Random(seed)
    for i in range(n):
        offset = (i - (n - 1) / 2) * spread * 1.4
        a = (p0[0] + perp[0] * offset, p0[1] + perp[1] * offset)
        b = (p1[0] + perp[0] * offset, p1[1] + perp[1] * offset)
        steps = rnd.randint(3, 4)
        pts = []
        for s in range(steps + 1):
            t = s / steps
            bx = a[0] + (b[0] - a[0]) * t
            by = a[1] + (b[1] - a[1]) * t
            j = rnd.uniform(-spread, spread) if 0 < s < steps else 0
            pts.append((bx + perp[0] * j, by + perp[1] * j))
        for k in range(len(pts) - 1):
            draw.line([pts[k], pts[k + 1]], fill=color, width=1)


def draw_horn(draw, color):
    draw.polygon([(13, 26), (19, 26), (21, 14), (16, 5), (11, 14)], fill=color, outline=shade(color, -70))
    for i in range(3):
        y = 22 - i * 6
        draw.line([(12, y), (20, y - 2)], fill=shade(color, -40))


def draw_sword(draw, blade, hilt, size="normal"):
    # diagonal blade (bottom-left grip -> top-right tip), the orientation
    # vanilla tool/weapon icons use so it reads clearly at small sizes
    draw.polygon([(25, 4), (28, 7), (13, 22), (10, 19)], fill=blade, outline=shade(blade, -70))
    draw.line([(23, 6), (12, 17)], fill=shade(blade, 70), width=1)
    # cross-guard, perpendicular to the blade
    draw.polygon([(9, 15), (13, 11), (17, 15), (13, 19)], fill=hilt, outline=shade(hilt, -70))
    # grip, continuing the diagonal down past the guard
    draw.polygon([(9, 16), (12, 19), (7, 24), (4, 21)], fill=shade(hilt, -20), outline=shade(hilt, -70))


def draw_pickaxe(draw, head, handle):
    # head: two angled prongs meeting at a top-center apex, vanilla-style
    # pickaxe silhouette (a hard-edged polygon reads better at 32px than an arc)
    draw.polygon([(16, 6), (19, 9), (6, 20), (3, 17)], fill=head, outline=shade(head, -70))
    draw.polygon([(16, 6), (13, 9), (26, 20), (29, 17)], fill=head, outline=shade(head, -70))
    draw.line([(17, 11), (28, 27)], fill=handle, width=4)
    draw.line([(17, 11), (28, 27)], fill=shade(handle, 40), width=1)


def draw_axe(draw, head, handle):
    draw.line([(10, 6), (24, 27)], fill=handle, width=4)
    draw.line([(10, 6), (24, 27)], fill=shade(handle, 40), width=1)
    draw.polygon([(5, 3), (19, 3), (21, 10), (18, 17), (10, 19), (5, 13)], fill=head, outline=shade(head, -70))


def draw_helmet(draw, color):
    draw.pieslice([7, 5, 25, 23], 180, 360, fill=color, outline=shade(color, -70))
    draw.rectangle([7, 14, 25, 18], fill=color, outline=shade(color, -70))
    draw.rectangle([11, 14, 14, 18], fill=(10, 10, 12, 255))
    draw.rectangle([18, 14, 21, 18], fill=(10, 10, 12, 255))


def draw_chestplate(draw, color):
    draw.polygon([(9, 6), (23, 6), (25, 12), (23, 27), (9, 27), (7, 12)], fill=color, outline=shade(color, -70))
    draw.rectangle([14, 6, 18, 27], fill=shade(color, -25))
    draw.polygon([(9, 6), (13, 6), (11, 14), (7, 12)], fill=shade(color, 30))


def draw_leggings(draw, color):
    draw.polygon([(9, 5), (23, 5), (23, 16), (18, 16), (18, 27), (14, 27), (14, 16), (9, 16)], fill=color, outline=shade(color, -70))


def draw_boots(draw, color):
    draw.polygon([(9, 5), (15, 5), (15, 18), (20, 18), (20, 24), (9, 24)], fill=color, outline=shade(color, -70))
    draw.polygon([(17, 5), (23, 5), (23, 24), (22, 24), (22, 18), (17, 18)], fill=color, outline=shade(color, -70))


def draw_lantern(draw):
    draw.rectangle([13, 3, 19, 6], fill=(60, 60, 60, 255))
    draw.rectangle([11, 8, 21, 22], fill=(230, 210, 130, 230), outline=(50, 40, 20, 255))
    draw.rectangle([9, 6, 23, 9], fill=(45, 40, 35, 255))
    draw.rectangle([9, 21, 23, 24], fill=(45, 40, 35, 255))
    draw.ellipse([14, 11, 18, 19], fill=(255, 250, 200, 255))


def draw_compass(draw, accent):
    draw.ellipse([6, 6, 26, 26], fill=(180, 150, 90, 255), outline=(70, 50, 20, 255))
    draw.ellipse([10, 10, 22, 22], fill=(230, 225, 210, 255))
    draw.polygon([(16, 12), (18, 16), (16, 20), (14, 16)], fill=accent)


def draw_book(draw, cover):
    draw.rectangle([7, 6, 25, 26], fill=cover, outline=shade(cover, -70))
    draw.rectangle([9, 8, 23, 24], fill=(235, 220, 180, 255))
    for y in range(10, 23, 3):
        draw.line([(11, y), (21, y)], fill=(150, 130, 90, 255))
    draw.ellipse([14, 13, 18, 17], outline=(255, 215, 90, 255), width=1)


def draw_rune_paper(draw, accent):
    draw.polygon([(7, 5), (25, 5), (23, 27), (9, 27)], fill=(210, 195, 160, 255), outline=(90, 75, 50, 255))
    rnd = random.Random(stable_seed(accent))
    for _ in range(5):
        y = rnd.randint(9, 22)
        x0, x1 = 11, 21
        draw.line([(x0, y), (x1, y)], fill=accent, width=1)
    draw.ellipse([13, 13, 19, 19], outline=accent, width=2)


def draw_igniter(draw):
    draw.line([(8, 24), (22, 8)], fill=(90, 90, 95, 255), width=4)
    # a blue-and-black soulfire spark, not vanilla flint and steel's gold one
    draw.polygon([(19, 5), (26, 5), (26, 12), (22, 15), (18, 11)], fill=(32, 32, 50, 255), outline=(8, 8, 14, 255))
    draw.polygon([(20, 7), (24, 7), (24, 11), (21, 12)], fill=(90, 140, 255, 255))


def draw_plate(draw, color):
    draw.rounded_rectangle([7, 9, 25, 23], radius=3, fill=color, outline=shade(color, -70))
    for x, y in [(10, 12), (22, 12), (10, 20), (22, 20)]:
        draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=shade(color, -90))
    draw.line([(9, 16), (23, 16)], fill=shade(color, 40), width=1)


def draw_chitin_shard(draw, color):
    draw.polygon([(16, 3), (21, 12), (18, 26), (14, 26), (11, 12)], fill=color, outline=shade(color, -70))
    draw.line([(16, 6), (16, 22)], fill=shade(color, -50), width=1)


def draw_hide(draw, color):
    draw.polygon([(8, 6), (22, 5), (25, 15), (20, 27), (10, 25), (6, 14)], fill=color, outline=shade(color, -70))
    draw.line([(10, 10), (20, 12)], fill=shade(color, -30), width=1)
    draw.line([(9, 17), (19, 19)], fill=shade(color, -30), width=1)


def draw_membrane(draw, color):
    draw.polygon([(9, 6), (24, 10), (20, 22), (12, 24), (9, 15)], fill=color, outline=shade(color, -70))
    for x in range(11, 22, 3):
        draw.line([(9, 6), (x, 20)], fill=shade(color, -40), width=1)


def draw_mushroom_icon(draw, cap_color, stem_color):
    draw.ellipse([13, 18, 19, 27], fill=stem_color, outline=shade(stem_color, -60))
    draw.pieslice([6, 4, 26, 22], 180, 360, fill=cap_color, outline=shade(cap_color, -70))
    for x, y in [(11, 12), (16, 9), (21, 12)]:
        draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=shade(cap_color, 60))


def draw_fruit(draw, color):
    draw.ellipse([9, 11, 23, 25], fill=color, outline=shade(color, -70))
    draw.line([(16, 11), (18, 5)], fill=(90, 60, 30, 255), width=2)
    draw.ellipse([17, 4, 22, 8], fill=(70, 130, 70, 255), outline=shade((70, 130, 70, 255), -60))
    draw.ellipse([12, 14, 16, 18], fill=shade(color, 60))


def draw_stew_bowl(draw, fill_color):
    draw.pieslice([6, 14, 26, 28], 0, 180, fill=(120, 110, 100, 255), outline=(60, 50, 45, 255))
    draw.ellipse([7, 12, 25, 20], fill=fill_color, outline=shade(fill_color, -60))
    draw.ellipse([11, 14, 15, 17], fill=shade(fill_color, 40))


def draw_dragon_egg(draw, color):
    draw.ellipse([10, 6, 22, 27], fill=color, outline=shade(color, -80))
    rnd = random.Random(stable_seed(color))
    for _ in range(8):
        x = rnd.randint(11, 21)
        y = rnd.randint(9, 24)
        draw.ellipse([x, y, x + 2, y + 2], fill=shade(color, 70))
    draw.ellipse([12, 9, 16, 13], fill=shade(color, 90))


def draw_charm(draw, accent):
    draw.ellipse([10, 4, 22, 10], outline=(120, 110, 90, 255), width=2)
    draw.polygon([(9, 12), (23, 12), (16, 28)], fill=(70, 70, 80, 255), outline=shade(accent, -60))
    draw.ellipse([12, 15, 20, 23], fill=accent, outline=shade(accent, -70))


# ---------------------------------------------------------------------------
# Vanilla-derived icons: base gear (raw ore, ingots, tools, armor) should
# look like Minecraft could have shipped it, not like a custom invention -
# so these are generated from the *shape* of the real vanilla icons rather
# than hand-drawn. Each grid below encodes, per pixel, its role (C = cool
# "material" pixel, H = warm wood-handle pixel, "." = transparent) and its
# relative brightness (0-9), extracted from Mojang's own bedrock-samples
# resource pack (items/iron_ingot, raw_iron, diamond_sword, diamond_pickaxe,
# diamond_axe, diamond_helmet/chestplate/leggings/boots - all 16x16). No
# actual color values or pixels from those files are reproduced here, only
# this derived brightness/role map, which render_vanilla_icon() recolors
# into this pack's own materials at native 16x16, un-antialiased, the same
# resolution and hard-edged style real item textures use.
IRON_INGOT_TPL = """
................................
................................
....................C3C3........
..............C3C3C3C6C6C4......
........C3C3C3C6C8C8C8C8C6C4....
..C3C3C3C6C8C8C8C8C8C8C8C8C6C4..
C3C9C8C8C8C8C8C8C8C8C8C8C9C9C8C4
C3C6C9C8C8C8C8C8C8C9C9C9C8C4C6C2
C3C6C6C9C8C8C9C9C9C8C5C4C4C5C6C2
C3C6C6C6C9C9C8C5C4C4C4C4C6C6C6C2
C3C5C6C6C8C5C4C4C4C4C6C6C5C2C2..
..C3C5C6C8C5C4C4C5C5C2C2C2......
....C3C5C6C5C3C2C2C2............
......C3C3C2C2..................
................................
................................
"""

RAW_ORE_TPL = """
................................
....H3H3H3H3H3..................
..H3H7H8H8H8H7H3H3H3............
..H3H8H9H8H9H8H8H8H7H3H3H3......
H3H8H9H9H9H8H9H8H9H8H8H8H7H3....
H3H8H7H8H9H9H8H8H8H8H8H7H8H7H3..
H2H8H5H5H8H7H5H5H4H4H5H7H5H7H3..
H2H7H4H5H7H5H5H5H4H3H3H4H5H5H3..
H2H7H4H4H7H5H5H4H3H3H3H3H3H4H2..
H2H5H4H4H4H3H3H3H3H8H9H8H5H5H2..
H2H5H5H4H4H3H3H3H8H8H8H8H7H5H4H2
..H2H5H4H4H4H2H2H5H8H8H7H4H3H3H2
....H2H2H2H2....H2H5H5H5H4H3H3H2
..................H2H5H5H3H3H2..
....................H2H2H2H2....
................................
"""

SWORD_TPL = """
..........................C1C1C1
........................C1C8C8C1
......................C1C8C5C8C1
....................C1C8C5C8C1..
..................C1C8C5C6C1....
................C1C8C5C6C1......
....C1C1......C1C6C5C6C1........
....C1C2C1..C1C6C5C6C1..........
......C1C4C1C6C4C6C1............
......C1C4C4C2C6C1..............
........C1C2C1C1................
......H2H3C1C1C1C1..............
....H2H4H1..C1C1C1C1............
C1C1H3H1........C1C1............
C1C2C1..........................
C1C1C1..........................
"""

PICKAXE_TPL = """
................................
................................
............C1C1C1C1C1..........
..........C1C6C5C5C5C5C1H2H3....
............C1C1C1C1C5C5H4H1....
....................H2C5C5C1....
..................H2H3H1C5C5C1..
................H2H4H1..C1C5C1..
..............H2H3H1....C1C5C1..
............H2H4H1......C1C5C1..
..........H2H3H1........C1C6C1..
........H2H4H1............C1....
......H2H3H1....................
....H2H4H1......................
....H1H1........................
................................
"""

AXE_TPL = """
................................
..................C1C1..........
................C1C6C6C1........
..............C1C6C5C5C1........
............C1C6C5C5C5H2H3......
............C1C6C5C5C4C5H1......
..............C1C1H2C5C4C5C1....
................H2H3H1C5C5C1....
..............H2H4H1..C1C1......
............H2H3H1..............
..........H2H3H1................
........H2H4H1..................
......H2H3H1....................
....H2H4H1......................
....H1H1........................
................................
"""

HELMET_TPL = """
................................
................................
................................
..........C1C1C1C1C1C1..........
........C1C5C7C7C7C7C4C1........
......C1C5C8C9C8C7C7C5C4C1......
......C1C7C8C8C7C7C5C5C5C1......
......C1C7C7C1C1C1C1C4C5C1......
......C1C7C1C1C1C1C1C1C5C1......
......C1C7C1C1C1C1C1C1C4C1......
......C1C5C1C1C1C1C1C1C4C1......
........C1C1........C1C1........
................................
................................
................................
................................
"""

CHESTPLATE_TPL = """
................................
................................
..C1C1C1C1C1........C1C1C1C1C1..
..C1C9C8C7C1........C1C9C8C7C1..
..C1C8C7C7C5C1....C1C5C8C7C7C1..
..C1C7C7C7C8C5C1C1C5C7C7C7C7C1..
..C1C4C5C7C9C8C8C8C7C7C7C5C4C1..
..C1C1C4C8C8C8C7C7C7C7C7C4C1C1..
......C1C8C8C7C7C7C7C7C7C1......
......C1C7C8C7C7C7C7C7C5C1......
......C1C7C7C7C7C7C7C7C5C1......
......C1C5C7C7C7C7C7C5C5C1......
......C1C4C5C5C5C5C5C5C4C1......
........C1C4C5C5C5C5C4C1........
..........C1C1C1C1C1C1..........
................................
"""

LEGGINGS_TPL = """
................................
................................
........C1C1C1C1C1C1C1C1........
......C1C8C9C9C8C8C7C7C4C1......
......C1C8C8C7C7C7C7C7C5C1......
......C1C8C7C7C5C5C7C7C5C1......
......C1C8C7C5C1C1C4C7C5C1......
......C1C7C7C1....C1C7C5C1......
......C1C7C5C1....C1C7C5C1......
......C1C7C5C1....C1C7C5C1......
......C1C5C5C1....C1C5C5C1......
......C1C5C4C1....C1C5C4C1......
......C1C4C4C1....C1C4C4C1......
......C1C1C1C1....C1C1C1C1......
................................
................................
"""

BOOTS_TPL = """
................................
................................
................................
........C1C1C1....C1C1C1........
......C1C9C8C1....C1C9C8C1......
......C1C8C8C1....C1C8C7C1......
......C1C8C7C1....C1C7C7C1......
......C1C7C7C1....C1C7C7C1......
......C1C7C5C1....C1C7C7C1......
....C1C7C7C5C1....C1C5C7C5C1....
..C1C7C7C5C4C1....C1C4C5C7C5C1..
..C1C5C5C4C1C1....C1C1C5C5C4C1..
..C1C1C1C1............C1C1C1C1..
................................
................................
................................
"""

HANDLE_H = 0.08  # warm brown, shared wood-grip hue for every tool tier
HANDLE_S = 0.55


def _parse_template(tpl):
    rows = [r for r in tpl.strip("\n").split("\n")]
    grid = []
    for row in rows:
        cells = [row[i : i + 2] for i in range(0, len(row), 2)]
        grid.append(cells)
    return grid


def render_vanilla_icon(tpl, tint_h, tint_s, handle_h=HANDLE_H, handle_s=HANDLE_S):
    """Recolors a vanilla-shape template (see *_TPL above) into this pack's
    material, preserving the original per-pixel lightness so the shading
    reads exactly like the source icon. 'C' cells take the material tint;
    'H' cells (tool handles) always take the shared wood-brown tint,
    matching how vanilla tool grips stay the same wood color across every
    material tier."""
    grid = _parse_template(tpl)
    h, w = len(grid), len(grid[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell == "..":
                continue
            role, bucket = cell[0], int(cell[1])
            l = bucket / 10 + 0.05
            if role == "H":
                r, g, b = colorsys.hls_to_rgb(handle_h, l, handle_s)
            else:
                r, g, b = colorsys.hls_to_rgb(tint_h, l, tint_s)
            px[x, y] = (int(r * 255), int(g * 255), int(b * 255), 255)
    return img


ORE_BLOCK_TPL = """
S5S4S4S4S4S4S4S4S4S4S4S4S4S4S5S5
S4S4S4S4S4S4S4S5S5S4F3F4F4F3S4S4
S4S4F4F5F4S4S4S4S4S4S4F4F5S4S4S4
S4F4F5F7S5S4S4S4S4S4S4S4S4S4S4S4
S4S5S5S5S4S4S4F4F4F5F5F4S4S4S4S4
S4S5S4S4F4F5F7F7F7F7F5S4S4F4F5S5
S4S4S4S5S5S5F5F7F7S5S4S4S4S5S5S4
S4S4S4S4S4S4S5S5S5S4S4S4S4S4S4S4
S5S5S4F4F5S4S4S4S4F3F4F5F3S4S4S4
S4S5F3F5F5F7F7S5S4S5F5F7S5S5S5S4
S4S4S5S5F7F7S5S4S4S4S5S5S4S4S4S4
S4S4S4S4S5S5S4S5S4S4S4F3F4S5S4S5
S4S4S4S4F4F5S5S4F3F4F5F7F7F5F4S4
S5F4F5S4S4S5S4S4S5F5F7F7F5S5S5S4
S4S5F4F3S4S4S4S4S4S5S5S5S5S4S4S4
S4S4S5S5S4S4S4S4S4S4S5S5S4S4S4S4
"""

DENSE_ORE_BLOCK_TPL = """
S5S4S4S5S4S4S4S4S4S4S4S4S4S5S5S5
S4S4S4S4S4S5S5S5S5S4S4S4S4S4S4S4
S4S4S4S4F4S5S4S4S4S4S4S4F6F3S4S4
S5S5S5S4F6S5S4F6F3F6S5S4F6S5S4S4
S4S4S4S4S4S4S4S5F6S4S4S4S5S4S4S4
S4S5S4S4S4F9F6S4S4S4F9F6S4S4S4S5
S4S4S5F9F6F4F4F3F6S4F4F3S4S4S4S4
S5S4S4S5F6S6F6F6S4S4S5F6S4S5S6S6
S4F6F4F6S5S4S4S4F9F6S4S4S4S4S5S4
S4F6F6S4S4S4S4F6F4F3F3F6S5S6S6S4
S4S4S4S4F4S4S4S5F6F6S5S4S4S4S4S4
S4S4S4S4S4S5S5S5S5S4S4F6F3S5S5S4
S4S4S5S4S4S4S5S4F6F9F6F4F4F3S5S4
S5S5F6F6F3S4S4S4S6F3F4F6F6S5S4S4
S4S4S4F6S5S5S5S4S4S5F6S4S4S4S4S4
S4S4S4S4S4S4S4S5S4S4S4S4S4S4S5S5
"""


def render_vanilla_ore_block(tpl, fleck_h, fleck_s, stone_h=0.09, stone_s=0.12):
    """Same idea as render_vanilla_icon but for ore blocks: 'S' (stone)
    cells take this dimension's pale bonestone hue, 'F' (fleck) cells take
    the ore's own color - the same "colored flecks in a stone matrix"
    convention vanilla iron/gold/diamond ore all use."""
    grid = _parse_template(tpl)
    h, w = len(grid), len(grid[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            role, bucket = cell[0], int(cell[1])
            l = bucket / 10 + 0.05
            if role == "F":
                r, g, b = colorsys.hls_to_rgb(fleck_h, l, fleck_s)
            else:
                r, g, b = colorsys.hls_to_rgb(stone_h, l, stone_s)
            px[x, y] = (int(r * 255), int(g * 255), int(b * 255), 255)
    return img


# per-tier tint (H, S in 0..1) - L always comes from the source template so
# the shading always matches the vanilla original
TIER_TINTS = {
    "wraithsteel": (0.055, 0.85),  # lava orange-red - "as good as diamond"
    "veilsteel": (0.60, 0.55),  # black metal with a blue sheen - "netherite-equivalent"
    "hollowforged": (0.0, 0.06),  # near-white/silver; the red comes from the glow-vein overlay
}
ORE_FLECK_TINTS = {
    "wraithsteel_ore": (0.055, 0.9),
    "veilsteel_ore": (0.60, 0.65),
    "hollowforged_ore": (0.0, 0.8),
}
# this dimension's stone (bonestone) is a pale warm grey, not vanilla's blue-grey
BONESTONE_STONE_TINT = (0.09, 0.12)


def tiered_vanilla_tool(tpl, tier, vein_color=None, seed=1, kind=None):
    tint_h, tint_s = TIER_TINTS[tier]

    def render():
        img = render_vanilla_icon(tpl, tint_h, tint_s)
        if vein_color and kind:
            d = ImageDraw.Draw(img)
            span = tuple((c[0] / 2, c[1] / 2) for c in VEIN_SPANS[kind])
            draw_glow_veins(d, vein_color, span, seed=seed, n=1, spread=1.1)
        return img

    return render


def tiered_vanilla_nugget(tpl, tier, vein_color=None, seed=1):
    tint_h, tint_s = TIER_TINTS[tier]

    def render():
        img = render_vanilla_icon(tpl, tint_h, tint_s)
        if vein_color:
            d = ImageDraw.Draw(img)
            span = ((5.5, 7.5), (10.5, 10))
            draw_glow_veins(d, vein_color, span, seed=seed, n=1, spread=1.0)
        return img

    return render


VEIN_COLORS = {
    "wraithsteel": (255, 190, 90, 255),
    "veilsteel": (90, 175, 255, 255),
    "hollowforged": (255, 60, 50, 255),
}

# name -> zero-argument function returning a finished 16x16 RGBA image
# (rendered at native vanilla resolution, not run through the icon
# supersampling pipeline - these should look exactly as crisp/blocky as a
# real item texture)

# The Soulfire and Steel is meant to be a reskin of flint and steel, so its
# icon is derived from the real vanilla flint_and_steel silhouette (shape and
# per-pixel lightness only) rather than drawn from scratch. The steel keeps a
# cold blue cast and the flint half burns soul-blue.
FLINT_STEEL_TPL = """................................
........S2S2....................
......S2S7S7S2..................
....S2S7S6S1S4S1................
....S2S7S1..S1S1................
....S2S6S2......................
....S2S6S2......................
....S2S4S2..S2S1......S0........
....S1S4S6S2S6S1....S0S3S0......
......S1S4S6S1....S0S1S2S0......
........S1S1....S0S2S3S4S1S0....
..............S0S1S2S6S1S0S0....
..............S0S3S4S1S0S0S1S0..
..............S0S3S2S0S1S2S3S0..
................S0S1S0S0S0S0....
..................S0S0.........."""


def render_soulfire_igniter():
    grid = _parse_template(FLINT_STEEL_TPL)
    h, w = len(grid), len(grid[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell == "..":
                continue
            bucket = int(cell[1])
            l = bucket / 10 + 0.06
            # the striker body stays steel-blue; the lower-right flint mass
            # is where the soul flame lives
            if y >= 7 and x >= 7:
                r, g, b = colorsys.hls_to_rgb(0.58, min(0.95, l * 1.25 + 0.10), 0.85)
            else:
                r, g, b = colorsys.hls_to_rgb(0.60, l, 0.16)
            px[x, y] = (int(r * 255), int(g * 255), int(b * 255), 255)
    return img

VANILLA_ICONS = {}
for _tier, _tpls in {
    "wraithsteel": (RAW_ORE_TPL, IRON_INGOT_TPL),
    "veilsteel": (RAW_ORE_TPL, IRON_INGOT_TPL),
    "hollowforged": (RAW_ORE_TPL, IRON_INGOT_TPL),
}.items():
    _scrap_tpl, _ingot_tpl = _tpls
    _vein = VEIN_COLORS[_tier]
    VANILLA_ICONS[f"{_tier}_scrap"] = tiered_vanilla_nugget(_scrap_tpl, _tier, _vein, seed=stable_seed(_tier) % 999 + 1)
    VANILLA_ICONS[f"{_tier}_ingot"] = tiered_vanilla_nugget(_ingot_tpl, _tier, _vein, seed=stable_seed(_tier) % 999 + 2)
    for _kind, _tpl in (("sword", SWORD_TPL), ("pickaxe", PICKAXE_TPL), ("axe", AXE_TPL)):
        VANILLA_ICONS[f"{_tier}_{_kind}"] = tiered_vanilla_tool(_tpl, _tier, _vein, seed=stable_seed((_tier, _kind)) % 999, kind=_kind)

# The three boss sets get the real vanilla armour silhouettes too. They used
# to be drawn with PIL primitives, which is why they showed up in the
# Equipment tab as plain coloured shapes next to properly-drawn vanilla gear.
BOSS_ARMOR_TINTS = {
    "spectral_regalia": (0.52, 0.22, (170, 235, 255, 255)),
    "mourners_shroud": (0.78, 0.32, (235, 180, 235, 255)),
    "ashen_demonplate": (0.02, 0.62, (255, 140, 60, 255)),
}
for _set, (_h, _s, _accent) in BOSS_ARMOR_TINTS.items():
    for _k, _t in (("helmet", HELMET_TPL), ("chestplate", CHESTPLATE_TPL),
                   ("leggings", LEGGINGS_TPL), ("boots", BOOTS_TPL)):
        def _mkboss(tpl=_t, kind=_k, hh=_h, ss=_s, accent=_accent, name=_set):
            def render():
                img = render_vanilla_icon(tpl, hh, ss)
                d = ImageDraw.Draw(img)
                span = tuple((c[0] / 2, c[1] / 2) for c in VEIN_SPANS[kind])
                draw_glow_veins(d, accent, span, seed=stable_seed((name, kind)) % 999, n=1, spread=1.0)
                return img
            return render
        VANILLA_ICONS[f"{_set}_{_k}"] = _mkboss()

VANILLA_ICONS["soulfire_igniter"] = render_soulfire_igniter

# armour icons for the two mid tiers, same vanilla shapes as Hollowforged
for _tier in ("wraithsteel", "veilsteel"):
    for _k, _t in (("helmet", HELMET_TPL), ("chestplate", CHESTPLATE_TPL),
                   ("leggings", LEGGINGS_TPL), ("boots", BOOTS_TPL)):
        def _mk(tpl=_t, kind=_k, tier=_tier):
            th, ts = TIER_TINTS[tier]
            vein = VEIN_COLORS[tier]
            def render():
                img = render_vanilla_icon(tpl, th, ts)
                d = ImageDraw.Draw(img)
                span = tuple((c[0] / 2, c[1] / 2) for c in VEIN_SPANS[kind])
                draw_glow_veins(d, vein, span, seed=stable_seed((tier, kind)) % 999, n=1, spread=1.0)
                return img
            return render
        VANILLA_ICONS[f"{_tier}_{_k}"] = _mk()

for _kind, _tpl in (
    ("helmet", HELMET_TPL), ("chestplate", CHESTPLATE_TPL),
    ("leggings", LEGGINGS_TPL), ("boots", BOOTS_TPL),
):
    _tint_h, _tint_s = TIER_TINTS["hollowforged"]
    _vein = VEIN_COLORS["hollowforged"]

    def _make(tpl=_tpl, kind=_kind, tint_h=_tint_h, tint_s=_tint_s, vein=_vein):
        def render():
            img = render_vanilla_icon(tpl, tint_h, tint_s)
            d = ImageDraw.Draw(img)
            span = tuple((c[0] / 2, c[1] / 2) for c in VEIN_SPANS[kind])
            draw_glow_veins(d, vein, span, seed=stable_seed(kind) % 999, n=1, spread=1.0)
            return img
        return render

    VANILLA_ICONS[f"hollowforged_{_kind}"] = _make()


# Everything in VANILLA_ICONS (ore-tier scrap/ingots/tools/armor) is
# rendered separately at native 16x16 - see gen_item_icons(). Everything
# below is the "custom stuff dropped by mobs and bosses" the user
# explicitly said should stay unique: still researched against vanilla
# icon conventions (bold flat-shaded silhouette, single dark outline,
# top-left highlight), just not tied to one specific vanilla item's shape.
ITEM_ICONS = {
    "soul_shard": lambda d: draw_shard(d, (140, 220, 210, 255)),
    "ember_dust": lambda d: draw_dust_pile(d, (230, 120, 40, 255)),
    "spectral_dust": lambda d: draw_dust_pile(d, (200, 180, 230, 255)),
    "demon_horn": lambda d: draw_horn(d, (60, 25, 25, 255)),
    "banshee_vocal_cord": lambda d: draw_shard(d, (215, 190, 225, 255)),
    "ember_core": lambda d: draw_gem(d, (255, 130, 40, 255)),
    "ghost_ward_charm": lambda d: draw_charm(d, (150, 230, 210, 255)),
    "spirit_lantern": lambda d: draw_lantern(d),
    "soul_compass": lambda d: draw_compass(d, (150, 230, 210, 255)),
    "journal": lambda d: draw_book(d, (90, 40, 100, 255)),
    "soulfire_igniter": lambda d: draw_igniter(d),
    "hollow_kings_reaper": lambda d: draw_sword(d, (225, 225, 240, 255), (100, 60, 130, 255)),
    "wailing_edge": lambda d: draw_sword(d, (215, 195, 230, 255), (70, 50, 90, 255)),
    "malacodas_fang": lambda d: draw_sword(d, (230, 100, 60, 255), (60, 20, 15, 255)),
    "sigil_hollow_king": lambda d: draw_rune_paper(d, (140, 100, 210, 255)),
    "sigil_weeping_widow": lambda d: draw_rune_paper(d, (200, 140, 220, 255)),
    "sigil_malacoda": lambda d: draw_rune_paper(d, (230, 90, 40, 255)),
    "ember_coal": lambda d: draw_nugget(d, (50, 35, 30, 255)),
    "sentinel_core": lambda d: draw_gem(d, (230, 170, 60, 255)),
    "veilsteel_plating": lambda d: draw_plate(d, (150, 160, 200, 255)),
    "chitin": lambda d: draw_chitin_shard(d, (120, 100, 70, 255)),
    "embered_scale": lambda d: draw_chitin_shard(d, (220, 110, 50, 255)),
    "elk_hide": lambda d: draw_hide(d, (150, 120, 90, 255)),
    "elk_marrow": lambda d: draw_nugget(d, (235, 225, 210, 255)),
    "bat_membrane": lambda d: draw_membrane(d, (70, 55, 80, 220)),
    "toad_mucus": lambda d: draw_dust_pile(d, (150, 220, 120, 255)),
    "glimmershroom_item": lambda d: draw_mushroom_icon(d, (130, 220, 200, 255), (220, 225, 210, 255)),
    "ember_fruit": lambda d: draw_fruit(d, (230, 90, 50, 255)),
    "veil_marrow_stew": lambda d: draw_stew_bowl(d, (190, 170, 140, 255)),
    "featherfall_charm": lambda d: draw_charm(d, (200, 190, 230, 255)),
    "dragon_egg": lambda d: draw_dragon_egg(d, (110, 60, 150, 255)),
}

# boss armour icons are built from the vanilla armour silhouettes below,
# alongside the ore-tier sets - see BOSS_ARMOR_TINTS.


# icons whose shapes are fine-grained single-pixel speckle (dust/powder) -
# supersampling+LANCZOS would blend those isolated pixels down to near
# invisibility, so these draw straight at native resolution instead.
RAW_ICONS = {"ember_dust", "spectral_dust", "toad_mucus"}


def gen_item_icons():
    # Hand-authored 16x16 pixel-art sprites for every bespoke item (see
    # tools/icons.py). These replaced PIL-primitive drawings, which is why
    # the icons used to read as soft blobs instead of item art.
    written = set()
    for name in icons.all_names():
        save(icons.render(name), RP, "textures", "items", f"{name}.png")
        written.add(name)

    # anything still using the old procedural path (none expected) plus the
    # dust icons, which stay native-resolution speckle
    for name, fn in ITEM_ICONS.items():
        if name in written:
            continue
        img = icon_canvas() if name in RAW_ICONS else None
        if img is not None:
            fn(ImageDraw.Draw(img))
        else:
            img = render_icon(fn)
        save(img, RP, "textures", "items", f"{name}.png")
        written.add(name)

    # vanilla-derived gear (ingots, tools, armor) renders at native 16x16
    for name, render in VANILLA_ICONS.items():
        save(render(), RP, "textures", "items", f"{name}.png")
        written.add(name)
    print(f"wrote {len(written)} item icons")


# ---------------------------------------------------------------------------
# Block textures — 16x16 tileable-ish noise textures
# ---------------------------------------------------------------------------


def gen_block_textures():
    blocks = {
        "soulforged_obsidian": (28, 12, 42, 255),
        "ashwood_planks": (74, 55, 50, 255),
        "ashwood_log_side": (58, 42, 38, 255),
        "ashwood_log_top": (90, 68, 58, 255),
        "bonestone": (201, 195, 173, 255),
        "ritual_altar_side": (95, 40, 90, 255),
        "ritual_altar_top": (130, 60, 120, 255),
        "soul_lantern": (244, 230, 184, 255),
        "veil_portal": (58, 6, 6, 255),
        "ember_coal_ore": (70, 45, 35, 255),
        "sunken_bricks": (55, 80, 75, 255),
        "bastion_brick": (70, 42, 40, 255),
        "veil_mud": (55, 58, 42, 255),
        "glimmershroom": (110, 150, 135, 255),
        "spawner_cage": (30, 40, 35, 160),
    }
    for name, color in blocks.items():
        img = noise_fill((16, 16), color, variance=16, seed=stable_seed(name) % 999)
        d = ImageDraw.Draw(img)
        if name == "ember_coal_ore":
            rnd = random.Random(3)
            for _ in range(10):
                x, y = rnd.randint(1, 14), rnd.randint(1, 14)
                d.ellipse([x, y, x + 2, y + 2], fill=(25, 20, 18, 255))
        if name == "soul_lantern":
            d.rectangle([3, 3, 12, 12], fill=(255, 250, 220, 255))
            d.rectangle([0, 0, 15, 15], outline=(120, 100, 60, 255))
        if name == "veil_portal":
            # red rift with hot flecks and darker smoke motes
            rnd = random.Random(9)
            for _ in range(55):
                x, y = rnd.randint(0, 15), rnd.randint(0, 15)
                t = rnd.random()
                if t < 0.45:
                    col = (255, 90, 60, 240)
                elif t < 0.75:
                    col = (200, 30, 25, 220)
                else:
                    col = (70, 55, 55, 200)
                d.point((x, y), fill=col)
        if name.startswith("ritual_altar") or name == "soulforged_obsidian":
            for i in range(0, 16, 4):
                d.line([(i, 0), (i, 15)], fill=shade(color, -20))
        if name in ("sunken_bricks", "bastion_brick"):
            for y in range(0, 16, 4):
                d.line([(0, y), (15, y)], fill=shade(color, -40))
            for x in range(0, 16, 8):
                d.line([(x, 0), (x, 15)], fill=shade(color, -40))
        if name == "glimmershroom":
            rnd = random.Random(5)
            for _ in range(14):
                x, y = rnd.randint(0, 15), rnd.randint(0, 15)
                d.ellipse([x, y, x + 1, y + 1], fill=(210, 250, 235, 255))
        if name == "spawner_cage":
            for x in range(0, 16, 3):
                d.line([(x, 0), (x, 15)], fill=(15, 20, 18, 200), width=1)
            for y in range(0, 16, 3):
                d.line([(0, y), (15, y)], fill=(15, 20, 18, 200), width=1)
        save(img, RP, "textures", "blocks", f"{name}.png")

    # ore-tier blocks: vanilla ore-block style (colored flecks in a stone
    # matrix, like iron_ore/diamond_ore) rather than a custom crack motif,
    # so they read as "an ore block" at a glance.
    ore_tpls = {
        "wraithsteel_ore": ORE_BLOCK_TPL,
        "veilsteel_ore": DENSE_ORE_BLOCK_TPL,
        "hollowforged_ore": DENSE_ORE_BLOCK_TPL,
    }
    for name, tpl in ore_tpls.items():
        fleck_h, fleck_s = ORE_FLECK_TINTS[name]
        stone_h, stone_s = BONESTONE_STONE_TINT
        img = render_vanilla_ore_block(tpl, fleck_h, fleck_s, stone_h, stone_s)
        save(img, RP, "textures", "blocks", f"{name}.png")

    print(f"wrote {len(blocks) + len(ore_tpls)} block textures")


# ---------------------------------------------------------------------------
# Particle textures — small glow sprites
# ---------------------------------------------------------------------------
# New effects reuse an existing sprite where the shape is the same and only
# the colour ramp differs - the tinting component recolours them at runtime.
PARTICLE_TEXTURE = {
    "portal_smoke": "smoke_puff",
    "boss_rage_particle": "hollow_king_pulse_particle",
    "soul_burst_particle": "soul_wisp_particle",
}


def gen_particle_textures():
    particles = {
        "soul_wisp_particle": (220, 250, 220, 255),
        "banshee_scream_particle": (230, 210, 240, 255),
        "ember_particle": (255, 140, 40, 255),
        "hollow_king_pulse_particle": (200, 200, 230, 255),
        "shade_teleport_particle": (90, 90, 140, 255),
        "portal_particle": (255, 120, 90, 255),
        "smoke_puff": (120, 110, 110, 255),
    }
    for name, color in particles.items():
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for r in range(4, 0, -1):
            t = r / 4
            col = tuple(int(color[i] * (1 - t) + 255 * t) if i < 3 else int(255 * (r / 4)) for i in range(4))
            d.ellipse([4 - r, 4 - r, 4 + r, 4 + r], fill=col)
        save(img, RP, "textures", "particle", f"{name}.png")
    print(f"wrote {len(particles)} particle textures")


# ---------------------------------------------------------------------------
# UI icons (journal/shop button glyphs used in forms via raw text, so only
# a couple of simple standalone UI textures are needed: item icon on the
# inventory tab and a small emblem for the pack's loading screen use)
# ---------------------------------------------------------------------------
def gen_ui_textures():
    img = render_icon(lambda d: draw_book(d, (90, 40, 100, 255)))
    save(img, RP, "textures", "ui", "hollowveil_journal_button.png")


# ---------------------------------------------------------------------------
# Texture atlases (item_texture.json / terrain_texture.json) — generated by
# scanning what's actually on disk so they can never drift out of sync.
# ---------------------------------------------------------------------------
def gen_texture_atlases():
    import json as _json

    item_dir = os.path.join(RP, "textures", "items")
    items = sorted(f[:-4] for f in os.listdir(item_dir) if f.endswith(".png"))
    item_atlas = {
        "resource_pack_name": "hollowveil_rp",
        "texture_name": "atlas.items",
        "texture_data": {name: {"textures": f"textures/items/{name}"} for name in items},
    }
    with open(os.path.join(RP, "textures", "item_texture.json"), "w") as f:
        _json.dump(item_atlas, f, indent=2)

    block_dir = os.path.join(RP, "textures", "blocks")
    blocks = sorted(f[:-4] for f in os.listdir(block_dir) if f.endswith(".png"))
    terrain_atlas = {
        "resource_pack_name": "hollowveil_rp",
        "texture_name": "atlas.terrain",
        "padding": 8,
        "num_mip_levels": 4,
        "texture_data": {name: {"textures": f"textures/blocks/{name}"} for name in blocks},
    }
    with open(os.path.join(RP, "textures", "terrain_texture.json"), "w") as f:
        _json.dump(terrain_atlas, f, indent=2)

    print(f"wrote item_texture.json ({len(items)} entries) and terrain_texture.json ({len(blocks)} entries)")


# ---------------------------------------------------------------------------
# Particle effect definitions (RP/particles) matching the sprites above
# ---------------------------------------------------------------------------
def gen_particle_definitions():
    import json as _json

    # NOTE ON SCHEMA: `minecraft:emitter_shape_point` takes `direction` as an
    # ARRAY of three Molang expressions. The string "outwards" is only valid
    # on the box/sphere emitters. Passing the string here made every one of
    # these effects fail to load with
    #   EmitterShapePointComponent | direction | error reading array
    # which is why nothing in the pack appeared to emit particles at all.
    # These now use a sphere emitter with "outwards", verified against
    # vanilla cherry_leaves_particle (outwards) and basic_flame (sphere).
    specs = {
        "soul_wisp_particle": dict(count=14, life="Math.random(0.7, 1.4)", speed=1.1, radius=0.35,
                                   size=0.14, drag=1.2, accel=[0, 1.4, 0],
                                   tint=[(0.0, "#c8ffe6"), (1.0, "#2f7f66")]),
        "banshee_scream_particle": dict(count=44, life="Math.random(0.35, 0.7)", speed=4.2, radius=0.2,
                                        size=0.22, drag=2.4, accel=[0, 0.4, 0],
                                        tint=[(0.0, "#ffffff"), (0.35, "#e2c8ff"), (1.0, "#6a3f8f")]),
        "ember_particle": dict(count=20, life="Math.random(0.5, 1.1)", speed=1.6, radius=0.3,
                               size=0.13, drag=0.9, accel=[0, 2.2, 0],
                               tint=[(0.0, "#fff2b0"), (0.3, "#ff9430"), (1.0, "#7a1c05")]),
        "hollow_king_pulse_particle": dict(count=60, life="Math.random(0.5, 0.9)", speed=5.5, radius=0.5,
                                           size=0.26, drag=2.8, accel=[0, 0.2, 0],
                                           tint=[(0.0, "#ffffff"), (0.4, "#b9c6ff"), (1.0, "#2a2f6b")]),
        "shade_teleport_particle": dict(count=26, life="Math.random(0.4, 0.8)", speed=1.8, radius=0.25,
                                        size=0.19, drag=1.6, accel=[0, -1.2, 0],
                                        tint=[(0.0, "#8f8fd6"), (1.0, "#12122b")]),
        "portal_particle": dict(count=18, life="Math.random(0.9, 1.8)", speed=0.9, radius=0.6,
                                size=0.15, drag=0.6, accel=[0, 0.9, 0],
                                tint=[(0.0, "#ffffff"), (0.5, "#ff5a4a"), (1.0, "#3d0505")]),
        # the new red portal's lazy smoke column
        "portal_smoke": dict(count=10, life="Math.random(1.4, 2.6)", speed=0.5, radius=0.55,
                             size=0.3, drag=0.4, accel=[0, 1.1, 0],
                             tint=[(0.0, "#4a3a3a"), (0.5, "#2a1e1e"), (1.0, "#100b0b")]),
        # boss telegraphs
        "boss_rage_particle": dict(count=70, life="Math.random(0.6, 1.2)", speed=6.5, radius=0.6,
                                   size=0.3, drag=2.2, accel=[0, 1.6, 0],
                                   tint=[(0.0, "#ffffff"), (0.25, "#ff4040"), (1.0, "#3a0000")]),
        "soul_burst_particle": dict(count=50, life="Math.random(0.5, 1.0)", speed=4.0, radius=0.4,
                                    size=0.2, drag=2.0, accel=[0, 2.4, 0],
                                    tint=[(0.0, "#eafff6"), (0.4, "#63e6bf"), (1.0, "#0d3b2e")]),
    }

    for name, s in specs.items():
        gradient = {str(stop): color for stop, color in s["tint"]}
        data = {
            "format_version": "1.10.0",
            "particle_effect": {
                "description": {
                    "identifier": f"hollowveil:{name}",
                    "basic_render_parameters": {
                        "material": "particles_alpha",
                        "texture": f"textures/particle/{PARTICLE_TEXTURE.get(name, name)}",
                    },
                },
                "components": {
                    "minecraft:emitter_rate_instant": {"num_particles": s["count"]},
                    "minecraft:emitter_lifetime_once": {"active_time": 0.25},
                    "minecraft:emitter_shape_sphere": {
                        "offset": [0, 0.2, 0],
                        "radius": s["radius"],
                        "direction": "outwards",
                    },
                    "minecraft:particle_lifetime_expression": {"max_lifetime": s["life"]},
                    "minecraft:particle_initial_speed": s["speed"],
                    "minecraft:particle_motion_dynamic": {
                        "linear_drag_coefficient": s["drag"],
                        "linear_acceleration": s["accel"],
                    },
                    # shrink over life so bursts dissipate instead of popping out
                    "minecraft:particle_appearance_billboard": {
                        "size": [
                            f"{s['size']} * (1.0 - variable.particle_age / variable.particle_lifetime)",
                            f"{s['size']} * (1.0 - variable.particle_age / variable.particle_lifetime)",
                        ],
                        "facing_camera_mode": "lookat_xyz",
                        "uv": {"texture_width": 8, "texture_height": 8, "uv": [0, 0], "uv_size": [8, 8]},
                    },
                    # colour ramp across the particle's life - this is what
                    # makes a burst read as fire/soul/void rather than a
                    # cloud of identical dots
                    "minecraft:particle_appearance_tinting": {
                        "color": {
                            "interpolant": "variable.particle_age / variable.particle_lifetime",
                            "gradient": gradient,
                        }
                    },
                },
            },
        }
        p = os.path.join(RP, "particles", f"{name}.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            _json.dump(data, f, indent=2)
    print(f"wrote {len(specs)} particle effect definitions")


# Vanilla armor-layer coverage/shading maps, extracted from Mojang's
# bedrock-samples (textures/models/armor/diamond_1 + diamond_2). Each
# character is one pixel: "." = transparent, "0"-"9" = relative
# lightness. As with the item icons this stores only the derived
# shape/shading, not Mojang color data - render_armor_layer() recolors
# it into each set's own palette. The previous hand-rolled version
# painted every box-UV face solid, which is why worn armor showed up
# in-game as huge featureless white boxes instead of armor.


# ---------------------------------------------------------------------------
# Armour trims
# ---------------------------------------------------------------------------
# Each set carries its own trim: a band that wraps the helmet, chest, arms,
# waist, thighs and boot tops, plus a crest on the chest. The bands sit on
# rows read off the actual 64x32 armour layer maps (rendered with a coordinate
# grid and checked by eye rather than guessed), and only ever paint on pixels
# the vanilla map already marks solid, so a trim can never bleed off the model.
#
# "Glowing" here is contrast, not a shader: Bedrock exposes no emissive
# material for armour attachables, and shipping a custom .material file would
# override vanilla's and risk breaking every other entity. What it does
# instead is what pixel art has always done - a saturated accent with a
# near-white core, on a dark suit, in a dark dimension. Paired with the
# enchanted glint every set carries, it reads as lit.

# (row, x-from, x-to) bands per layer, from the armour layer maps.
TRIM_BANDS = {
    1: [
        (10, 0, 32),    # helmet, all four faces
        (22, 16, 40),   # chest
        (22, 40, 56),   # upper arms
        (30, 16, 40),   # tunic hem
        (30, 40, 56),   # cuffs
        (29, 0, 16),    # boot tops
    ],
    2: [
        (29, 24, 40),   # belt
        (23, 0, 16),    # thigh
        (27, 0, 16),    # knee
    ],
}

# Where the crest goes: the front of the chest on layer 1.
TRIM_CREST_ORIGIN = (20, 24)


def trim_rivets(x):
    """Solid band, bright rivet every fourth pixel. Plain forge work."""
    return 2 if x % 4 == 1 else 1


def trim_circuit(x):
    """Dashes with a tick that alternates above and below the line."""
    if x % 4 == 3:
        return 0
    return 2 if x % 8 == 0 else 1


def trim_molten(x):
    """A cracked seam - broken, with the hot core showing through the gaps."""
    if x % 7 in (3, 4):
        return 0
    return 2 if x % 7 in (2, 5) else 1


def trim_chevron(x):
    """Repeating arrowheads."""
    return 2 if x % 3 == 0 else (1 if x % 3 == 1 else 0)


def trim_tears(x):
    """A mourning band: long dashes, a drop hanging every fifth pixel."""
    if x % 5 == 4:
        return 0
    return 2 if x % 10 == 2 else 1


def trim_sawtooth(x):
    """Teeth. Reads as flame at a glance, which is the idea."""
    return 2 if x % 2 == 0 else 1


TRIM_PATTERNS = {
    "rivets": trim_rivets, "circuit": trim_circuit, "molten": trim_molten,
    "chevron": trim_chevron, "tears": trim_tears, "sawtooth": trim_sawtooth,
}

# A 5x5 crest per set, drawn on the chest. "." skips, "o" is the accent,
# "@" is the hot core. Each one is the set's own mark: a warding eye, a
# tear, a horned skull, a crown, a rune, a flame.
TRIM_CRESTS = {
    "wraithsteel": [
        ".o@o.",
        "o@.@o",
        "@.@.@",
        "o@.@o",
        ".o@o.",
    ],
    "veilsteel": [
        "..@..",
        ".o@o.",
        "@@.@@",
        ".o@o.",
        "..@..",
    ],
    "hollowforged": [
        "@.@.@",
        ".@@@.",
        "@@.@@",
        ".@@@.",
        "@.@.@",
    ],
    "spectral_regalia": [
        "@.@.@",
        "@o@o@",
        "@@@@@",
        ".@@@.",
        "..@..",
    ],
    "mourners_shroud": [
        "..@..",
        ".o@o.",
        ".@@@.",
        ".o@o.",
        "..@..",
    ],
    "ashen_demonplate": [
        "@...@",
        ".@.@.",
        "..@..",
        ".@o@.",
        "@.@.@",
    ],
}


def _hot(color):
    """The core colour of a trim: the accent pushed toward white so the band
    has a lit centre instead of being one flat stripe."""
    return tuple(min(255, int(c + (255 - c) * 0.62)) if i < 3 else 255
                 for i, c in enumerate(color))


def paint_trim(img, rows, spec, layer):
    """Bands plus crest, on solid pixels only."""
    w, h = img.size
    px = img.load()
    accent = spec["accent"]
    hot = _hot(accent)
    pattern = TRIM_PATTERNS[spec["trim"]]

    def solid(x, y):
        return 0 <= x < w and 0 <= y < h and rows[y][x] != "."

    for (y, x0, x1) in TRIM_BANDS[layer]:
        for x in range(x0, min(x1, w)):
            if not solid(x, y):
                continue
            mark = pattern(x)
            if mark:
                px[x, y] = hot if mark == 2 else accent

    if layer == 1:
        crest = TRIM_CRESTS.get(spec["name"])
        if crest:
            ox, oy = TRIM_CREST_ORIGIN
            for cy, line in enumerate(crest):
                for cx, ch in enumerate(line):
                    if ch == "." or not solid(ox + cx, oy + cy):
                        continue
                    px[ox + cx, oy + cy] = hot if ch == "@" else accent
    return img


ARMOR_LAYER_1_TPL = """
........65566655................................................
........69988776................................................
........69677776................................................
........58766676................................................
........58767775................................................
........57767786................................................
........67777885................................................
........66556665................................................
66556656666655666566556666665665................................
69877776597777656777789669987776................................
58766785565765655876678569776676................................
576666556..96..55566667558666675................................
6655.......66.......556657677786................................
........................65778865................................
..........................5665..................................
................................................................
........6566................................6665................
........5765................................6986................
........6776................................5866................
........6656................................5555................
................665566....66665566....666566556655665665........
................6976686..5766976685665956986689669866985........
................5876598559765876698778756875668567756766........
................677569778775677559777766577657........76........
................677668777776677668777676565556........65........
................576657777776576667777776........................
5566556656656566577657777776577657776675........................
6986598669856985676567777775676557777776........................
6776677567765776665666777766665667766676........................
5675676657765676.....567765......665565.........................
6786687657866785......5555......................................
5665565555655566................................................
"""

ARMOR_LAYER_2_TPL = """
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
................................................................
....6656........................................................
....6975........................................................
....5765........................................................
....5555........................................................
6665566566556655................................................
6675677567766765................................................
5676677657755776................................................
6776577567765776................................................
6775676667766776................................................
5675667657666766................................................
6766576567756675................................................
6776666656766775665566556656565566656555........................
6566566655665566697669987776697569998776........................
................576658776675676658776676........................
................667567666776567657666775........................
................566557765665566557765666........................
"""


def render_armor_layer(tpl, spec, layer):
    """Renders one worn-armour layer for a set.

    This used to be a flat hue swap of the vanilla map, so all four sets were
    the same armour in different colours. Each set now gets its own surface
    treatment painted on top of the vanilla shape: the shape and shading come
    from the vanilla layer (so it fits the player model exactly and keeps its
    transparency), everything else is the set's own."""
    rows = [r for r in tpl.strip("\n").split("\n")]
    h, w = len(rows), len(rows[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    tint_h, tint_s = spec["tint"]
    lscale = spec.get("lscale", 1.0)
    lbias = spec.get("lbias", 0.0)
    style = spec["style"]
    accent = spec["accent"]
    rnd = random.Random(stable_seed((spec["name"], layer)))

    def solid(x, y):
        return 0 <= x < w and 0 <= y < h and rows[y][x] != "."

    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            l = max(0.04, min(0.97, (int(ch) / 10 + 0.05) * lscale + lbias))
            hue, sat = tint_h, tint_s
            edge = not (solid(x - 1, y) and solid(x + 1, y) and solid(x, y - 1) and solid(x, y + 1))

            if style == "plate":
                # riveted banding: darker seams every few rows, bright rivets
                if y % 4 == 0:
                    l *= 0.74
                if y % 4 == 2 and x % 5 == 1:
                    l = min(0.98, l * 1.5)
            elif style == "cloth":
                # vertical folds, softer and less reflective
                if x % 3 == 0:
                    l *= 0.82
                elif x % 3 == 1:
                    l = min(0.98, l * 1.10)
                sat = min(1.0, sat * 1.15)
            elif style == "charred":
                # scorched blotches with ember flecks in the cracks
                if rnd.random() < 0.16:
                    l *= 0.6
                if rnd.random() < 0.05:
                    hue, sat, l = 0.06, 0.95, min(0.95, l * 1.9)
            elif style == "forged":
                # hammered facets plus hairline glowing cracks
                if (x + y) % 5 == 0:
                    l = min(0.98, l * 1.18)
                if (x * 3 + y * 5) % 23 == 0:
                    hue, sat, l = 0.0, 0.9, min(0.95, l * 1.6)

            # every set gets a dark outline so it reads against skin
            if edge:
                l *= 0.55

            r, g, b = colorsys.hls_to_rgb(hue, l, sat)
            px[x, y] = (int(r * 255), int(g * 255), int(b * 255), 255)

    return paint_trim(img, rows, spec, layer)


# Each set is a distinct suit, not a recolour: its own hue, brightness range,
# surface treatment and trim.
ARMOR_SETS = {
    "spectral_regalia": {
        "name": "spectral_regalia", "trim": "chevron", "tint": (0.52, 0.30), "accent": (150, 245, 255, 255),
        "lscale": 0.62, "lbias": -0.02, "style": "cloth",
    },
    "mourners_shroud": {
        "name": "mourners_shroud", "trim": "tears", "tint": (0.78, 0.38), "accent": (248, 165, 255, 255),
        "lscale": 0.55, "lbias": -0.03, "style": "cloth",
    },
    "ashen_demonplate": {
        "name": "ashen_demonplate", "trim": "sawtooth", "tint": (0.02, 0.60), "accent": (255, 140, 60, 255),
        "lscale": 0.52, "lbias": -0.04, "style": "charred",
    },
    "hollowforged": {
        "name": "hollowforged", "trim": "molten", "tint": (0.0, 0.06), "accent": (255, 60, 50, 255),
        "lscale": 1.12, "lbias": 0.05, "style": "forged",
    },
    "veilsteel": {
        "name": "veilsteel", "trim": "circuit", "tint": (0.60, 0.55), "accent": (120, 200, 255, 255),
        "lscale": 0.55, "lbias": -0.02, "style": "plate",
    },
    "wraithsteel": {
        "name": "wraithsteel", "trim": "rivets", "tint": (0.055, 0.85), "accent": (255, 232, 160, 255),
        "lscale": 0.66, "lbias": -0.02, "style": "plate",
    },
}

def gen_armor_layer_textures():
    for name, spec in ARMOR_SETS.items():
        for layer, tpl in ((1, ARMOR_LAYER_1_TPL), (2, ARMOR_LAYER_2_TPL)):
            img = render_armor_layer(tpl, spec, layer)
            save(img, RP, "textures", "models", "armor", f"{name}_{layer}.png")
    print(f"wrote {len(ARMOR_SETS) * 2} armor layer textures")


def gen_armor_attachables():
    import json as _json

    slot_geometry = {
        "helmet": ("geometry.player.armor.helmet", 1, "helmet_layer_visible", "animation.armor.helmet.offset"),
        "chestplate": ("geometry.player.armor.chestplate", 1, "chest_layer_visible", "animation.armor.chestplate.offset"),
        "leggings": ("geometry.player.armor.leggings", 2, "leg_layer_visible", "animation.armor.leggings.offset"),
        "boots": ("geometry.player.armor.boots", 1, "boot_layer_visible", "animation.armor.boots.offset"),
    }
    count = 0
    for name in ARMOR_SETS:
        for slot, (geometry, layer, visible_var, anim_id) in slot_geometry.items():
            item_id = f"hollowveil:{name}_{slot}"
            data = {
                "format_version": "1.10.0",
                "minecraft:attachable": {
                    "description": {
                        "identifier": f"{item_id}.player",
                        "item": {item_id: "query.owner_identifier == 'minecraft:player'"},
                        "materials": {"default": "armor", "enchanted": "armor_enchanted"},
                        "textures": {
                            "default": f"textures/models/armor/{name}_{layer}",
                            "enchanted": "textures/misc/enchanted_actor_glint",
                        },
                        "geometry": {"default": geometry},
                        "scripts": {
                            "parent_setup": f"variable.{visible_var} = 0.0;",
                            "animate": ["offset"],
                        },
                        "animations": {"offset": anim_id},
                        "render_controllers": ["controller.render.armor"],
                    }
                },
            }
            p = os.path.join(RP, "attachables", f"{name}_{slot}.player.json")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                _json.dump(data, f, indent=2)
            count += 1
    print(f"wrote {count} armor attachables")


if __name__ == "__main__":
    gen_pack_icons()
    gen_item_icons()
    gen_block_textures()
    gen_particle_textures()
    gen_particle_definitions()
    gen_ui_textures()
    gen_armor_layer_textures()
    gen_armor_attachables()
    gen_texture_atlases()
    print("Hollow Veil asset generator ready.")
