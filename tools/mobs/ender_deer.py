import sys
sys.path.insert(0, "tools")
from mobkit import (UVAtlas, bone, cube, geometry, limb, muzzle, spine_row,
                    stand, taper_chain, write)

# Ender Deer: the one thing in the End that looks like it belongs somewhere
# gentler. Long legs, a light frame, and a rack of antlers grown from the same
# crystal as the islands - the antlers are the whole silhouette, so they get
# real branching rather than two forked sticks.
atlas = UVAtlas(256, 256, padding=1)
bones = []

HIP = 30

uv = atlas.box((11, 12, 20))
bones.append(bone("body", [0, HIP, 0], [cube([-5.5, HIP - 6, -10], [11, 12, 20], uv)]))
uv = atlas.box((12, 13, 10))
bones.append(bone("chest", [0, HIP + 1, -9],
                  [cube([-6, HIP - 5.5, -18], [12, 13, 10], uv)], parent="body"))
uv = atlas.box((10, 10, 8))
bones.append(bone("rump", [0, HIP, 9], [cube([-5, HIP - 5, 8], [10, 10, 8], uv)],
                  parent="body"))

uv = atlas.box((6, 12, 6))
bones.append(bone("neck", [0, HIP + 5, -16],
                  [cube([-3, HIP + 3, -20], [6, 12, 6], uv)], parent="chest",
                  rotation=[-42, 0, 0]))
bones.extend(muzzle(atlas, "head", "neck", [0, HIP + 20, -22],
                    skull=(7, 7, 7), snout=(5, 5, 7),
                    jaw_drop=8.0, teeth=3, tooth_size=(1, 2, 1)))
# Ears, set wide and back.
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((2, 5, 3))
    bones.append(bone("ear_%s" % ("l" if side > 0 else "r"),
                      [side * 3.5, HIP + 24, -20],
                      [cube([side * 3.5 - 1, HIP + 24, -22], [2, 5, 3], uv,
                            mirror=mirror)], parent="head",
                      rotation=[30, side * 26, side * 34]))

# Antlers: a beam a side with tines coming off it, each on its own bone.
for side, mirror in ((1, False), (-1, True)):
    tag = "antler_" + ("l" if side > 0 else "r")
    prev = "head"
    x, y, z = side * 3, HIP + 26, -20
    for i in range(4):
        w = max(1, 3 - i // 2)
        length = 7 - i
        uv = atlas.box((w, length, w))
        bones.append(bone("%s_%d" % (tag, i), [x, y, z],
                          [cube([x - w / 2.0, y, z - w / 2.0], [w, length, w], uv,
                                mirror=mirror)],
                          parent=prev,
                          # The head hangs off a neck pitched 42 forward, and
                          # the antlers inherit that - built without undoing
                          # it, the whole rack curls down over the deer's own
                          # face. The first segment pays the neck back and
                          # then some, so the beam leaves the skull going up
                          # and back; the rest only add their own curve.
                          rotation=[62 if i == 0 else 8,
                                    side * (10 + i * 6),
                                    side * (26 - i * 5)]))
        prev = "%s_%d" % (tag, i)
        y += length
        z -= 2
        # A tine forking off this segment.
        if i < 3:
            tl = 6 - i
            uv = atlas.box((2, tl, 2))
            bones.append(bone("%s_tine_%d" % (tag, i), [x, y - 1, z],
                              [cube([x - 1, y - 1, z - 1], [2, tl, 2], uv,
                                    mirror=mirror)],
                              parent=prev,
                              rotation=[-40 + i * 14, side * 20, side * (52 - i * 8)]))

# A spine ridge of small crystal, and a short flagged tail.
bones.extend(spine_row(atlas, "ridge", "body", [0, HIP + 6, -8], 5, (2, 3, 3), 4.0,
                       taper=0.9))
tail, tip = taper_chain(atlas, "tail", "rump", [0, HIP + 4, 15], 3, (3, 4, 4), 3.0,
                        shrink=0.8)
bones.extend(tail)
uv = atlas.box((5, 7, 3))
bones.append(bone("flag", [0, HIP + 4, 24], [cube([-2.5, HIP - 3, 23], [5, 7, 3], uv)],
                  parent=tip, rotation=[-20, 0, 0]))

# Long thin legs, with a fetlock and a split hoof.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    for name, hz, parent in (("fore_" + tag, -13, "chest"), ("hind_" + tag, 10, "rump")):
        bones.extend(limb(atlas, name, parent, [side * 4, HIP - 5, hz],
                          (4, 12, 5), (3, 12, 4), foot=(4, 3, 6), mirrored=mirror))
        for t, off in ((0, -1), (1, 1)):
            uv = atlas.box((2, 3, 4))
            bx = side * 4 + off
            by = HIP - 5 - 12 - 12 - 3
            bones.append(bone("%s_toe%d" % (name, t), [bx, by, hz],
                              [cube([bx - 1, by, hz - 4], [2, 3, 4], uv,
                                    mirror=mirror)], parent=name + "_foot"))

write("RP/models/entity/ender_deer.geo.json",
      geometry("geometry.voidbound.ender_deer", (256, 256), stand(bones),
               bounds=(2, 3, (0, 1.3, 0))))
print("ender_deer: %d bones" % len(bones))
