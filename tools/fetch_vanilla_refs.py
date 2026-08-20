#!/usr/bin/env python3
"""Download the vanilla textures this pack recolours, once.

    python3 tools/fetch_vanilla_refs.py

The tools and armour are meant to be the classic Minecraft shapes in a new
colour, not new shapes. Approximating those silhouettes by hand does not work -
the eye knows them too well - so the pipeline recolours Mojang's own art
instead. The references are cached in tools/vanilla_refs/ and committed, so
tools/gen_art.py stays reproducible offline.

Source: Mojang's bedrock-samples repository, which they publish as the
starting point for creators building resource packs.
"""

import os
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/Mojang/bedrock-samples/main/resource_pack/textures"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "vanilla_refs")

# Diamond is the right donor: full-brightness art with clean, saturated metal
# that separates cleanly from the wooden handle when recolouring by hue.
FILES = [
    "items/diamond_sword.png",
    "items/diamond_pickaxe.png",
    "items/diamond_axe.png",
    "items/diamond_shovel.png",
    "items/diamond_hoe.png",
    "models/armor/diamond_1.png",
    "models/armor/diamond_2.png",
]


def main():
    os.makedirs(OUT, exist_ok=True)
    for path in FILES:
        target = os.path.join(OUT, os.path.basename(path))
        try:
            with urllib.request.urlopen(f"{BASE}/{path}", timeout=30) as response:
                data = response.read()
        except Exception as error:  # noqa: BLE001 - report and keep going
            print(f"  ! {path}: {error}")
            continue
        with open(target, "wb") as fh:
            fh.write(data)
        print(f"  {os.path.basename(path)}  {len(data)} bytes")
    print(f"cached in {os.path.relpath(OUT, os.path.dirname(HERE))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
