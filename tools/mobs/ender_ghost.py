import sys
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, muzzle, stand, taper_chain, write

# Ender Ghost: what is left of something that used to walk here. A heavy
# hooded shoulder line, long arms that end in claws, and a lower body that
# stops being a body - it frays into strips and then into nothing.
#
# It has to read differently from the Wisp at a glance, so where the Wisp is
# a small light in rags, this is large, cloth-heavy and lit only in the face.
atlas = UVAtlas(256, 256, padding=1)
bones = []

uv = atlas.box((14, 13, 8))
bones.append(bone("torso", [0, 34, 0], [cube([-7, 28, -4], [14, 13, 8], uv)]))
# The shoulder mantle: the thing that gives it presence.
uv = atlas.box((22, 6, 12))
bones.append(bone("mantle", [0, 41, 0], [cube([-11, 38, -6], [22, 6, 12], uv)],
                  parent="torso"))
for side in (1, -1):
    uv = atlas.box((7, 9, 10))
    bones.append(bone("shoulder_%s" % ("l" if side > 0 else "r"),
                      [side * 9, 40, 0],
                      [cube([side * 9 - 3.5, 31, -5], [7, 9, 10], uv)],
                      parent="mantle", rotation=[0, 0, side * 16]))
uv = atlas.box((12, 7, 9))
bones.append(bone("collar", [0, 44, 0], [cube([-6, 42, -4.5], [12, 7, 9], uv)],
                  parent="mantle"))

# The hood, and a face set back inside it so the light has somewhere to come
# from. The brim overhangs, which is what puts the eyes in shadow.
uv = atlas.box((12, 11, 11))
bones.append(bone("hood", [0, 50, 0], [cube([-6, 46, -5.5], [12, 11, 11], uv)],
                  parent="collar", rotation=[6, 0, 0]))
uv = atlas.box((13, 5, 6))
bones.append(bone("brim", [0, 52, -5], [cube([-6.5, 50, -10], [13, 5, 6], uv)],
                  parent="hood", rotation=[-22, 0, 0]))
for i in range(3):
    uv = atlas.box((5, 8 - i, 4))
    bones.append(bone("crest_%d" % i, [0, 57, 4 + i * 3],
                      [cube([-2.5, 57, 3 + i * 3], [5, 8 - i, 4], uv)],
                      parent="hood", rotation=[26 + i * 12, 0, 0]))

bones.extend(muzzle(atlas, "face", "hood", [0, 50, -4],
                    skull=(8, 8, 4), snout=(6, 5, 3),
                    jaw_drop=20.0, teeth=4, tooth_size=(1, 3, 1),
                    nostrils=False, brow=False))

# Arms: long, thin, and hanging. Three joints so they can trail behind it.
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((5, 13, 5))
    bones.append(bone("upper_" + tag, [side * 10, 38, 0],
                      [cube([side * 10 - 2.5, 25, -2.5], [5, 13, 5], uv,
                            mirror=mirror)], parent="shoulder_" + tag,
                      rotation=[-8, 0, side * 10]))
    uv = atlas.box((4, 14, 4))
    bones.append(bone("fore_" + tag, [side * 12, 25, 0],
                      [cube([side * 12 - 2, 11, -2], [4, 14, 4], uv,
                            mirror=mirror)], parent="upper_" + tag,
                      rotation=[-18, 0, side * 6]))
    # A ragged cuff over the wrist, so the arm is dressed like the rest.
    uv = atlas.box((7, 7, 7))
    bones.append(bone("cuff_" + tag, [side * 13, 14, 0],
                      [cube([side * 13 - 3.5, 9, -3.5], [7, 7, 7], uv,
                            mirror=mirror)], parent="fore_" + tag))
    uv = atlas.box((5, 5, 5))
    bones.append(bone("hand_" + tag, [side * 13, 9, 0],
                      [cube([side * 13 - 2.5, 4, -2.5], [5, 5, 5], uv,
                            mirror=mirror)], parent="cuff_" + tag,
                      rotation=[-10, 0, 0]))
    for i in range(4):
        uv = atlas.box((1, 7 - (i % 2), 1))
        cx = side * 13 + (i - 1.5) * 1.4
        bones.append(bone("claw_%s%d" % (tag, i), [cx, 4, -1],
                          [cube([cx - 0.5, -3 + (i % 2), -1.5],
                                [1, 7 - (i % 2), 1], uv)],
                          parent="hand_" + tag,
                          rotation=[16 + i * 5, 0, (i - 1.5) * 10]))

# The lower body: strips that get thinner and fainter until they stop.
for i in range(9):
    ang = i * 40
    uv = atlas.box((4, 14, 3))
    bones.append(bone("tatter_%d" % i, [0, 28, 0],
                      [cube([-2, 14, -5], [4, 14, 3], uv)],
                      parent="torso", rotation=[10 + (i % 3) * 6, ang, 0]))
    uv = atlas.box((3, 11, 2))
    bones.append(bone("tatter_%d_end" % i, [0, 14, -5],
                      [cube([-1.5, 3, -5.5], [3, 11, 2], uv)],
                      parent="tatter_%d" % i, rotation=[10 + (i % 4) * 8, 0, 0]))

# A last thread of it trailing away underneath.
chain, _ = taper_chain(atlas, "wisp", "torso", [0, 14, 0], 5, (4, 5, 4), -6.0,
                       shrink=0.76, axis="y")
bones.extend(chain)

write("RP/models/entity/ender_ghost.geo.json",
      geometry("geometry.voidbound.ender_ghost", (256, 256), stand(bones),
               bounds=(2, 3, (0, 1.6, 0))))
print("ender_ghost: %d bones" % len(bones))
