#!/usr/bin/env python3
"""One sheet of the whole mob roster, grouped and labelled."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from artlib import Canvas, canvas_from_png, hex_rgba  # noqa: E402
from sheet import text, text_width  # noqa: E402

GROUPS = [
    ("bosses", ["void_dragon", "ender_overlord", "end_king", "echo_warden"]),
    ("hostiles", ["void_stalker", "purpur_golem", "shulker_beast",
                  "corrupted_enderman", "end_spider", "chorus_fiend",
                  "obsidian_beast", "endermite_hive", "void_wisp",
                  "void_slime", "teleporter", "end_crab", "ender_ghost"]),
    ("passives", ["astral_whale", "sky_ray", "ender_deer", "chorus_cow",
                  "void_hog", "ender_bird"]),
]

TILE, COLS, PAD, LABEL = 300, 5, 8, 22
BG, INK, RULE = hex_rgba("#0D0916"), hex_rgba("#D8C7F5"), hex_rgba("#2A1E44")


def main():
    for _, names in GROUPS:
        for name in names:
            out = "dist/tile_%s.png" % name
            if not os.path.exists(out):
                subprocess.check_call(
                    [sys.executable, os.path.join(HERE, "render_mob.py"), name,
                     "--size", str(TILE), "--out", out],
                    stdout=subprocess.DEVNULL)

    rows = sum((len(n) + COLS - 1) // COLS for _, n in GROUPS)
    width = PAD + COLS * (TILE + PAD)
    height = 52 + rows * (TILE + LABEL + PAD) + len(GROUPS) * 34
    sheet = Canvas(width, height)
    sheet.fill(BG)
    total = sum(len(n) for _, n in GROUPS)
    text(sheet, PAD, 14, "end ascendant - %d mobs" % total, INK, scale=3)

    y = 56
    for title, names in GROUPS:
        text(sheet, PAD, y, title, INK, scale=2)
        for x in range(PAD, width - PAD):
            sheet.set(x, y + 20, RULE)
        y += 32
        for i, name in enumerate(names):
            col = i % COLS
            if col == 0 and i:
                y += TILE + LABEL + PAD
            x = PAD + col * (TILE + PAD)
            src = canvas_from_png("dist/tile_%s.png" % name)
            for sy in range(src.h):
                for sx in range(src.w):
                    px = src.get(sx, sy)
                    if px[3]:
                        sheet.set(x + sx, y + sy, px)
            label = name.replace("_", " ")
            text(sheet, x + (TILE - text_width(label, 2)) // 2, y + TILE + 2,
                 label, INK, scale=2)
        y += TILE + LABEL + PAD
    sheet.save("dist/roster.png")
    print("dist/roster.png  %dx%d  (%d mobs)" % (width, height, total))


if __name__ == "__main__":
    main()
