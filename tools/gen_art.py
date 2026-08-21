#!/usr/bin/env python3
"""Regenerate every End Unbound texture from source.

    python3 tools/gen_art.py

No arguments, no dependencies, no network. Output is byte-for-byte identical on
every run, so regenerating produces an empty diff unless a recipe actually
changed. Each recipe below is authored as "what is this material made of",
and the matching MER map is derived from the albedo rather than painted twice.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artlib import (  # noqa: E402
    TRANSPARENT,
    Canvas,
    canvas_from_png,
    recolour,
    Rng,
    bevel,
    fbm,
    hex_rgba,
    hsv,
    luma,
    make_mer,
    mix,
    radial,
    shade,
    speckle,
    veins,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCKS = os.path.join(ROOT, "RP", "textures", "blocks")
ITEMS = os.path.join(ROOT, "RP", "textures", "items")
ENTITY = os.path.join(ROOT, "RP", "textures", "entity")

# The whole pack is built from six anchor colours so nothing drifts out of key.
PALETTE = {
    "endstone": hex_rgba("#DCE0A8"),
    "endstone_dark": hex_rgba("#A8AC78"),
    "void": hex_rgba("#2A1140"),
    "void_lit": hex_rgba("#C77BFF"),
    "lumen": hex_rgba("#1E8C7E"),
    "lumen_lit": hex_rgba("#5FE8D2"),
}


def out(canvas, folder, name):
    path = os.path.join(folder, name + ".png")
    canvas.save(path)
    return path


def emit(albedo, folder, name, **mer_kwargs):
    """Write an albedo texture plus its derived MER companion."""
    out(albedo, folder, name)
    if mer_kwargs.pop("mer", True):
        make_mer(albedo, **mer_kwargs).save(os.path.join(folder, name + "_mer.png"))


# --------------------------------------------------------------------------
# Blocks
# --------------------------------------------------------------------------


def stone_base(seed, base, dark, contrast=0.30, size=16):
    """Shared end-stone substrate: soft blotches, not per-pixel static."""
    c = Canvas(size)

    def paint(x, y, _cur):
        n = fbm(x, y, size, seed, octaves=3, base_period=4)
        grain = fbm(x, y, size, seed + 1301, octaves=2, base_period=8)
        t = (n * 0.75 + grain * 0.25 - 0.5) * 2.0 * contrast
        return shade(mix(base, dark, max(0.0, min(1.0, n * 0.55))), t)

    c.each(paint)
    return c


def block_shattered_end_stone():
    """End stone that the void has been pulling apart for a few aeons."""
    c = stone_base(4021, PALETTE["endstone"], PALETTE["endstone_dark"], 0.34)
    veins(c, 9107, 3, mix(PALETTE["endstone_dark"], PALETTE["void"], 0.55), 22, wobble=1.1)
    veins(c, 9108, 2, mix(PALETTE["void"], (0, 0, 0, 255), 0.35), 14, wobble=1.3)
    speckle(c, 5501, 0.06, [shade(PALETTE["endstone_dark"], -0.25), shade(PALETTE["endstone"], 0.18)])
    emit(c, BLOCKS, "voidbound_shattered_end_stone", roughness=246, roughness_variation=14, seed=3)


def block_verdant_end_stone():
    """End stone colonised by void moss - the ground cover of the groves."""
    c = stone_base(6613, PALETTE["endstone"], PALETTE["endstone_dark"], 0.24)
    moss = mix(PALETTE["lumen"], PALETTE["void"], 0.35)
    moss_lit = mix(PALETTE["lumen_lit"], moss, 0.45)

    def overgrow(x, y, cur):
        n = fbm(x, y, 16, 8821, octaves=3, base_period=4)
        if n < 0.46:
            return None
        t = min(1.0, (n - 0.46) / 0.34)
        return mix(cur, mix(moss, moss_lit, t * 0.6), 0.35 + 0.6 * t)

    c.each(overgrow)
    speckle(c, 8822, 0.045, [moss_lit, shade(moss, -0.3)])
    emit(
        c,
        BLOCKS,
        "voidbound_verdant_end_stone",
        roughness=238,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=0.5,
        emissive_threshold=0.30,
    )


def block_echo_ore():
    """Echo shards embedded in end stone: clustered, not scattered confetti."""
    c = stone_base(1777, PALETTE["endstone"], PALETTE["endstone_dark"], 0.26)
    rng = Rng(3311)
    core = PALETTE["lumen_lit"]
    rim = mix(PALETTE["lumen"], PALETTE["void"], 0.4)
    for _ in range(4):
        cx, cy = rng.range(2, 14), rng.range(2, 14)
        r = rng.range(1.8, 3.1)
        for y in range(16):
            for x in range(16):
                # Wrap the distance so clusters bleed across the tile seam.
                dx = min(abs(x + 0.5 - cx), 16 - abs(x + 0.5 - cx))
                dy = min(abs(y + 0.5 - cy), 16 - abs(y + 0.5 - cy))
                d = math.hypot(dx, dy) / r
                if d > 1.0:
                    continue
                c.blend(x, y, mix(core, rim, min(1.0, d ** 0.7)))
    speckle(c, 3312, 0.03, [shade(core, 0.35)])
    emit(
        c,
        BLOCKS,
        "voidbound_echo_ore",
        roughness=200,
        emissive_from=core[:3],
        emissive_gain=1.15,
        emissive_threshold=0.12,
    )


def block_void_crystal():
    """A solid crystal block, read as large facets rather than noise."""
    c = Canvas(16)
    deep = PALETTE["void"]
    lit = PALETTE["void_lit"]

    def facets(x, y, _cur):
        # Two rotated sawtooth fields intersect into flat, angular planes.
        a = ((x * 0.62 + y * 0.31) % 4.0) / 4.0
        b = ((x * -0.28 + y * 0.71) % 5.0) / 5.0
        n = fbm(x, y, 16, 4477, octaves=2, base_period=4)
        t = 0.45 * a + 0.35 * b + 0.20 * n
        return mix(deep, lit, max(0.0, min(1.0, t * 1.15)))

    c.each(facets)
    veins(c, 4478, 4, shade(lit, 0.45), 16, wobble=0.35)
    emit(
        c,
        BLOCKS,
        "voidbound_void_crystal_block",
        metalness=0,
        roughness=54,
        emissive_from=lit[:3],
        emissive_gain=0.95,
        emissive_threshold=0.20,
    )


def block_void_glass():
    """Tinted, mostly-clear glass with a bright rift seam through it."""
    c = Canvas(16)
    deep = mix(PALETTE["void"], (0, 0, 0, 255), 0.35)
    tint = (deep[0], deep[1], deep[2], 104)
    c.fill(tint)
    frame = (PALETTE["void_lit"][0], PALETTE["void_lit"][1], PALETTE["void_lit"][2], 205)
    for i in range(16):
        c.set(i, 0, frame)
        c.set(i, 15, frame)
        c.set(0, i, frame)
        c.set(15, i, frame)
    for i in range(3, 13):
        c.blend(i, i, (255, 255, 255, 60))
    emit(
        c,
        BLOCKS,
        "voidbound_void_glass",
        roughness=18,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=0.5,
        emissive_threshold=0.35,
    )


def _stalk(c, x, top, bottom, color, rng, sway=0.0):
    px = x
    for y in range(bottom, top - 1, -1):
        px += rng.range(-sway, sway)
        c.blend(int(round(px)), y, color)
    return px


def block_voidbloom():
    """Cross-model flora: paired stalks, each opening into a violet blossom."""
    c = Canvas(16)
    rng = Rng(2204)
    stalk = mix(PALETTE["void"], PALETTE["endstone_dark"], 0.30)
    stalk_lit = mix(stalk, PALETTE["void_lit"], 0.30)
    petal = PALETTE["void_lit"]
    petal_deep = mix(PALETTE["void"], PALETTE["void_lit"], 0.45)

    def blossom(cx, cy, r):
        # Four petals around a bright pistil - a shape, not a gradient blob.
        for angle in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
            px = cx + math.cos(angle) * r * 0.72
            py = cy + math.sin(angle) * r * 0.72
            for y in range(c.h):
                for x in range(c.w):
                    d = math.hypot(x + 0.5 - px, y + 0.5 - py) / (r * 0.62)
                    if d <= 1.0:
                        c.blend(x, y, mix(petal, petal_deep, d ** 0.8))
        for y in range(c.h):
            for x in range(c.w):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / (r * 0.44)
                if d <= 1.0:
                    c.blend(x, y, mix((255, 246, 255, 255), petal, d))

    for base_x, top, r in ((4, 7, 3.0), (11, 10, 2.2)):
        px = base_x
        for y in range(15, top - 1, -1):
            px += rng.range(-0.28, 0.28)
            c.blend(int(round(px)), y, stalk)
            if y % 4 == 1:
                c.blend(int(round(px)) + rng.int(-1, 1), y, stalk_lit)
        blossom(px + 0.5, top - 0.5, r)

    # A couple of shed motes drifting off the blossoms.
    for mx, my in ((13, 4), (2, 3), (8, 12)):
        c.blend(mx, my, shade(petal, 0.45))
    emit(
        c,
        BLOCKS,
        "voidbound_voidbloom",
        roughness=170,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=1.3,
        emissive_threshold=0.10,
    )

def block_lumen_bulb():
    """Cross-model flora: teal lantern-fruit on a pale stem."""
    c = Canvas(16)
    rng = Rng(7702)
    stem = mix(PALETTE["lumen"], PALETTE["endstone_dark"], 0.4)
    tip = _stalk(c, 8, 7, 15, stem, rng, sway=0.25)
    radial(c, tip + 0.5, 5.5, 4.0, PALETTE["lumen_lit"], (20, 80, 76, 0), falloff=1.35)
    radial(c, tip - 0.6, 4.4, 1.6, (235, 255, 250, 255), (95, 232, 210, 0), falloff=1.2)
    for y in range(8, 13):
        c.blend(int(tip) - 2, y, mix(stem, PALETTE["lumen_lit"], 0.3))
        c.blend(int(tip) + 2, y + 1, mix(stem, PALETTE["lumen_lit"], 0.2))
    emit(
        c,
        BLOCKS,
        "voidbound_lumen_bulb",
        roughness=140,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=1.45,
        emissive_threshold=0.08,
    )


def block_rift_lantern():
    """A caged lantern: obsidian frame, violet rift burning behind the bars."""
    frame = mix(PALETTE["void"], (0, 0, 0, 255), 0.45)
    frame_lit = shade(frame, 0.22)
    core = PALETTE["void_lit"]

    side = Canvas(16)
    # Glowing interior first, then the ironwork on top of it.
    side.fill(mix(frame, core, 0.10))
    radial(side, 8.0, 8.5, 7.5, shade(core, 0.55), mix(frame, core, 0.18), falloff=1.25)
    # Heavy top and bottom caps.
    side.rect(0, 0, 15, 2, frame)
    side.rect(0, 13, 15, 15, frame)
    for x in range(16):
        side.blend(x, 0, frame_lit)
        side.blend(x, 15, shade(frame, -0.35))
        side.blend(x, 2, shade(frame, -0.3))
        side.blend(x, 13, frame_lit)
    # Two vertical bars and one waist band - sparse enough to see the rift.
    for x in (3, 12):
        for y in range(3, 13):
            side.set(x, y, frame if y % 3 else frame_lit)
    for x in range(16):
        side.set(x, 8, frame if x % 4 else frame_lit)
    # Corner rivets.
    for x, y in ((1, 3), (14, 3), (1, 12), (14, 12)):
        side.set(x, y, frame_lit)
    emit(
        side,
        BLOCKS,
        "voidbound_rift_lantern_side",
        metalness=0,
        roughness=120,
        emissive_from=core[:3],
        emissive_gain=1.25,
        emissive_threshold=0.14,
    )

    top = Canvas(16)
    top.fill(shade(frame, -0.10))
    top.rect(2, 2, 13, 13, frame)
    radial(top, 8.0, 8.0, 5.4, shade(core, 0.35), shade(frame, 0.05), falloff=1.7)
    for i in range(16):
        top.blend(i, 0, frame_lit)
        top.blend(0, i, frame_lit)
        top.blend(i, 15, shade(frame, -0.3))
        top.blend(15, i, shade(frame, -0.3))
    speckle(top, 991, 0.04, [frame_lit, shade(frame, -0.2)])
    emit(
        top,
        BLOCKS,
        "voidbound_rift_lantern_top",
        roughness=150,
        emissive_from=core[:3],
        emissive_gain=0.9,
        emissive_threshold=0.22,
    )

def _shard_silhouette(c, points, fill_inner, fill_outer):
    """Fill a convex polygon with a centre-out gradient, then bevel it."""
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    for y in range(c.h):
        for x in range(c.w):
            px, py = x + 0.5, y + 0.5
            inside = True
            for i in range(len(points)):
                ax, ay = points[i]
                bx, by = points[(i + 1) % len(points)]
                if (bx - ax) * (py - ay) - (by - ay) * (px - ax) < 0:
                    inside = False
                    break
            if not inside:
                continue
            d = min(1.0, math.hypot(px - cx, py - cy) / 6.0)
            c.set(x, y, mix(fill_inner, fill_outer, d))


def item_echo_shard():
    c = Canvas(16)
    _shard_silhouette(
        c,
        [(8, 1), (12, 7), (9.5, 14.5), (6, 14), (3.5, 7)],
        PALETTE["lumen_lit"],
        mix(PALETTE["lumen"], PALETTE["void"], 0.45),
    )
    veins(c, 6161, 2, shade(PALETTE["lumen_lit"], 0.5), 9, wobble=0.5)
    bevel(c)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.5))
    emit(
        c,
        ITEMS,
        "voidbound_echo_shard",
        roughness=64,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=1.1,
        emissive_threshold=0.16,
    )


def item_void_crystal():
    c = Canvas(16)
    _shard_silhouette(
        c,
        [(8, 0.5), (13, 5), (11, 13), (5, 13.5), (3, 5)],
        shade(PALETTE["void_lit"], 0.25),
        PALETTE["void"],
    )
    for y in range(2, 13):
        c.blend(8, y, shade(PALETTE["void_lit"], 0.55))
    bevel(c, light=0.3, dark=0.3)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.6))
    emit(
        c,
        ITEMS,
        "voidbound_void_crystal",
        roughness=42,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=1.2,
        emissive_threshold=0.18,
    )


def item_rift_compass():
    """A ring of dark alloy around a floating violet needle."""
    c = Canvas(16)
    body = mix(PALETTE["void"], PALETTE["endstone_dark"], 0.30)
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
            if 4.4 <= d <= 7.2:
                c.set(x, y, shade(body, 0.18 - 0.12 * ((d - 4.4) / 2.8)))
    radial(c, 8, 8, 4.6, mix(PALETTE["void"], (0, 0, 0, 255), 0.55), mix(PALETTE["void"], PALETTE["void_lit"], 0.25))
    for i in range(-3, 4):
        c.blend(8 + i, 8 - i, shade(PALETTE["void_lit"], 0.35 if i < 0 else -0.1))
    c.blend(8, 8, (255, 255, 255, 255))
    bevel(c)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.65))
    emit(
        c,
        ITEMS,
        "voidbound_rift_compass",
        metalness=140,
        roughness=96,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=0.9,
        emissive_threshold=0.30,
    )


def item_lumen_berry():
    c = Canvas(16)
    radial(c, 7.5, 8.5, 5.2, PALETTE["lumen_lit"], mix(PALETTE["lumen"], PALETTE["void"], 0.5), falloff=1.25)
    radial(c, 6.0, 6.5, 2.0, (240, 255, 252, 255), (95, 232, 210, 0), falloff=1.1)
    for y in range(2, 5):
        c.blend(10, y, mix(PALETTE["lumen"], PALETTE["void"], 0.3))
    c.blend(11, 4, mix(PALETTE["lumen"], PALETTE["void"], 0.3))
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.55))
    emit(
        c,
        ITEMS,
        "voidbound_lumen_berry",
        roughness=110,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=1.0,
        emissive_threshold=0.20,
    )


def item_raw_haunch():
    """Pale meat with a violet cast - it came off something from the End."""
    c = Canvas(16)
    meat = hex_rgba("#B9668F")
    meat_dark = mix(meat, PALETTE["void"], 0.45)
    fat = hex_rgba("#E8C4D8")
    bone = hex_rgba("#EDE6DC")
    for y in range(4, 14):
        for x in range(2, 13):
            d = math.hypot((x - 7.5) / 5.5, (y - 9) / 4.5)
            if d > 1.0:
                continue
            n = fbm(x * 2, y * 2, 16, 5150, octaves=3, base_period=4)
            c.set(x, y, mix(meat, meat_dark, min(1.0, d * 0.8 + n * 0.3)))
    for x in range(4, 11):
        c.blend(x, 6, mix(fat, meat, 0.3))
    for y in range(2, 6):
        c.set(9, y, bone)
        c.set(10, y, mix(bone, meat_dark, 0.3))
    c.set(9, 1, bone)
    c.set(10, 1, bone)
    bevel(c)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.55))
    emit(c, ITEMS, "voidbound_raw_haunch", roughness=200)


def item_cooked_haunch():
    """The same cut, seared."""
    c = Canvas(16)
    meat = hex_rgba("#8A4A32")
    meat_dark = mix(meat, (0, 0, 0, 255), 0.4)
    crust = hex_rgba("#C98A4C")
    bone = hex_rgba("#EDE6DC")
    for y in range(4, 14):
        for x in range(2, 13):
            d = math.hypot((x - 7.5) / 5.5, (y - 9) / 4.5)
            if d > 1.0:
                continue
            n = fbm(x * 2, y * 2, 16, 5151, octaves=3, base_period=4)
            base = mix(meat, meat_dark, min(1.0, d * 0.75 + n * 0.35))
            c.set(x, y, mix(base, crust, max(0.0, 0.55 - d) * 0.9))
    for y in range(2, 6):
        c.set(9, y, bone)
        c.set(10, y, mix(bone, meat_dark, 0.3))
    c.set(9, 1, bone)
    c.set(10, 1, bone)
    bevel(c)
    c.outline(mix(hex_rgba("#2A1408"), (0, 0, 0, 255), 0.3))
    emit(c, ITEMS, "voidbound_cooked_haunch", roughness=190)


def item_echo_bread():
    """A dense loaf pressed from lumen berries - the travel ration."""
    c = Canvas(16)
    crust = hex_rgba("#8C7A4E")
    crust_hi = hex_rgba("#C4B075")
    berry = PALETTE["lumen_lit"]
    for y in range(5, 13):
        for x in range(2, 14):
            d = math.hypot((x - 8) / 6.2, (y - 9) / 4.0)
            if d > 1.0:
                continue
            n = fbm(x * 2.2, y * 2.2, 16, 6262, octaves=3, base_period=4)
            c.set(x, y, mix(crust_hi, crust, min(1.0, d * 0.7 + n * 0.4)))
    # Berries showing through the crust.
    for bx, by in ((5, 8), (9, 7), (11, 10), (7, 11)):
        c.blend(bx, by, berry)
        c.blend(bx + 1, by, mix(berry, crust, 0.45))
    for x in range(4, 12, 3):
        c.blend(x, 6, mix(crust, (0, 0, 0, 255), 0.25))
    bevel(c)
    c.outline(mix(hex_rgba("#3A2E16"), (0, 0, 0, 255), 0.3))
    emit(c, ITEMS, "voidbound_echo_bread", roughness=214,
         emissive_from=berry[:3], emissive_gain=0.8, emissive_threshold=0.3)


# --------------------------------------------------------------------------
# Entities
# --------------------------------------------------------------------------


def paint_box(c, u, v, w, h, d, painter):
    """Fill the six faces of a Bedrock box UV footprint.

    Bedrock lays a box out as: top and bottom on the first `d` rows, then
    east / north / west / south across the next `h` rows. `painter(face, fx,
    fy, fw, fh)` returns the colour for one pixel of one face.
    """
    faces = [
        ("top", u + d, v, w, d),
        ("bottom", u + d + w, v, w, d),
        ("east", u, v + d, d, h),
        ("north", u + d, v + d, w, h),
        ("west", u + d + w, v + d, d, h),
        ("south", u + d + w + d, v + d, w, h),
    ]
    for name, ox, oy, fw, fh in faces:
        for fy in range(fh):
            for fx in range(fw):
                color = painter(name, fx, fy, fw, fh)
                if color is not None:
                    c.set(ox + fx, oy + fy, color)


def entity_lumen_wisp():
    """32x32 sheet for the wisp: a glowing core plus three orbiting shards."""
    c = Canvas(32, 32)
    core_in = shade(PALETTE["lumen_lit"], 0.55)
    core_out = mix(PALETTE["lumen"], PALETTE["void"], 0.30)

    def core(_face, fx, fy, fw, fh):
        dx = (fx + 0.5) / fw - 0.5
        dy = (fy + 0.5) / fh - 0.5
        d = min(1.0, math.hypot(dx, dy) * 2.0)
        n = fbm(fx * 2, fy * 2, 12, 1234, octaves=2, base_period=4)
        return mix(core_in, core_out, min(1.0, d * 0.85 + n * 0.2))

    paint_box(c, 0, 0, 6, 6, 6, core)

    def shard(_face, fx, fy, fw, fh):
        t = (fx + fy) / float(max(1, fw + fh - 2))
        return mix(shade(PALETTE["lumen_lit"], 0.3), mix(PALETTE["lumen"], PALETTE["void"], 0.5), t)

    for u, v in ((0, 14), (12, 14), (0, 20)):
        paint_box(c, u, v, 2, 2, 2, shard)

    emit(
        c,
        ENTITY,
        "voidbound_lumen_wisp",
        roughness=90,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=1.35,
        emissive_threshold=0.10,
    )


def entity_rift_stalker():
    """64x32 sheet: obsidian carapace with violet rift light in the seams."""
    c = Canvas(64, 32)
    hide = mix(PALETTE["void"], (0, 0, 0, 255), 0.12)
    hide_lit = mix(PALETTE["void"], PALETTE["void_lit"], 0.55)

    def carapace(face, fx, fy, fw, fh):
        n = fbm(fx * 1.5, fy * 1.5, 16, 5150, octaves=3, base_period=4)
        base = mix(hide, shade(hide, 0.42), n)
        # A bright ridge runs down the spine and along each flank seam.
        if face == "top" and abs(fx - (fw - 1) / 2.0) < 0.9:
            return mix(base, PALETTE["void_lit"], 0.55)
        if face in ("east", "west") and fy in (1, fh - 2):
            return mix(base, hide_lit, 0.6)
        return base

    paint_box(c, 0, 0, 8, 6, 12, carapace)

    def skull(face, fx, fy, fw, fh):
        n = fbm(fx * 2, fy * 2, 12, 6160, octaves=2, base_period=4)
        base = mix(hide, shade(hide, 0.38), n)
        if face == "north" and fy in (1, 2) and fx in (1, fw - 2):
            return shade(PALETTE["void_lit"], 0.5)  # eyes
        return base

    paint_box(c, 0, 20, 6, 5, 5, skull)

    def crest(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(PALETTE["void_lit"], hide, min(1.0, t * 1.3))

    paint_box(c, 24, 20, 2, 4, 6, crest)

    def jaw(face, fx, fy, fw, fh):
        n = fbm(fx * 2, fy * 2, 12, 6161, octaves=2, base_period=4)
        base = mix(shade(hide, -0.12), hide_lit, n * 0.3)
        # Teeth along the lower edge of the muzzle.
        if face == "north" and fy == fh - 1 and fx % 2 == 0:
            return hex_rgba("#E8E0F0")
        return base

    paint_box(c, 40, 19, 6, 2, 4, jaw)

    def tail(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(hide_lit, hide, min(1.0, t * 1.4))

    paint_box(c, 40, 26, 2, 2, 4, tail)

    def limb(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(shade(hide, 0.1), mix(hide, PALETTE["void_lit"], 0.25), t)

    for u, v in ((44, 0), (44, 10), (52, 0), (52, 10)):
        paint_box(c, u, v, 2, 6, 2, limb)

    emit(
        c,
        ENTITY,
        "voidbound_rift_stalker",
        roughness=150,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=1.1,
        emissive_threshold=0.22,
    )


def entity_void_moth():
    """64x32 sheet: a dusty violet body under four translucent-looking wings."""
    c = Canvas(64, 32)
    fur = mix(PALETTE["void"], PALETTE["endstone_dark"], 0.22)
    fur_hi = mix(fur, PALETTE["void_lit"], 0.35)
    wing = mix(PALETTE["void_lit"], PALETTE["void"], 0.45)
    wing_edge = shade(PALETTE["void_lit"], 0.35)

    def body(face, fx, fy, fw, fh):
        n = fbm(fx * 2, fy * 2, 12, 4310, octaves=3, base_period=4)
        base = mix(fur, fur_hi, n * 0.55)
        # Banding along the abdomen.
        if face in ("east", "west", "top") and fy % 2 == 0:
            return shade(base, -0.12)
        return base

    paint_box(c, 0, 0, 4, 4, 6, body)

    def head(face, fx, fy, fw, fh):
        base = mix(fur_hi, fur, 0.3)
        if face == "north" and fy == 1 and fx in (1, fw - 2):
            return shade(PALETTE["lumen_lit"], 0.4)  # eyes
        return base

    paint_box(c, 22, 0, 4, 3, 2, head)

    def make_wing(scale):
        def paint(face, fx, fy, fw, fh):
            # Veins run outward from the wing root; the trailing edge glows.
            t = fx / float(max(1, fw - 1))
            n = fbm(fx * 3, fy * 3, 16, 4311, octaves=2, base_period=4)
            base = mix(wing, mix(wing, PALETTE["void"], 0.55), t * scale)
            if fx % 3 == 0:
                base = mix(base, wing_edge, 0.45)
            if face == "top" or face == "bottom":
                return mix(base, wing_edge, 0.15 + n * 0.2)
            return base
        return paint

    paint_box(c, 0, 12, 7, 1, 5, make_wing(0.9))
    paint_box(c, 0, 19, 7, 1, 5, make_wing(0.9))
    paint_box(c, 26, 12, 5, 1, 4, make_wing(1.1))
    paint_box(c, 26, 18, 5, 1, 4, make_wing(1.1))

    def antenna(_face, fx, fy, fw, fh):
        return mix(fur_hi, PALETTE["lumen_lit"], 1.0 - fy / float(max(1, fh - 1)))

    paint_box(c, 46, 0, 1, 3, 1, antenna)

    emit(
        c,
        ENTITY,
        "voidbound_void_moth",
        roughness=190,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=0.85,
        emissive_threshold=0.28,
    )


def entity_echo_sentinel():
    """64x64 sheet: quarried end stone bound around a burning echo core."""
    c = Canvas(64, 64)
    stone = mix(PALETTE["endstone_dark"], PALETTE["void"], 0.42)
    stone_hi = mix(stone, PALETTE["endstone"], 0.35)
    seam = PALETTE["lumen_lit"]

    def masonry(seed, seam_faces=()):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 1.4, fy * 1.4, 16, seed, octaves=3, base_period=4)
            base = mix(stone, stone_hi, n)
            # Brick courses, offset every other row.
            if fy % 4 == 0:
                base = shade(base, -0.22)
            elif (fx + (fy // 4) * 2) % 5 == 0:
                base = shade(base, -0.16)
            if face in seam_faces and abs(fx - (fw - 1) / 2.0) < 0.6:
                return mix(base, seam, 0.5)
            return base
        return paint

    paint_box(c, 0, 0, 10, 14, 6, masonry(7710, ("north",)))
    paint_box(c, 0, 22, 8, 8, 8, masonry(7711))
    paint_box(c, 34, 0, 4, 14, 4, masonry(7712))
    paint_box(c, 34, 20, 4, 14, 4, masonry(7713))
    paint_box(c, 0, 40, 4, 12, 4, masonry(7714))
    paint_box(c, 18, 40, 4, 12, 4, masonry(7715))

    def core(_face, fx, fy, fw, fh):
        dx = (fx + 0.5) / fw - 0.5
        dy = (fy + 0.5) / fh - 0.5
        d = min(1.0, math.hypot(dx, dy) * 2.2)
        return mix(shade(seam, 0.6), mix(seam, PALETTE["void"], 0.6), d)

    paint_box(c, 36, 40, 4, 4, 1, core)

    # Eyes on the head's north face.
    for x, y in ((10, 33), (13, 33), (10, 34), (13, 34)):
        c.set(x, y, shade(seam, 0.55))

    emit(
        c,
        ENTITY,
        "voidbound_echo_sentinel",
        roughness=232,
        emissive_from=PALETTE["lumen_lit"][:3],
        emissive_gain=1.2,
        emissive_threshold=0.22,
    )


# --------------------------------------------------------------------------
# Tools and armour: recoloured vanilla art
# --------------------------------------------------------------------------

VANILLA_REFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vanilla_refs")

# The brief was "a reskin of the classic sword, tools and armour", and the eye
# knows those silhouettes far too well for a hand-drawn approximation to pass -
# an earlier pass tried and every shape read as almost-but-not-quite. So the
# real vanilla textures are recoloured instead: the shape, shading and outline
# are Mojang's, only the metal's hue changes.
#
# Diamond is the donor. Its metal sits at hue 180 and its wooden handles at
# hue 30, which separates cleanly, so a hue window over the metal leaves the
# sticks untouched.
METAL_HUES = (150.0 / 360.0, 210.0 / 360.0)
TOOL_METAL = hex_rgba("#9B5FD6")
ARMOR_METAL = hex_rgba("#7A4CB8")


def _require_ref(filename):
    path = os.path.join(VANILLA_REFS, filename)
    if not os.path.exists(path):
        raise SystemExit(
            "missing %s\n  run: python3 tools/fetch_vanilla_refs.py" % os.path.relpath(path, ROOT)
        )
    return path


def tool_set():
    """Five tools, recoloured from vanilla diamond so the shapes are exact."""
    for vanilla, name in (
        ("diamond_sword.png", "void_sword"),
        ("diamond_pickaxe.png", "void_pickaxe"),
        ("diamond_axe.png", "void_axe"),
        ("diamond_shovel.png", "void_shovel"),
        ("diamond_hoe.png", "void_hoe"),
    ):
        c = canvas_from_png(_require_ref(vanilla))
        recolour(c, TOOL_METAL, hue_window=METAL_HUES, value_scale=0.94)
        emit(
            c, ITEMS, "voidbound_%s" % name,
            metalness=96, roughness=84,
            emissive_from=TOOL_METAL[:3], emissive_gain=0.55, emissive_threshold=0.55,
        )


def armor_layers():
    """Both armour layers, recoloured from vanilla diamond."""
    os.makedirs(ARMOR, exist_ok=True)
    for vanilla, name in (
        ("diamond_1.png", "voidbound_armor_1"),
        ("diamond_2.png", "voidbound_armor_2"),
    ):
        c = canvas_from_png(_require_ref(vanilla))
        # No hue window here: armour layers are all metal.
        recolour(c, ARMOR_METAL, value_scale=0.92)
        emit(
            c, ARMOR, name,
            metalness=72, roughness=104,
            emissive_from=ARMOR_METAL[:3], emissive_gain=0.5, emissive_threshold=0.62,
        )


# --------------------------------------------------------------------------
# Armor
# --------------------------------------------------------------------------

ARMOR = os.path.join(ROOT, "RP", "textures", "models", "armor")

def _armor_icon(name, draw):
    """Shared finishing pass for the four armour icons."""
    c = Canvas(16)
    plate = mix(PALETTE["void"], (0, 0, 0, 255), 0.28)
    draw(c, plate, PALETTE["void_lit"], PALETTE["lumen_lit"])
    bevel(c, light=0.26, dark=0.28)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.65))
    emit(
        c,
        ITEMS,
        name,
        metalness=64,
        roughness=104,
        emissive_from=PALETTE["void_lit"][:3],
        emissive_gain=1.1,
        emissive_threshold=0.26,
    )


def item_void_helmet():
    def draw(c, plate, lit, echo):
        c.rect(3, 3, 12, 10, plate)
        c.rect(2, 5, 13, 11, plate)
        c.rect(5, 8, 10, 11, TRANSPARENT)   # face opening
        for x in range(5, 11):
            c.set(x, 7, lit)                # visor band
        c.set(7, 2, lit)
        c.set(8, 2, lit)
        c.set(3, 11, echo)
        c.set(12, 11, echo)
    _armor_icon("voidbound_void_helmet", draw)


def item_void_chestplate():
    def draw(c, plate, lit, echo):
        c.rect(2, 3, 13, 5, plate)          # shoulders
        c.rect(4, 3, 11, 13, plate)         # torso
        c.rect(2, 4, 3, 9, plate)           # left pauldron
        c.rect(12, 4, 13, 9, plate)         # right pauldron
        for y in range(5, 13):
            c.set(7, y, lit)
            c.set(8, y, lit)
        c.set(3, 6, echo)
        c.set(12, 6, echo)
    _armor_icon("voidbound_void_chestplate", draw)


def item_void_leggings():
    def draw(c, plate, lit, echo):
        c.rect(3, 2, 12, 5, plate)          # belt
        c.rect(3, 5, 6, 14, plate)          # left leg
        c.rect(9, 5, 12, 14, plate)         # right leg
        for x in range(4, 12):
            c.set(x, 3, lit)
        c.set(4, 9, echo)
        c.set(11, 9, echo)
    _armor_icon("voidbound_void_leggings", draw)


def item_void_boots():
    def draw(c, plate, lit, echo):
        c.rect(2, 6, 6, 12, plate)
        c.rect(9, 6, 13, 12, plate)
        c.rect(1, 11, 6, 13, plate)         # left toe
        c.rect(9, 11, 14, 13, plate)        # right toe
        for x in range(2, 7):
            c.set(x, 7, lit)
        for x in range(9, 14):
            c.set(x, 7, lit)
        c.set(2, 12, echo)
        c.set(13, 12, echo)
    _armor_icon("voidbound_void_boots", draw)


def entity_chorus_hopper():
    """32x32: a plump chorus-fed grazer, pale purple with darker dapples."""
    c = Canvas(32, 32)
    hide = hex_rgba("#8A5FA8")
    hide_dark = mix(hide, PALETTE["void"], 0.5)
    belly = mix(hide, hex_rgba("#E8D8F2"), 0.55)

    def body(face, fx, fy, fw, fh):
        n = fbm(fx * 2.2, fy * 2.2, 16, 4501, octaves=3, base_period=4)
        base = mix(hide, hide_dark, n * 0.7)
        if face == "bottom":
            return belly
        if n > 0.68:
            return hide_dark            # dapples
        return base

    paint_box(c, 0, 0, 6, 5, 8, body)

    def head(face, fx, fy, fw, fh):
        base = mix(hide, belly, 0.25)
        if face == "north" and fy == 1 and fx in (0, fw - 1):
            return PALETTE["void_lit"]  # eyes
        if face == "north" and fy == 3:
            return hide_dark            # mouth line
        return base

    paint_box(c, 0, 14, 4, 4, 3, head)

    def leg(_face, fx, fy, fw, fh):
        return mix(hide_dark, hide, fy / float(max(1, fh - 1)))

    paint_box(c, 16, 14, 2, 2, 2, leg)
    paint_box(c, 16, 19, 2, 2, 2, leg)

    def frond(_face, fx, fy, fw, fh):
        return mix(PALETTE["void_lit"], hide_dark, fy / float(max(1, fh - 1)))

    paint_box(c, 0, 22, 1, 3, 1, frond)
    paint_box(c, 6, 22, 1, 3, 1, frond)

    emit(c, ENTITY, "voidbound_chorus_hopper", roughness=210,
         emissive_from=PALETTE["void_lit"][:3], emissive_gain=0.7, emissive_threshold=0.34)


def entity_shard_wraith():
    """64x32: a hollow shroud with nothing inside it but light."""
    c = Canvas(64, 32)
    cloth = mix(PALETTE["void"], (0, 0, 0, 255), 0.30)
    cloth_hi = mix(cloth, hex_rgba("#7B4FA8"), 0.55)
    inner = hex_rgba("#D9A8FF")

    def hood(face, fx, fy, fw, fh):
        n = fbm(fx * 2, fy * 2, 16, 7801, octaves=3, base_period=4)
        base = mix(cloth, cloth_hi, n * 0.8)
        if face == "north":
            # A dark void under the hood, with two points of light in it.
            if 0 < fx < fw - 1 and fy > 1:
                if fy == 3 and fx in (1, fw - 2):
                    return inner
                return mix(cloth, (0, 0, 0, 255), 0.7)
        if face == "top":
            return shade(base, 0.16)
        return base

    paint_box(c, 0, 0, 6, 6, 6, hood)

    def shroud(face, fx, fy, fw, fh):
        n = fbm(fx * 1.6, fy * 1.6, 16, 7802, octaves=3, base_period=4)
        base = mix(cloth, cloth_hi, n * 0.6)
        t = fy / float(max(1, fh - 1))
        # The hem frays into light.
        if t > 0.7 and (fx + fy) % 2 == 0:
            return mix(base, inner, (t - 0.7) / 0.3 * 0.7)
        if face in ("east", "west") and fx % 3 == 0:
            return shade(base, -0.2)
        return base

    paint_box(c, 0, 13, 8, 9, 8, shroud)

    def tatter(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(cloth_hi, mix(cloth, inner, 0.4), t)

    paint_box(c, 34, 0, 1, 5, 3, tatter)
    paint_box(c, 44, 0, 1, 5, 3, tatter)

    emit(c, ENTITY, "voidbound_shard_wraith", roughness=176,
         emissive_from=inner[:3], emissive_gain=1.25, emissive_threshold=0.18)


def entity_crystal_crawler():
    """64x32: a low six-legged thing armoured in echo crystal."""
    c = Canvas(64, 32)
    chitin = mix(PALETTE["endstone_dark"], PALETTE["void"], 0.55)
    chitin_hi = mix(chitin, PALETTE["endstone"], 0.4)
    crystal = PALETTE["lumen_lit"]

    def body(face, fx, fy, fw, fh):
        n = fbm(fx * 1.5, fy * 1.5, 16, 3901, octaves=3, base_period=4)
        base = mix(chitin, chitin_hi, n)
        if face == "top" and fy % 3 == 1:
            return shade(base, -0.2)     # segment plates
        if face in ("east", "west") and fy == fh - 1:
            return mix(base, crystal, 0.35)
        return base

    paint_box(c, 0, 0, 8, 4, 12, body)

    def head(face, fx, fy, fw, fh):
        base = mix(chitin_hi, chitin, 0.3)
        if face == "north" and fy == 1 and fx in (1, fw - 2):
            return shade(crystal, 0.5)   # eyes
        return base

    paint_box(c, 0, 18, 6, 3, 3, head)

    def spine(_face, fx, fy, fw, fh):
        t = 1.0 - fy / float(max(1, fh - 1))
        return mix(chitin, crystal, min(1.0, t * 1.15))

    paint_box(c, 20, 18, 4, 4, 1, spine)
    paint_box(c, 32, 18, 2, 3, 1, spine)

    def leg(_face, fx, fy, fw, fh):
        return mix(chitin_hi, chitin, fy / float(max(1, fh - 1)))

    for u, v in ((42, 0), (42, 6), (42, 12), (48, 0), (48, 6), (48, 12)):
        paint_box(c, u, v, 1, 4, 1, leg)

    emit(c, ENTITY, "voidbound_crystal_crawler", roughness=224,
         emissive_from=crystal[:3], emissive_gain=1.0, emissive_threshold=0.26)


def item_gameplay_set():
    """The three utility items, plus the decorative block variants."""
    # Rift Charm: a bound loop of crystal on a cord.
    charm = Canvas(16)
    cord = mix(PALETTE["void"], hex_rgba("#8A7BA8"), 0.4)
    ring = PALETTE["void_lit"]
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 9)
            if 3.4 <= d <= 5.4:
                charm.set(x, y, mix(ring, PALETTE["void"], (d - 3.4) / 2.0 * 0.8))
    for i in range(4):
        charm.set(8, 2 + i, cord)
        charm.set(9, 2 + i, shade(cord, -0.25))
    charm.set(7, 1, cord); charm.set(8, 1, cord); charm.set(9, 1, cord)
    radial(charm, 8, 9, 3.0, mix(ring, (255, 255, 255, 255), 0.5), (0, 0, 0, 0), falloff=1.6)
    bevel(charm)
    charm.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.65))
    emit(charm, ITEMS, "voidbound_rift_charm", metalness=120, roughness=70,
         emissive_from=ring[:3], emissive_gain=1.25, emissive_threshold=0.22)

    # Echo Horn: a curled shell horn with a lit mouth.
    horn = Canvas(16)
    shell = hex_rgba("#C6BE94")
    shell_lo = mix(shell, PALETTE["void"], 0.45)
    mouth = PALETTE["lumen_lit"]
    for i in range(11):
        t = i / 10.0
        cx = 3 + i * 0.95
        cy = 12 - i * 0.75
        width = 1.0 + t * 2.6
        for dy in range(-int(width), int(width) + 1):
            for dx in range(-int(width), int(width) + 1):
                if dx * dx + dy * dy <= width * width:
                    horn.set(int(cx) + dx, int(cy) + dy, mix(shell_lo, shell, 1.0 - t * 0.5))
    radial(horn, 12.5, 4.5, 3.2, mouth, mix(shell, mouth, 0.2), falloff=1.5)
    speckle(horn, 9601, 0.06, [shade(shell, 0.25), shade(shell_lo, -0.2)])
    bevel(horn)
    horn.outline(mix(hex_rgba("#3A3418"), (0, 0, 0, 255), 0.35))
    emit(horn, ITEMS, "voidbound_echo_horn", roughness=170,
         emissive_from=mouth[:3], emissive_gain=1.1, emissive_threshold=0.28)

    # Ender Fruit Pie.
    pie = Canvas(16)
    crust = hex_rgba("#C4A96A")
    crust_lo = mix(crust, hex_rgba("#6B5730"), 0.5)
    filling = hex_rgba("#3FE0C4")
    pie.rect(2, 6, 13, 13, crust)
    for x in range(2, 14):
        pie.set(x, 6, mix(crust, (255, 255, 255, 255), 0.25))
        pie.set(x, 13, crust_lo)
    pie.rect(3, 7, 12, 10, filling)
    for x in range(3, 13, 2):
        pie.set(x, 8, mix(filling, (255, 255, 255, 255), 0.4))
    for x in range(2, 14, 3):
        pie.set(x, 11, crust_lo)
    bevel(pie)
    pie.outline(mix(hex_rgba("#3A2E16"), (0, 0, 0, 255), 0.35))
    emit(pie, ITEMS, "voidbound_ender_fruit_pie", roughness=204,
         emissive_from=filling[:3], emissive_gain=0.8, emissive_threshold=0.3)


def block_decor_set():
    """Chiselled bricks, a pillar and tiles - the finishing blocks."""
    brick = mix(PALETTE["endstone_dark"], hex_rgba("#CFC8A4"), 0.5)
    brick_lo = mix(brick, PALETTE["void"], 0.4)
    mortar = mix(brick_lo, (0, 0, 0, 255), 0.35)
    lit = PALETTE["void_lit"]

    chiselled = Canvas(16)

    def chisel(x, y, _cur):
        n = fbm(x * 1.8, y * 1.8, 16, 9610, octaves=3, base_period=4)
        base = mix(brick_lo, brick, n)
        if x in (0, 15) or y in (0, 15):
            return mortar
        # An inset panel with a rift glyph cut into it.
        if 2 <= x <= 13 and 2 <= y <= 13:
            if x in (2, 13) or y in (2, 13):
                return shade(base, -0.28)
            on_glyph = abs(x - 8) + abs(y - 8) in (2, 5) or (x == 8 and 4 <= y <= 12)
            if on_glyph:
                return mix(base, lit, 0.55)
        return base

    chiselled.each(chisel)
    emit(chiselled, BLOCKS, "voidbound_chiseled_ender_bricks", roughness=236,
         emissive_from=lit[:3], emissive_gain=0.7, emissive_threshold=0.36)

    pillar = Canvas(16)

    def pillar_face(x, y, _cur):
        n = fbm(x * 2.6, y * 0.9, 16, 9620, octaves=3, base_period=4)
        base = mix(brick_lo, brick, n)
        if x in (0, 1, 14, 15):
            return shade(base, -0.26)             # fluted edges
        if y in (0, 15):
            return mortar                          # collar
        if x in (5, 10):
            return shade(base, -0.16)
        return base

    pillar.each(pillar_face)
    emit(pillar, BLOCKS, "voidbound_ender_pillar", roughness=238)

    pillar_top = Canvas(16)

    def pillar_cap(x, y, _cur):
        d = max(abs(x - 7.5), abs(y - 7.5))
        n = fbm(x * 2, y * 2, 16, 9621, octaves=2, base_period=4)
        base = mix(brick_lo, brick, n)
        if d > 6.2:
            return mortar
        if d > 4.4:
            return shade(base, -0.2)
        return mix(base, lit, 0.18)

    pillar_top.each(pillar_cap)
    emit(pillar_top, BLOCKS, "voidbound_ender_pillar_top", roughness=234,
         emissive_from=lit[:3], emissive_gain=0.55, emissive_threshold=0.42)

    tiles = Canvas(16)

    def tile_face(x, y, _cur):
        n = fbm(x * 2.2, y * 2.2, 16, 9630, octaves=3, base_period=4)
        base = mix(brick_lo, brick, n)
        if x % 8 == 0 or y % 8 == 0:
            return mortar
        if (x // 8 + y // 8) % 2 == 0:
            return shade(base, 0.12)
        return shade(base, -0.10)

    tiles.each(tile_face)
    speckle(tiles, 9631, 0.05, [shade(brick, 0.22), shade(brick_lo, -0.2)])
    emit(tiles, BLOCKS, "voidbound_ender_tiles", roughness=240)


# --------------------------------------------------------------------------
# The End forest
# --------------------------------------------------------------------------


def block_ender_log():
    """Pale, chalky bark with dark rift seams running the grain."""
    bark = hex_rgba("#6E5F86")
    bark_lo = mix(bark, PALETTE["void"], 0.55)
    bark_hi = mix(bark, hex_rgba("#CFC4E2"), 0.45)
    seam = mix(PALETTE["void_lit"], PALETTE["void"], 0.35)

    side = Canvas(16)

    def grain(x, y, _cur):
        # Vertical grain: noise stretched hard on x so it reads as fibre.
        n = fbm(x * 3.4, y * 0.7, 16, 7300, octaves=3, base_period=4)
        base = mix(bark_lo, bark, n)
        if n > 0.62:
            base = mix(base, bark_hi, (n - 0.62) / 0.38 * 0.8)
        return base

    side.each(grain)
    veins(side, 7301, 2, seam, 18, wobble=0.25, width=1)
    emit(side, BLOCKS, "voidbound_ender_log", roughness=236,
         emissive_from=seam[:3], emissive_gain=0.55, emissive_threshold=0.42)

    top = Canvas(16)

    def rings(x, y, _cur):
        d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
        n = fbm(x * 2, y * 2, 16, 7302, octaves=2, base_period=4)
        ring = (math.sin(d * 2.1 + n * 1.4) + 1) * 0.5
        return mix(bark_lo, bark_hi, ring * 0.75)

    top.each(rings)
    radial(top, 8, 8, 2.2, seam, mix(bark, seam, 0.2), falloff=1.4)
    emit(top, BLOCKS, "voidbound_ender_log_top", roughness=232,
         emissive_from=seam[:3], emissive_gain=0.6, emissive_threshold=0.4)


def block_ender_leaves():
    """Airy violet canopy - alpha-tested, so it needs real holes."""
    c = Canvas(16)
    leaf = hex_rgba("#7B3FA8")
    leaf_lo = mix(leaf, PALETTE["void"], 0.5)
    leaf_hi = mix(leaf, hex_rgba("#D8A8F0"), 0.5)

    def canopy(x, y, _cur):
        n = fbm(x * 2.6, y * 2.6, 16, 7310, octaves=3, base_period=4)
        clump = fbm(x * 1.2, y * 1.2, 16, 7311, octaves=2, base_period=4)
        if clump < 0.36:
            return TRANSPARENT          # gaps you can see sky through
        base = mix(leaf_lo, leaf, n)
        if n > 0.66:
            return mix(base, leaf_hi, (n - 0.66) / 0.34)
        return base

    c.each(canopy)
    speckle(c, 7312, 0.05, [leaf_hi, shade(leaf_lo, -0.25)])
    emit(c, BLOCKS, "voidbound_ender_leaves", roughness=222,
         emissive_from=leaf_hi[:3], emissive_gain=0.45, emissive_threshold=0.5)


def block_ender_bush():
    """Low bush carrying ripe fruit - the ground-level source."""
    c = Canvas(16)
    stem = mix(PALETTE["void"], hex_rgba("#7B6A92"), 0.55)
    leaf = hex_rgba("#6E3A96")
    leaf_hi = mix(leaf, hex_rgba("#C89AE8"), 0.5)
    fruit = hex_rgba("#3FE0C4")

    rng = Rng(7320)
    for base_x in (4, 8, 11):
        px = base_x
        for y in range(15, 8, -1):
            px += rng.range(-0.3, 0.3)
            c.blend(int(round(px)), y, stem)
    for cx, cy, r in ((5, 8, 3.2), (9, 6, 3.6), (11, 9, 2.8)):
        for y in range(16):
            for x in range(16):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / r
                if d <= 1.0 and rng.next() > d * 0.55:
                    c.blend(x, y, mix(leaf_hi, leaf, min(1.0, d * 1.1)))
    for fx, fy in ((5, 9), (10, 6), (12, 10)):
        c.blend(fx, fy, fruit)
        c.blend(fx + 1, fy, mix(fruit, leaf, 0.4))
        c.blend(fx, fy + 1, mix(fruit, leaf, 0.55))
    emit(c, BLOCKS, "voidbound_ender_bush", roughness=200,
         emissive_from=fruit[:3], emissive_gain=1.15, emissive_threshold=0.2)


def item_ender_fruit():
    """A dense teal fruit with a pale rind seam."""
    c = Canvas(16)
    flesh = hex_rgba("#3FE0C4")
    flesh_deep = mix(flesh, PALETTE["void"], 0.55)
    rind = hex_rgba("#DFF7F0")
    radial(c, 7.6, 9.0, 5.6, flesh, flesh_deep, falloff=1.2)
    radial(c, 5.8, 7.0, 2.2, rind, (63, 224, 196, 0), falloff=1.1)
    for y in range(5, 14):
        c.blend(11, y, mix(rind, flesh_deep, 0.45))
    for y in range(2, 6):
        c.set(9, y, mix(PALETTE["void"], hex_rgba("#7B6A92"), 0.5))
    c.set(10, 2, mix(flesh, rind, 0.4))
    c.set(8, 2, mix(flesh, rind, 0.4))
    bevel(c)
    c.outline(mix(PALETTE["void"], (0, 0, 0, 255), 0.55))
    emit(c, ITEMS, "voidbound_ender_fruit", roughness=140,
         emissive_from=flesh[:3], emissive_gain=1.2, emissive_threshold=0.18)


def item_sovereign_crown():
    """The Sovereign's crown - the reason to fight it twice."""
    c = Canvas(16)
    gold = hex_rgba("#E8C766")
    gold_lo = hex_rgba("#8A6E28")
    gem = hex_rgba("#E75BE0")
    for x in range(2, 14):
        c.set(x, 10, gold)
        c.set(x, 11, gold_lo)
    # Five points, tallest in the centre.
    for x, height in ((2, 6), (5, 4), (8, 2), (11, 4), (13, 6)):
        for y in range(height, 10):
            c.set(x, y, gold if y > height else mix(gold, rind_white(), 0.35))
            c.set(x + 1, y, gold_lo)
    for gx, gy in ((3, 8), (8, 5), (12, 8)):
        c.set(gx, gy, gem)
        c.blend(gx + 1, gy, mix(gem, gold, 0.5))
    c.set(8, 4, shade(gem, 0.5))
    bevel(c, light=0.3, dark=0.28)
    c.outline(mix(hex_rgba("#3A2A08"), (0, 0, 0, 255), 0.35))
    emit(c, ITEMS, "voidbound_sovereign_crown", metalness=190, roughness=52,
         emissive_from=gem[:3], emissive_gain=1.2, emissive_threshold=0.3)


def rind_white():
    return hex_rgba("#FFF4CC")


def entity_echo_warden():
    """The Echo Warden: the sentinel's build in older, gilded stone."""
    c = Canvas(64, 64)
    stone = mix(PALETTE["endstone_dark"], PALETTE["void"], 0.72)
    stone_hi = mix(stone, hex_rgba("#C9B98A"), 0.42)
    gold = hex_rgba("#D8B45C")
    core = hex_rgba("#FF9C3F")

    def masonry(seed, gilded=False):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 1.4, fy * 1.4, 16, seed, octaves=3, base_period=4)
            base = mix(stone, stone_hi, n)
            if fy % 4 == 0:
                base = shade(base, -0.24)
            elif (fx + (fy // 4) * 2) % 5 == 0:
                base = shade(base, -0.18)
            if gilded and face in ("north", "south") and fy in (2, fh - 3):
                return gold
            if gilded and face in ("east", "west") and fx == fw // 2:
                return mix(base, gold, 0.55)
            return base
        return paint

    paint_box(c, 0, 0, 10, 14, 6, masonry(8810, gilded=True))
    paint_box(c, 0, 22, 8, 8, 8, masonry(8811, gilded=True))
    paint_box(c, 34, 0, 4, 14, 4, masonry(8812))
    paint_box(c, 34, 20, 4, 14, 4, masonry(8813))
    paint_box(c, 0, 40, 4, 12, 4, masonry(8814))
    paint_box(c, 18, 40, 4, 12, 4, masonry(8815))

    def furnace(_face, fx, fy, fw, fh):
        dx = (fx + 0.5) / fw - 0.5
        dy = (fy + 0.5) / fh - 0.5
        d = min(1.0, math.hypot(dx, dy) * 2.2)
        return mix(shade(core, 0.6), mix(core, PALETTE["void"], 0.55), d)

    paint_box(c, 36, 40, 4, 4, 1, furnace)
    for x, y in ((10, 33), (13, 33), (10, 34), (13, 34)):
        c.set(x, y, shade(core, 0.5))

    emit(c, ENTITY, "voidbound_echo_warden", metalness=60, roughness=228,
         emissive_from=core[:3], emissive_gain=1.3, emissive_threshold=0.2)


def block_building_set():
    """Four worked blocks, so the End's materials can actually be built with."""
    # Planks: milled ender log, grain running one way.
    planks = Canvas(16)
    plank = hex_rgba("#7E6D96")
    plank_lo = mix(plank, PALETTE["void"], 0.45)
    plank_hi = mix(plank, hex_rgba("#D2C6E4"), 0.4)

    def plank_face(x, y, _cur):
        row = y // 4
        n = fbm(x * 3.0, y * 0.8, 16, 9400 + row * 31, octaves=3, base_period=4)
        base = mix(plank_lo, plank, n)
        if n > 0.66:
            base = mix(base, plank_hi, (n - 0.66) / 0.34 * 0.7)
        if y % 4 == 0:
            return shade(base, -0.30)              # board seam
        # Stagger the butt joints like vanilla planks do.
        if (x + row * 5) % 8 == 0:
            return shade(base, -0.20)
        return base

    planks.each(plank_face)
    emit(planks, BLOCKS, "voidbound_ender_planks", roughness=238)

    # Ender bricks: coursed masonry from shattered end stone.
    bricks = Canvas(16)
    brick = mix(PALETTE["endstone_dark"], hex_rgba("#CFC8A4"), 0.5)
    brick_lo = mix(brick, PALETTE["void"], 0.4)
    mortar = mix(brick_lo, (0, 0, 0, 255), 0.35)

    def brick_face(x, y, _cur):
        row = y // 4
        n = fbm(x * 1.8, y * 1.8, 16, 9410, octaves=3, base_period=4)
        if y % 4 == 0:
            return mortar
        if (x + row * 4) % 8 == 0:
            return mortar
        return mix(brick_lo, brick, n)

    bricks.each(brick_face)
    speckle(bricks, 9411, 0.05, [shade(brick, 0.2), shade(brick_lo, -0.2)])
    emit(bricks, BLOCKS, "voidbound_ender_bricks", roughness=242)

    # Crystal bricks: cut void crystal, still lit from within.
    crystal = Canvas(16)
    deep = PALETTE["void"]
    lit = PALETTE["void_lit"]

    def crystal_face(x, y, _cur):
        row = y // 8
        n = fbm(x * 2.2, y * 2.2, 16, 9420, octaves=3, base_period=4)
        base = mix(deep, lit, min(1.0, n * 0.95))
        if y % 8 == 0 or (x + row * 4) % 8 == 0:
            return mix(shade(deep, -0.25), lit, 0.15)
        return base

    crystal.each(crystal_face)
    emit(crystal, BLOCKS, "voidbound_void_crystal_bricks", roughness=64,
         emissive_from=lit[:3], emissive_gain=0.95, emissive_threshold=0.24)

    # Echo lamp: a full-brightness lamp, the End's answer to glowstone.
    lamp = Canvas(16)
    frame = mix(PALETTE["endstone_dark"], PALETTE["void"], 0.5)
    glow = PALETTE["lumen_lit"]
    lamp.fill(frame)
    for cx, cy in ((4, 4), (11, 4), (4, 11), (11, 11), (8, 8)):
        radial(lamp, cx + 0.5, cy + 0.5, 3.4, shade(glow, 0.45), frame, falloff=1.5)
    speckle(lamp, 9430, 0.06, [shade(glow, 0.6), shade(frame, -0.2)])
    emit(lamp, BLOCKS, "voidbound_echo_lamp", roughness=110,
         emissive_from=glow[:3], emissive_gain=1.5, emissive_threshold=0.1)


def entity_void_serpent():
    """64x64: a segmented eel of the void, dark with a lit dorsal line."""
    c = Canvas(64, 64)
    scale_dark = mix(PALETTE["void"], (0, 0, 0, 255), 0.25)
    scale_lit = mix(PALETTE["void"], PALETTE["void_lit"], 0.55)
    belly = mix(scale_dark, hex_rgba("#8E7BB0"), 0.45)
    maw = hex_rgba("#FF6BD8")

    def hide(seed, dorsal=True):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 2.1, fy * 2.1, 16, seed, octaves=3, base_period=4)
            base = mix(scale_dark, mix(scale_dark, scale_lit, 0.5), n)
            # Diamond scale pattern.
            if (fx + fy) % 3 == 0:
                base = shade(base, 0.16)
            if face == "bottom":
                return mix(base, belly, 0.7)
            if dorsal and face == "top" and abs(fx - (fw - 1) / 2.0) < 0.9:
                return scale_lit
            return base
        return paint

    paint_box(c, 0, 0, 6, 5, 6, hide(9501))

    def head(face, fx, fy, fw, fh):
        base = hide(9502)(face, fx, fy, fw, fh)
        if face == "north":
            if fy == 1 and fx in (1, fw - 2):
                return maw                       # eyes
            if fy >= fh - 2:
                return mix(base, maw, 0.45)      # lit throat
        return base

    paint_box(c, 0, 0, 6, 5, 6, head)

    def jaw(face, fx, fy, fw, fh):
        base = mix(scale_dark, belly, 0.35)
        if face == "north" and fy == 0 and fx % 2 == 0:
            return hex_rgba("#F2E8FF")           # teeth
        return base

    paint_box(c, 0, 13, 5, 2, 4, jaw)
    paint_box(c, 26, 0, 5, 5, 5, hide(9503))     # shared by every body segment
    paint_box(c, 26, 12, 3, 3, 5, hide(9504))    # tail

    def fin(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(scale_lit, mix(scale_dark, maw, 0.3), t)

    paint_box(c, 0, 21, 1, 4, 6, fin)
    paint_box(c, 16, 21, 1, 4, 6, fin)

    emit(c, ENTITY, "voidbound_void_serpent", roughness=150,
         emissive_from=maw[:3], emissive_gain=1.2, emissive_threshold=0.24)


def entity_glimmerfin():
    """64x32: a translucent ray that drifts between islands."""
    c = Canvas(64, 32)
    membrane = hex_rgba("#3E7FA8")
    membrane_hi = hex_rgba("#9FE4F5")
    core = hex_rgba("#DFF7FF")

    def body(face, fx, fy, fw, fh):
        n = fbm(fx * 2, fy * 2, 16, 9510, octaves=3, base_period=4)
        base = mix(membrane, membrane_hi, n * 0.7)
        if face == "top":
            return mix(base, core, 0.3)
        if face == "north" and fy == 1 and fx in (0, fw - 1):
            return core                          # eyes
        return base

    paint_box(c, 0, 0, 4, 3, 8, body)

    def wing(face, fx, fy, fw, fh):
        # Thin toward the trailing edge, and veined along the span.
        span = fx / float(max(1, fw - 1))
        n = fbm(fx * 2.4, fy * 2.4, 16, 9511, octaves=2, base_period=4)
        base = mix(membrane_hi, membrane, min(1.0, span * 1.15 + n * 0.2))
        if fx % 3 == 0:
            return mix(base, core, 0.35)
        if face in ("top", "bottom") and span > 0.82:
            return mix(base, membrane, 0.6)
        return base

    paint_box(c, 0, 12, 8, 1, 10, wing)

    def tail(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(membrane_hi, membrane, t)

    paint_box(c, 38, 0, 1, 1, 6, tail)

    emit(c, ENTITY, "voidbound_glimmerfin", roughness=96,
         emissive_from=core[:3], emissive_gain=1.0, emissive_threshold=0.3)


def entity_endstone_golem():
    """64x64: quarried end stone bound with crystal - a guardian, not a threat."""
    c = Canvas(64, 64)
    rock = mix(PALETTE["endstone"], PALETTE["endstone_dark"], 0.4)
    rock_lo = mix(rock, PALETTE["void"], 0.32)
    rock_hi = mix(rock, hex_rgba("#F2EFD0"), 0.4)
    binding = PALETTE["lumen_lit"]

    def stone(seed, bound=False):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 1.5, fy * 1.5, 16, seed, octaves=3, base_period=4)
            base = mix(rock_lo, rock, n)
            if n > 0.7:
                base = mix(base, rock_hi, (n - 0.7) / 0.3 * 0.85)
            # Cracks, filled with crystal where the stone was rebound.
            crack = fbm(fx * 3.2, fy * 3.2, 16, seed + 71, octaves=2, base_period=4)
            if crack > 0.76:
                return mix(base, binding, 0.75) if bound else shade(base, -0.35)
            if face == "bottom":
                return shade(base, -0.2)
            return base
        return paint

    paint_box(c, 0, 0, 10, 12, 8, stone(9520, bound=True))

    def head(face, fx, fy, fw, fh):
        base = stone(9521)(face, fx, fy, fw, fh)
        if face == "north" and fy in (2, 3) and fx in (1, fw - 2):
            return shade(binding, 0.45)          # eyes
        return base

    paint_box(c, 0, 22, 7, 6, 7, head)
    paint_box(c, 38, 0, 4, 12, 4, stone(9522, bound=True))
    paint_box(c, 38, 20, 4, 12, 4, stone(9523, bound=True))
    paint_box(c, 0, 37, 4, 8, 4, stone(9524))
    paint_box(c, 18, 37, 4, 8, 4, stone(9525))

    emit(c, ENTITY, "voidbound_endstone_golem", roughness=246,
         emissive_from=binding[:3], emissive_gain=0.95, emissive_threshold=0.3)


def entity_astral_whale():
    """128x128: the End's leviathan - a slow, harmless giant with a lit belly."""
    c = Canvas(128, 128)
    hide = mix(PALETTE["void"], hex_rgba("#2E4A78"), 0.55)
    hide_hi = mix(hide, hex_rgba("#8FA8D8"), 0.4)
    belly = mix(hex_rgba("#6FD8F0"), hide, 0.35)
    star = hex_rgba("#EAF6FF")

    def flank(seed, constellations=False):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 1.1, fy * 1.1, 32, seed, octaves=4, base_period=4)
            base = mix(hide, hide_hi, n * 0.7)
            if face == "bottom":
                # Bioluminescent underside, brightest along the midline.
                mid = 1.0 - abs(fx - (fw - 1) / 2.0) / max(1.0, (fw - 1) / 2.0)
                return mix(base, belly, 0.35 + mid * 0.5)
            if face == "top":
                base = shade(base, -0.12)
            # A scatter of star-points across the flanks, like a night sky.
            if constellations and face in ("east", "west"):
                spark = fbm(fx * 4.3, fy * 4.3, 32, seed + 313, octaves=2, base_period=4)
                if spark > 0.86:
                    return star
                if spark > 0.80:
                    return mix(base, star, 0.5)
            return base
        return paint

    paint_box(c, 0, 0, 16, 14, 40, flank(9701, constellations=True))
    paint_box(c, 0, 56, 14, 12, 14, flank(9702))

    def fin(_face, fx, fy, fw, fh):
        span = fx / float(max(1, fw - 1))
        return mix(hide_hi, mix(hide, belly, 0.3), min(1.0, span * 1.2))

    paint_box(c, 0, 84, 10, 2, 12, fin)
    paint_box(c, 46, 84, 10, 2, 12, fin)
    paint_box(c, 0, 100, 14, 2, 10, fin)

    emit(c, ENTITY, "voidbound_astral_whale", roughness=196,
         emissive_from=belly[:3], emissive_gain=0.95, emissive_threshold=0.3)


def entity_voidling():
    """32x32: a small, angry scrap of the void."""
    c = Canvas(32, 32)
    skin = mix(PALETTE["void"], (0, 0, 0, 255), 0.2)
    skin_hi = mix(skin, PALETTE["void_lit"], 0.45)
    eye = hex_rgba("#FF5BC8")

    def body(face, fx, fy, fw, fh):
        n = fbm(fx * 2.6, fy * 2.6, 16, 9710, octaves=3, base_period=4)
        base = mix(skin, skin_hi, n * 0.55)
        # A ragged lit seam down the spine.
        if face == "north" and abs(fx - (fw - 1) / 2.0) < 0.7 and fy > 1:
            return mix(base, PALETTE["void_lit"], 0.5)
        return base

    paint_box(c, 0, 0, 5, 6, 4, body)

    def head(face, fx, fy, fw, fh):
        base = mix(skin_hi, skin, 0.35)
        if face == "north" and fy == 1 and fx in (1, fw - 2):
            return eye
        if face == "north" and fy == 3 and fx % 2 == 0:
            return shade(skin, -0.4)             # gappy teeth
        return base

    paint_box(c, 0, 12, 5, 4, 4, head)

    def arm(_face, fx, fy, fw, fh):
        return mix(skin_hi, skin, fy / float(max(1, fh - 1)))

    paint_box(c, 20, 0, 2, 5, 2, arm)
    paint_box(c, 20, 10, 2, 5, 2, arm)

    emit(c, ENTITY, "voidbound_voidling", roughness=180,
         emissive_from=eye[:3], emissive_gain=1.3, emissive_threshold=0.22)


def entity_ender_beetle():
    """64x32: armoured grazer - the chitin is the point."""
    c = Canvas(64, 32)
    chitin = mix(PALETTE["void"], hex_rgba("#6E5A8C"), 0.6)
    chitin_hi = mix(chitin, hex_rgba("#C8B4E0"), 0.5)
    seam = PALETTE["lumen_lit"]

    def shell(face, fx, fy, fw, fh):
        n = fbm(fx * 1.7, fy * 1.7, 16, 9720, octaves=3, base_period=4)
        base = mix(chitin, chitin_hi, n)
        if face == "top":
            # Split carapace with a lit seam down the join.
            if abs(fx - (fw - 1) / 2.0) < 0.7:
                return mix(base, seam, 0.6)
            if fy % 3 == 0:
                return shade(base, -0.2)
            return shade(base, 0.14)
        if face == "bottom":
            return shade(base, -0.3)
        return base

    paint_box(c, 0, 0, 8, 4, 10, shell)

    def head(face, fx, fy, fw, fh):
        base = mix(chitin_hi, chitin, 0.4)
        if face == "north" and fy == 1 and fx in (0, fw - 1):
            return shade(seam, 0.45)
        return base

    paint_box(c, 0, 16, 5, 3, 4, head)

    def leg(_face, fx, fy, fw, fh):
        return mix(chitin_hi, chitin, fy / float(max(1, fh - 1)))

    for u, v in ((38, 0), (38, 5), (38, 10), (44, 0), (44, 5), (44, 10)):
        paint_box(c, u, v, 1, 3, 1, leg)

    emit(c, ENTITY, "voidbound_ender_beetle", roughness=210,
         emissive_from=seam[:3], emissive_gain=0.9, emissive_threshold=0.3)


def entity_void_titan():
    """64x64: the golem's build in blackened, rift-bound stone."""
    c = Canvas(64, 64)
    rock = mix(PALETTE["void"], (0, 0, 0, 255), 0.32)
    rock_hi = mix(rock, hex_rgba("#9A88C0"), 0.5)
    core = hex_rgba("#FF4FD0")

    def stone(seed, bound=False):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 1.4, fy * 1.4, 16, seed, octaves=3, base_period=4)
            base = mix(rock, rock_hi, n * 0.8)
            crack = fbm(fx * 3.0, fy * 3.0, 16, seed + 97, octaves=2, base_period=4)
            if crack > 0.70:
                # Where a golem shows crystal, the Titan shows raw rift.
                return mix(base, core, 0.85) if bound else shade(base, -0.4)
            if face == "bottom":
                return shade(base, -0.24)
            return base
        return paint

    paint_box(c, 0, 0, 10, 12, 8, stone(9730, bound=True))

    def head(face, fx, fy, fw, fh):
        base = stone(9731, bound=True)(face, fx, fy, fw, fh)
        if face == "north" and fy in (1, 2, 3) and fx in (1, fw - 2):
            return shade(core, 0.55)
        return base

    paint_box(c, 0, 22, 7, 6, 7, head)
    paint_box(c, 38, 0, 4, 12, 4, stone(9732, bound=True))
    paint_box(c, 38, 20, 4, 12, 4, stone(9733, bound=True))
    paint_box(c, 0, 37, 4, 8, 4, stone(9734))
    paint_box(c, 18, 37, 4, 8, 4, stone(9735))

    emit(c, ENTITY, "voidbound_void_titan", roughness=214,
         emissive_from=core[:3], emissive_gain=1.4, emissive_threshold=0.18)


# --------------------------------------------------------------------------
# The Rift Sovereign and its particles
# --------------------------------------------------------------------------

PARTICLE = os.path.join(ROOT, "RP", "textures", "particle")


def particle_atlas():
    """A 64x64 sheet of four 16x16 particle cells.

    Cell layout, referenced by uv in the particle JSON:
      (0,0)   soft glow      (16,0)  four-point spark
      (0,16)  crystal shard  (16,16) smoke puff
    """
    c = Canvas(64, 64)
    white = (255, 255, 255, 255)

    # Soft radial glow - tinted at runtime, so authored white.
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8) / 7.5
            if d <= 1.0:
                a = int(255 * (1.0 - d) ** 2.0)
                c.set(x, y, (255, 255, 255, a))

    # Spark: a bright core with four tapering arms.
    for i in range(8):
        a = int(255 * (1.0 - i / 8.0) ** 1.4)
        c.set(16 + 8 + i, 8, (255, 255, 255, a))
        c.set(16 + 8 - i, 8, (255, 255, 255, a))
        c.set(16 + 8, 8 + i, (255, 255, 255, a))
        c.set(16 + 8, 8 - i, (255, 255, 255, a))
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1)):
        c.set(16 + 8 + dx, 8 + dy, white)

    # Crystal shard: a small faceted diamond.
    for y in range(16):
        for x in range(16):
            if abs(x - 8) + abs(y - 8) * 0.7 <= 5:
                edge = (abs(x - 8) + abs(y - 8) * 0.7) / 5.0
                c.set(x, 16 + y, (255, 255, 255, int(255 * (1.0 - edge * 0.45))))

    # Smoke puff: soft noise blob.
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8) / 8.0
            n = fbm(x * 2, y * 2, 16, 6060, octaves=3, base_period=4)
            a = max(0.0, (1.0 - d) * (0.45 + n * 0.55))
            if a > 0.03:
                c.set(16 + x, 16 + y, (255, 255, 255, int(min(255, a * 210))))

    os.makedirs(PARTICLE, exist_ok=True)
    out(c, PARTICLE, "voidbound_particles")


# Boss UV layout on a 128x128 sheet, kept here so the geometry and the painter
# cannot drift apart.
SOVEREIGN_PARTS = [
    ("core", 0, 0, 10, 10, 10),
    ("shell_upper", 0, 22, 16, 6, 16),
    ("shell_lower", 0, 46, 16, 6, 16),
    ("spike_a", 66, 0, 2, 8, 2),
    ("spike_b", 66, 12, 2, 8, 2),
    ("spike_c", 66, 24, 2, 8, 2),
    ("spike_d", 66, 36, 2, 8, 2),
    ("mantle", 66, 48, 12, 14, 2),
    ("shard_a", 96, 0, 3, 3, 3),
    ("shard_b", 96, 10, 3, 3, 3),
    ("shard_c", 96, 20, 3, 3, 3),
    ("shard_d", 96, 30, 3, 3, 3),
    ("eye", 76, 66, 6, 2, 1),
]


def entity_rift_sovereign():
    """128x128 sheet: black basalt regalia around a magenta rift core."""
    c = Canvas(128, 128)
    regalia = mix(PALETTE["void"], (0, 0, 0, 255), 0.52)
    regalia_hi = mix(regalia, hex_rgba("#E56BD8"), 0.30)
    gold = hex_rgba("#C9A85C")
    core_hot = hex_rgba("#FFE4FA")
    core_mid = hex_rgba("#E75BE0")
    core_deep = hex_rgba("#5A0F7A")

    def paint_core(_face, fx, fy, fw, fh):
        dx = (fx + 0.5) / fw - 0.5
        dy = (fy + 0.5) / fh - 0.5
        d = min(1.0, math.hypot(dx, dy) * 2.1)
        n = fbm(fx * 2.4, fy * 2.4, 16, 9001, octaves=3, base_period=4)
        t = min(1.0, d * 0.8 + n * 0.28)
        return mix(core_hot, mix(core_mid, core_deep, t), min(1.0, t * 1.25))

    def paint_shell(seed, banded):
        def paint(face, fx, fy, fw, fh):
            n = fbm(fx * 1.3, fy * 1.3, 16, seed, octaves=3, base_period=4)
            base = mix(regalia, shade(regalia, 0.30), n)
            if face == "top":
                base = shade(base, 0.14)
            elif face == "bottom":
                base = shade(base, -0.24)
            # Inlaid gold banding around the rim of each shell.
            if banded and face in ("north", "south", "east", "west"):
                if fy == 1 or fy == fh - 2:
                    return mix(base, gold, 0.65)
                if fx % 4 == 0:
                    return mix(base, regalia_hi, 0.5)
            return base
        return paint

    def paint_spike(_face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        return mix(mix(core_mid, gold, 0.35), regalia, min(1.0, t * 1.2))

    def paint_mantle(face, fx, fy, fw, fh):
        t = fy / float(max(1, fh - 1))
        n = fbm(fx * 2, fy * 2, 16, 9100, octaves=2, base_period=4)
        base = mix(regalia, shade(regalia, 0.22), n * 0.6)
        # The hem burns out into rift light.
        if t > 0.62:
            return mix(base, core_mid, (t - 0.62) / 0.38 * 0.9)
        if face in ("north", "south") and fx % 3 == 0:
            return mix(base, regalia_hi, 0.35)
        return base

    def paint_shard(_face, fx, fy, fw, fh):
        t = (fx + fy) / float(max(1, fw + fh - 2))
        return mix(shade(core_mid, 0.4), core_deep, t)

    def paint_eye(_face, fx, fy, fw, fh):
        return mix(core_hot, core_mid, fx / float(max(1, fw - 1)))

    painters = {
        "core": paint_core,
        "shell_upper": paint_shell(9010, True),
        "shell_lower": paint_shell(9011, True),
        "mantle": paint_mantle,
        "eye": paint_eye,
    }
    for part, u, v, w, h, d in SOVEREIGN_PARTS:
        if part.startswith("spike"):
            painter = paint_spike
        elif part.startswith("shard"):
            painter = paint_shard
        else:
            painter = painters[part]
        paint_box(c, u, v, w, h, d, painter)

    emit(
        c,
        ENTITY,
        "voidbound_rift_sovereign",
        metalness=72,
        roughness=96,
        emissive_from=core_mid[:3],
        emissive_gain=1.45,
        emissive_threshold=0.12,
    )


# --------------------------------------------------------------------------
# The End sky
# --------------------------------------------------------------------------

ENVIRONMENT = os.path.join(ROOT, "RP", "textures", "environment")


def end_sky():
    """Replace the End's skybox tile: textures/environment/end_sky.png.

    The End sky is a cube, and the game tiles this one texture across all six
    faces. That creates two failure modes, and this pack hit both:

    - High-contrast, large features turn into visible wallpaper.
    - *Any* low-frequency variation makes each face average to a slightly
      different brightness, and the cube's edges become visible as seams.

    So there is no noise here at all. The base is a perfectly flat colour,
    which means every face averages identically and the corners disappear, and
    every bit of visible interest comes from stars. Movement comes from
    particles in front of the sky (see world/ambience.js), because Bedrock
    gives a pack no way to animate a skybox.

    Density is the whole game, and the first version got it badly wrong: 2358
    stars in a 128px tile is fourteen percent of every pixel, and at the
    distance a skybox is actually viewed that stops reading as stars and starts
    reading as film grain. A real night sky is mostly empty. So this is sparse
    - about three percent coverage - and it buys back the lost interest with
    *contrast* instead of count: a few genuinely bright stars with halos, over
    a scattering of faint ones, rather than a uniform wash of dim ones.
    """
    size = 128
    c = Canvas(size, size)
    c.fill(hex_rgba("#120A26"))

    rng = Rng(31337)
    tints = [
        hex_rgba("#FFFFFF"), hex_rgba("#F4E8FF"), hex_rgba("#D6C2FF"),
        hex_rgba("#A9D8FF"), hex_rgba("#FFC2E8"), hex_rgba("#FFE7C2"),
    ]

    # Three tiers, faintest first so brighter stars land on top. The faint tier
    # is the one that turns into grain, so it is the one kept smallest.
    for count, low, high in ((300, 0.10, 0.24), (110, 0.30, 0.52), (34, 0.60, 0.86)):
        for _ in range(count):
            sx, sy = rng.int(0, size - 1), rng.int(0, size - 1)
            c.set(sx, sy, mix(c.get(sx, sy), rng.pick(tints), rng.range(low, high)))

    # The handful that carry the sky. Full brightness with a soft halo, few
    # enough that the halo never reads as a repeating shape across the tile.
    for _ in range(14):
        sx, sy = rng.int(0, size - 1), rng.int(0, size - 1)
        tint = rng.pick(tints)
        c.set(sx, sy, tint)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = (sx + dx) % size, (sy + dy) % size
            c.set(nx, ny, mix(c.get(nx, ny), tint, 0.34))
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = (sx + dx) % size, (sy + dy) % size
            c.set(nx, ny, mix(c.get(nx, ny), tint, 0.12))

    os.makedirs(ENVIRONMENT, exist_ok=True)
    out(c, ENVIRONMENT, "end_sky")


# --------------------------------------------------------------------------
# Pack icons
# --------------------------------------------------------------------------


def pack_icon(path, accent):
    """128x128 emblem: a torn rift over the void, ringed by an End horizon."""
    size = 128
    c = Canvas(size, size)
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - 64, y - 64) / 78.0
            n = fbm(x * 0.25, y * 0.25, size, 909, octaves=4, base_period=8)
            base = mix(hex_rgba("#150C2E"), hex_rgba("#05030C"), min(1.0, d * 1.15))
            c.set(x, y, shade(base, (n - 0.5) * 0.22))
    # Horizon glow.
    radial(c, 64, 92, 74, (accent[0], accent[1], accent[2], 90), (0, 0, 0, 0), falloff=1.6)
    # The rift: a vertical tear with ragged edges and a white-hot centre.
    rng = Rng(4242)
    half = []
    width = 0.0
    for y in range(18, 110):
        t = (y - 18) / 92.0
        width = 13.0 * math.sin(math.pi * t) ** 1.35 + rng.range(-0.7, 0.7)
        half.append((y, max(0.6, width)))
    for y, w in half:
        for x in range(int(64 - w), int(64 + w) + 1):
            e = abs(x - 64) / w
            color = mix((255, 255, 255, 255), accent, min(1.0, e ** 0.65))
            c.blend(x, y, mix(color, (accent[0], accent[1], accent[2], 0), max(0.0, (e - 0.75) / 0.25)))
    for y, w in half:
        for side in (-1, 1):
            gx = 64 + side * (w + rng.range(0.5, 3.0))
            c.blend(int(gx), y, (accent[0], accent[1], accent[2], 120))
    # Floating shards to sell the scale.
    for _ in range(26):
        sx, sy = rng.range(8, 120), rng.range(8, 120)
        if abs(sx - 64) < 20:
            continue
        s = rng.int(1, 3)
        col = mix(accent, hex_rgba("#DCE0A8"), rng.range(0.0, 0.6))
        for oy in range(s):
            for ox in range(s):
                c.blend(int(sx) + ox, int(sy) + oy, (col[0], col[1], col[2], 210))
    c.save(path)


def item_material_set():
    """The four new crafting materials, drawn as four different kinds of object.

    A shard, a plate, an ingot and a core need to be told apart at 16px in a
    hotbar, so each gets its own silhouette rather than its own hue.
    """
    # Astral Shard - a pale blue splinter, the whale's drop.
    c = Canvas(16)
    _shard_silhouette(
        c,
        [(9, 1), (13, 6), (10, 15), (6, 14), (4, 6)],
        hex_rgba("#BFEFFF"),
        hex_rgba("#3D6FA8"),
    )
    veins(c, 8821, 2, hex_rgba("#EAF9FF"), 8, wobble=0.6)
    bevel(c, light=0.34, dark=0.26)
    c.outline(hex_rgba("#122238"))
    emit(c, ITEMS, "voidbound_astral_shard", roughness=58,
         emissive_from=(191, 239, 255), emissive_gain=1.15, emissive_threshold=0.30)

    # Void Chitin - a curved carapace plate with a ridged spine.
    c = Canvas(16)
    plate = hex_rgba("#4A3C62")
    plate_lo = hex_rgba("#241C34")
    sheen = hex_rgba("#68E2CC")
    for y in range(16):
        for x in range(16):
            # An ellipse squashed on Y reads as a shell rather than a stone.
            d = math.hypot((x + 0.5 - 8) / 6.4, (y + 0.5 - 8.5) / 5.2)
            if d > 1.0:
                continue
            c.set(x, y, mix(plate, plate_lo, d * 0.85))
    for i, x in enumerate(range(3, 14, 2)):
        for y in range(4, 13):
            if math.hypot((x + 0.5 - 8) / 6.4, (y + 0.5 - 8.5) / 5.2) > 0.95:
                continue
            c.blend(x, y, (sheen[0], sheen[1], sheen[2], 60 + 14 * (i % 3)))
    for y in range(4, 13):
        c.blend(8, y, shade(sheen, 0.1))
    bevel(c, light=0.28, dark=0.3)
    c.outline(hex_rgba("#120C1E"))
    emit(c, ITEMS, "voidbound_void_chitin", roughness=118,
         emissive_from=sheen[:3], emissive_gain=0.7, emissive_threshold=0.42)

    # Voidsteel Ingot - vanilla ingot footprint, violet alloy.
    c = Canvas(16)
    metal = hex_rgba("#8E6FC8")
    metal_lo = hex_rgba("#3E2C63")
    for y in range(5, 12):
        # Trapezoid: narrow at the top, wide at the base - the ingot read.
        inset = 5 - (y - 5) // 2
        for x in range(inset, 16 - inset):
            t = (y - 5) / 6.0
            c.set(x, y, mix(shade(metal, 0.22), metal_lo, t))
    for x in range(4, 12):
        c.blend(x, 6, shade(metal, 0.45))
    for x in range(2, 14):
        c.blend(x, 11, shade(metal_lo, -0.25))
    bevel(c, light=0.36, dark=0.3)
    c.outline(hex_rgba("#1B1230"))
    emit(c, ITEMS, "voidbound_voidsteel_ingot", metalness=225, roughness=44,
         emissive_from=(142, 111, 200), emissive_gain=0.5, emissive_threshold=0.55)

    # Titan Core - a caged sphere, unmistakably a boss drop.
    c = Canvas(16)
    cage = hex_rgba("#6B5A48")
    core_hot = hex_rgba("#FFD9A0")
    core_mid = hex_rgba("#E8703A")
    radial(c, 8, 8, 5.6, core_hot, mix(core_mid, hex_rgba("#3A1408"), 0.45))
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
            if d > 7.0:
                continue
            # Two meridians and one equator: a cage, not a ball of paint.
            if abs(x - 7.5) < 0.9 or abs(y - 7.5) < 0.9 or d > 6.1:
                c.set(x, y, shade(cage, 0.2 - 0.35 * (d / 7.0)))
    c.blend(6, 6, (255, 255, 255, 190))
    bevel(c, light=0.3, dark=0.3)
    c.outline(hex_rgba("#1A1108"))
    emit(c, ITEMS, "voidbound_titan_core", metalness=120, roughness=70,
         emissive_from=core_hot[:3], emissive_gain=1.6, emissive_threshold=0.24)


def block_waystone():
    """A carved travel marker: a rune-cut face, a worn cap, a glowing core.

    Because it is a full block, the *face* has to do all the work of saying
    "this is a device". So the sides get a deep inset frame with a vertical
    rune down the middle and a bright node at its heart, and the top gets a
    socket rather than more brickwork.
    """
    stone = mix(PALETTE["endstone_dark"], hex_rgba("#C9C2A0"), 0.42)
    stone_lo = mix(stone, PALETTE["void"], 0.48)
    seam = mix(stone_lo, (0, 0, 0, 255), 0.42)
    rune = hex_rgba("#7CE8FF")
    core = hex_rgba("#D6FBFF")

    side = Canvas(16)

    def face(x, y, _cur):
        n = fbm(x * 1.7, y * 1.7, 16, 4413, octaves=3, base_period=5)
        base = mix(stone_lo, stone, n)
        if x in (0, 15) or y in (0, 15):
            return seam
        # Inset panel.
        if 2 <= x <= 13 and 1 <= y <= 14:
            if x in (2, 13) or y in (1, 14):
                return shade(base, -0.32)
            # Rune: a spine with three crossbars and a diamond node.
            spine = x == 8 and 3 <= y <= 12
            bars = y in (5, 8, 11) and 5 <= x <= 11
            node = abs(x - 8) + abs(y - 8) <= 1
            if node:
                return core
            if spine or bars:
                return mix(base, rune, 0.72)
        return base

    side.each(face)
    emit(side, BLOCKS, "voidbound_waystone_side", roughness=214,
         emissive_from=rune[:3], emissive_gain=1.5, emissive_threshold=0.30)

    top = Canvas(16)

    def cap(x, y, _cur):
        n = fbm(x * 2.1, y * 2.1, 16, 4414, octaves=3, base_period=5)
        base = mix(stone_lo, stone, n)
        if x in (0, 15) or y in (0, 15):
            return seam
        d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
        if d <= 2.2:
            return mix(core, rune, min(1.0, d / 2.2))   # the socket, lit
        if d <= 3.4:
            return shade(base, -0.34)                    # its rim, in shadow
        # Four spokes running out to the edges, so the cap reads as machined.
        if (abs(x - 7.5) < 0.9 or abs(y - 7.5) < 0.9) and d <= 6.6:
            return mix(base, rune, 0.30)
        return base

    top.each(cap)
    emit(top, BLOCKS, "voidbound_waystone_top", roughness=210,
         emissive_from=rune[:3], emissive_gain=1.5, emissive_threshold=0.30)


def block_flora_and_stone():
    """A sapling, a chitin block, polished end stone and cracked bricks."""
    # Ender sapling: the thicket in miniature, so it reads as the same plant.
    sap = Canvas(16)
    stem = mix(PALETTE["void"], hex_rgba("#8A78A4"), 0.6)
    leaf = hex_rgba("#7B3FA8")
    leaf_hi = mix(leaf, hex_rgba("#D6A8F0"), 0.55)
    bud = hex_rgba("#3FE0C4")

    rng = Rng(5150)
    for y in range(15, 7, -1):
        sap.set(8, y, stem if y % 3 else shade(stem, 0.18))
    for dx, dy in ((-1, 11), (1, 12), (-1, 13)):
        sap.blend(8 + dx, dy, shade(stem, -0.2))
    for cx, cy, r in ((8, 6, 4.2), (5.5, 8.5, 2.6), (10.5, 8.5, 2.6)):
        for y in range(16):
            for x in range(16):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / r
                if d <= 1.0 and rng.next() > d * 0.5:
                    sap.blend(x, y, mix(leaf_hi, leaf, min(1.0, d * 1.15)))
    for bx, by in ((6, 6), (10, 5), (8, 9)):
        sap.blend(bx, by, bud)
    emit(sap, BLOCKS, "voidbound_ender_sapling", roughness=204,
         emissive_from=bud[:3], emissive_gain=1.0, emissive_threshold=0.24)

    # Void chitin block: overlapping plates, the beetle's drop stacked up.
    chitin = Canvas(16)
    plate = hex_rgba("#4A3C62")
    plate_lo = mix(plate, PALETTE["void"], 0.55)
    sheen = hex_rgba("#68E2CC")

    def chitin_face(x, y, _cur):
        row = y // 4
        # Offset rows so the plates interlock rather than tile as a grid.
        col = (x + row * 2) // 4
        n = fbm(x * 2.4, y * 2.4, 16, 7710 + row * 17 + col * 3, octaves=3, base_period=4)
        base = mix(plate_lo, plate, n)
        local_y = y % 4
        if local_y == 0:
            return shade(base, -0.36)                    # plate lip
        if local_y == 1:
            return mix(base, sheen, 0.20)                # the light catching it
        if (x + row * 2) % 4 == 0:
            return shade(base, -0.24)
        return base

    chitin.each(chitin_face)
    emit(chitin, BLOCKS, "voidbound_void_chitin_block", roughness=128,
         emissive_from=sheen[:3], emissive_gain=0.6, emissive_threshold=0.46)

    # Polished end stone: the same substrate, worked flat.
    polished = stone_base(3311, PALETTE["endstone"], PALETTE["endstone_dark"], contrast=0.12)

    def polish(x, y, cur):
        # A shallow chamfer reads as "cut and smoothed" at this size.
        if x == 0 or y == 0:
            return shade(cur, 0.16)
        if x == 15 or y == 15:
            return shade(cur, -0.16)
        return cur

    polished.each(polish)
    emit(polished, BLOCKS, "voidbound_polished_end_stone", roughness=170)

    # Cracked ender bricks: the coursed masonry, broken open.
    brick = mix(PALETTE["endstone_dark"], hex_rgba("#CFC8A4"), 0.5)
    brick_lo = mix(brick, PALETTE["void"], 0.4)
    mortar = mix(brick_lo, (0, 0, 0, 255), 0.35)
    cracked = Canvas(16)

    def cracked_face(x, y, _cur):
        row = y // 4
        n = fbm(x * 2.2, y * 2.2, 16, 9440 + row * 13, octaves=3, base_period=4)
        base = mix(brick_lo, brick, n)
        if y % 4 == 0:
            return mortar
        if (x + row * 6) % 8 == 0:
            return mortar
        return shade(base, -0.06)

    cracked.each(cracked_face)
    # Fracture lines drawn after the masonry, so they cut across the courses.
    veins(cracked, 4477, 5, shade(mortar, -0.3), 13, wobble=1.5)
    veins(cracked, 4478, 3, shade(brick_lo, -0.35), 8, wobble=1.9)
    emit(cracked, BLOCKS, "voidbound_cracked_ender_bricks", roughness=244)


def block_end_detail():
    """Four pieces of natural clutter: vines, clusters, moss and shrooms.

    The End reads as empty largely because every surface is the same flat
    yellow and every island edge just stops. These are the small things that
    make somewhere look inhabited by its own geology - growth on the ground,
    growth hanging off the underside, and a second stone colour so the terrain
    is not one tone from horizon to horizon.
    """
    # Ender vines: strands hanging from an overhang, thinning as they fall.
    vines = Canvas(16)
    cord = mix(PALETTE["void"], hex_rgba("#8E5FB8"), 0.62)
    cord_hi = mix(cord, hex_rgba("#E0B8F5"), 0.45)
    bead = hex_rgba("#5FE8D2")
    rng = Rng(6270)
    for start_x in (2, 5, 8, 11, 14):
        px = float(start_x)
        # Each strand ends at its own depth, so the fringe is ragged.
        depth = rng.int(8, 16)
        for y in range(depth):
            px += rng.range(-0.35, 0.35)
            x = int(round(px)) % 16
            thin = y > depth - 4
            vines.blend(x, y, mix(cord_hi, cord, min(1.0, y / 9.0)))
            if not thin:
                vines.blend((x + 1) % 16, y, shade(cord, -0.22))
            if rng.chance(0.12):
                vines.blend(x, y, bead)
    emit(vines, BLOCKS, "voidbound_ender_vines", roughness=206,
         emissive_from=bead[:3], emissive_gain=1.1, emissive_threshold=0.3)

    # Echo crystal cluster: a splay of shards from a common root.
    cluster = Canvas(16)
    shard = hex_rgba("#6FE6D8")
    shard_lo = mix(shard, PALETTE["void"], 0.6)
    for base_x, tip_x, tip_y, width in (
        (7, 4, 3, 1.6), (8, 8, 1, 2.0), (9, 12, 5, 1.4), (6, 5, 8, 1.1), (10, 11, 9, 1.0)
    ):
        steps = 15 - tip_y
        for i in range(steps + 1):
            t = i / max(1, steps)
            x = base_x + (tip_x - base_x) * t
            y = 15 - (15 - tip_y) * t
            half = max(0.5, width * (1.0 - t * 0.85))
            for ox in range(int(-half), int(half) + 1):
                px = int(round(x)) + ox
                if 0 <= px < 16:
                    cluster.blend(px, int(round(y)),
                                  mix(shard, shard_lo, min(1.0, t * 0.5 + abs(ox) * 0.3)))
        cluster.blend(int(round(tip_x)), tip_y, (235, 255, 252, 255))
    emit(cluster, BLOCKS, "voidbound_echo_cluster", roughness=48,
         emissive_from=shard[:3], emissive_gain=1.5, emissive_threshold=0.22)

    # Mossy end stone: the substrate again, with growth taking the low ground.
    moss = stone_base(2814, PALETTE["endstone"], PALETTE["endstone_dark"], contrast=0.26)
    growth = hex_rgba("#5E8F6A")
    growth_lo = mix(growth, PALETTE["void"], 0.45)

    def creep(x, y, cur):
        # Moss follows one noise field and ignores the stone's own, so the two
        # patterns cross instead of tracing each other.
        n = fbm(x * 1.5, y * 1.5, 16, 2815, octaves=3, base_period=6)
        if n < 0.52:
            return cur
        t = min(1.0, (n - 0.52) / 0.36)
        return mix(cur, mix(growth_lo, growth, t), 0.35 + t * 0.55)

    moss.each(creep)
    speckle(moss, 2816, 0.05, [mix(growth, hex_rgba("#B8E8C4"), 0.5), shade(growth_lo, -0.2)])
    emit(moss, BLOCKS, "voidbound_mossy_end_stone", roughness=232)

    # Pale shroom: a stubby cap on a short stalk, lit from underneath.
    shroom = Canvas(16)
    stalk = hex_rgba("#D8CFE8")
    cap = hex_rgba("#F0E4FF")
    gill = hex_rgba("#9C5FD6")
    for y in range(9, 15):
        shroom.set(7, y, stalk)
        shroom.set(8, y, shade(stalk, -0.2))
    for y in range(4, 10):
        spread = 6 - abs(y - 7)
        for x in range(8 - spread, 9 + spread):
            if not 0 <= x < 16:
                continue
            top = y < 8
            shroom.blend(x, y, cap if top else mix(gill, cap, 0.35))
    for x in range(3, 13, 2):
        shroom.blend(x, 9, gill)
    shroom.blend(6, 5, (255, 255, 255, 255))
    emit(shroom, BLOCKS, "voidbound_pale_shroom", roughness=176,
         emissive_from=cap[:3], emissive_gain=1.2, emissive_threshold=0.42)


# --------------------------------------------------------------------------


def main():
    for folder in (BLOCKS, ITEMS, ENTITY, ARMOR, ENVIRONMENT, PARTICLE):
        os.makedirs(folder, exist_ok=True)

    recipes = [
        block_shattered_end_stone,
        block_verdant_end_stone,
        block_echo_ore,
        block_void_crystal,
        block_void_glass,
        block_voidbloom,
        block_lumen_bulb,
        block_rift_lantern,
        item_echo_shard,
        item_void_crystal,
        item_rift_compass,
        item_lumen_berry,
        item_raw_haunch,
        item_cooked_haunch,
        item_echo_bread,
        tool_set,
        entity_lumen_wisp,
        entity_rift_stalker,
        entity_void_moth,
        entity_echo_sentinel,
        entity_chorus_hopper,
        entity_shard_wraith,
        entity_crystal_crawler,
        entity_rift_sovereign,
        entity_echo_warden,
        entity_void_serpent,
        entity_glimmerfin,
        entity_endstone_golem,
        entity_astral_whale,
        entity_voidling,
        entity_ender_beetle,
        entity_void_titan,
        block_ender_log,
        block_ender_leaves,
        block_ender_bush,
        block_building_set,
        block_decor_set,
        block_waystone,
        block_flora_and_stone,
        block_end_detail,
        item_gameplay_set,
        item_ender_fruit,
        item_sovereign_crown,
        item_material_set,
        particle_atlas,
        armor_layers,
        item_void_helmet,
        item_void_chestplate,
        item_void_leggings,
        item_void_boots,
        end_sky,
    ]
    for recipe in recipes:
        recipe()
        print("  generated", recipe.__name__)

    pack_icon(os.path.join(ROOT, "BP", "pack_icon.png"), PALETTE["void_lit"])
    pack_icon(os.path.join(ROOT, "RP", "pack_icon.png"), PALETTE["lumen_lit"])
    print("  generated pack icons")

    total = sum(
        len([f for f in os.listdir(d) if f.endswith(".png")]) for d in (BLOCKS, ITEMS, ENTITY, ARMOR, ENVIRONMENT, PARTICLE)
    )
    print(f"{total} texture files written")


if __name__ == "__main__":
    main()
