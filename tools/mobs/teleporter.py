import sys
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, muzzle, stand, taper_chain, write

# Teleporter: a thing that never finishes arriving. It is built as a humanoid
# that has come apart at every joint - head, chest, waist and hands all float
# clear of each other with a lit rift running up the gaps - and the gaps are
# the design. Rings orbit the waist where the legs should be, because the
# bottom half is still somewhere else.
atlas = UVAtlas(256, 256, padding=1)
bones = []

HIP = 22

uv = atlas.box((12, 9, 7))
bones.append(bone("chest", [0, HIP + 16, 0],
                  [cube([-6, HIP + 12, -3.5], [12, 9, 7], uv)]))
uv = atlas.box((10, 6, 6))
bones.append(bone("waist", [0, HIP + 6, 0],
                  [cube([-5, HIP + 3, -3], [10, 6, 6], uv)], parent="chest"))
uv = atlas.box((8, 4, 5))
bones.append(bone("pelvis", [0, HIP - 2, 0],
                  [cube([-4, HIP - 4, -2.5], [8, 4, 5], uv)], parent="waist"))

# The rift running up the body through every gap.
for i, (ry, rh, rw) in enumerate(((HIP - 1, 5, 5), (HIP + 8, 5, 6),
                                  (HIP + 21, 5, 6))):
    uv = atlas.box((rw, rh, 4))
    bones.append(bone("rift_%d" % i, [0, ry, 0],
                      [cube([-rw / 2.0, ry, -2], [rw, rh, 4], uv)],
                      parent="chest" if i else "waist"))

# Shoulders sit clear of the chest - the arm is not attached to anything.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((4, 4, 4))
    bones.append(bone("pauldron_" + tag, [side * 8, HIP + 19, 0],
                      [cube([side * 8 - 2, HIP + 17, -2], [4, 4, 4], uv,
                            mirror=mirror)], parent="chest",
                      rotation=[0, 0, side * 14]))
    uv = atlas.box((4, 8, 4))
    bones.append(bone("upper_" + tag, [side * 9, HIP + 15, 0],
                      [cube([side * 9 - 2, HIP + 7, -2], [4, 8, 4], uv,
                            mirror=mirror)], parent="pauldron_" + tag,
                      rotation=[-12, 0, side * 8]))
    # Forearm floating clear of the elbow.
    uv = atlas.box((4, 9, 4))
    bones.append(bone("fore_" + tag, [side * 10, HIP + 5, 0],
                      [cube([side * 10 - 2, HIP - 5, -2], [4, 9, 4], uv,
                            mirror=mirror)], parent="upper_" + tag,
                      rotation=[-26, 0, side * 6]))
    uv = atlas.box((5, 5, 5))
    bones.append(bone("hand_" + tag, [side * 11, HIP - 7, 0],
                      [cube([side * 11 - 2.5, HIP - 12, -2.5], [5, 5, 5], uv,
                            mirror=mirror)], parent="fore_" + tag,
                      rotation=[-14, 0, 0]))
    for i in range(3):
        uv = atlas.box((1, 4, 1))
        fx = side * 11 + (i - 1) * 1.6
        bones.append(bone("digit_%s%d" % (tag, i), [fx, HIP - 12, 0],
                          [cube([fx - 0.5, HIP - 16, -0.5], [1, 4, 1], uv)],
                          parent="hand_" + tag,
                          rotation=[10 + i * 6, 0, (i - 1) * 12]))

# The head, floating a clear gap above the shoulders.
bones.extend(muzzle(atlas, "head", "chest", [0, HIP + 30, 0],
                    skull=(9, 9, 8), snout=(6, 6, 5),
                    jaw_drop=14.0, teeth=4, tooth_size=(1, 3, 1),
                    nostrils=False, brow=True))
# A crown of shards, so the head has a top worth looking at.
for i in range(6):
    uv = atlas.box((2, 6 - (i % 3), 2))
    bones.append(bone("spike_%d" % i, [0, HIP + 35, 0],
                      [cube([-1, HIP + 35, -6], [2, 6 - (i % 3), 2], uv)],
                      parent="head", rotation=[-16, i * 60, 0]))

# Two rings orbiting the waist, each a circle of blocks on its own bone so
# the whole ring can be spun in an animation.
for ring, (ry, rr, count, tilt) in enumerate(((HIP + 4, 13, 10, 0),
                                              (HIP - 2, 16, 12, 18))):
    for i in range(count):
        uv = atlas.box((3, 2, 2))
        bones.append(bone("ring%d_%d" % (ring, i), [0, ry, 0],
                          [cube([-1.5, ry, -rr], [3, 2, 2], uv)],
                          parent="waist",
                          rotation=[tilt, i * (360.0 / count), 0]))

# What is left of the legs: a stub that falls away into loose blocks.
for side in (1, -1):
    chain, _ = taper_chain(atlas, "leg_%s" % ("l" if side > 0 else "r"), "pelvis",
                           [side * 3, HIP - 6, 0], 4, (5, 5, 5), -7.0,
                           shrink=0.74, axis="y")
    bones.extend(chain)

write("RP/models/entity/teleporter.geo.json",
      geometry("geometry.voidbound.teleporter", (256, 256), bones,
               bounds=(1.6, 3, (0, 1.4, 0))))
print("teleporter: %d bones" % len(bones))
