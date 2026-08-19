#!/usr/bin/env python3
"""Compose every generated texture into one zoomed contact sheet.

    python3 tools/preview.py [out.png]

Minecraft textures are far too small to judge at 1:1, and _mer maps are
meaningless to the eye on their own. This scales each texture up with
nearest-neighbour (so pixels stay crisp), composites transparency over a
checkerboard, and lays everything out in a grid for a single glance.
"""

import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artlib import Canvas, mix  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = ((58, 52, 74, 255), (40, 36, 54, 255))
BACKDROP = (22, 18, 32, 255)


def load_png(path):
    """Minimal reader for the RGBA/filter-0 PNGs this pipeline writes."""
    data = open(path, "rb").read()
    pos, width, height, idat = 8, 0, 0, b""
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        tag = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, color_type = struct.unpack(">IIBB", body[:10])
            if (depth, color_type) != (8, 6):
                raise ValueError("%s is not 8-bit RGBA" % path)
        elif tag == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * 4
    pixels, offset = [], 0
    for _ in range(height):
        if raw[offset] != 0:
            raise ValueError("%s uses PNG filters this reader does not handle" % path)
        offset += 1
        line = raw[offset : offset + stride]
        offset += stride
        for x in range(width):
            pixels.append(tuple(line[x * 4 : x * 4 + 4]))
    return width, height, pixels


def collect():
    found = []
    for folder in ("blocks", "items", "entity"):
        directory = os.path.join(ROOT, "RP", "textures", folder)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if name.endswith(".png"):
                found.append(os.path.join(directory, name))
    icon = os.path.join(ROOT, "RP", "pack_icon.png")
    if os.path.exists(icon):
        found.append(icon)
    return found


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist", "texture_preview.png")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    files = collect()
    if not files:
        print("no textures found - run tools/gen_art.py first")
        return 1

    tile, pad, columns = 112, 6, 6
    cell = tile + pad
    rows = (len(files) + columns - 1) // columns
    sheet = Canvas(columns * cell + pad, rows * cell + pad, BACKDROP)

    for index, path in enumerate(files):
        width, height, pixels = load_png(path)
        scale = max(1, tile // max(width, height))
        ox = pad + (index % columns) * cell + (tile - width * scale) // 2
        oy = pad + (index // columns) * cell + (tile - height * scale) // 2
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[y * width + x]
                for sy in range(scale):
                    for sx in range(scale):
                        px, py = ox + x * scale + sx, oy + y * scale + sy
                        under = CHECKER[((px // 8) + (py // 8)) % 2]
                        sheet.set(px, py, mix(under, (r, g, b, 255), a / 255.0))

    sheet.save(target)
    print("wrote %s (%d textures)" % (target, len(files)))
    for index, path in enumerate(files):
        print("  %2d  %s" % (index, os.path.relpath(path, ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
