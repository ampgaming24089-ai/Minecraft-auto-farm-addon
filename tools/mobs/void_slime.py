import sys
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, stand, taper_chain, write

# Void Slime: a block of congealed void. Built as stacked slabs rather than
# one cube so an animation can squash and rebound through it, with a lit core
# suspended in the middle, swallowed rubble it has not finished digesting, and
# a split down the front that opens into a mouth.
atlas = UVAtlas(256, 256, padding=1)
bones = []

# Body slabs, widest in the middle - a slime sags.
SLABS = ((0, 13, 12), (4, 17, 16), (9, 19, 18), (14, 17, 16), (19, 11, 11))
prev = None
for i, (y, w, d) in enumerate(SLABS):
    uv = atlas.box((w, 5, d))
    name = "blob_%d" % i
    bones.append(bone(name, [0, y, 0],
                      [cube([-w / 2.0, y, -d / 2.0], [w, 5, d], uv)],
                      parent=prev))
    prev = name

# The core: what is actually alive in there. A nucleus buried at the centre
# of an opaque body is a nucleus nobody ever sees - Bedrock gives an entity no
# real transparency to look through - so it sits in an open cavity in the
# back, framed by a lip of jelly, where it lights the mob from behind.
uv = atlas.box((13, 11, 4))
bones.append(bone("socket", [0, 15, 8],
                  [cube([-6.5, 10, 6], [13, 11, 4], uv)], parent="blob_2"))
uv = atlas.box((9, 8, 5))
bones.append(bone("core", [0, 15, 9], [cube([-4.5, 11, 7], [9, 8, 5], uv)],
                  parent="socket"))
uv = atlas.box((11, 10, 3))
bones.append(bone("halo", [0, 15, 11], [cube([-5.5, 10.5, 10], [11, 10, 3], uv,
                                             inflate=0.3)], parent="core"))

# Rubble it swallowed, pressing out through the surface rather than floating
# invisibly at the middle - half in, half proud of the skin.
for i, (rx, ry, rz, rs, rot) in enumerate(((-8, 6, -3, 4, 22), (7, 12, 3, 5, -34),
                                           (-4, 19, -7, 4, 48), (8, 7, -4, 3, -12),
                                           (2, 22, 5, 4, 30), (-7, 13, 6, 3, -50))):
    uv = atlas.box((rs, rs, rs))
    bones.append(bone("rubble_%d" % i, [rx, ry, rz],
                      [cube([rx - rs / 2.0, ry, rz - rs / 2.0], [rs, rs, rs], uv)],
                      parent="blob_%d" % min(4, max(0, int(ry / 5))),
                      rotation=[rot * 0.5, rot, rot * 0.3]))

# The split: an upper and a lower lip parted over a dark gullet, with teeth
# that are not teeth so much as swallowed shards it never spat out.
uv = atlas.box((13, 4, 4))
bones.append(bone("lip_upper", [0, 14, -8],
                  [cube([-6.5, 13, -9.5], [13, 4, 4], uv)], parent="blob_2",
                  rotation=[-16, 0, 0]))
uv = atlas.box((13, 4, 4))
bones.append(bone("lip_lower", [0, 11, -8],
                  [cube([-6.5, 8, -9.5], [13, 4, 4], uv)], parent="blob_1",
                  rotation=[20, 0, 0]))
uv = atlas.box((11, 6, 5))
bones.append(bone("gullet", [0, 12, -7],
                  [cube([-5.5, 9, -8], [11, 6, 5], uv)], parent="blob_1"))
for i in range(4):
    t = (i + 0.5) / 4.0
    tx = -5 + t * 10
    uv = atlas.box((1, 3, 1))
    bones.append(bone("shard_u%d" % i, [tx, 13, -9],
                      [cube([tx - 0.5, 10.5, -9.5], [1, 3, 1], uv)],
                      parent="lip_upper", rotation=[10, 0, (i - 1.5) * 8]))
    uv = atlas.box((1, 3, 1))
    bones.append(bone("shard_l%d" % i, [tx, 12, -9],
                      [cube([tx - 0.5, 12, -9.5], [1, 3, 1], uv)],
                      parent="lip_lower", rotation=[-10, 0, (i - 1.5) * 8]))

# Eyes: two lit motes floating in the jelly above the split.
for side in (1, -1):
    uv = atlas.box((3, 3, 3))
    bones.append(bone("eye_%s" % ("l" if side > 0 else "r"), [side * 4, 18, -7],
                      [cube([side * 4 - 1.5, 18, -8], [3, 3, 3], uv)],
                      parent="blob_3"))

# Drips running off the bottom edge, and a couple stretching free.
for i, (dx, dz, dl) in enumerate(((-6, -4, 5), (5, 3, 6), (-2, 6, 4),
                                  (7, -3, 4), (1, -6, 5), (-7, 2, 3))):
    chain, _ = taper_chain(atlas, "drip_%d" % i, "blob_0", [dx, 2, dz], 2,
                           (3, 4, 3), -4.0, shrink=0.7, axis="y")
    bones.extend(chain)

write("RP/models/entity/void_slime.geo.json",
      geometry("geometry.voidbound.void_slime", (256, 256), stand(bones),
               bounds=(2, 2, (0, 0.8, 0))))
print("void_slime: %d bones" % len(bones))
