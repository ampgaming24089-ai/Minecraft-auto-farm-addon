import sys, os
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, taper_chain, spine_row, write

# Sky Ray: a manta the size of a small boat. The old one was a body slab, two
# flat fins and a stub tail - this is the same silhouette actually built.
atlas = UVAtlas(256, 256, padding=1)
bones = []

# Core body: five segments so the whole animal can undulate, widest at the
# shoulders and tapering both ways, which is what makes a ray a ray.
BODY = [(22, 6, 10), (26, 7, 12), (24, 6, 12), (18, 5, 10), (12, 4, 8)]
z = -18
prev = None
for i, (w, h, d) in enumerate(BODY):
    uv = atlas.box((w, h, d))
    name = "body_%d" % i
    bones.append(bone(name, [0, 20, z],
                      [cube([-w / 2.0, 20 - h / 2.0, z], [w, h, d], uv)],
                      parent=prev))
    prev = name
    z += d
core = "body_2"

# Head: a blunt wedge with a lit brow, plus two cephalic horns - the detail
# that separates a manta from a lozenge.
uv = atlas.box((14, 5, 8))
bones.append(bone("head", [0, 20, -18],
                  [cube([-7, 17.5, -26], [14, 5, 8], uv)], parent="body_0"))
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((3, 3, 7))
    bones.append(bone("horn_%s" % ("left" if side > 0 else "right"), [side * 5, 20, -26],
                      [cube([side * 5 - 1.5, 18.5, -32], [3, 3, 7], uv, mirror=mirror)],
                      parent="head", rotation=[-12, side * 9, 0]))

# Wings: five tapering panels a side, each its own bone, each swept a little
# further back and drooping a little more toward the tip.
for side, mirror in ((1, False), (-1, True)):
    tag = "left" if side > 0 else "right"
    parent = core
    reach = 6
    for i in range(5):
        w = 9 - i
        d = 20 - i * 3
        t = 6 - i
        uv = atlas.box((w, 2, d))
        name = "wing_%s_%d" % (tag, i)
        ox = side * reach if side > 0 else side * reach - w
        bones.append(bone(name, [side * reach, 20, -4],
                          [cube([ox, 19, -d / 2.0 - 2], [w, 2, d], uv, mirror=mirror)],
                          parent=parent,
                          rotation=[0, 0, side * (-4 - i * 2.5)]))
        parent = name
        reach += w

# Tail: eight shrinking links with a barb, so it whips instead of pointing.
tail_bones, tail_tip = taper_chain(atlas, "tail", "body_4", [0, 20, 24], 8,
                                   (5, 4, 5), 4.4, shrink=0.86)
bones.extend(tail_bones)
uv = atlas.box((2, 2, 6))
bones.append(bone("barb", [0, 20, 60], [cube([-1, 19, 58], [2, 2, 6], uv)],
                  parent=tail_tip))

# Dorsal ridge and belly plates: the two rows that stop it reading as a slab.
bones.extend(spine_row(atlas, "ridge", core, [0, 24, -14], 7, (3, 3, 4), 5.2,
                       taper=0.88))
for i in range(4):
    uv = atlas.box((10, 1, 6))
    bones.append(bone("gill_%d" % i, [0, 17, -14 + i * 6],
                      [cube([-5, 16.5, -14 + i * 6], [10, 1, 6], uv)],
                      parent=core))

write("RP/models/entity/sky_ray.geo.json",
      geometry("geometry.voidbound.sky_ray", (256, 256), bones,
               bounds=(6, 3, (0, 1.4, 0))))
print("sky_ray: %d bones, %d cubes" % (len(bones), sum(len(b.get("cubes", [])) for b in bones)))
