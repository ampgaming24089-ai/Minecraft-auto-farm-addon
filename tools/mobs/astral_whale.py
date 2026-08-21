import sys
sys.path.insert(0, "tools")
from mobkit import (UVAtlas, bone, cube, geometry, taper_chain, spine_row,
                    muzzle, write)

# Astral Whale: a sky-leviathan that something once harnessed. The body is the
# easy half; what makes it a *design* rather than a shape is the ironmongery -
# gold bands strapped around the hull, lanterns swinging off them, and a
# banner trailing behind. It reads as a creature people have used.
atlas = UVAtlas(512, 512, padding=1)
bones = []

# --- Hull: seven segments, fattest a third of the way back ----------------
BODY = [(20, 18, 12), (26, 24, 14), (30, 26, 16), (28, 24, 16),
        (24, 20, 14), (18, 15, 12), (12, 10, 10)]
z = -34
prev = None
segs = []
for i, (w, h, d) in enumerate(BODY):
    uv = atlas.box((w, h, d))
    name = "body_%d" % i
    bones.append(bone(name, [0, 26, z],
                      [cube([-w / 2.0, 26 - h / 2.0, z], [w, h, d], uv)], parent=prev))
    segs.append((name, w, h, z, d))
    prev = name
    z += d - 1
core = "body_2"

# --- Head: skull, brow ridge, lower jaw, and a blowhole -------------------
# A whale's head is the same problem as a dragon's - a flat front is a flat
# front whatever it belongs to - so it gets the same treatment: a braincase, a
# rostrum forward of it, a hinged lower jaw with a dark palate, and eyes in
# sockets. No teeth: it filters, so the gap carries baleen instead.
bones.extend(muzzle(atlas, "head", "body_0", [0, 28, -34],
                    skull=(22, 18, 14), snout=(17, 12, 15),
                    jaw_drop=9.0, teeth=0, nostrils=False))

# Baleen plates hanging from the palate down into the gap.
for i in range(6):
    uv = atlas.box((14, 5, 2))
    bones.append(bone("baleen_%d" % i, [0, 25, -60 + i * 3],
                      [cube([-7, 20, -60 + i * 3], [14, 5, 2], uv)],
                      parent="head_snout"))

# The rostrum: two more segments forward of the snout, each narrower and
# shallower, so the head comes to a point instead of ending in a wall.
prev_r = "head_snout"
rx_w, rx_h, rx_d = 14, 9, 12
rz = -63
for i in range(2):
    uv = atlas.box((rx_w, rx_h, rx_d))
    name = "rostrum_%d" % i
    bones.append(bone(name, [0, 26, rz],
                      [cube([-rx_w / 2.0, 26 - rx_h / 2.0 + 1, rz - rx_d],
                            [rx_w, rx_h, rx_d], uv)], parent=prev_r))
    prev_r = name
    rz -= rx_d - 1
    rx_w *= 0.72
    rx_h *= 0.78

# Blowhole on top of the braincase, where a whale actually breathes.
uv = atlas.box((6, 3, 6))
bones.append(bone("blowhole", [0, 37, -40], [cube([-3, 36, -43], [6, 3, 6], uv)],
                  parent="head"))

# --- Gold strapping: three bands around the hull, each with buckles -------
# (segment index, how far along that segment the band sits)
BANDS = [(1, 4), (3, 6), (5, 4)]
for index, (seg_index, along) in enumerate(BANDS):
    parent, seg_w, seg_h, seg_z, seg_d = segs[seg_index]
    band_z = seg_z + along
    band_w = seg_w + 2
    band_h = seg_h + 2
    tag = "strap_%d" % index
    # The band itself: four plates making a ring around the segment.
    for side, (ox, oy, w, h, d) in enumerate((
            (-band_w / 2.0, 26 - band_h / 2.0, band_w, 2, 4),        # under
            (-band_w / 2.0, 26 + band_h / 2.0 - 2, band_w, 2, 4),    # over
            (-band_w / 2.0 - 1, 26 - band_h / 2.0, 2, band_h, 4),    # left
            (band_w / 2.0 - 1, 26 - band_h / 2.0, 2, band_h, 4))):   # right
        uv = atlas.box((w, h, d))
        bones.append(bone("%s_%d" % (tag, side), [0, 26, band_z],
                          [cube([ox, oy, band_z], [w, h, d], uv)], parent=parent))
    # A buckle on top, and a lantern swinging under each band.
    uv = atlas.box((6, 5, 6))
    bones.append(bone(tag + "_buckle", [0, 26 + band_h / 2.0, band_z],
                      [cube([-3, 26 + band_h / 2.0 - 1, band_z - 1], [6, 5, 6], uv)],
                      parent=parent))
    for side in (1, -1):
        lx = side * (band_w / 2.0 + 1)
        hang = 26 - band_h / 2.0
        uv = atlas.box((1, 3, 1))
        chain = "%s_chain_%d" % (tag, 0 if side > 0 else 1)
        bones.append(bone(chain, [lx, hang, band_z + 2],
                          [cube([lx - 0.5, hang - 3, band_z + 1.5], [1, 3, 1], uv)],
                          parent=parent))
        uv = atlas.box((5, 6, 5))
        bones.append(bone("%s_lantern_%d" % (tag, 0 if side > 0 else 1),
                          [lx, hang - 3, band_z + 2],
                          [cube([lx - 2.5, hang - 9, band_z - 0.5], [5, 6, 5], uv)],
                          parent=chain))

# --- Fins: two big pectorals, each three tapering panels -----------------
for side, mirror in ((1, False), (-1, True)):
    tag = "fin_left" if side > 0 else "fin_right"
    parent = "body_2"
    reach = 14
    for i in range(3):
        w, d, t = 12 - i * 3, 20 - i * 5, 3 - i
        uv = atlas.box((w, max(1, t), d))
        name = "%s_%d" % (tag, i)
        ox = side * reach if side > 0 else side * reach - w
        bones.append(bone(name, [side * reach, 24, -6],
                          [cube([ox, 23, -d / 2.0], [w, max(1, t), d], uv, mirror=mirror)],
                          parent=parent, rotation=[0, 0, side * (-8 - i * 7)]))
        parent = name
        reach += w

# --- Tail: a peduncle chain into a broad horizontal fluke ----------------
tail_bones, tip = taper_chain(atlas, "tail", "body_6", [0, 26, 62], 4,
                              (10, 9, 8), 7.0, shrink=0.82)
bones.extend(tail_bones)
for side, mirror in ((1, False), (-1, True)):
    uv = atlas.box((18, 2, 14))
    ox = 0 if side > 0 else -18
    bones.append(bone("fluke_%s" % ("left" if side > 0 else "right"), [0, 26, 90],
                      [cube([ox, 25, 84], [18, 2, 14], uv, mirror=mirror)],
                      parent=tip, rotation=[0, side * 16, side * 6]))

# --- Dorsal ridge, and a banner trailing off the rear strap --------------
bones.extend(spine_row(atlas, "ridge", core, [0, 38, -26], 9, (4, 5, 5), 7.0,
                       taper=0.9))
BANNER_TOP = 26 - (segs[5][2] + 2) / 2.0
for i in range(2):
    uv = atlas.box((9, 8, 1))
    top = BANNER_TOP - i * 8
    bones.append(bone("banner_%d" % i, [0, top, segs[5][3] + 4],
                      [cube([-4.5, top - 8, segs[5][3] + 4], [9, 8, 1], uv)],
                      parent="strap_2_0" if i == 0 else "banner_%d" % (i - 1)))

write("RP/models/entity/astral_whale.geo.json",
      geometry("geometry.voidbound.astral_whale", (512, 512), bones,
               bounds=(8, 5, (0, 2, 0))))
print("astral_whale: %d bones, %d cubes"
      % (len(bones), sum(len(b.get("cubes", [])) for b in bones)))
