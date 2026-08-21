import sys
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, muzzle, limb, taper_chain, spine_row, write, stand

# Void Stalker: a big cat built low and long. The whole read is predator
# posture - shoulders higher than hips, head carried below the shoulder line,
# and a spine of spikes that runs the entire length of the animal.
atlas = UVAtlas(256, 256, padding=1)
bones = []

uv = atlas.box((10, 11, 16))
bones.append(bone("chest", [0, 17, -6], [cube([-5, 12, -14], [10, 11, 16], uv)]))
uv = atlas.box((9, 10, 14))
bones.append(bone("hips", [0, 16, 4], [cube([-4.5, 11, 2], [9, 10, 14], uv)],
                  parent="chest"))

# Neck slung forward and down, the way a stalking cat carries its head.
uv = atlas.box((7, 7, 9))
bones.append(bone("neck", [0, 18, -14], [cube([-3.5, 13, -22], [7, 7, 9], uv)],
                  parent="chest", rotation=[16, 0, 0]))
bones.extend(muzzle(atlas, "head", "neck", [0, 17, -21],
                    skull=(8, 8, 8), snout=(6, 5, 6),
                    jaw_drop=11.0, teeth=4, tooth_size=(1, 2, 1)))

# Ears, because a cat without them reads as a lizard.
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((2, 4, 3))
    bones.append(bone("ear_%s" % ("l" if side > 0 else "r"), [side * 2.5, 21, -24],
                      [cube([side * 2.5 - 1, 21, -25], [2, 4, 3], uv, mirror=mirror)],
                      parent="head", rotation=[-10, 0, side * 14]))

for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    bones.extend(limb(atlas, "fore_" + tag, "chest", [side * 3.5, 12, -10],
                      (4, 7, 4), (3, 7, 3), foot=(4, 2, 6), mirrored=mirror))
    bones.extend(limb(atlas, "hind_" + tag, "hips", [side * 3.5, 11, 12],
                      (5, 8, 5), (3, 8, 3), foot=(4, 2, 6), mirrored=mirror))

tail, tip = taper_chain(atlas, "tail", "hips", [0, 18, 16], 7, (4, 4, 6), 5.2,
                        shrink=0.88)
bones.extend(tail)
uv = atlas.box((3, 3, 5))
bones.append(bone("tail_tuft", [0, 18, 52], [cube([-1.5, 16.5, 50], [3, 3, 5], uv)],
                  parent=tip))

# Spines: shoulder to hip, tallest over the shoulders.
bones.extend(spine_row(atlas, "spine", "chest", [0, 23, -13], 5, (2, 6, 3), 3.6,
                       taper=0.92))
bones.extend(spine_row(atlas, "rump", "hips", [0, 21, 3], 4, (2, 4, 3), 3.4,
                       taper=0.9))

# --- Ornament. A shape is not a design; the whale earned its keep with the
# gear strapped to it, so the Stalker gets the same treatment - something
# collared and armoured it, and crystal is growing out through the plates.
uv = atlas.box((11, 3, 5))
bones.append(bone("collar", [0, 18, -12],
                  [cube([-5.5, 15, -13], [11, 3, 5], uv)], parent="chest"))
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((3, 4, 3))
    bones.append(bone("collar_stud_%s" % ("l" if side > 0 else "r"),
                      [side * 4, 20, -11],
                      [cube([side * 4 - 1.5, 18, -12], [3, 4, 3], uv, mirror=mirror)],
                      parent="collar"))
# A pendant crystal hanging from the collar, so it swings when it moves.
uv = atlas.box((3, 5, 3))
bones.append(bone("pendant", [0, 15, -11],
                  [cube([-1.5, 10, -12.5], [3, 5, 3], uv)], parent="collar"))

# Shoulder plates bolted over the forelegs.
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((6, 6, 8))
    ox = side * 3 if side > 0 else side * 3 - 6
    bones.append(bone("pauldron_%s" % ("l" if side > 0 else "r"), [side * 5, 19, -9],
                      [cube([ox, 16, -13], [6, 6, 8], uv, mirror=mirror)],
                      parent="chest", rotation=[0, 0, side * -14]))

# Crystal breaking out through the hide along the flanks and haunches.
for i, (x, y, z, h) in enumerate([(4, 21, -8, 5), (-4, 21, -5, 4),
                                  (4, 19, 6, 4), (-4, 20, 9, 5),
                                  (0, 24, -2, 6)]):
    uv = atlas.box((2, h, 2))
    bones.append(bone("growth_%d" % i, [x, y, z],
                      [cube([x - 1, y, z - 1], [2, h, 2], uv)],
                      parent="chest" if z < 2 else "hips",
                      rotation=[-20, 0, (18 if x >= 0 else -18)]))

# Ear tufts and whiskers - small, but they finish a cat's head.
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((1, 4, 1))
    bones.append(bone("tuft_%s" % ("l" if side > 0 else "r"), [side * 2.5, 25, -24],
                      [cube([side * 2.5 - 0.5, 25, -24.5], [1, 4, 1], uv, mirror=mirror)],
                      parent="ear_%s" % ("l" if side > 0 else "r"),
                      rotation=[-14, 0, side * 20]))
    for i in range(2):
        uv = atlas.box((5, 1, 1))
        wx = side * 3 if side > 0 else side * 3 - 5
        bones.append(bone("whisker_%s%d" % ("l" if side > 0 else "r", i),
                          [side * 3, 15 + i, -26],
                          [cube([wx, 15 + i, -26.5], [5, 1, 1], uv, mirror=mirror)],
                          parent="head_snout", rotation=[0, 0, side * (8 + i * 10)]))

write("RP/models/entity/void_stalker.geo.json",
      geometry("geometry.voidbound.void_stalker", (256, 256), stand(bones),
               bounds=(2.5, 2, (0, 1, 0))))
print("void_stalker: %d bones" % len(bones))
