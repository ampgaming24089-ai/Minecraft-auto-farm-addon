import sys
sys.path.insert(0, "tools")
from mobkit import (UVAtlas, bone, cube, geometry, limb, muzzle, stand,
                    taper_chain, write)

# Chorus Cow: a heavy grazer that has been eating chorus fruit its whole life
# and is now partly made of it. A chorus plant grows out of its back in
# proper jointed segments with fruit on the ends, and the same purple has got
# into its hide in blotches.
atlas = UVAtlas(256, 256, padding=1)
bones = []

HIP = 26

uv = atlas.box((14, 14, 22))
bones.append(bone("body", [0, HIP, 0],
                  [cube([-7, HIP - 7, -11], [14, 14, 22], uv)]))
uv = atlas.box((15, 15, 10))
bones.append(bone("chest", [0, HIP + 1, -10],
                  [cube([-7.5, HIP - 6.5, -19], [15, 15, 10], uv)], parent="body"))
uv = atlas.box((13, 12, 8))
bones.append(bone("rump", [0, HIP - 1, 10],
                  [cube([-6.5, HIP - 7, 9], [13, 12, 8], uv)], parent="body"))
# Udder, because a cow that has none reads as a bull with the wrong horns.
uv = atlas.box((7, 4, 8))
bones.append(bone("udder", [0, HIP - 8, 5],
                  [cube([-3.5, HIP - 11, 1], [7, 4, 8], uv)], parent="body"))
for i, ux in enumerate((-2, 2)):
    uv = atlas.box((2, 3, 2))
    bones.append(bone("teat_%d" % i, [ux, HIP - 11, 4],
                      [cube([ux - 1, HIP - 14, 3], [2, 3, 2], uv)], parent="udder"))

uv = atlas.box((8, 9, 8))
bones.append(bone("neck", [0, HIP + 3, -17],
                  [cube([-4, HIP - 1, -24], [8, 9, 8], uv)], parent="chest",
                  rotation=[-14, 0, 0]))
bones.extend(muzzle(atlas, "head", "neck", [0, HIP + 4, -23],
                    skull=(10, 9, 8), snout=(8, 7, 7),
                    jaw_drop=9.0, teeth=4, tooth_size=(1, 2, 1)))
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((3, 3, 5))
    bones.append(bone("ear_" + tag, [side * 5, HIP + 6, -26],
                      [cube([side * 5 - 1.5, HIP + 5, -28], [3, 3, 5], uv,
                            mirror=mirror)], parent="head",
                      rotation=[0, side * 40, side * 18]))
    # Short curved horns.
    prev = "head"
    x, y, z = side * 4, HIP + 9, -27
    for i in range(2):
        w = 3 - i
        uv = atlas.box((w, w, 5 - i))
        bones.append(bone("horn_%s%d" % (tag, i), [x, y, z],
                          [cube([x - w / 2.0, y - w / 2.0, z - (5 - i)],
                                [w, w, 5 - i], uv, mirror=mirror)],
                          parent=prev, rotation=[-24 - i * 26, side * 40, side * 22]))
        prev = "horn_%s%d" % (tag, i)
        y += 2
        z -= 3

# The chorus plant growing out of its back: jointed stems with fruit.
PLANTS = ((-4, -5, 3, 20), (4, 2, 4, -26), (-2, 8, 3, 12))
for p, (px, pz, count, lean) in enumerate(PLANTS):
    prev = "body"
    x, y, z = px, HIP + 7, pz
    for i in range(count):
        w = 4 - i
        uv = atlas.box((max(2, w), 5, max(2, w)))
        name = "stem_%d_%d" % (p, i)
        bones.append(bone(name, [x, y, z],
                          [cube([x - max(2, w) / 2.0, y, z - max(2, w) / 2.0],
                                [max(2, w), 5, max(2, w)], uv)],
                          parent=prev,
                          rotation=[lean * 0.3, 0, lean * (0.5 if i % 2 else -0.4)]))
        prev = name
        y += 5
        # A side bud on the middle joints - a chorus plant is never a pole.
        if 0 < i < count - 1:
            uv = atlas.box((3, 4, 3))
            bones.append(bone("bud_%d_%d" % (p, i), [x, y - 2, z],
                              [cube([x - 1.5, y - 2, z - 1.5], [3, 4, 3], uv)],
                              parent=name, rotation=[0, 0, -lean * 1.6]))
    uv = atlas.box((5, 5, 5))
    bones.append(bone("fruit_%d" % p, [x, y, z],
                      [cube([x - 2.5, y, z - 2.5], [5, 5, 5], uv)], parent=prev))

tail, tip = taper_chain(atlas, "tail", "rump", [0, HIP + 3, 16], 3, (3, 3, 5), 4.0,
                        shrink=0.8, drop=-3.0)
bones.extend(tail)
uv = atlas.box((3, 6, 3))
bones.append(bone("tuft", [0, HIP - 6, 27], [cube([-1.5, HIP - 12, 26], [3, 6, 3], uv)],
                  parent=tip))

for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    bones.extend(limb(atlas, "fore_" + tag, "chest", [side * 5, HIP - 6, -13],
                      (6, 10, 6), (5, 9, 5), foot=(6, 4, 7), mirrored=mirror))
    bones.extend(limb(atlas, "hind_" + tag, "rump", [side * 5, HIP - 6, 11],
                      (6, 10, 6), (5, 9, 5), foot=(6, 4, 7), mirrored=mirror))

write("RP/models/entity/chorus_cow.geo.json",
      geometry("geometry.voidbound.chorus_cow", (256, 256), stand(bones),
               bounds=(2, 3, (0, 1.2, 0))))
print("chorus_cow: %d bones" % len(bones))
