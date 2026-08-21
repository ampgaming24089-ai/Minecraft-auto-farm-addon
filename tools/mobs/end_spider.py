import sys, math
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, muzzle, radial_leg, stand, write

# End Spider: eight legs is the whole silhouette, so they get built properly -
# three jointed segments each, splayed on a fan, with the front pair raised.
# Everything else exists to give the eye somewhere to land: a cluster of eyes,
# fangs, a crystal-studded abdomen and a spinneret.
atlas = UVAtlas(256, 256, padding=1)
bones = []

uv = atlas.box((10, 8, 10))
bones.append(bone("thorax", [0, 14, -2], [cube([-5, 10, -7], [10, 8, 10], uv)]))
uv = atlas.box((14, 12, 15))
bones.append(bone("abdomen", [0, 15, 6], [cube([-7, 9, 5], [14, 12, 15], uv)],
                  parent="thorax", rotation=[-8, 0, 0]))
# Spinneret, and crystal studs growing out of the abdomen.
# Spinnerets: a cluster of small dark nozzles, not one glowing block. A
# 4x4x4 cube painted bright reads as a sticker stuck to the tail end.
for i, (sx, sy, sw) in enumerate(((0, 12, 3), (-3, 14, 2), (3, 14, 2))):
    uv = atlas.box((sw, sw, 3))
    bones.append(bone("spinneret_%d" % i, [sx, sy, 20],
                      [cube([sx - sw / 2.0, sy, 19], [sw, sw, 3], uv)],
                      parent="abdomen",
                      rotation=[0, (0 if sx == 0 else (12 if sx > 0 else -12)), 0]))

# Carapace plates over the abdomen, so a big smooth box gets some structure.
for i, (pz, pw, ph) in enumerate(((7, 15, 4), (12, 14, 4), (16, 12, 3))):
    uv = atlas.box((pw, ph, 4))
    bones.append(bone("shell_%d" % i, [0, 20, pz],
                      [cube([-pw / 2.0, 20 - ph / 2.0, pz - 2], [pw, ph, 4], uv,
                            inflate=0.35)], parent="abdomen",
                      rotation=[-6 + i * 4, 0, 0]))

# Bristles along the flanks.
for side in (1, -1):
    for i in range(4):
        uv = atlas.box((1, 4, 1))
        bz = 7 + i * 3
        bones.append(bone("bristle_%s%d" % ("l" if side > 0 else "r", i),
                          [side * 7, 16, bz],
                          [cube([side * 7, 16, bz], [1, 4, 1], uv)],
                          parent="abdomen", rotation=[-20, 0, side * 62]))
for i, (x, y, z, h) in enumerate([(4, 21, 9, 5), (-5, 20, 12, 4), (0, 22, 15, 6),
                                  (5, 18, 16, 3), (-4, 19, 7, 4)]):
    uv = atlas.box((2, h, 2))
    bones.append(bone("stud_%d" % i, [x, y, z],
                      [cube([x - 1, y, z - 1], [2, h, 2], uv)], parent="abdomen",
                      rotation=[-18, 0, (14 if x >= 0 else -14)]))

bones.extend(muzzle(atlas, "head", "thorax", [0, 14, -7],
                    skull=(8, 6, 6), snout=(6, 4, 4),
                    jaw_drop=16.0, teeth=2, tooth_size=(1, 3, 1),
                    nostrils=False, brow=False))
# Eight eyes in two rows - a spider's face is a cluster, not a pair.
for row, (count, y, size) in enumerate([(4, 16, 2), (4, 13, 1)]):
    for i in range(count):
        t = (i - (count - 1) / 2.0)
        uv = atlas.box((size, size, size))
        bones.append(bone("eye_%d_%d" % (row, i), [t * 2.2, y, -12],
                          [cube([t * 2.2 - size / 2.0, y, -12 - size],
                                [size, size, size], uv)], parent="head"))
# Fangs, hinged below the face.
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((2, 6, 2))
    bones.append(bone("fang_%s" % ("l" if side > 0 else "r"), [side * 2, 12, -11],
                      [cube([side * 2 - 1, 6, -12], [2, 6, 2], uv, mirror=mirror)],
                      parent="head", rotation=[18, 0, side * 10]))

# Legs: four a side. Out from the body and up to a high knee, then back down
# past the belly to the floor - the arch is the whole reason a spider reads as
# a spider, and it only works if the femur goes sideways rather than back.
for side, mirror in ((1, False), (-1, True)):
    for i in range(4):
        tag = "%s%d" % ("l" if side > 0 else "r", i)
        bones.extend(radial_leg(atlas, "leg_" + tag, "thorax",
                                [side * 5, 15, -6 + i * 4],
                                femur=(11, 3, 3), tibia=(3, 20, 3),
                                tarsus=(2, 6, 2),
                                fan=40 - i * 26, lift=36 - i * 3,
                                drop=18 + i * 2, claw=54, mirrored=mirror))

write("RP/models/entity/end_spider.geo.json",
      geometry("geometry.voidbound.end_spider", (256, 256), stand(bones),
               bounds=(4, 2, (0, 0.8, 0))))
print("end_spider: %d bones" % len(bones))
