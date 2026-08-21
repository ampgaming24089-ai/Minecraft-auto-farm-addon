import sys
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, muzzle, stand, taper_chain, write

# Void Wisp: a small drifting light wearing a rag of shadow.
#
# The first build wrapped the shroud *around* the core in a full ring, which
# sealed the light inside a drum - a wisp with no visible light is just a
# lampshade. So the core sits proud on top and the rags hang beneath it, the
# way a lantern carries its own glow above the shadow it casts.
atlas = UVAtlas(256, 256, padding=1)
bones = []

uv = atlas.box((9, 9, 9))
bones.append(bone("core", [0, 26, 0], [cube([-4.5, 22, -4.5], [9, 9, 9], uv)]))
uv = atlas.box((11, 11, 11))
bones.append(bone("glow", [0, 26, 0],
                  [cube([-5.5, 21, -5.5], [11, 11, 11], uv, inflate=0.4)],
                  parent="core"))
# Flares breaking off the core on the diagonals - it is burning, not lit.
for i in range(4):
    uv = atlas.box((3, 6, 3))
    bones.append(bone("flare_%d" % i, [0, 27, 0],
                      [cube([-1.5, 30, -2], [3, 6, 3], uv)],
                      parent="core", rotation=[24, 45 + i * 90, 0]))

# A cowl over the back and top only, so the face stays in the open.
uv = atlas.box((11, 5, 8))
bones.append(bone("cowl", [0, 31, 2], [cube([-5.5, 29, -2], [11, 5, 8], uv)],
                  parent="core", rotation=[10, 0, 0]))
uv = atlas.box((9, 8, 4))
bones.append(bone("nape", [0, 29, 5], [cube([-4.5, 22, 4], [9, 8, 4], uv)],
                  parent="cowl", rotation=[-12, 0, 0]))

# The rags: panels hanging from the underside, splayed on a fan.
for i in range(8):
    ang = i * 45
    uv = atlas.box((5, 12, 3))
    bones.append(bone("rag_%d" % i, [0, 22, 0],
                      [cube([-2.5, 10, -6], [5, 12, 3], uv)],
                      parent="core", rotation=[16 + (i % 3) * 5, ang, 0]))
    uv = atlas.box((4, 9, 2))
    bones.append(bone("rag_%d_hem" % i, [0, 10, -6],
                      [cube([-2, 1, -6.5], [4, 9, 2], uv)],
                      parent="rag_%d" % i, rotation=[12 + (i % 4) * 7, 0, 0]))

# The face, hung on the front of the core where the light is.
bones.extend(muzzle(atlas, "face", "core", [0, 26, -4],
                    skull=(8, 7, 3), snout=(6, 5, 3),
                    jaw_drop=26.0, teeth=3, tooth_size=(1, 2, 1),
                    nostrils=False, brow=True))

# Motes orbiting it. Small and tinted - a 2x2 white cube at this scale is a
# die floating in mid air, not a spark.
for i, (r, y, ang) in enumerate(((8, 22, 0), (10, 30, 70), (7, 34, 140),
                                 (11, 19, 210), (9, 27, 290), (12, 32, 335))):
    uv = atlas.box((1, 1, 1))
    bones.append(bone("mote_%d" % i, [0, y, 0],
                      [cube([-0.5, y, -r], [1, 1, 1], uv)],
                      parent="core", rotation=[0, ang, 0]))

# Two trailing wisps of the stuff it is made of.
for side in (1, -1):
    chain, _ = taper_chain(atlas, "trail_%s" % ("l" if side > 0 else "r"), "core",
                           [side * 3, 20, 5], 5, (3, 3, 4), 4.0, shrink=0.78,
                           drop=-1.5)
    bones.extend(chain)

write("RP/models/entity/void_wisp.geo.json",
      geometry("geometry.voidbound.void_wisp", (256, 256), bones,
               bounds=(1.5, 2, (0, 1.2, 0))))
print("void_wisp: %d bones" % len(bones))
