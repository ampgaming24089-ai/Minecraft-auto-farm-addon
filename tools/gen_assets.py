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
import math
import random
import os

from PIL import Image, ImageDraw, ImageFilter

import boxuv

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
    "wraith": (225, 255, 245, 255), "banshee": (255, 245, 255, 255), "shade": (150, 150, 220, 255),
    "hollow_king": (225, 255, 245, 255), "weeping_widow": (255, 245, 255, 255), "city_wraithguard": (200, 230, 255, 255),
    "hellhound": (255, 170, 60, 255), "imp": (255, 170, 60, 255), "malacoda": (255, 190, 80, 255),
    "ashen_whelp": (255, 170, 60, 255), "bastion_sentinel": (255, 190, 100, 255),
    "occultist": (255, 210, 120, 255), "fallen_knight": (200, 60, 55, 255),
    "ashwing_bat": (210, 130, 230, 255), "bonehide_elk": (40, 30, 25, 255), "marrow_crawler": (210, 60, 50, 255),
    "veil_dragon": (255, 230, 150, 255),
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
    rnd = random.Random(hash(color) % 1000)
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


def tiered_tool_icon(kind, blade, hilt, vein_color=None, seed=1):
    """Factory for the wraithsteel/veilsteel/hollowforged tool icons: same
    base shapes as draw_sword/draw_pickaxe/draw_axe, optionally with a
    glowing vein accent for the new-ore-tier materials."""
    def render(d):
        if kind == "sword":
            draw_sword(d, blade, hilt)
        elif kind == "pickaxe":
            draw_pickaxe(d, blade, hilt)
        elif kind == "axe":
            draw_axe(d, blade, hilt)
        if vein_color:
            draw_glow_veins(d, vein_color, VEIN_SPANS[kind], seed=seed, n=2)
    return render


def tiered_nugget_icon(color, vein_color=None, seed=1):
    def render(d):
        draw_nugget(d, color)
        if vein_color:
            draw_glow_veins(d, vein_color, VEIN_SPANS["nugget"], seed=seed, n=1)
    return render


def with_veins(fn, vein_color, kind, seed=1, n=2):
    def render(d):
        fn(d)
        draw_glow_veins(d, vein_color, VEIN_SPANS[kind], seed=seed, n=n)
    return render


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
    rnd = random.Random(hash(accent))
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
    rnd = random.Random(hash(color))
    for _ in range(8):
        x = rnd.randint(11, 21)
        y = rnd.randint(9, 24)
        draw.ellipse([x, y, x + 2, y + 2], fill=shade(color, 70))
    draw.ellipse([12, 9, 16, 13], fill=shade(color, 90))


def draw_charm(draw, accent):
    draw.ellipse([10, 4, 22, 10], outline=(120, 110, 90, 255), width=2)
    draw.polygon([(9, 12), (23, 12), (16, 28)], fill=(70, 70, 80, 255), outline=shade(accent, -60))
    draw.ellipse([12, 15, 20, 23], fill=accent, outline=shade(accent, -70))


ITEM_ICONS = {
    "soul_shard": lambda d: draw_shard(d, (140, 220, 210, 255)),
    "ember_dust": lambda d: draw_dust_pile(d, (230, 120, 40, 255)),
    "spectral_dust": lambda d: draw_dust_pile(d, (200, 180, 230, 255)),
    "demon_horn": lambda d: draw_horn(d, (60, 25, 25, 255)),
    "banshee_vocal_cord": lambda d: draw_shard(d, (215, 190, 225, 255)),
    # lava-look, glowing orange/red cracks - the "diamond-equivalent" tier
    "wraithsteel_scrap": tiered_nugget_icon((190, 80, 30, 255), (255, 170, 70, 255), seed=201),
    "wraithsteel_ingot": tiered_nugget_icon((225, 105, 40, 255), (255, 190, 90, 255), seed=202),
    "ember_core": lambda d: draw_gem(d, (255, 130, 40, 255)),
    "ghost_ward_charm": lambda d: draw_charm(d, (150, 230, 210, 255)),
    "spirit_lantern": lambda d: draw_lantern(d),
    "soul_compass": lambda d: draw_compass(d, (150, 230, 210, 255)),
    "journal": lambda d: draw_book(d, (90, 40, 100, 255)),
    "soulfire_igniter": lambda d: draw_igniter(d),
    "wraithsteel_sword": tiered_tool_icon("sword", (225, 105, 40, 255), (45, 32, 28, 255), (255, 190, 90, 255), seed=203),
    "wraithsteel_pickaxe": tiered_tool_icon("pickaxe", (225, 105, 40, 255), (45, 32, 28, 255), (255, 190, 90, 255), seed=204),
    "wraithsteel_axe": tiered_tool_icon("axe", (225, 105, 40, 255), (45, 32, 28, 255), (255, 190, 90, 255), seed=205),
    "hollow_kings_reaper": lambda d: draw_sword(d, (225, 225, 240, 255), (100, 60, 130, 255)),
    "wailing_edge": lambda d: draw_sword(d, (215, 195, 230, 255), (70, 50, 90, 255)),
    "malacodas_fang": lambda d: draw_sword(d, (230, 100, 60, 255), (60, 20, 15, 255)),
    "sigil_hollow_king": lambda d: draw_rune_paper(d, (140, 100, 210, 255)),
    "sigil_weeping_widow": lambda d: draw_rune_paper(d, (200, 140, 220, 255)),
    "sigil_malacoda": lambda d: draw_rune_paper(d, (230, 90, 40, 255)),
    # solid black, glowing blue cracks + blue edge - the "netherite-equivalent" tier
    "veilsteel_scrap": tiered_nugget_icon((28, 30, 42, 255), (80, 165, 255, 255), seed=211),
    "veilsteel_ingot": tiered_nugget_icon((22, 24, 34, 255), (100, 180, 255, 255), seed=212),
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
    "veilsteel_sword": tiered_tool_icon("sword", (26, 28, 38, 255), (60, 62, 74, 255), (90, 175, 255, 255), seed=213),
    "veilsteel_pickaxe": tiered_tool_icon("pickaxe", (26, 28, 38, 255), (60, 62, 74, 255), (90, 175, 255, 255), seed=214),
    "veilsteel_axe": tiered_tool_icon("axe", (26, 28, 38, 255), (60, 62, 74, 255), (90, 175, 255, 255), seed=215),
    "featherfall_charm": lambda d: draw_charm(d, (200, 190, 230, 255)),
    "dragon_egg": lambda d: draw_dragon_egg(d, (110, 60, 150, 255)),
    # white, glowing red cracks + red edge - exceeds the netherite-equivalent tier
    "hollowforged_scrap": tiered_nugget_icon((225, 220, 210, 255), (255, 70, 60, 255), seed=221),
    "hollowforged_ingot": tiered_nugget_icon((240, 237, 230, 255), (255, 60, 50, 255), seed=222),
    "hollowforged_sword": tiered_tool_icon("sword", (235, 232, 224, 255), (70, 30, 28, 255), (255, 60, 50, 255), seed=223),
    "hollowforged_pickaxe": tiered_tool_icon("pickaxe", (235, 232, 224, 255), (70, 30, 28, 255), (255, 60, 50, 255), seed=224),
    "hollowforged_axe": tiered_tool_icon("axe", (235, 232, 224, 255), (70, 30, 28, 255), (255, 60, 50, 255), seed=225),
    "hollowforged_helmet": with_veins(lambda d: draw_helmet(d, (235, 232, 224, 255)), (255, 60, 50, 255), "helmet", seed=226, n=1),
    "hollowforged_chestplate": with_veins(lambda d: draw_chestplate(d, (235, 232, 224, 255)), (255, 60, 50, 255), "chestplate", seed=227),
    "hollowforged_leggings": with_veins(lambda d: draw_leggings(d, (235, 232, 224, 255)), (255, 60, 50, 255), "leggings", seed=228, n=1),
    "hollowforged_boots": with_veins(lambda d: draw_boots(d, (235, 232, 224, 255)), (255, 60, 50, 255), "boots", seed=229, n=1),
}

for setname, hcol, ccol, lcol, bcol in [
    ("spectral_regalia", (225, 225, 235, 255), (200, 200, 220, 255), (190, 190, 215, 255), (180, 180, 205, 255)),
    ("mourners_shroud", (210, 195, 225, 255), (185, 165, 205, 255), (170, 150, 195, 255), (160, 140, 185, 255)),
    ("ashen_demonplate", (120, 40, 30, 255), (100, 30, 22, 255), (90, 25, 18, 255), (80, 20, 15, 255)),
]:
    ITEM_ICONS[f"{setname}_helmet"] = (lambda c: (lambda d: draw_helmet(d, c)))(hcol)
    ITEM_ICONS[f"{setname}_chestplate"] = (lambda c: (lambda d: draw_chestplate(d, c)))(ccol)
    ITEM_ICONS[f"{setname}_leggings"] = (lambda c: (lambda d: draw_leggings(d, c)))(lcol)
    ITEM_ICONS[f"{setname}_boots"] = (lambda c: (lambda d: draw_boots(d, c)))(bcol)


# icons whose shapes are fine-grained single-pixel speckle (dust/powder) -
# supersampling+LANCZOS would blend those isolated pixels down to near
# invisibility, so these draw straight at native resolution instead.
RAW_ICONS = {"ember_dust", "spectral_dust", "toad_mucus"}


def gen_item_icons():
    for name, fn in ITEM_ICONS.items():
        if name in RAW_ICONS:
            img = icon_canvas()
            fn(ImageDraw.Draw(img))
        else:
            img = render_icon(fn)
        save(img, RP, "textures", "items", f"{name}.png")
    print(f"wrote {len(ITEM_ICONS)} item icons")


# ---------------------------------------------------------------------------
# Block textures — 16x16 tileable-ish noise textures
# ---------------------------------------------------------------------------
def draw_ore_cracks(d, seed, crack_color, edge_glow=None):
    """A branching crack line with a dim halo + bright glowing core, plus an
    optional glowing border - used for the three named-ore-tier looks
    (lava/orange, black+blue, white+red)."""
    rnd = random.Random(seed)
    for _ in range(rnd.randint(2, 3)):
        x, y = rnd.randint(2, 13), rnd.randint(2, 13)
        pts = [(x, y)]
        for _ in range(rnd.randint(3, 5)):
            x = max(0, min(15, x + rnd.randint(-3, 3)))
            y = max(0, min(15, y + rnd.randint(-3, 3)))
            pts.append((x, y))
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=shade(crack_color, -50), width=2)
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=crack_color, width=1)
    if edge_glow:
        d.rectangle([0, 0, 15, 15], outline=edge_glow)


def gen_block_textures():
    blocks = {
        "soulforged_obsidian": (28, 12, 42, 255),
        "ashwood_planks": (74, 55, 50, 255),
        "ashwood_log_side": (58, 42, 38, 255),
        "ashwood_log_top": (90, 68, 58, 255),
        "bonestone": (201, 195, 173, 255),
        # lava-rock base; glowing orange/red cracks painted in below
        "wraithsteel_ore": (55, 32, 24, 255),
        "ritual_altar_side": (95, 40, 90, 255),
        "ritual_altar_top": (130, 60, 120, 255),
        "soul_lantern": (244, 230, 184, 255),
        "veil_portal": (10, 10, 14, 255),
        # solid black base; glowing blue cracks + blue edge glow painted in below
        "veilsteel_ore": (20, 20, 26, 255),
        "ember_coal_ore": (70, 45, 35, 255),
        # off-white/bone base; glowing red cracks + red edge glow painted in below
        "hollowforged_ore": (222, 218, 210, 255),
        "sunken_bricks": (55, 80, 75, 255),
        "bastion_brick": (70, 42, 40, 255),
        "veil_mud": (55, 58, 42, 255),
        "glimmershroom": (110, 150, 135, 255),
        "spawner_cage": (30, 40, 35, 160),
    }
    for name, color in blocks.items():
        img = noise_fill((16, 16), color, variance=16, seed=hash(name) % 999)
        d = ImageDraw.Draw(img)
        if name == "wraithsteel_ore":
            draw_ore_cracks(d, 11, (255, 130, 40, 255))
        if name == "veilsteel_ore":
            draw_ore_cracks(d, 22, (70, 150, 255, 255), edge_glow=(60, 140, 255, 255))
        if name == "hollowforged_ore":
            draw_ore_cracks(d, 33, (255, 60, 50, 255), edge_glow=(230, 40, 35, 255))
        if name == "ember_coal_ore":
            rnd = random.Random(3)
            for _ in range(10):
                x, y = rnd.randint(1, 14), rnd.randint(1, 14)
                d.ellipse([x, y, x + 2, y + 2], fill=(25, 20, 18, 255))
        if name == "soul_lantern":
            d.rectangle([3, 3, 12, 12], fill=(255, 250, 220, 255))
            d.rectangle([0, 0, 15, 15], outline=(120, 100, 60, 255))
        if name == "veil_portal":
            rnd = random.Random(9)
            for _ in range(45):
                x, y = rnd.randint(0, 15), rnd.randint(0, 15)
                t = rnd.random()
                col = (255, 255, 255, 235) if t < 0.6 else (180, 190, 220, 200)
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
    print(f"wrote {len(blocks)} block textures")


# ---------------------------------------------------------------------------
# Particle textures — small glow sprites
# ---------------------------------------------------------------------------
def gen_particle_textures():
    particles = {
        "soul_wisp_particle": (220, 250, 220, 255),
        "banshee_scream_particle": (230, 210, 240, 255),
        "ember_particle": (255, 140, 40, 255),
        "hollow_king_pulse_particle": (200, 200, 230, 255),
        "shade_teleport_particle": (90, 90, 140, 255),
        "portal_particle": (235, 235, 245, 255),
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

    specs = {
        "soul_wisp_particle": {"speed": 0.8, "life": 0.8, "size": 0.12, "count": 8},
        "banshee_scream_particle": {"speed": 1.6, "life": 0.5, "size": 0.2, "count": 14},
        "ember_particle": {"speed": 1.0, "life": 0.6, "size": 0.15, "count": 10},
        "hollow_king_pulse_particle": {"speed": 1.8, "life": 0.7, "size": 0.25, "count": 20},
        "shade_teleport_particle": {"speed": 0.6, "life": 0.5, "size": 0.18, "count": 12},
        "portal_particle": {"speed": 0.5, "life": 1.0, "size": 0.15, "count": 6},
    }
    for name, s in specs.items():
        data = {
            "format_version": "1.10.0",
            "particle_effect": {
                "description": {
                    "identifier": f"hollowveil:{name}",
                    "basic_render_parameters": {
                        "material": "particles_alpha",
                        "texture": f"textures/particle/{name}",
                    },
                },
                "components": {
                    "minecraft:emitter_rate_instant": {"num_particles": s["count"]},
                    "minecraft:emitter_lifetime_once": {"active_time": 0.2},
                    "minecraft:emitter_shape_point": {"offset": [0, 0.5, 0], "direction": "outwards"},
                    "minecraft:particle_lifetime_expression": {"max_lifetime": s["life"]},
                    "minecraft:particle_initial_speed": s["speed"],
                    "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.1},
                    "minecraft:particle_appearance_billboard": {
                        "size": [s["size"], s["size"]],
                        "facing_camera_mode": "lookat_xyz",
                        "uv": {"texture_width": 8, "texture_height": 8, "uv": [0, 0], "uv_size": [8, 8]},
                    },
                },
            },
        }
        p = os.path.join(RP, "particles", f"{name}.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            _json.dump(data, f, indent=2)
    print(f"wrote {len(specs)} particle effect definitions")


# ---------------------------------------------------------------------------
# Worn armor: attachables + 64x32 legacy armor-layer textures.
#
# Every armor item previously only had an inventory icon - equipping it
# changed nothing about how the player looked, because Bedrock only renders
# custom worn armor through an RP/attachables/*.player.json bound to a real
# texture, and none existed. This paints one using the same box-UV math as
# boxuv.py, applied to the fixed vanilla legacy armor-layer regions (head at
# uv 0,0; body at 16,16; arm at 40,16; leg at 0,16 - see diamond_1/diamond_2
# in Mojang's bedrock-samples resource pack), so it's derived from code
# instead of hand-painted, same as everything else in this pipeline.
# ---------------------------------------------------------------------------
ARMOR_SETS = {
    "spectral_regalia": {"base": (205, 205, 222, 255), "accent": (225, 255, 245, 255)},
    "mourners_shroud": {"base": (135, 105, 155, 255), "accent": (230, 190, 230, 255)},
    "ashen_demonplate": {"base": (75, 25, 22, 255), "accent": (255, 150, 70, 255)},
    "hollowforged": {"base": (232, 228, 220, 255), "accent": (255, 60, 50, 255)},
}

# (u, v, dx, dy, dz) for each body part in the fixed 64x32 legacy armor layout
ARMOR_PART_BOXES = [
    (0, 0, 8, 8, 8),  # head
    (16, 16, 8, 12, 4),  # body
    (40, 16, 4, 12, 4),  # arm (mirrored for both arms by the built-in geometry)
    (0, 16, 4, 12, 4),  # leg (mirrored for both legs by the built-in geometry)
]


def gen_armor_layer_textures():
    for name, spec in ARMOR_SETS.items():
        base = spec["base"]
        outline = tuple(max(0, c - 45) if i < 3 else 255 for i, c in enumerate(base))
        for layer in (1, 2):
            img = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            rnd = random.Random(hash((name, layer)) % 999)
            for (u, v, dx, dy, dz) in ARMOR_PART_BOXES:
                rects = boxuv.face_rects(u, v, dx, dy, dz)
                for x, y, w, h in rects.values():
                    for px in range(w):
                        for py in range(h):
                            jitter = rnd.randint(-14, 14)
                            col = tuple(max(0, min(255, c + jitter)) if i < 3 else c for i, c in enumerate(base))
                            d.point((x + px, y + py), fill=col)
                    d.rectangle([x, y, x + w - 1, y + h - 1], outline=outline)
            # a glowing accent seam across the body's front face, standing
            # in for trim/engraving so the set reads as themed, not just a
            # solid-colored recolor
            body_front = boxuv.face_rects(16, 16, 8, 12, 4)["front"]
            fx, fy, fw, fh = body_front
            seam_y = fy + fh // 3
            d.line([(fx, seam_y), (fx + fw - 1, seam_y)], fill=spec["accent"], width=1)
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
