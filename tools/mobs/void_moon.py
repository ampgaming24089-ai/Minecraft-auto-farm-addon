import sys
sys.path.insert(0, "tools")
from mobkit import UVAtlas, bone, cube, geometry, write

# The Void Moon: the planet hanging over the End.
#
# It cannot come from the skybox. That texture is tiled across all six faces of
# a cube, so anything the size of a planet in it appears dozens of times, and
# Bedrock draws no sun or moon in the End at all - moon_phases.png is an
# Overworld texture and never renders here. So the planet is an entity: one
# flat plate, held far from the player by script and turned to face them, which
# is the only way to put a single large object in this sky.
#
# One plate rather than a disc built from rows. The silhouette comes from the
# texture's alpha instead, which gives a true circle and a dithered halo for
# the price of two triangles.
atlas = UVAtlas(128, 128, padding=1)
bones = []

uv = atlas.box((60, 60, 1))
bones.append(bone("disc", [0, 0, 0], [cube([-30, -30, 0], [60, 60, 1], uv)]))

write("RP/models/entity/void_moon.geo.json",
      geometry("geometry.voidbound.void_moon", (128, 128), bones,
               bounds=(4, 4, (0, 0, 0))))
print("void_moon: %d bones" % len(bones))
