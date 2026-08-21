import sys
sys.path.insert(0, "tools")
from mobkit import (UVAtlas, bone, cube, geometry, limb, muzzle, spine_row,
                    stand, write)

# Echo Warden: the pack's second boss, and until now it was wearing a retired
# mob's skeleton. It listens rather than looks - a blind armoured sentinel
# with a resonator in its chest and a ring of listening vanes around its head,
# so the silhouette says "this thing hears you" before it does anything.
atlas = UVAtlas(256, 256, padding=1)
bones = []

HIP = 26

uv = atlas.box((18, 18, 12))
bones.append(bone("chest", [0, HIP + 20, 0],
                  [cube([-9, HIP + 12, -6], [18, 18, 12], uv)]))
uv = atlas.box((14, 10, 10))
bones.append(bone("waist", [0, HIP + 10, 0],
                  [cube([-7, HIP + 4, -5], [14, 10, 10], uv)], parent="chest"))
uv = atlas.box((16, 6, 11))
bones.append(bone("belt", [0, HIP + 6, 0],
                  [cube([-8, HIP + 3, -5.5], [16, 6, 11], uv, inflate=0.4)],
                  parent="waist"))

# Armour plates over the chest, stepped so the light breaks across them.
for i, (py, pw, pd, grow) in enumerate(((HIP + 27, 17, 6, 0.6),
                                        (HIP + 22, 19, 7, 0.4),
                                        (HIP + 17, 17, 6, 0.2))):
    uv = atlas.box((pw, 6, pd))
    bones.append(bone("plate_%d" % i, [0, py, -4],
                      [cube([-pw / 2.0, py - 3, -4 - pd / 2.0], [pw, 6, pd], uv,
                            inflate=grow)], parent="chest"))

# The resonator: a lit drum sunk into the chest behind a cage of ribs.
uv = atlas.box((10, 10, 5))
bones.append(bone("resonator", [0, HIP + 22, -7],
                  [cube([-5, HIP + 17, -9], [10, 10, 5], uv)], parent="chest"))
for i in range(4):
    uv = atlas.box((1, 12, 3))
    rx = -4.5 + i * 3
    bones.append(bone("ribcage_%d" % i, [rx, HIP + 22, -9],
                      [cube([rx - 0.5, HIP + 16, -10], [1, 12, 3], uv)],
                      parent="resonator"))

uv = atlas.box((8, 6, 8))
bones.append(bone("neck", [0, HIP + 31, 0],
                  [cube([-4, HIP + 30, -4], [8, 6, 8], uv)], parent="chest"))
bones.extend(muzzle(atlas, "head", "neck", [0, HIP + 40, -1],
                    skull=(11, 10, 10), snout=(8, 6, 6),
                    jaw_drop=16.0, teeth=5, tooth_size=(1, 3, 1),
                    nostrils=False, brow=True))
# Listening vanes: a ring of blades around the skull, the mob's whole read.
for i in range(8):
    length = 9 - (i % 3) * 2
    uv = atlas.box((2, length, 4))
    bones.append(bone("vane_%d" % i, [0, HIP + 44, -1],
                      [cube([-1, HIP + 44, -8], [2, length, 4], uv)],
                      parent="head", rotation=[-20, i * 45, (i % 2) * 12 - 6]))

# A crest down the spine.
bones.extend(spine_row(atlas, "crest", "chest", [0, HIP + 38, 2], 4, (3, 6, 4),
                       4.0, taper=0.86))

# Arms: heavy, with a fist that reads as something to be hit with.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((7, 7, 9))
    bones.append(bone("pauldron_" + tag, [side * 11, HIP + 28, 0],
                      [cube([side * 11 - 3.5, HIP + 24, -4.5], [7, 7, 9], uv,
                            mirror=mirror)], parent="chest",
                      rotation=[0, 0, side * 14]))
    uv = atlas.box((6, 14, 6))
    bones.append(bone("upper_" + tag, [side * 12, HIP + 26, 0],
                      [cube([side * 12 - 3, HIP + 12, -3], [6, 14, 6], uv,
                            mirror=mirror)], parent="pauldron_" + tag,
                      rotation=[-6, 0, side * 6]))
    uv = atlas.box((7, 13, 7))
    bones.append(bone("fore_" + tag, [side * 13, HIP + 12, 0],
                      [cube([side * 13 - 3.5, HIP - 1, -3.5], [7, 13, 7], uv,
                            mirror=mirror)], parent="upper_" + tag,
                      rotation=[-14, 0, 0]))
    uv = atlas.box((8, 7, 8))
    bones.append(bone("fist_" + tag, [side * 13, HIP - 1, 0],
                      [cube([side * 13 - 4, HIP - 8, -4], [8, 7, 8], uv,
                            mirror=mirror)], parent="fore_" + tag))
    for i in range(3):
        uv = atlas.box((2, 3, 2))
        kx = side * 13 + (i - 1) * 2.6
        bones.append(bone("knuckle_%s%d" % (tag, i), [kx, HIP - 8, -3],
                          [cube([kx - 1, HIP - 10, -4.5], [2, 3, 2], uv)],
                          parent="fist_" + tag))
    bones.extend(limb(atlas, "leg_" + tag, "waist", [side * 5, HIP + 4, 0],
                      (7, 13, 8), (6, 12, 7), foot=(8, 4, 11), mirrored=mirror))

write("RP/models/entity/echo_warden.geo.json",
      geometry("geometry.voidbound.echo_warden", (256, 256), stand(bones),
               bounds=(2, 4, (0, 2.0, 0))))
print("echo_warden: %d bones" % len(bones))
