"""
Painting a mob's texture atlas from its materials.

Every cube carries a `Mat`, and the painter fills that cube's six face
rectangles from it: a base colour, per-face lighting so a cube reads as a solid
object rather than a flat sticker, a dither so large panels are not dead flat,
and then whatever detail the material asks for - crystal growths, plating,
scales, glowing veins, eyes.

Glow is carried in the alpha channel. Bedrock's `entity_emissive_alpha`
material treats a texel with alpha below 255 as emissive and alpha 0 as
cut out, so a glowing crystal is simply painted at alpha 254 and lights itself
with no extra geometry, no second texture and no render controller. Nothing
here ever writes alpha 0: every mob in this pack is a solid silhouette, which
keeps the material's cutout path out of the picture entirely.

The same glow mask is written out again as the emissive channel of a MER map,
so the mobs also light correctly under Vibrant Visuals.
"""

from __future__ import annotations

from PIL import Image

# Alpha value that marks a texel emissive. Anything under 255 works; a single
# constant keeps the MER pass able to recover the mask exactly.
GLOW_ALPHA = 254

# How much each face is lightened or darkened, so a cube has form. Roughly the
# ratios Minecraft's own block lighting uses.
FACE_LIGHT = {
    "up": 1.18,
    "down": 0.62,
    "north": 1.0,
    "south": 0.86,
    "west": 0.78,
    "east": 0.78,
}


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def scale(rgb, factor):
    return tuple(max(0, min(255, int(round(c * factor)))) for c in rgb)


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


class Rng:
    """
    A tiny deterministic PRNG.

    Deliberately not `random`: the textures are checked into the repository, so
    a rebuild must produce byte-identical PNGs or every build is a twenty-file
    binary diff. Seeded per cube from the mob name, so adding a mob never
    reshuffles the ones before it.
    """

    def __init__(self, seed):
        self.state = (seed ^ 0x9E3779B9) & 0xFFFFFFFF or 0x1234567

    def next(self):
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state / 0xFFFFFFFF

    def chance(self, p):
        return self.next() < p

    def between(self, lo, hi):
        return lo + (hi - lo) * self.next()

    def pick(self, items):
        return items[min(len(items) - 1, int(self.next() * len(items)))]


class Mat:
    """
    How one cube is painted.

    `base` is the body colour and `glow` the emissive accent. `pattern` picks
    the detail treatment; `eyes` puts a face on the north side of the cube,
    which is the side a mob looks out of.
    """

    def __init__(self, base, glow=None, pattern="dither", accent=None,
                 density=0.16, noise=0.09, eyes=None, mouth=None, plate=None,
                 emissive_all=False):
        self.base = hex_to_rgb(base)
        self.glow = hex_to_rgb(glow) if glow else None
        self.accent = hex_to_rgb(accent) if accent else scale(self.base, 1.35)
        self.pattern = pattern
        self.density = density
        self.noise = noise
        self.eyes = hex_to_rgb(eyes) if eyes else None
        self.mouth = hex_to_rgb(mouth) if mouth else None
        self.plate = hex_to_rgb(plate) if plate else None
        self.emissive_all = emissive_all


def string_seed(text):
    seed = 0x811C9DC5
    for ch in text:
        seed = ((seed ^ ord(ch)) * 0x01000193) & 0xFFFFFFFF
    return seed


class Atlas:
    """The texture being built, plus the emissive mask that mirrors it."""

    def __init__(self, size):
        self.size = size
        self.image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        self.px = self.image.load()

    def put(self, x, y, rgb, glow=False):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.px[x, y] = (rgb[0], rgb[1], rgb[2], GLOW_ALPHA if glow else 255)

    def get(self, x, y):
        return self.px[x, y]


def paint_model(model, name):
    """
    Paint every cube of a packed model.

    @returns (colour image, MER image)
    """
    atlas = Atlas(model.texture_width)

    for index, cube in enumerate(model.cubes):
        rng = Rng(string_seed(f"{name}/{index}/{cube.uv}"))
        for face in ("up", "down", "west", "north", "east", "south"):
            _paint_face(atlas, cube, face, rng)

    # Any texel no cube claimed stays fully transparent. Bedrock never samples
    # it, but leaving it black would show up as a seam under filtering, so it
    # is filled with the nearest painted colour instead.
    _flood_gaps(atlas)

    return atlas.image, _mer_from(atlas.image)


def _paint_face(atlas, cube, face, rng):
    mat = cube.mat
    x0, y0, w, h = cube.face_rect(face)
    if w <= 0 or h <= 0:
        return

    light = FACE_LIGHT[face]
    base = scale(mat.base, light)
    accent = scale(mat.accent, light)
    glow = mat.glow

    for dy in range(h):
        for dx in range(w):
            shade = 1.0 + (rng.next() - 0.5) * 2 * mat.noise
            atlas.put(x0 + dx, y0 + dy, scale(base, shade), mat.emissive_all)

    painter = _PATTERNS.get(mat.pattern, _pattern_dither)
    painter(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng)

    # Plating runs a darker rim around the panel, which reads as a seam between
    # armour segments and stops big cubes looking like untextured boxes.
    if mat.plate is not None and w > 2 and h > 2:
        rim = scale(mat.plate, light)
        for dx in range(w):
            atlas.put(x0 + dx, y0, rim)
            atlas.put(x0 + dx, y0 + h - 1, rim)
        for dy in range(h):
            atlas.put(x0, y0 + dy, rim)
            atlas.put(x0 + w - 1, y0 + dy, rim)

    if face == "north" and mat.eyes is not None:
        _paint_eyes(atlas, x0, y0, w, h, mat)


# --------------------------------------------------------------------------
# Detail patterns.
# --------------------------------------------------------------------------

def _pattern_dither(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """
    Scattered lighter patches. The default: quiet, and never wrong.

    Patches, not loose texels: single random pixels read as sensor noise once
    the texture is on a moving mob, where a two-by-two blotch reads as a
    marking. Same density, completely different impression.
    """
    for dy in range(h):
        for dx in range(w):
            if not rng.chance(mat.density * 0.22):
                continue
            for oy in range(min(2, h - dy)):
                for ox in range(min(2, w - dx)):
                    if rng.chance(0.75):
                        atlas.put(x0 + dx + ox, y0 + dy + oy, accent)


def _pattern_crystals(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """
    Crystal growths: a bright core texel with a dimmer halo, the way the
    reference sheets draw the violet shards on every End creature.
    """
    _pattern_dither(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng)
    if glow is None or face == "down":
        return
    for dy in range(h):
        for dx in range(w):
            if not rng.chance(mat.density * 0.15):
                continue
            atlas.put(x0 + dx, y0 + dy, glow, glow=True)
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = dx + ox, dy + oy
                if 0 <= nx < w and 0 <= ny < h and rng.chance(0.5):
                    atlas.put(x0 + nx, y0 + ny, mix(base, glow, 0.55), glow=True)


def _pattern_veins(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """Cracks of light running down the panel - corrupted, fissured stone."""
    _pattern_dither(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng)
    if glow is None:
        return
    strands = max(1, int(w * mat.density))
    for _ in range(strands):
        x = int(rng.between(0, w))
        y = int(rng.between(0, max(1, h * 0.4)))
        length = int(rng.between(h * 0.35, h * 0.95))
        for step in range(length):
            if not (0 <= x < w and 0 <= y < h):
                break
            atlas.put(x0 + x, y0 + y, glow if rng.chance(0.6) else mix(base, glow, 0.6),
                      glow=True)
            y += 1
            if rng.chance(0.28):
                x += 1 if rng.chance(0.5) else -1


def _pattern_scales(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """Overlapping plates. Dragons, serpents, crab shells."""
    dark = scale(base, 0.72)
    for dy in range(h):
        row = dy % 3
        for dx in range(w):
            offset = 0 if (dy // 3) % 2 == 0 else 1
            if row == 2 or (dx + offset) % 3 == 0:
                atlas.put(x0 + dx, y0 + dy, dark if rng.chance(0.7) else base)
            elif rng.chance(mat.density * 0.4):
                atlas.put(x0 + dx, y0 + dy, accent)
    if glow is not None and face in ("up", "north"):
        for dy in range(h):
            for dx in range(w):
                if rng.chance(mat.density * 0.14):
                    atlas.put(x0 + dx, y0 + dy, glow, glow=True)


def _pattern_fur(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """Vertical strands, for the four-legged animals."""
    dark = scale(base, 0.76)
    for dx in range(w):
        tone = accent if rng.chance(0.3) else (dark if rng.chance(0.45) else None)
        if tone is None:
            continue
        top = int(rng.between(0, h * 0.5))
        bottom = int(rng.between(h * 0.5, h))
        for dy in range(top, bottom):
            if rng.chance(0.72):
                atlas.put(x0 + dx, y0 + dy, tone)
    if glow is not None:
        for dy in range(h):
            for dx in range(w):
                if rng.chance(mat.density * 0.1):
                    atlas.put(x0 + dx, y0 + dy, glow, glow=True)


def _pattern_membrane(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """
    Wing and fin webbing: ribs of the darker body colour with lit panels
    between them, which is what makes a flat slab read as a wing.
    """
    rib = scale(base, 0.55)
    panel = mix(base, glow or accent, 0.45)
    for dx in range(w):
        ribbed = dx % 4 == 0
        for dy in range(h):
            if ribbed:
                atlas.put(x0 + dx, y0 + dy, rib)
            else:
                lit = glow is not None and rng.chance(mat.density * 0.5)
                atlas.put(x0 + dx, y0 + dy, glow if lit else panel, glow=lit)


def _pattern_core(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """A single bright heart in the middle of the panel - golems, slimes."""
    _pattern_dither(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng)
    if glow is None:
        return
    cx, cy = (w - 1) / 2, (h - 1) / 2
    radius = max(1.0, min(w, h) * 0.3)
    for dy in range(h):
        for dx in range(w):
            distance = ((dx - cx) ** 2 + (dy - cy) ** 2) ** 0.5
            if distance <= radius * 0.55:
                atlas.put(x0 + dx, y0 + dy, glow, glow=True)
            elif distance <= radius:
                atlas.put(x0 + dx, y0 + dy, mix(base, glow, 0.5), glow=True)


def _pattern_feather(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """Chevron banding, for the birds and the ray."""
    for dy in range(h):
        band = (dy // 2) % 2 == 0
        for dx in range(w):
            edge = abs(dx - (w - 1) / 2) / max(1.0, (w - 1) / 2)
            tone = mix(base, accent, 0.55 if band else 0.15)
            if edge > 0.72:
                tone = scale(tone, 0.7)
            atlas.put(x0 + dx, y0 + dy, tone)
    if glow is not None:
        for dy in range(0, h, 3):
            for dx in range(w):
                if rng.chance(mat.density * 0.75):
                    atlas.put(x0 + dx, y0 + dy, glow, glow=True)


def _pattern_flame(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """A soft vertical gradient with licking tips - wisps and spirits."""
    target = glow or accent
    for dy in range(h):
        t = 1.0 - dy / max(1, h - 1)
        for dx in range(w):
            edge = abs(dx - (w - 1) / 2) / max(1.0, (w - 1) / 2)
            heat = max(0.0, t * (1.0 - edge * 0.55))
            lit = heat > 0.45 or rng.chance(heat * 0.5)
            atlas.put(x0 + dx, y0 + dy, mix(base, target, min(1.0, heat + 0.1)),
                      glow=lit)


def _pattern_stone(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """Blotchy rock, for the golems and the obsidian beast."""
    dark = scale(base, 0.7)
    for dy in range(h):
        for dx in range(w):
            roll = rng.next()
            if roll < 0.16:
                atlas.put(x0 + dx, y0 + dy, dark)
            elif roll < 0.28:
                atlas.put(x0 + dx, y0 + dy, accent)
    if glow is not None:
        for dy in range(h):
            for dx in range(w):
                if rng.chance(mat.density * 0.11):
                    atlas.put(x0 + dx, y0 + dy, glow, glow=True)


def _pattern_cloth(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """Hanging fabric: vertical folds that get darker toward the hem."""
    for dy in range(h):
        hem = dy / max(1, h - 1)
        for dx in range(w):
            fold = 0.82 if dx % 3 == 0 else 1.0
            tone = scale(mix(base, accent, 0.25 * (1 - hem)), fold * (1.0 - hem * 0.3))
            atlas.put(x0 + dx, y0 + dy, tone)
    if glow is not None:
        for dy in range(h):
            for dx in range(w):
                if rng.chance(mat.density * 0.3):
                    atlas.put(x0 + dx, y0 + dy, glow, glow=True)


def _pattern_metal(atlas, x0, y0, w, h, base, accent, glow, mat, face, rng):
    """Brushed plate with a highlight along the top - crowns and armour."""
    for dy in range(h):
        t = dy / max(1, h - 1)
        for dx in range(w):
            tone = mix(scale(base, 1.22), scale(base, 0.72), t)
            if rng.chance(0.1):
                tone = accent
            atlas.put(x0 + dx, y0 + dy, tone)
    if glow is not None:
        for dx in range(w):
            if rng.chance(mat.density * 1.4):
                atlas.put(x0 + dx, y0, glow, glow=True)


_PATTERNS = {
    "dither": _pattern_dither,
    "crystals": _pattern_crystals,
    "veins": _pattern_veins,
    "scales": _pattern_scales,
    "fur": _pattern_fur,
    "membrane": _pattern_membrane,
    "core": _pattern_core,
    "feather": _pattern_feather,
    "flame": _pattern_flame,
    "stone": _pattern_stone,
    "cloth": _pattern_cloth,
    "metal": _pattern_metal,
}


def _paint_eyes(atlas, x0, y0, w, h, mat):
    """
    A face on the north panel.

    Placed proportionally rather than at fixed offsets, because the heads in
    this pack run from a 3-pixel glowmite to a 20-pixel dragon skull and a
    hard-coded eye position would slide off both ends.
    """
    if w < 3 or h < 3:
        return
    eye_y = y0 + max(1, int(h * 0.32))
    inset = max(1, int(w * 0.2))
    thickness = 2 if w >= 8 else 1
    height = 2 if h >= 8 else 1

    for side in (0, 1):
        ex = x0 + inset if side == 0 else x0 + w - inset - thickness
        for dx in range(thickness):
            for dy in range(height):
                atlas.put(ex + dx, eye_y + dy, mat.eyes, glow=True)

    if mat.mouth is not None and h >= 6:
        mouth_y = y0 + int(h * 0.7)
        for dx in range(max(1, int(w * 0.25)), w - max(1, int(w * 0.25))):
            atlas.put(x0 + dx, mouth_y, mat.mouth, glow=True)


def _flood_gaps(atlas):
    """
    Bleed painted texels one ring outward, then fill the rest flat.

    The bleed exists only so that bilinear filtering at a UV edge samples the
    cube's own colour rather than whatever is next to it on the atlas. Two
    rings is enough for that. The passes are snapshotted rather than done in
    place, because filling from a texel that was itself filled this pass turns
    a one-pixel skirt into a flood across the whole sheet.
    """
    size = atlas.size
    px = atlas.px
    empty = [(x, y) for y in range(size) for x in range(size) if px[x, y][3] == 0]

    for _ in range(2):
        if not empty:
            return
        painted = {(x, y): px[x, y] for x in range(size) for y in range(size)
                   if px[x, y][3] != 0}
        still_empty = []
        for x, y in empty:
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                source = painted.get((x + ox, y + oy))
                if source:
                    px[x, y] = (source[0], source[1], source[2], 255)
                    break
            else:
                still_empty.append((x, y))
        empty = still_empty

    for x, y in empty:
        px[x, y] = (18, 13, 26, 255)


def _mer_from(image):
    """
    The metalness / emissive / roughness map that mirrors the colour texture.

    Nothing in this pack is metal, emissiveness is exactly the alpha mask the
    colour texture already carries, and roughness is read off brightness so
    the polished crystal faces catch a highlight and the matte hide does not.
    """
    size = image.size[0]
    mer = Image.new("RGBA", image.size, (0, 0, 0, 255))
    src = image.load()
    dst = mer.load()
    for y in range(size):
        for x in range(size):
            r, g, b, a = src[x, y]
            emissive = 255 if a == GLOW_ALPHA else 0
            luma = (r * 30 + g * 59 + b * 11) // 100
            roughness = max(40, 235 - luma)
            dst[x, y] = (0, emissive, roughness, 255)
    return mer
