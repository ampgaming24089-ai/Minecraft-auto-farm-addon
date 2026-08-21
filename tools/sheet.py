#!/usr/bin/env python3
"""Tile model renders into one labelled progress sheet.

Every batch of models gets shown before it gets wired up, and an unlabelled
strip of three black beasts is not much use to anyone. This renders each named
model, stacks the rows, and writes the mob's name under it in a small bitmap
font so the sheet reads on its own.
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from artlib import Canvas, canvas_from_png, hex_rgba  # noqa: E402

# A 5x7 uppercase font. Each glyph is seven rows of five bits, high bit left.
GLYPHS = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
}


def text(canvas, x, y, message, colour, scale=2):
    """Draw `message` with the top-left of the first glyph at (x, y)."""
    cx = x
    for char in message.upper():
        rows = GLYPHS.get(char, GLYPHS[" "])
        for ry, bits in enumerate(rows):
            for rx in range(5):
                if bits & (1 << (4 - rx)):
                    for sy in range(scale):
                        for sx in range(scale):
                            canvas.set(cx + rx * scale + sx, y + ry * scale + sy,
                                       colour)
        cx += 6 * scale
    return cx


def text_width(message, scale=2):
    return len(message) * 6 * scale


def blit(dst, src, x, y):
    for sy in range(src.h):
        for sx in range(src.w):
            pixel = src.get(sx, sy)
            if pixel[3]:
                dst.set(x + sx, y + sy, pixel)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="+")
    parser.add_argument("--out", default="dist/progress.png")
    parser.add_argument("--size", type=int, default=380)
    parser.add_argument("--turnaround", type=int, default=3)
    parser.add_argument("--title", default=None)
    parser.add_argument("--render", action="store_true",
                        help="re-render each model before tiling")
    args = parser.parse_args()

    BG = hex_rgba("#0D0916")
    INK = hex_rgba("#D8C7F5")
    RULE = hex_rgba("#2A1E44")

    rows = []
    for name in args.names:
        path = "dist/model_%s.png" % name
        if args.render or not os.path.exists(path):
            subprocess.check_call([sys.executable, os.path.join(HERE, "render_mob.py"),
                                   name, "--size", str(args.size),
                                   "--turnaround", str(args.turnaround)],
                                  stdout=subprocess.DEVNULL)
        rows.append((name, canvas_from_png(path)))

    label_h = 26
    pad = 14
    width = max(row.w for _, row in rows) + pad * 2
    head = 40 if args.title else 0
    height = head + pad + sum(row.h + label_h + pad for _, row in rows)

    sheet = Canvas(width, height)
    for y in range(height):
        for x in range(width):
            sheet.set(x, y, BG)

    if args.title:
        text(sheet, pad, 14, args.title, INK, scale=2)
        for x in range(pad, width - pad):
            sheet.set(x, 34, RULE)

    y = head + pad
    for name, row in rows:
        blit(sheet, row, (width - row.w) // 2, y)
        y += row.h + 4
        label = name.replace("_", " ")
        text(sheet, (width - text_width(label, 2)) // 2, y, label, INK, scale=2)
        y += label_h + pad - 4

    sheet.save(args.out)
    print("%s  (%d models) -> %s" % (os.path.basename(args.out), len(rows), args.out))


if __name__ == "__main__":
    main()
