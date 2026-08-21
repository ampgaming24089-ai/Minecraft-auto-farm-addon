import sys
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, muzzle, limb, taper_chain, spine_row, write

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

write("RP/models/entity/void_stalker.geo.json",
      geometry("geometry.voidbound.void_stalker", (256, 256), bones,
               bounds=(2.5, 2, (0, 1, 0))))
print("void_stalker: %d bones" % len(bones))
