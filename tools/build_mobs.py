#!/usr/bin/env python3
"""Rebuild every mob model and its texture.

    python3 tools/build_mobs.py            # all of them
    python3 tools/build_mobs.py void_dragon

Each mob is a pair of scripts under tools/mobs/: one that builds the geometry
out of mobkit primitives, one that paints the texture from that geometry. They
are kept separate because the two get iterated at different rates - a
silhouette settles early and the art keeps moving for a long time after.
"""

import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MOBS = os.path.join(HERE, "mobs")


def names():
    found = []
    for entry in sorted(os.listdir(MOBS)):
        if entry.endswith("_paint.py") or not entry.endswith(".py"):
            continue
        found.append(entry[:-3])
    return found


def main():
    wanted = sys.argv[1:] or names()
    os.chdir(ROOT)
    for name in wanted:
        build = os.path.join(MOBS, name + ".py")
        paint = os.path.join(MOBS, name + "_paint.py")
        if not os.path.exists(build):
            raise SystemExit("no builder for %s" % name)
        runpy.run_path(build, run_name="__main__")
        if os.path.exists(paint):
            runpy.run_path(paint, run_name="__main__")


if __name__ == "__main__":
    main()
