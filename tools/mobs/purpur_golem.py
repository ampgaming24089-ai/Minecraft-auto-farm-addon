import sys
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, limb, write

# Purpur Golem: a thing assembled out of blocks, so the design leans into that
# rather than hiding it - chunky masses with visible gaps at the joints, and
# every mass built from two or three offset slabs so no surface is one flat
# plane. What sells a golem is weight: wide shoulders, short neck, huge hands.
atlas = UVAtlas(256, 256, padding=1)
bones = []
HIP = 22


def massing(name, parent, centre, size, splits, rotation=None):
    """One body mass built from several offset slabs, so its silhouette has
    steps in it instead of being a single box."""
    cx, cy, cz = centre
    w, h, d = size
    out = []
    uv = atlas.box((w, h, d))
    out.append(bone(name, [cx, cy, cz],
                    [cube([cx - w / 2.0, cy - h / 2.0, cz - d / 2.0], [w, h, d], uv)],
                    parent=parent, rotation=rotation))
    for i, (sw, sh, sd, ox, oy, oz) in enumerate(splits):
        uv = atlas.box((sw, sh, sd))
        out.append(bone("%s_p%d" % (name, i), [cx, cy, cz],
                        [cube([cx + ox - sw / 2.0, cy + oy - sh / 2.0,
                               cz + oz - sd / 2.0], [sw, sh, sd], uv)],
                        parent=name))
    return out


bones.extend(massing("torso", None, [0, HIP + 16, 0], (18, 20, 12),
                     [(20, 6, 14, 0, 8, 0), (14, 5, 14, 0, -9, 0),
                      (8, 12, 15, 0, 2, 0)]))
bones.extend(massing("head", "torso", [0, HIP + 32, -1], (12, 10, 11),
                     [(14, 3, 12, 0, 5, 0), (6, 4, 4, 0, -3, -6)]))
# Brow slab over the eyes; a golem's whole face is the shadow under this.
uv = atlas.box((14, 3, 4))
bones.append(bone("brow", [0, HIP + 36, -6],
                  [cube([-7, HIP + 34, -8], [14, 3, 4], uv)], parent="head"))

for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    bones.extend(massing("shoulder_" + tag, "torso",
                         [side * 11, HIP + 24, 0], (8, 8, 12),
                         [(10, 4, 13, 0, 3, 0)]))
    arm = "arm_" + tag
    bones.extend(massing(arm, "shoulder_" + tag, [side * 12, HIP + 14, 0],
                         (7, 16, 8), [(8, 5, 9, 0, 6, 0)],
                         rotation=[0, 0, side * -5]))
    # Oversized fists, which is most of what makes a golem look heavy.
    bones.extend(massing("fist_" + tag, arm, [side * 12, HIP + 3, 0], (9, 9, 10),
                         [(10, 4, 11, 0, -3, 0)]))

for side, mirror in ((1, False), (-1, True)):
    tag = "l" if side > 0 else "r"
    bones.extend(limb(atlas, "leg_" + tag, "torso", [side * 5, HIP + 6, 0],
                      (8, 12, 8), (7, 11, 7), foot=(9, 4, 12), mirrored=mirror))

# Crystal growths breaking out of the shoulders and back - it is made of
# purpur, and purpur grows.
for i, (x, y, z, w, h, d) in enumerate([(6, HIP + 28, 5, 3, 7, 3),
                                        (-7, HIP + 26, 4, 3, 6, 3),
                                        (0, HIP + 30, 6, 4, 8, 4),
                                        (9, HIP + 18, 4, 3, 5, 3)]):
    uv = atlas.box((w, h, d))
    bones.append(bone("shard_%d" % i, [x, y, z],
                      [cube([x - w / 2.0, y, z - d / 2.0], [w, h, d], uv)],
                      parent="torso", rotation=[-22, 0, (12 if x >= 0 else -12)]))

# --- Ornament. What holds a golem together is as interesting as the golem:
# a core burning in its chest, iron bands clamping the masses shut, and runes
# cut into the plates.
uv = atlas.box((7, 7, 4))
bones.append(bone("core", [0, HIP + 18, -6],
                  [cube([-3.5, HIP + 15, -10], [7, 7, 4], uv)], parent="torso"))
uv = atlas.box((11, 11, 3))
bones.append(bone("core_frame", [0, HIP + 18, -6],
                  [cube([-5.5, HIP + 13, -9], [11, 11, 3], uv)], parent="torso"))

# Bands clamping the torso and each upper arm.
for i, (w, h, d, y, parent) in enumerate([(21, 3, 15, HIP + 22, "torso"),
                                          (17, 3, 15, HIP + 8, "torso")]):
    uv = atlas.box((w, h, d))
    bones.append(bone("band_%d" % i, [0, y, 0],
                      [cube([-w / 2.0, y, -d / 2.0], [w, h, d], uv)], parent=parent))
for side in (1, -1):
    tag = "l" if side > 0 else "r"
    uv = atlas.box((9, 3, 10))
    bones.append(bone("armband_" + tag, [side * 12, HIP + 16, 0],
                      [cube([side * 12 - 4.5, HIP + 16, -5], [9, 3, 10], uv)],
                      parent="arm_" + tag))

# More crystal, and bigger, breaking out of the back and forearms.
for i, (x, y, z, w, h, d, parent) in enumerate([
        (4, HIP + 32, 6, 4, 10, 4, "torso"), (-6, HIP + 29, 6, 3, 8, 3, "torso"),
        (11, HIP + 10, 3, 3, 7, 3, "arm_l"), (-11, HIP + 10, 3, 3, 7, 3, "arm_r")]):
    uv = atlas.box((w, h, d))
    bones.append(bone("bigshard_%d" % i, [x, y, z],
                      [cube([x - w / 2.0, y, z - d / 2.0], [w, h, d], uv)],
                      parent=parent, rotation=[-26, 0, (16 if x >= 0 else -16)]))

write("RP/models/entity/purpur_golem.geo.json",
      geometry("geometry.voidbound.purpur_golem", (256, 256), bones,
               bounds=(3, 4, (0, 1.6, 0))))
print("purpur_golem: %d bones" % len(bones))
