import sys, math
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, taper_chain, write

# Chorus Fiend: a chorus plant that stood up. The silhouette is the plant's -
# a knobbled central stem with branches budding off it at every angle - and
# the face is a lantern hollowed into the trunk.
atlas = UVAtlas(256, 256, padding=1)
bones = []

# Trunk: five knuckled segments, each fatter at the joint than between them.
z_y = 8
prev = None
trunk = []
for i, (w, h) in enumerate([(11, 9), (9, 8), (10, 8), (8, 7), (9, 6)]):
    uv = atlas.box((w, h, w))
    name = "trunk_%d" % i
    bones.append(bone(name, [0, z_y, 0],
                      [cube([-w / 2.0, z_y, -w / 2.0], [w, h, w], uv)], parent=prev))
    # A knuckle collar at each joint, which is what makes chorus read as
    # chorus rather than as a stack of boxes.
    uv = atlas.box((w + 2, 2, w + 2))
    bones.append(bone(name + "_knuckle", [0, z_y + h - 1, 0],
                      [cube([-(w + 2) / 2.0, z_y + h - 1, -(w + 2) / 2.0],
                            [w + 2, 2, w + 2], uv)], parent=name))
    trunk.append(name)
    prev = name
    z_y += h

# The face: a hollow burned into the trunk, with a lit interior.
uv = atlas.box((7, 6, 2))
bones.append(bone("hollow", [0, 26, -5],
                  [cube([-3.5, 24, -5.5], [7, 6, 2], uv)], parent="trunk_2"))
for i, (x, y) in enumerate(((-2, 27), (2, 27))):
    uv = atlas.box((2, 2, 2))
    bones.append(bone("glow_%d" % i, [x, y, -5.5],
                      [cube([x - 1, y, -6.5], [2, 2, 2], uv)], parent="hollow"))

# Branches: eight arms budding off the trunk on taper chains, each ending in
# a bud. They are the reach of the thing and they carry the whole silhouette.
for i in range(8):
    angle = (i / 8.0) * math.pi * 2 + 0.3
    host = trunk[1 + i % 4]
    y = 14 + (i % 4) * 8
    rx, rz = math.cos(angle) * 4, math.sin(angle) * 4
    chain, tip = taper_chain(atlas, "branch_%d" % i, host, [rx, y, rz],
                             3 + i % 2, (5, 5, 6), 5.0, shrink=0.82)
    chain[0]["rotation"] = [62 - (i % 3) * 18, math.degrees(angle), 0]
    for link in chain[1:]:
        link["rotation"] = [-14, 0, 0]
    bones.extend(chain)
    uv = atlas.box((6, 6, 6))
    bones.append(bone("bud_%d" % i, [rx, y, rz],
                      [cube([rx - 3, y, rz - 3], [6, 6, 6], uv)], parent=tip))

# Roots gripping the ground.
for i in range(6):
    angle = (i / 6.0) * math.pi * 2
    rx, rz = math.cos(angle) * 5, math.sin(angle) * 5
    uv = atlas.box((3, 9, 3))
    bones.append(bone("root_%d" % i, [rx, 8, rz],
                      [cube([rx - 1.5, 0, rz - 1.5], [3, 9, 3], uv)],
                      parent="trunk_0", rotation=[16, math.degrees(angle), 0]))

write("RP/models/entity/chorus_fiend.geo.json",
      geometry("geometry.voidbound.chorus_fiend", (256, 256), bones,
               bounds=(4, 4, (0, 1.8, 0))))
print("chorus_fiend: %d bones" % len(bones))
