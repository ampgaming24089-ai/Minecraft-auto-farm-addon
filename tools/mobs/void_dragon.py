import sys
sys.path.insert(0, "tools")
from mobkit import (UVAtlas, bone, cube, geometry, taper_chain, spine_row,
                    limb, muzzle, write)

# Void Dragon. The flagship, so everything that reads at silhouette gets built
# properly: a neck that curves, a skull with a real jaw and horns, wings that
# are a spar with ribs and membrane rather than a plate, four jointed legs, and
# a tail that runs half the length of the animal.
atlas = UVAtlas(512, 512, padding=1)
bones = []

# --- Torso: chest and hips, chest deeper so the wings have something to hang
# off and the profile is not a tube.
uv = atlas.box((16, 16, 22))
bones.append(bone("chest", [0, 30, -6], [cube([-8, 22, -17], [16, 16, 22], uv)]))
uv = atlas.box((14, 14, 16))
bones.append(bone("hips", [0, 30, 5], [cube([-7, 23, 5], [14, 14, 16], uv)],
                  parent="chest"))

# --- Neck: five links curving up, then a skull ---------------------------
neck, neck_tip = taper_chain(atlas, "neck", "chest", [0, 34, -18], 5,
                             (9, 9, 7), -6.5, shrink=0.9, drop=1.4)
for b in neck:
    b["rotation"] = [-9, 0, 0]
bones.extend(neck)

# A proper head: braincase, a snout that comes forward off it, a hinged lower
# jaw with a dark maw behind the teeth, nostrils and an overhanging brow.
bones.extend(muzzle(atlas, "skull", neck_tip, [0, 41, -44],
                    skull=(11, 10, 12), snout=(8, 7, 11),
                    jaw_drop=13.0, teeth=5, tooth_size=(1, 3, 1)))
for side, mirror in ((1, False), (-1, True)):
    tag = "horn_" + ("left" if side > 0 else "right")
    prev = "skull"
    x, y, z = side * 3.5, 45, -46
    for i in range(3):
        w = 3 - i
        uv = atlas.box((max(1, w), max(1, w), 8 - i * 2))
        bones.append(bone("%s_%d" % (tag, i), [x, y, z],
                          [cube([x - w / 2.0, y, z], [max(1, w), max(1, w), 8 - i * 2],
                                uv, mirror=mirror)],
                          parent=prev, rotation=[-14, side * 12, side * 6]))
        prev = "%s_%d" % (tag, i)
        y += 2.5
        z += 5
# A frill of spikes around the jaw hinge, which is what makes a head read as
# a dragon's rather than a lizard's.
for i in range(3):
    for side, mirror in ((1, False), (-1, True)):
        uv = atlas.box((2, 6 - i, 2))
        bones.append(bone("frill_%s_%d" % ("l" if side > 0 else "r", i),
                          [side * 5.5, 41, -38 + i * 4],
                          [cube([side * 5.5 - 1, 41, -38 + i * 4], [2, 7 - i, 2],
                                uv, mirror=mirror)],
                          parent="skull", rotation=[0, 0, side * (30 + i * 10)]))

# --- Wings ---------------------------------------------------------------
for side, mirror in ((1, False), (-1, True)):
    tag = "wing_" + ("left" if side > 0 else "right")
    # Upper arm out from the shoulder, then a forearm swept back.
    uv = atlas.box((18, 4, 5))
    ox = 8 if side > 0 else -26
    bones.append(bone(tag, [side * 8, 36, -12],
                      [cube([ox, 34, -14], [18, 4, 5], uv, mirror=mirror)],
                      parent="chest", rotation=[0, 0, side * -16]))
    uv = atlas.box((22, 3, 4))
    fx = 26 if side > 0 else -48
    bones.append(bone(tag + "_fore", [side * 26, 36, -12],
                      [cube([fx, 34.5, -13], [22, 3, 4], uv, mirror=mirror)],
                      parent=tag, rotation=[0, side * -10, side * -8]))
    # Four fingers off the forearm, each with a membrane panel behind it.
    for i in range(4):
        reach = 48
        length = 30 - i * 5
        uv = atlas.box((2, 2, length))
        px = side * reach if side > 0 else side * reach - 2
        finger = "%s_finger_%d" % (tag, i)
        bones.append(bone(finger, [side * reach, 36, -12],
                          [cube([px, 35, -12], [2, 2, length], uv, mirror=mirror)],
                          parent=tag + "_fore",
                          rotation=[0, side * (-14 + i * 13), side * (4 - i * 3)]))
        uv = atlas.box((14, 1, length))
        wx = side * reach - (14 if side > 0 else 0)
        bones.append(bone("%s_web_%d" % (tag, i), [side * reach, 36, -12],
                          [cube([wx, 35.5, -12], [14, 1, length], uv, mirror=mirror)],
                          parent=finger, rotation=[3 + i * 2, 0, 0]))

# --- Legs: four, jointed, with claws -------------------------------------
for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    bones.extend(limb(atlas, "foreleg_" + tag, "chest", [side * 6, 24, -12],
                      (5, 9, 5), (4, 9, 4), foot=(5, 3, 7), splay=6, mirrored=mirror))
    bones.extend(limb(atlas, "hindleg_" + tag, "hips", [side * 6, 25, 14],
                      (6, 10, 6), (4, 10, 4), foot=(6, 3, 8), splay=8, mirrored=mirror))

# --- Tail: ten links, spined, with a blade at the end --------------------
tail, tail_tip = taper_chain(atlas, "tail", "hips", [0, 30, 22], 8,
                             (10, 10, 8), 6.6, shrink=0.93)
bones.extend(tail)
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((5, 2, 10))
    ox = 1 if side > 0 else -6
    bones.append(bone("tailfin_" + ("l" if side > 0 else "r"), [0, 30, 70],
                      [cube([ox, 29, 68], [5, 2, 10], uv, mirror=mirror)],
                      parent=tail_tip, rotation=[0, side * 18, side * 26]))

# --- Spines down the whole back ------------------------------------------
bones.extend(spine_row(atlas, "spine", "chest", [0, 38, -16], 5, (2, 6, 3), 5.0,
                       taper=0.94))
bones.extend(spine_row(atlas, "hipspine", "hips", [0, 37, 6], 4, (2, 5, 3), 4.5,
                       taper=0.9))

write("RP/models/entity/void_dragon.geo.json",
      geometry("geometry.voidbound.void_dragon", (512, 512), bones,
               bounds=(11, 6, (0, 2.5, 0))))
print("void_dragon: %d bones, %d cubes"
      % (len(bones), sum(len(b.get("cubes", [])) for b in bones)))
