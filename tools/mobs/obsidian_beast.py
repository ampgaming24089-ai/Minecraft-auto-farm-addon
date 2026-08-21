import sys
sys.path.insert(0, "tools")
from mobkit import (UVAtlas, bone, cube, geometry, muzzle, limb, stand,
                    taper_chain, spine_row, write)

# Obsidian Beast: a bull made of volcanic glass. Heavy front, low head, huge
# curved horns, and plates of obsidian over a body that glows in the seams
# between them - the light comes out of the cracks, not off the surface.
atlas = UVAtlas(256, 256, padding=1)
bones = []

uv = atlas.box((16, 15, 20))
bones.append(bone("chest", [0, 22, -6], [cube([-8, 15, -18], [16, 15, 20], uv)]))
uv = atlas.box((13, 13, 16))
bones.append(bone("hips", [0, 21, 4], [cube([-6.5, 14, 2], [13, 13, 16], uv)],
                  parent="chest"))
# A humped shoulder ridge - the mass that tells you it charges.
uv = atlas.box((14, 6, 14))
bones.append(bone("hump", [0, 30, -10], [cube([-7, 28, -16], [14, 6, 14], uv)],
                  parent="chest"))

# Plates. A torso built from two boxes reads as two boxes however it is
# painted; slabs laid over it at slightly different depths give the light
# somewhere to break, which is the whole reason obsidian looks like obsidian.
PLATES = (
    ("plate_shoulder", "chest", (15, 7, 9), (0, 24, -15), 0.5),
    ("plate_rib",      "chest", (17, 6, 11), (0, 19, -8), 0.25),
    ("plate_belly",    "chest", (13, 4, 13), (0, 14, -6), 0.4),
    ("plate_flank",    "hips",  (14, 7, 11), (0, 22, 7), 0.3),
    ("plate_rump",     "hips",  (12, 6, 8), (0, 17, 14), 0.35),
)
for name, parent, size, centre, grow in PLATES:
    pw, ph, pd = size
    cx, cy, cz = centre
    uv = atlas.box((pw, ph, pd))
    bones.append(bone(name, [cx, cy, cz],
                      [cube([cx - pw / 2.0, cy - ph / 2.0, cz - pd / 2.0],
                            [pw, ph, pd], uv, inflate=grow)], parent=parent))

# Vents cut through the hump, where the heat gets out.
for i in range(3):
    uv = atlas.box((2, 1, 7))
    vx = -4 + i * 4
    bones.append(bone("vent_%d" % i, [vx, 34, -10],
                      [cube([vx - 1, 33.5, -14], [2, 1, 7], uv, inflate=0.1)],
                      parent="hump", rotation=[0, 0, (i - 1) * 6]))

uv = atlas.box((9, 9, 8))
bones.append(bone("neck", [0, 22, -18], [cube([-4.5, 17, -25], [9, 9, 8], uv)],
                  parent="chest", rotation=[18, 0, 0]))
# A collar of broken glass around the neck join, hiding the seam and giving
# the head something to turn against.
for i in range(6):
    ang = i * 60
    uv = atlas.box((4, 4, 5))
    bones.append(bone("collar_%d" % i, [0, 22, -20],
                      [cube([-2, 22 + 4.5, -22.5], [4, 4, 5], uv, inflate=0.3)],
                      parent="neck", rotation=[0, 0, ang]))

bones.extend(muzzle(atlas, "head", "neck", [0, 20, -24],
                    skull=(11, 10, 10), snout=(9, 8, 8),
                    jaw_drop=10.0, teeth=4, tooth_size=(1, 3, 1)))

# Tusks curving up out of the lower jaw, past the snout.
for side, mirror in ((1, False), (-1, True)):
    tag = "tusk_" + ("l" if side > 0 else "r")
    prev, x, y, z = "head_jaw", side * 4, 15, -30
    for i in range(2):
        w = 3 - i
        uv = atlas.box((max(1, w), max(1, w), 5 - i))
        bones.append(bone("%s_%d" % (tag, i), [x, y, z],
                          [cube([x - w / 2.0, y - w / 2.0, z - (5 - i)],
                                [max(1, w), max(1, w), 5 - i], uv, mirror=mirror)],
                          parent=prev, rotation=[-34 - i * 20, side * 8, 0]))
        prev = "%s_%d" % (tag, i)
        y += 2
        z -= 3

# Horns: four tapering segments a side, curving forward and up. They are the
# silhouette of the whole animal from the front, so they are worth the bones.
for side, mirror in ((1, False), (-1, True)):
    tag = "horn_" + ("l" if side > 0 else "r")
    prev, x, y, z = "head", side * 5, 26, -28
    for i in range(4):
        w = 6 - i
        d = 9 - i
        uv = atlas.box((max(1, w), max(1, w), d))
        bones.append(bone("%s_%d" % (tag, i), [x, y, z],
                          [cube([x - w / 2.0, y - w / 2.0, z - d],
                                [max(1, w), max(1, w), d], uv, mirror=mirror)],
                          parent=prev,
                          rotation=[-8 - i * 13, side * (26 - i * 9), side * 9]))
        prev = "%s_%d" % (tag, i)
        y += 3
        z -= 7
    # Shards over the eye, so the brow line is broken glass rather than a lip.
    uv = atlas.box((2, 3, 2))
    bones.append(bone(tag.replace("horn", "browshard"), [side * 4, 24, -32],
                      [cube([side * 4 - 1, 24, -33], [2, 3, 2], uv)],
                      parent="head_brow", rotation=[-24, 0, side * 14]))

for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    bones.extend(limb(atlas, "fore_" + tag, "chest", [side * 6, 15, -12],
                      (7, 9, 7), (6, 8, 6), foot=(8, 4, 10), mirrored=mirror))
    bones.extend(limb(atlas, "hind_" + tag, "hips", [side * 5, 14, 12],
                      (7, 9, 7), (5, 9, 5), foot=(7, 4, 9), mirrored=mirror))
    # Cloven toes. A flat slab foot is the last thing that reads as furniture.
    for foot, fz, toe in (("fore_" + tag + "_foot", -19, 3), ("hind_" + tag + "_foot", 5, 3)):
        for t, off in ((0, -2), (1, 2)):
            uv = atlas.box((3, 3, 4))
            bx = side * (6 if "fore" in foot else 5) + off
            by = 15 - 9 - 8 - 4 if "fore" in foot else 14 - 9 - 9 - 4
            bones.append(bone("%s_toe%d" % (foot, t), [bx, by, fz],
                              [cube([bx - 1.5, by, fz - 3], [3, 3, 4], uv,
                                    mirror=mirror)], parent=foot))

tail, tip = taper_chain(atlas, "tail", "hips", [0, 24, 18], 6, (5, 5, 6), 5.0,
                        shrink=0.88)
bones.extend(tail)
# A club at the end, not a nub: a core with spikes coming off four faces.
uv = atlas.box((9, 9, 10))
bones.append(bone("tailmace", [0, 24, 47], [cube([-4.5, 19.5, 42], [9, 9, 10], uv)],
                  parent=tip))
# Four spikes and a point, tilted off true so the club reads as broken rock
# rather than a machined wheel.
for i, rot in enumerate(([-9, 0, 4], [7, 0, 184], [4, 0, -86], [-6, 0, 94])):
    uv = atlas.box((3, 6, 4))
    bones.append(bone("macespike_%d" % i, [0, 24, 47],
                      [cube([-1.5, 28, 45], [3, 6, 4], uv)],
                      parent="tailmace", rotation=rot))
uv = atlas.box((4, 4, 6))
bones.append(bone("macespike_4", [0, 24, 47], [cube([-2, 22, 51], [4, 4, 6], uv)],
                  parent="tailmace"))

# Obsidian shards erupting along the spine.
bones.extend(spine_row(atlas, "shard", "chest", [0, 34, -14], 4, (3, 7, 4), 5.0,
                       taper=0.9))
bones.extend(spine_row(atlas, "rumpshard", "hips", [0, 28, 4], 3, (3, 5, 4), 5.0,
                       taper=0.88))
# Smaller splinters flanking the ridge, so it is a fracture and not a comb.
for side in (1, -1):
    for i in range(3):
        uv = atlas.box((2, 4, 3))
        z = -12 + i * 7
        bones.append(bone("splinter_%s%d" % ("l" if side > 0 else "r", i),
                          [side * 4, 31, z],
                          [cube([side * 4 - 1, 31, z - 1.5], [2, 4, 3], uv)],
                          parent="chest", rotation=[0, 0, side * 34]))
# Nose ring, because something once tried to lead it.
uv = atlas.box((5, 5, 2))
bones.append(bone("ring", [0, 15, -36], [cube([-2.5, 10, -36], [5, 5, 2], uv)],
                  parent="head_snout"))

write("RP/models/entity/obsidian_beast.geo.json",
      geometry("geometry.voidbound.obsidian_beast", (256, 256), stand(bones),
               bounds=(4, 3, (0, 1.4, 0))))
print("obsidian_beast: %d bones" % len(bones))
