import sys
sys.path.insert(0, "tools")
from mobkit import (UVAtlas, bone, cube, geometry, muzzle, radial_leg, stand,
                    write)

# Endermite Hive: the mite that stopped running. Its back has gone over to a
# comb of brood cells lit from inside, the shell has cracked open around them,
# and its own young ride on it. The vanilla endermite silhouette is kept -
# stacked segments, widest at the shoulder - so it still reads as one of them.
atlas = UVAtlas(256, 256, padding=1)
bones = []

SEGMENTS = ((16, 13, 8, -8), (18, 15, 9, 0), (15, 13, 8, 9), (11, 10, 7, 17))
prev = None
for i, (w, h, d, z) in enumerate(SEGMENTS):
    uv = atlas.box((w, h, d))
    name = "seg_%d" % i
    bones.append(bone(name, [0, 11, z],
                      [cube([-w / 2.0, 11 - h / 2.0, z - d / 2.0], [w, h, d], uv)],
                      parent=prev, rotation=[(i - 1) * 3, 0, 0]))
    prev = name
    # A plate overhanging the joint behind it, so the segments interlock
    # instead of butting together like stacked crates.
    uv = atlas.box((w + 1, 4, 5))
    bones.append(bone("lip_%d" % i, [0, 11 + h / 2.0 - 2, z + d / 2.0],
                      [cube([-(w + 1) / 2.0, 11 + h / 2.0 - 4, z + d / 2.0 - 2],
                            [w + 1, 4, 5], uv, inflate=0.3)], parent=name,
                      rotation=[-14, 0, 0]))

# The comb: brood cells sunk into the back, each a dark rim around a lit core.
CELLS = ((-5, -6, 4), (3, -5, 5), (-2, 1, 5), (5, 3, 4), (-6, 4, 4), (0, 9, 3))
for i, (cx, cz, cs) in enumerate(CELLS):
    uv = atlas.box((cs + 3, 4, cs + 3))
    bones.append(bone("cell_%d" % i, [cx, 18, cz],
                      [cube([cx - (cs + 3) / 2.0, 16, cz - (cs + 3) / 2.0],
                            [cs + 3, 4, cs + 3], uv)], parent="seg_1"
                      if cz < 4 else "seg_2"))
    uv = atlas.box((cs, 5, cs))
    bones.append(bone("brood_%d" % i, [cx, 20, cz],
                      [cube([cx - cs / 2.0, 18, cz - cs / 2.0], [cs, 5, cs], uv)],
                      parent="cell_%d" % i))

# Cracks in the shell where the comb burst through: thin lit wedges.
for i, (rx, rz, rl) in enumerate(((-8, -2, 7), (8, 1, 6), (-4, 8, 5), (6, -7, 5))):
    uv = atlas.box((2, 3, rl))
    bones.append(bone("rift_%d" % i, [rx, 16, rz],
                      [cube([rx - 1, 15, rz - rl / 2.0], [2, 3, rl], uv,
                            inflate=0.2)], parent="seg_1",
                      rotation=[0, (24 if i % 2 else -24), 0]))

# Two of its young riding on the back.
for i, (mx, mz, my, yaw) in enumerate(((-7, 6, 20, 40), (6, -3, 20, -55))):
    uv = atlas.box((5, 4, 7))
    bones.append(bone("mite_%d" % i, [mx, my, mz],
                      [cube([mx - 2.5, my, mz - 3.5], [5, 4, 7], uv)],
                      parent="seg_2" if mz > 0 else "seg_1",
                      rotation=[0, yaw, 0]))
    uv = atlas.box((4, 3, 4))
    bones.append(bone("mite_%d_head" % i, [mx, my + 1, mz - 3.5],
                      [cube([mx - 2, my + 1, mz - 7], [4, 3, 4], uv)],
                      parent="mite_%d" % i))
    for eside in (1, -1):
        uv = atlas.box((1, 1, 1))
        bones.append(bone("miteeye_%d_%d" % (i, eside > 0),
                          [mx + eside, my + 3, mz - 7],
                          [cube([mx + eside - 0.5, my + 2.5, mz - 7.6],
                                [1, 1, 1], uv)], parent="mite_%d_head" % i))

# Head and mandibles.
bones.extend(muzzle(atlas, "head", "seg_0", [0, 11, -12],
                    skull=(11, 8, 6), snout=(7, 5, 5),
                    jaw_drop=22.0, teeth=3, tooth_size=(1, 3, 1),
                    nostrils=False, brow=True))
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((2, 3, 9))
    bones.append(bone("mandible_%s" % ("l" if side > 0 else "r"),
                      [side * 4, 9, -17],
                      [cube([side * 4 - 1, 8, -26], [2, 3, 9], uv, mirror=mirror)],
                      parent="head", rotation=[6, side * 22, side * -12]))
    uv = atlas.box((2, 2, 5))
    bones.append(bone("mandibletip_%s" % ("l" if side > 0 else "r"),
                      [side * 4, 9, -26],
                      [cube([side * 4 - 1, 8, -31], [2, 2, 5], uv, mirror=mirror)],
                      parent="mandible_%s" % ("l" if side > 0 else "r"),
                      rotation=[0, side * -34, 0]))
for side in (1, -1):
    for row, ey in ((0, 13), (1, 10)):
        uv = atlas.box((2, 2, 2))
        bones.append(bone("eye_%s%d" % ("l" if side > 0 else "r", row),
                          [side * 3.5, ey, -18],
                          [cube([side * 3.5 - 1, ey, -18.5], [2, 2, 2], uv)],
                          parent="head"))

# Six legs, low and scuttling.
for side, mirror in ((1, False), (-1, True)):
    for i in range(3):
        bones.extend(radial_leg(atlas, "leg_%s%d" % ("l" if side > 0 else "r", i),
                                "seg_%d" % (i if i < 2 else 2),
                                [side * 8, 9, -8 + i * 9],
                                femur=(7, 3, 3), tibia=(3, 11, 3),
                                tarsus=(2, 4, 2),
                                fan=26 - i * 26, lift=30, drop=22, claw=58,
                                mirrored=mirror))

write("RP/models/entity/endermite_hive.geo.json",
      geometry("geometry.voidbound.endermite_hive", (256, 256), stand(bones),
               bounds=(2, 2, (0, 0.7, 0))))
print("endermite_hive: %d bones" % len(bones))
