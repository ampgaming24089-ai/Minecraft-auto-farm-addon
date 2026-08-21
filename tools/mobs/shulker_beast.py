import sys
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, muzzle, taper_chain, write

# Shulker Beast: mostly head. The reference is a mouth with wings behind it, so
# the body is deliberately small and everything is arranged to point the eye at
# the maw - a huge jaw, a lot of teeth, and a shell over the back that opens
# rather than a smooth spine.
atlas = UVAtlas(256, 256, padding=1)
bones = []

uv = atlas.box((12, 11, 14))
bones.append(bone("body", [0, 20, 2], [cube([-6, 15, 2], [12, 11, 14], uv)]))

# The shell: three overlapping plates over the back, stepped so it reads as a
# shulker's box splitting open rather than as a turtle.
for i, (w, h, d, y, z) in enumerate([(15, 5, 12, 26, 3), (13, 5, 10, 29, 5),
                                     (10, 4, 8, 32, 7)]):
    uv = atlas.box((w, h, d))
    bones.append(bone("shell_%d" % i, [0, y, z],
                      [cube([-w / 2.0, y, z], [w, h, d], uv)], parent="body",
                      rotation=[-8 - i * 6, 0, 0]))

bones.extend(muzzle(atlas, "head", "body", [0, 22, 2],
                    skull=(13, 12, 10), snout=(11, 9, 9),
                    jaw_drop=26.0, teeth=6, tooth_size=(1, 4, 1)))
# Horns sweeping back off the skull.
for side, mirror in ((1, False), (-1, True)):
    prev = "head"
    x, y, z = side * 5, 27, -4
    for i in range(2):
        w = 3 - i
        uv = atlas.box((max(1, w), max(1, w), 7))
        bones.append(bone("horn_%s_%d" % ("l" if side > 0 else "r", i), [x, y, z],
                          [cube([x - w / 2.0, y, z], [max(1, w), max(1, w), 7], uv,
                                mirror=mirror)],
                          parent=prev, rotation=[-16, side * 16, side * 8]))
        prev = "horn_%s_%d" % ("l" if side > 0 else "r", i)
        y += 2
        z += 5

# Wings: a spar, a forearm, and three fingers with membrane between.
for side, mirror in ((1, False), (-1, True)):
    tag = "wing_" + ("l" if side > 0 else "r")
    uv = atlas.box((14, 3, 4))
    ox = 6 if side > 0 else -20
    bones.append(bone(tag, [side * 6, 26, 6],
                      [cube([ox, 25, 4], [14, 3, 4], uv, mirror=mirror)],
                      parent="body", rotation=[0, 0, side * -22]))
    for i in range(3):
        length = 26 - i * 6
        uv = atlas.box((2, 2, length))
        px = side * 20 if side > 0 else side * 20 - 2
        finger = "%s_f%d" % (tag, i)
        bones.append(bone(finger, [side * 20, 26, 6],
                          [cube([px, 25, 4], [2, 2, length], uv, mirror=mirror)],
                          parent=tag, rotation=[0, side * (-18 + i * 20), side * 4]))
        uv = atlas.box((12, 1, length))
        wx = side * 20 - (12 if side > 0 else 0)
        bones.append(bone("%s_w%d" % (tag, i), [side * 20, 26, 6],
                          [cube([wx, 25.5, 4], [12, 1, length], uv, mirror=mirror)],
                          parent=finger, rotation=[4 + i * 3, 0, 0]))

# Clawed feet tucked under, and a short whip tail.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((4, 7, 4))
    bones.append(bone("leg_" + tag, [side * 4, 15, 8],
                      [cube([side * 4 - 2, 8, 6], [4, 7, 4], uv, mirror=mirror)],
                      parent="body", rotation=[14, 0, side * 6]))
    for i in range(3):
        uv = atlas.box((1, 1, 4))
        bones.append(bone("claw_%s%d" % (tag, i), [side * 4, 8, 6],
                          [cube([side * 4 - 2 + i * 1.4, 8, 3], [1, 1, 4], uv,
                                mirror=mirror)], parent="leg_" + tag))

tail, tip = taper_chain(atlas, "tail", "body", [0, 20, 16], 5, (5, 5, 6), 5.0,
                        shrink=0.84)
bones.extend(tail)

write("RP/models/entity/shulker_beast.geo.json",
      geometry("geometry.voidbound.shulker_beast", (256, 256), bones,
               bounds=(4, 3, (0, 1.4, 0))))
print("shulker_beast: %d bones" % len(bones))
