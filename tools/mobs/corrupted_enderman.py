import sys, math
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, taper_chain, write

# Corrupted Enderman: the reference is a figure coming apart. So the design
# problem is the opposite of every other mob here - the silhouette has to be
# *broken*. Solid where the body still holds together, and dissolving into
# hanging strips everywhere it does not.
atlas = UVAtlas(256, 256, padding=1)
bones = []
HIP = 26

uv = atlas.box((8, 16, 5))
bones.append(bone("torso", [0, HIP + 16, 0],
                  [cube([-4, HIP + 8, -2.5], [8, 16, 5], uv)]))
# The corruption: a lit fissure running up the chest, which is the one thing
# on it that is not black.
uv = atlas.box((3, 12, 2))
bones.append(bone("rift", [0, HIP + 16, -2.5],
                  [cube([-1.5, HIP + 10, -3.5], [3, 12, 2], uv)], parent="torso"))

uv = atlas.box((8, 9, 8))
bones.append(bone("head", [0, HIP + 28, 0],
                  [cube([-4, HIP + 26, -4], [8, 9, 8], uv)], parent="torso"))
# The jaw hangs open and unhinged - the mouth is part of what is broken.
uv = atlas.box((6, 5, 6))
bones.append(bone("jaw", [0, HIP + 27, -1],
                  [cube([-3, HIP + 22, -5], [6, 5, 6], uv)], parent="head",
                  rotation=[22, 0, 0]))
for i in range(4):
    uv = atlas.box((1, 3, 1))
    x = -2.4 + i * 1.6
    bones.append(bone("tooth_%d" % i, [x, HIP + 27, -4.5],
                      [cube([x - 0.5, HIP + 24, -4.5], [1, 3, 1], uv)], parent="jaw"))

# Long arms, enderman proportions, hanging well below the waist.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((3, 26, 3))
    ox = side * 4 if side > 0 else side * 4 - 3
    bones.append(bone("arm_" + tag, [side * 5, HIP + 23, 0],
                      [cube([ox, HIP - 3, -1.5], [3, 26, 3], uv, mirror=mirror)],
                      parent="torso", rotation=[6, 0, side * -3]))
    for i in range(3):
        uv = atlas.box((1, 5, 1))
        bones.append(bone("finger_%s%d" % (tag, i), [side * 5, HIP - 3, 0],
                          [cube([ox + i * 1.1, HIP - 8, -1.5], [1, 5, 1], uv,
                                mirror=mirror)], parent="arm_" + tag,
                          rotation=[0, 0, side * (i - 1) * 8]))
    uv = atlas.box((3, 26, 3))
    bones.append(bone("leg_" + tag, [side * 2.5, HIP + 8, 0],
                      [cube([side * 2.5 - 1.5, HIP - 18, -1.5], [3, 26, 3], uv,
                            mirror=mirror)], parent="torso"))

# The tatters. Ten strips hanging off the shoulders and ribs at varying
# lengths, each a short chain so they drift independently - this is the whole
# silhouette and it is why the thing does not read as a stick figure.
STRIPS = [(-5, HIP + 22, 2, 5), (5, HIP + 22, 2, 5), (-4, HIP + 18, 3, 4),
          (4, HIP + 18, 3, 4), (-3, HIP + 14, 3, 6), (3, HIP + 14, 3, 6),
          (0, HIP + 20, 3, 5), (-5, HIP + 12, 2, 3), (5, HIP + 12, 2, 3),
          (0, HIP + 10, 3, 4)]
for i, (x, y, z, count) in enumerate(STRIPS):
    # A chain with a step of zero puts every link in the same place, which is
    # how ten hanging rags turned into one lump on the shoulder. The step has
    # to match the link depth for the chain to actually extend.
    chain, _ = taper_chain(atlas, "tatter_%d" % i, "torso", [x, y, z], count,
                           (2, 1, 4), 4, shrink=0.92)
    # Chains walk along +z; rotating the root ninety degrees turns that walk
    # into a fall, and a few degrees on each link after gives it a curl.
    for j, link in enumerate(chain):
        link["rotation"] = [92 if j == 0 else 6 + j, (i * 37) % 40 - 20 if j == 0 else 0, 0]
    bones.extend(chain)

write("RP/models/entity/corrupted_enderman.geo.json",
      geometry("geometry.voidbound.corrupted_enderman", (256, 256), bones,
               bounds=(2, 4, (0, 1.8, 0))))
print("corrupted_enderman: %d bones" % len(bones))
