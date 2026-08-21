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

# --- Ornament. It is a thing coming apart, so the pieces that have already
# left it hang in the air around it: a broken halo over the head and shards
# orbiting the torso, each on its own bone so they can drift.
for i in range(7):
    angle = (i / 7.0) * math.pi * 2
    if i in (2, 5):
        continue                                  # the halo is broken
    rx = math.cos(angle) * 7
    rz = math.sin(angle) * 7
    uv = atlas.box((3, 1, 2))
    bones.append(bone("halo_%d" % i, [rx, HIP + 40, rz],
                      [cube([rx - 1.5, HIP + 40, rz - 1], [3, 1, 2], uv)],
                      parent="head", rotation=[0, math.degrees(angle), 0]))

for i, (rx, ry, rz, size) in enumerate([(7, HIP + 24, 2, 2), (-8, HIP + 20, -3, 3),
                                        (6, HIP + 14, -4, 2), (-6, HIP + 30, 3, 2),
                                        (9, HIP + 6, 1, 2), (-7, HIP + 2, -2, 3)]):
    uv = atlas.box((size, size, size))
    bones.append(bone("debris_%d" % i, [rx, ry, rz],
                      [cube([rx - size / 2.0, ry, rz - size / 2.0],
                            [size, size, size], uv)], parent="torso",
                      rotation=[i * 23, i * 41, i * 17]))

# Rifts opening down the arms and legs, matching the one on the chest.
for side in (1, -1):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((1, 14, 1))
    bones.append(bone("armrift_" + tag, [side * 5, HIP + 14, -1.6],
                      [cube([side * 5 - 0.5, HIP + 4, -2.1], [1, 14, 1], uv)],
                      parent="arm_" + tag))
    uv = atlas.box((1, 10, 1))
    bones.append(bone("legrift_" + tag, [side * 2.5, HIP - 2, -1.6],
                      [cube([side * 2.5 - 0.5, HIP - 12, -2.1], [1, 10, 1], uv)],
                      parent="leg_" + tag))

write("RP/models/entity/corrupted_enderman.geo.json",
      geometry("geometry.voidbound.corrupted_enderman", (256, 256), bones,
               bounds=(2, 4, (0, 1.8, 0))))
print("corrupted_enderman: %d bones" % len(bones))
