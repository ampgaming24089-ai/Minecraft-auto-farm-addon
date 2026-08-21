"""Tiny dependency-free imaging toolkit for End Unbound's texture pipeline.

Everything here is pure standard library: PNGs are encoded by hand with zlib so
the art can be regenerated on any machine with a bare Python 3, no Pillow, no
node_modules, no binary assets committed by hand.

The two ideas that make the output look deliberate rather than noisy:

1. Every random source is a seeded, *tileable* value-noise lattice, so block
   faces wrap seamlessly when Minecraft repeats them across a chunk.
2. Colour is chosen in HSV and converted late, so a texture is authored as
   "this material, lit this way" instead of as a pile of hex constants.
"""

import math
import struct
import zlib

# --------------------------------------------------------------------------
# PNG output
# --------------------------------------------------------------------------


def _chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def save_png(path, width, height, pixels):
    """Write 8-bit RGBA PNG. `pixels` is a flat list of (r, g, b, a) tuples."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None) keeps the encoder trivial
        row = pixels[y * width : (y + 1) * width]
        for r, g, b, a in row:
            raw += bytes((r & 255, g & 255, b & 255, a & 255))
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


# --------------------------------------------------------------------------
# Deterministic randomness
# --------------------------------------------------------------------------


def _hash2(x, y, seed):
    """Integer hash -> float in [0, 1). Stable across platforms and runs."""
    h = (x * 374761393 + y * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0x1000000)


class Rng:
    """xorshift32 - small, seeded, and identical on every machine."""

    def __init__(self, seed):
        self.state = (seed & 0xFFFFFFFF) or 0x9E3779B9

    def next(self):
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state / 0x100000000

    def range(self, lo, hi):
        return lo + (hi - lo) * self.next()

    def int(self, lo, hi):
        return int(self.range(lo, hi + 1)) if hi >= lo else lo

    def chance(self, p):
        return self.next() < p

    def pick(self, items):
        return items[int(self.next() * len(items)) % len(items)]


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def tileable_noise(x, y, period, seed):
    """Value noise on a lattice that wraps every `period` cells."""
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - x0, y - y0
    sx, sy = _smooth(fx), _smooth(fy)
    v = 0.0
    for dy in (0, 1):
        for dx in (0, 1):
            n = _hash2((x0 + dx) % period, (y0 + dy) % period, seed)
            wx = sx if dx else 1.0 - sx
            wy = sy if dy else 1.0 - sy
            v += n * wx * wy
    return v


def fbm(x, y, size, seed, octaves=3, lacunarity=2.0, gain=0.5, base_period=4):
    """Fractal noise that stays seamless across a `size` x `size` texture."""
    total, amplitude, norm = 0.0, 1.0, 0.0
    period = base_period
    for octave in range(octaves):
        scale = period / float(size)
        total += amplitude * tileable_noise(x * scale, y * scale, period, seed + octave * 7919)
        norm += amplitude
        amplitude *= gain
        period = int(period * lacunarity)
    return total / norm


# --------------------------------------------------------------------------
# PNG input
# --------------------------------------------------------------------------


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def load_png(path):
    """Decode an 8-bit PNG to (width, height, [(r, g, b, a), ...]).

    Deliberately more capable than the writer above: the writer only ever
    emits filter-0 RGBA, but Mojang's own textures use the full filter set and
    a mix of colour types, and this pack recolours them.
    """
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s is not a PNG" % path)

    pos = 8
    width = height = 0
    depth = color_type = 0
    idat = bytearray()
    palette = []
    trns = []
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        tag = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, color_type = struct.unpack(">IIBB", body[:10])
        elif tag == b"PLTE":
            palette = [tuple(body[i : i + 3]) for i in range(0, len(body), 3)]
        elif tag == b"tRNS":
            trns = list(body)
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + length

    if depth not in (1, 2, 4, 8):
        raise ValueError("%s: unsupported bit depth %d" % (path, depth))

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    bits_per_pixel = channels * depth
    # Per the PNG spec, filtering works on whole bytes and the "left" offset is
    # the pixel size rounded up to a byte.
    filter_step = max(1, bits_per_pixel // 8)
    stride = (width * bits_per_pixel + 7) // 8
    raw = zlib.decompress(bytes(idat))

    rows = []
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        line = bytearray(raw[offset : offset + stride])
        offset += stride
        for i in range(stride):
            left = line[i - filter_step] if i >= filter_step else 0
            up = previous[i]
            upleft = previous[i - filter_step] if i >= filter_step else 0
            if filter_type == 1:
                line[i] = (line[i] + left) & 255
            elif filter_type == 2:
                line[i] = (line[i] + up) & 255
            elif filter_type == 3:
                line[i] = (line[i] + ((left + up) >> 1)) & 255
            elif filter_type == 4:
                line[i] = (line[i] + _paeth(left, up, upleft)) & 255
            elif filter_type != 0:
                raise ValueError("%s: unknown PNG filter %d" % (path, filter_type))
        rows.append(line)
        previous = line

    def sample(line, index):
        """Read sample `index` from a scanline, honouring sub-byte depths."""
        if depth == 8:
            return line[index]
        per_byte = 8 // depth
        byte = line[index // per_byte]
        shift = 8 - depth * (index % per_byte + 1)
        return (byte >> shift) & ((1 << depth) - 1)

    pixels = []
    for line in rows:
        for x in range(width):
            chunk = [sample(line, x * channels + i) for i in range(channels)]
            if color_type == 0:
                pixels.append((chunk[0], chunk[0], chunk[0], 255))
            elif color_type == 4:
                pixels.append((chunk[0], chunk[0], chunk[0], chunk[1]))
            elif color_type == 2:
                pixels.append((chunk[0], chunk[1], chunk[2], 255))
            elif color_type == 6:
                pixels.append((chunk[0], chunk[1], chunk[2], chunk[3]))
            else:
                index = chunk[0]
                r, g, b = palette[index]
                alpha = trns[index] if index < len(trns) else 255
                pixels.append((r, g, b, alpha))
    return width, height, pixels


def canvas_from_png(path):
    width, height, pixels = load_png(path)
    c = Canvas(width, height)
    c.px = pixels
    return c


# --------------------------------------------------------------------------
# Colour
# --------------------------------------------------------------------------


def hsv(h, s, v, a=255):
    """h in [0,1), s/v in [0,1] -> (r, g, b, a) ints."""
    h = h % 1.0
    i = int(h * 6.0)
    f = h * 6.0 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]
    return (int(r * 255 + 0.5), int(g * 255 + 0.5), int(b * 255 + 0.5), a)


def hex_rgba(code, a=255):
    code = code.lstrip("#")
    return (int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16), a)


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t + 0.5) for i in range(4))


def shade(color, amount):
    """amount > 0 lightens toward white, < 0 darkens toward black."""
    target = (255, 255, 255, color[3]) if amount >= 0 else (0, 0, 0, color[3])
    return mix(color, target, abs(amount))


def luma(color):
    return (0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]) / 255.0


def rgb_to_hsv(color):
    r, g, b = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
    high, low = max(r, g, b), min(r, g, b)
    span = high - low
    if span == 0:
        hue = 0.0
    elif high == r:
        hue = ((g - b) / span) % 6
    elif high == g:
        hue = (b - r) / span + 2
    else:
        hue = (r - g) / span + 4
    return hue / 6.0, (span / high if high else 0.0), high


def recolour(canvas, target, hue_window=None, saturation_floor=0.12,
             saturation_scale=1.0, value_scale=1.0):
    """Re-tint a texture while keeping its shading intact.

    Value is what carries a Minecraft texture's form - the highlights and
    shadows that make a sword look like a sword. So this keeps each pixel's
    value and only replaces hue and saturation, which is why the result reads
    as the same object in a different metal rather than as a flat repaint.

    `hue_window` limits the change to a band of source hues, so a tool's wooden
    handle survives while its head is recoloured.
    """
    target_h, target_s, _ = rgb_to_hsv(target)

    def paint(x, y, current):
        if current[3] == 0:
            return None
        h, s, v = rgb_to_hsv(current)
        if s < saturation_floor:
            return None  # Near-greyscale pixels (outlines) stay as they are.
        if hue_window is not None:
            low, high = hue_window
            inside = (low <= h <= high) if low <= high else (h >= low or h <= high)
            if not inside:
                return None
        # Blend the source saturation toward the target's, so a washed-out
        # pixel stays washed out and a vivid one stays vivid.
        new_s = max(0.0, min(1.0, (s * 0.45 + target_s * 0.55) * saturation_scale))
        new_v = max(0.0, min(1.0, v * value_scale))
        return hsv(target_h, new_s, new_v, current[3])

    canvas.each(paint)
    return canvas


# --------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------

TRANSPARENT = (0, 0, 0, 0)


class Canvas:
    def __init__(self, size, height=None, fill=TRANSPARENT):
        self.w = size
        self.h = height if height is not None else size
        self.px = [fill] * (self.w * self.h)

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y * self.w + x]
        return TRANSPARENT

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = color

    def blend(self, x, y, color):
        """Alpha-composite `color` over whatever is already there."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        dst = self.px[y * self.w + x]
        sa = color[3] / 255.0
        if sa >= 1.0 or dst[3] == 0:
            self.px[y * self.w + x] = color if sa >= 1.0 else (color[0], color[1], color[2], color[3])
            return
        da = dst[3] / 255.0
        out_a = sa + da * (1 - sa)
        out = [0, 0, 0, int(out_a * 255 + 0.5)]
        for i in range(3):
            out[i] = int((color[i] * sa + dst[i] * da * (1 - sa)) / out_a + 0.5)
        self.px[y * self.w + x] = tuple(out)

    def fill(self, color):
        self.px = [color] * (self.w * self.h)

    def rect(self, x0, y0, x1, y1, color):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, color)

    def each(self, fn):
        """fn(x, y, current) -> new colour (or None to leave it alone)."""
        for y in range(self.h):
            for x in range(self.w):
                out = fn(x, y, self.px[y * self.w + x])
                if out is not None:
                    self.px[y * self.w + x] = out

    def outline(self, color, only_opaque=True):
        """Draw `color` on transparent pixels orthogonally touching opaque ones."""
        edges = []
        for y in range(self.h):
            for x in range(self.w):
                if self.get(x, y)[3] != 0:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if self.get(x + dx, y + dy)[3] > (0 if only_opaque else -1):
                        edges.append((x, y))
                        break
        for x, y in edges:
            self.set(x, y, color)

    def save(self, path):
        save_png(path, self.w, self.h, self.px)


# --------------------------------------------------------------------------
# Material helpers
# --------------------------------------------------------------------------


def speckle(canvas, seed, density, colors, alpha_only_opaque=True):
    """Scatter single-pixel grit without disturbing transparent regions."""
    rng = Rng(seed)
    for y in range(canvas.h):
        for x in range(canvas.w):
            if alpha_only_opaque and canvas.get(x, y)[3] == 0:
                continue
            if rng.chance(density):
                canvas.blend(x, y, colors[rng.int(0, len(colors) - 1)])


def veins(canvas, seed, count, color, length, wobble=0.9, width=1):
    """Random walks used for cracks, crystal seams and ore threads."""
    rng = Rng(seed)
    for _ in range(count):
        x = rng.range(0, canvas.w)
        y = rng.range(0, canvas.h)
        angle = rng.range(0, math.tau)
        for _ in range(length):
            angle += rng.range(-wobble, wobble)
            x = (x + math.cos(angle)) % canvas.w
            y = (y + math.sin(angle)) % canvas.h
            for oy in range(width):
                for ox in range(width):
                    canvas.blend(int(x) + ox, int(y) + oy, color)


def radial(canvas, cx, cy, radius, inner, outer, falloff=1.0, mask_alpha=False):
    """Paint a soft circular gradient from `inner` at the centre to `outer`."""
    for y in range(canvas.h):
        for x in range(canvas.w):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / radius
            if d > 1.0:
                continue
            if mask_alpha and canvas.get(x, y)[3] == 0:
                continue
            canvas.blend(x, y, mix(inner, outer, d ** falloff))


def bevel(canvas, light=0.22, dark=0.26):
    """Cheap top-left highlight / bottom-right shadow on the opaque silhouette."""
    src = list(canvas.px)

    def lit(x, y, cur):
        if cur[3] == 0:
            return None
        above = src[(y - 1) * canvas.w + x] if y > 0 else TRANSPARENT
        left = src[y * canvas.w + (x - 1)] if x > 0 else TRANSPARENT
        below = src[(y + 1) * canvas.w + x] if y < canvas.h - 1 else TRANSPARENT
        right = src[y * canvas.w + (x + 1)] if x < canvas.w - 1 else TRANSPARENT
        if above[3] == 0 or left[3] == 0:
            return shade(cur, light)
        if below[3] == 0 or right[3] == 0:
            return shade(cur, -dark)
        return None

    canvas.each(lit)


# --------------------------------------------------------------------------
# MER (metalness / emissive / roughness) map synthesis
# --------------------------------------------------------------------------


def make_mer(albedo, metalness=0, roughness=230, emissive_from=None, emissive_gain=1.0,
             emissive_threshold=0.0, roughness_variation=0.0, seed=0):
    """Derive a Vibrant Visuals MER map from an albedo canvas.

    `emissive_from` is an RGB anchor: the closer a pixel sits to that hue, the
    more it glows. That keeps the glow locked to the art instead of needing a
    hand-painted mask per texture.
    """
    mer = Canvas(albedo.w, albedo.h, (metalness, 0, roughness, 255))
    rng = Rng(seed or 1)
    for y in range(albedo.h):
        for x in range(albedo.w):
            c = albedo.get(x, y)
            if c[3] == 0:
                mer.set(x, y, (0, 0, 255, 255))
                continue
            emissive = 0
            if emissive_from is not None:
                # Distance in RGB, normalised: near the anchor colour -> bright.
                dist = math.sqrt(
                    sum((c[i] - emissive_from[i]) ** 2 for i in range(3))
                ) / 441.67
                closeness = max(0.0, 1.0 - dist * 1.9)
                strength = closeness * (0.35 + 0.65 * luma(c))
                if strength > emissive_threshold:
                    emissive = int(min(255, strength * 255 * emissive_gain))
            rough = roughness
            if roughness_variation:
                rough = int(max(0, min(255, roughness + rng.range(-1, 1) * roughness_variation)))
            mer.set(x, y, (metalness, emissive, rough, 255))
    return mer
