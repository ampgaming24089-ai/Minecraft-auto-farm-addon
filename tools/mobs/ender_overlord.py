import sys, math
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, taper_chain, write

# Ender Overlord: a thing that is mostly eye. The design problem is that a
# sphere of cubes reads as a lump, so the mass is built as an irregular cluster
# of offset plates around a core - and then every silhouette-carrying feature
# radiates: tentacles below, eye stalks above and out.
atlas = UVAtlas(512, 512, padding=1)
bones = []

CENTRE_Y = 34

# --- Core mass: a stack of slabs, each rotated a little, so the body has
# facets that catch light instead of being one smooth ball.
uv = atlas.box((20, 18, 20))
bones.append(bone("core", [0, CENTRE_Y, 0],
                  [cube([-10, CENTRE_Y - 9, -10], [20, 18, 20], uv)]))
SHELL = [(24, 6, 22, 0, 6, 0, 0), (22, 5, 24, 0, -6, 0, 18),
         (18, 22, 18, 0, 0, 0, 45), (26, 4, 18, 0, 1, 0, -22)]
for i, (w, h, d, ox, oy, oz, spin) in enumerate(SHELL):
    uv = atlas.box((w, h, d))
    bones.append(bone("shell_%d" % i, [0, CENTRE_Y, 0],
                      [cube([ox - w / 2.0, CENTRE_Y + oy - h / 2.0, oz - d / 2.0],
                            [w, h, d], uv)], parent="core",
                      rotation=[0, spin, 0]))

# --- The central eye: concentric rings stepping forward to a lit pupil, which
# is the only way a flat disc reads as an eyeball at this scale.
RINGS = [(16, 16, 3, 0), (13, 13, 3, 2), (10, 10, 3, 4), (6, 6, 3, 6), (3, 3, 3, 8)]
prev = "core"
for i, (w, h, d, push) in enumerate(RINGS):
    uv = atlas.box((w, h, d))
    bones.append(bone("iris_%d" % i, [0, CENTRE_Y, -10 - push],
                      [cube([-w / 2.0, CENTRE_Y - h / 2.0, -10 - push - d],
                            [w, h, d], uv)], parent=prev))
    prev = "iris_%d" % i
# A lid over the top of the eye, so it can blink and so the eye has a brow.
uv = atlas.box((18, 5, 6))
bones.append(bone("lid", [0, CENTRE_Y + 8, -12],
                  [cube([-9, CENTRE_Y + 6, -18], [18, 5, 6], uv)], parent="core"))

# --- Tentacles: nine, radiating down and out on a ring, each a taper chain
# with its own bones so they can writhe independently.
for i in range(9):
    angle = (i / 9.0) * math.pi * 2
    rx = math.cos(angle) * 8
    rz = math.sin(angle) * 8
    chain, tip = taper_chain(atlas, "tent_%d" % i, "core",
                             [rx, CENTRE_Y - 9, rz], 6, (4, 4, 5), 4.4,
                             shrink=0.84)
    # Splay each chain outward from the body and let it fall.
    chain[0]["rotation"] = [58, math.degrees(angle), 0]
    for link in chain[1:]:
        link["rotation"] = [9, 0, 0]
    bones.extend(chain)
    uv = atlas.box((2, 3, 2))
    bones.append(bone("barb_%d" % i, [rx, CENTRE_Y - 9, rz],
                      [cube([rx - 1, CENTRE_Y - 12, rz - 1], [2, 3, 2], uv)],
                      parent=tip))

# --- Satellite eyes: six on stalks, each a segment then a small eyeball with
# its own lit pupil. These are what make it read as a *watcher*.
for i in range(6):
    angle = (i / 6.0) * math.pi * 2 + 0.4
    rx = math.cos(angle) * 11
    rz = math.sin(angle) * 11
    stalk = "stalk_%d" % i
    uv = atlas.box((3, 12, 3))
    bones.append(bone(stalk, [rx, CENTRE_Y + 8, rz],
                      [cube([rx - 1.5, CENTRE_Y + 8, rz - 1.5], [3, 12, 3], uv)],
                      parent="core",
                      rotation=[-26, math.degrees(angle), 0]))
    uv = atlas.box((7, 7, 7))
    bones.append(bone("eye_%d" % i, [rx, CENTRE_Y + 20, rz],
                      [cube([rx - 3.5, CENTRE_Y + 20, rz - 3.5], [7, 7, 7], uv)],
                      parent=stalk))
    uv = atlas.box((3, 3, 3))
    bones.append(bone("pupil_%d" % i, [rx, CENTRE_Y + 23, rz - 3.5],
                      [cube([rx - 1.5, CENTRE_Y + 22, rz - 6], [3, 3, 3], uv)],
                      parent="eye_%d" % i))

# --- A crown of spikes around the upper shell, for silhouette.
for i in range(8):
    angle = (i / 8.0) * math.pi * 2 + 0.2
    rx = math.cos(angle) * 11
    rz = math.sin(angle) * 11
    uv = atlas.box((2, 9, 2))
    bones.append(bone("spike_%d" % i, [rx, CENTRE_Y + 6, rz],
                      [cube([rx - 1, CENTRE_Y + 6, rz - 1], [2, 9, 2], uv)],
                      parent="core",
                      rotation=[-18, math.degrees(angle), 0]))

write("RP/models/entity/ender_overlord.geo.json",
      geometry("geometry.voidbound.ender_overlord", (512, 512), bones,
               bounds=(5, 5, (0, 2, 0))))
print("ender_overlord: %d bones, %d cubes"
      % (len(bones), sum(len(b.get("cubes", [])) for b in bones)))
