import sys
sys.path.insert(0, "tools")
from mobkit import (UVAtlas, bone, cube, geometry, limb, muzzle, spine_row,
                    stand, taper_chain, write)

# Void Hog: low, heavy and front-weighted, the way a boar is. All the mass is
# in the shoulder, the head is carried low, and it has tusks, a bristle ridge
# and a blunt snout it clearly uses to shove things over.
atlas = UVAtlas(256, 256, padding=1)
bones = []

HIP = 20

uv = atlas.box((15, 14, 18))
bones.append(bone("body", [0, HIP, 0],
                  [cube([-7.5, HIP - 7, -9], [15, 14, 18], uv)]))
# The shoulder hump - the single thing that says boar rather than pig.
uv = atlas.box((17, 15, 12))
bones.append(bone("shoulder", [0, HIP + 2, -9],
                  [cube([-8.5, HIP - 5, -19], [17, 15, 12], uv)], parent="body"))
uv = atlas.box((13, 8, 10))
bones.append(bone("crest", [0, HIP + 10, -10],
                  [cube([-6.5, HIP + 7, -17], [13, 8, 10], uv)], parent="shoulder"))
uv = atlas.box((12, 11, 7))
bones.append(bone("rump", [0, HIP - 1, 9], [cube([-6, HIP - 6, 8], [12, 11, 7], uv)],
                  parent="body"))

uv = atlas.box((10, 9, 6))
bones.append(bone("neck", [0, HIP + 3, -18],
                  [cube([-5, HIP - 1, -23], [10, 9, 6], uv)], parent="shoulder",
                  rotation=[12, 0, 0]))
bones.extend(muzzle(atlas, "head", "neck", [0, HIP + 2, -22],
                    skull=(11, 9, 7), snout=(8, 6, 8),
                    jaw_drop=12.0, teeth=4, tooth_size=(1, 2, 1)))
# A flat disc on the end of the snout.
uv = atlas.box((8, 6, 2))
bones.append(bone("disc", [0, HIP - 1, -37],
                  [cube([-4, HIP - 4, -37.5], [8, 6, 2], uv, inflate=0.3)],
                  parent="head_snout"))

# Tusks: two a side, the lower pair long and curving up past the snout.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    prev, x, y, z = "head_jaw", side * 4, HIP - 4, -32
    for i in range(2):
        w = 3 - i
        uv = atlas.box((max(1, w), max(1, w), 6 - i))
        bones.append(bone("tusk_%s%d" % (tag, i), [x, y, z],
                          [cube([x - w / 2.0, y - w / 2.0, z - (6 - i)],
                                [max(1, w), max(1, w), 6 - i], uv, mirror=mirror)],
                          parent=prev, rotation=[-44 - i * 22, side * 10, side * 8]))
        prev = "tusk_%s%d" % (tag, i)
        y += 2
        z -= 3
    # A short upper tusk over it.
    uv = atlas.box((2, 2, 5))
    bones.append(bone("uptusk_" + tag, [side * 5, HIP - 1, -33],
                      [cube([side * 5 - 1, HIP - 2, -38], [2, 2, 5], uv,
                            mirror=mirror)], parent="head_snout",
                      rotation=[-28, side * 14, 0]))
    uv = atlas.box((2, 4, 3))
    bones.append(bone("ear_" + tag, [side * 5, HIP + 8, -24],
                      [cube([side * 5 - 1, HIP + 8, -25.5], [2, 4, 3], uv,
                            mirror=mirror)], parent="head",
                      rotation=[-14, side * 18, side * 24]))

# The bristle ridge: a mane of stiff spines down the neck and back.
bones.extend(spine_row(atlas, "bristle", "shoulder", [0, HIP + 15, -14], 4,
                       (3, 7, 3), 4.0, taper=0.88, lean=-14.0))
bones.extend(spine_row(atlas, "backbristle", "body", [0, HIP + 7, -2], 4,
                       (2, 5, 3), 4.0, taper=0.9, lean=-8.0))

tail, tip = taper_chain(atlas, "tail", "rump", [0, HIP + 3, 14], 3, (3, 3, 4), 3.0,
                        shrink=0.78, drop=-2.0)
bones.extend(tail)
uv = atlas.box((3, 5, 3))
bones.append(bone("tuft", [0, HIP - 3, 22], [cube([-1.5, HIP - 8, 21], [3, 5, 3], uv)],
                  parent=tip))

# Short thick legs on cloven trotters.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    for name, hz, parent in (("fore_" + tag, -12, "shoulder"),
                             ("hind_" + tag, 9, "rump")):
        bones.extend(limb(atlas, name, parent, [side * 5, HIP - 6, hz],
                          (6, 7, 6), (5, 6, 5), foot=(6, 4, 7), mirrored=mirror))
        for t, off in ((0, -1.5), (1, 1.5)):
            uv = atlas.box((2, 4, 4))
            bx = side * 5 + off
            by = HIP - 6 - 7 - 6 - 4
            bones.append(bone("%s_toe%d" % (name, t), [bx, by, hz],
                              [cube([bx - 1, by, hz - 5], [2, 4, 4], uv,
                                    mirror=mirror)], parent=name + "_foot"))

write("RP/models/entity/void_hog.geo.json",
      geometry("geometry.voidbound.void_hog", (256, 256), stand(bones),
               bounds=(2, 2, (0, 0.9, 0))))
print("void_hog: %d bones" % len(bones))
