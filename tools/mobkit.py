#!/usr/bin/env python3
"""Building blocks for detailed Bedrock entity models.

The models in this pack were, until now, hand-typed boxes: a body slab, a head
slab, two flat fins. Five cubes and no shape. Detail at this scale is not a
matter of typing more numbers - it is a matter of having the right primitives,
because the things that make a creature read are all *sequences*: a tail is a
chain of shrinking segments, a wing is a frame of bones with a membrane
stretched between them, a spine is a row of plates that follow a curve.

So this is a small kit of those. Each returns Bedrock bones, ready to drop into
a geometry, and each takes a UV allocator so the texture layout stays packed
and every cube knows where it samples from.
"""

import math


class UVAtlas:
    """Hands out non-overlapping rectangles in a texture, packed in rows.

    Every cube in a Bedrock model needs somewhere to sample from, and a model
    with sixty cubes needs those sixty footprints laid out without collisions.
    Doing that by hand is where UV bugs come from, so it is done here instead.
    """

    def __init__(self, width, height, padding=0):
        self.width = width
        self.height = height
        self.padding = padding
        self._x = 0
        self._y = 0
        self._row_height = 0
        self.regions = []

    def box(self, size):
        """Reserve a box unwrap footprint for a cube of `size` (w, h, d)."""
        w, h, d = (int(math.ceil(v)) for v in size)
        need_w = 2 * (w + d)
        need_h = h + d
        return self._alloc(need_w, need_h, (w, h, d))

    def _alloc(self, need_w, need_h, size):
        if self._x + need_w > self.width:
            self._x = 0
            self._y += self._row_height + self.padding
            self._row_height = 0
        if self._y + need_h > self.height:
            raise ValueError(
                "UV atlas full: needed %dx%d at row %d in a %dx%d sheet"
                % (need_w, need_h, self._y, self.width, self.height))
        uv = [self._x, self._y]
        self.regions.append({"uv": uv, "need": (need_w, need_h), "size": size})
        self._x += need_w + self.padding
        self._row_height = max(self._row_height, need_h)
        return uv


def cube(origin, size, uv, inflate=None, mirror=False, rotation=None, pivot=None):
    entry = {"origin": [round(v, 3) for v in origin],
             "size": [round(v, 3) for v in size],
             "uv": uv}
    if inflate:
        entry["inflate"] = inflate
    if mirror:
        entry["mirror"] = True
    if rotation:
        entry["rotation"] = [round(v, 2) for v in rotation]
        entry["pivot"] = [round(v, 3) for v in (pivot or origin)]
    return entry


def bone(name, pivot, cubes=None, parent=None, rotation=None):
    entry = {"name": name}
    if parent:
        entry["parent"] = parent
    entry["pivot"] = [round(v, 3) for v in pivot]
    if rotation:
        entry["rotation"] = [round(v, 2) for v in rotation]
    if cubes:
        entry["cubes"] = cubes
    return entry


def taper_chain(atlas, prefix, parent, start, count, size, step,
                shrink=0.82, drop=0.0, spread=0.0, axis="z"):
    """A chain of shrinking segments - a tail, a neck, a tentacle, a body.

    Each link is its own bone parented to the last, so an animation can put a
    wave through the whole thing by rotating each link a little. That is the
    only way a long shape ever looks alive rather than rigid.
    """
    bones = []
    width, height, depth = size
    x, y, z = start
    previous = parent
    for i in range(count):
        w = max(1, width)
        h = max(1, height)
        d = max(1, depth)
        uv = atlas.box((w, h, d))
        name = "%s_%d" % (prefix, i)
        pivot = [x, y, z]
        origin = [x - w / 2.0, y - h / 2.0, z if axis == "z" else z - d / 2.0]
        bones.append(bone(name, pivot, [cube(origin, [w, h, d], uv)], parent=previous))
        previous = name
        # Advance along the chain, dropping and spreading as configured.
        if axis == "z":
            z += step
        else:
            x += step
        y += drop
        x += spread
        width *= shrink
        height *= shrink
        depth = depth if axis == "z" else depth * shrink
    return bones, previous


def wing(atlas, name, parent, shoulder, span, chord, ribs=4, sweep=-18.0,
         thickness=1, droop=6.0, mirrored=False):
    """A framed wing: an arm bone, ribs fanning off it, membrane between.

    A flat plate reads as cardboard from any angle. What makes a wing read is
    that it has structure the light can catch - so the leading edge is a solid
    spar, the ribs step back along the span, and the membrane panels between
    them each sit at a slightly different angle.
    """
    side = -1 if mirrored else 1
    bones = []
    sx, sy, sz = shoulder

    spar_uv = atlas.box((span, 2, 3))
    spar_origin = [sx if side > 0 else sx - span, sy - 1, sz - 1.5]
    bones.append(bone(name, [sx, sy, sz],
                      [cube(spar_origin, [span, 2, 3], spar_uv, mirror=mirrored)],
                      parent=parent,
                      rotation=[0, 0, sweep * side]))

    for i in range(ribs):
        t = (i + 1) / float(ribs)
        rib_len = chord * (1.0 - t * 0.45)
        offset = span * t
        rib_uv = atlas.box((2, thickness + 1, rib_len))
        rx = sx + offset * side if side > 0 else sx - offset
        origin = [rx - 1, sy - 1, sz]
        bones.append(bone("%s_rib_%d" % (name, i), [rx, sy, sz],
                          [cube(origin, [2, thickness + 1, rib_len], rib_uv,
                                mirror=mirrored)],
                          parent=name,
                          rotation=[droop * t, 0, 0]))

        panel_len = chord * (1.0 - t * 0.45)
        panel_w = max(1, int(span / ribs))
        panel_uv = atlas.box((panel_w, thickness, panel_len))
        px = rx - panel_w if side > 0 else rx
        bones.append(bone("%s_web_%d" % (name, i), [rx, sy, sz],
                          [cube([px, sy - 0.5, sz], [panel_w, thickness, panel_len],
                                panel_uv, mirror=mirrored)],
                          parent=name,
                          rotation=[droop * t * 0.8, 0, 0]))
    return bones


def spine_row(atlas, prefix, parent, start, count, size, step, taper=0.85,
              lean=0.0):
    """A row of plates along a back. Cheap, and it does more for a silhouette
    than almost anything else - a smooth back reads as a box, a ridged one
    reads as an animal."""
    bones = []
    x, y, z = start
    w, h, d = size
    for i in range(count):
        uv = atlas.box((max(1, w), max(1, h), max(1, d)))
        name = "%s_%d" % (prefix, i)
        bones.append(bone(name, [x, y, z],
                          [cube([x - w / 2.0, y, z - d / 2.0], [w, h, d], uv)],
                          parent=parent,
                          rotation=[lean, 0, 0] if lean else None))
        z += step
        w *= taper
        h *= taper
    return bones


def limb(atlas, name, parent, hip, upper, lower, foot=None, splay=0.0,
         mirrored=False):
    """A jointed leg: thigh, shin, and optionally a foot, each its own bone.

    Three bones rather than one box is the difference between a leg that can
    walk and a post that slides.
    """
    bones = []
    hx, hy, hz = hip
    uw, uh, ud = upper
    lw, lh, ld = lower

    thigh_uv = atlas.box((uw, uh, ud))
    bones.append(bone(name, [hx, hy, hz],
                      [cube([hx - uw / 2.0, hy - uh, hz - ud / 2.0], [uw, uh, ud],
                            thigh_uv, mirror=mirrored)],
                      parent=parent,
                      rotation=[0, 0, splay * (-1 if mirrored else 1)]))

    knee = [hx, hy - uh, hz]
    shin_uv = atlas.box((lw, lh, ld))
    shin = name + "_lower"
    bones.append(bone(shin, knee,
                      [cube([knee[0] - lw / 2.0, knee[1] - lh, knee[2] - ld / 2.0],
                            [lw, lh, ld], shin_uv, mirror=mirrored)],
                      parent=name))

    if foot:
        fw, fh, fd = foot
        ankle = [knee[0], knee[1] - lh, knee[2]]
        foot_uv = atlas.box((fw, fh, fd))
        bones.append(bone(name + "_foot", ankle,
                          [cube([ankle[0] - fw / 2.0, ankle[1] - fh, ankle[2] - fd * 0.7],
                                [fw, fh, fd], foot_uv, mirror=mirrored)],
                          parent=shin))
    return bones


def geometry(identifier, texture_size, bones, bounds=(3, 3, (0, 1, 0))):
    return {
        "description": {
            "identifier": identifier,
            "texture_width": texture_size[0],
            "texture_height": texture_size[1],
            "visible_bounds_width": bounds[0],
            "visible_bounds_height": bounds[1],
            "visible_bounds_offset": list(bounds[2]),
        },
        "bones": bones,
    }


def write(path, *geometries):
    import json
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"format_version": "1.12.0",
                   "minecraft:geometry": list(geometries)}, handle, indent=2)
        handle.write("\n")


def muzzle(atlas, name, parent, anchor, skull, snout, jaw_drop=7.0, teeth=4,
           tooth_size=(1, 2, 1), nostrils=True, brow=True, cavity=True):
    """A head with a mouth that reads as a mouth.

    A face painted onto the flat front of a cube is the single thing that made
    every model here look wrong, and no amount of texture fixes it: what the
    eye is looking for is *geometry*. A snout that comes forward off the skull,
    an upper and a lower jaw with a dark gap between them, teeth that break the
    line of that gap, a brow that overhangs the eyes, and nostrils.

    So this builds all of it, and every mob in the pack gets its head from
    here rather than from a box with eyes drawn on.

    `anchor` is where the head joins its parent. `skull` and `snout` are
    (w, h, d). The snout is deliberately narrower and shallower than the skull
    - a muzzle that matches the braincase reads as a brick.
    """
    ax, ay, az = anchor
    sw, sh, sd = skull
    nw, nh, nd = snout
    bones = []

    uv = atlas.box((sw, sh, sd))
    bones.append(bone(name, [ax, ay, az],
                      [cube([ax - sw / 2.0, ay - sh / 2.0, az - sd], [sw, sh, sd], uv)],
                      parent=parent))

    # The snout sits forward of the skull and slightly high, so the mouth line
    # falls below the middle of the face where a real one does.
    snout_z = az - sd
    snout_y = ay - sh / 2.0 + (sh - nh) * 0.62
    uv = atlas.box((nw, nh, nd))
    bones.append(bone(name + "_snout", [ax, snout_y + nh / 2.0, snout_z],
                      [cube([ax - nw / 2.0, snout_y, snout_z - nd], [nw, nh, nd], uv)],
                      parent=name))

    # A black box behind the teeth. Without it a parted jaw shows sky through
    # the head, which is worse than no mouth at all.
    if cavity:
        # The palate: a thin dark plate on the underside of the snout, so a
        # parted jaw shows the roof of a mouth rather than sky through the
        # head. It belongs to the snout, not the skull - hung off the skull it
        # stays put while the jaw swings and pokes out through the chin.
        cw, ch, cd = nw - 2, 2, nd - 1
        uv = atlas.box((cw, ch, cd))
        bones.append(bone(name + "_maw", [ax, snout_y, snout_z],
                          [cube([ax - cw / 2.0, snout_y - ch, snout_z - cd],
                                [cw, ch, cd], uv)], parent=name + "_snout"))

    # Lower jaw: hinged at the back of the skull, dropped so the mouth is open.
    jw, jh, jd = nw, max(2, int(nh * 0.7)), nd + 1
    uv = atlas.box((jw, jh, jd))
    bones.append(bone(name + "_jaw", [ax, snout_y, az - sd * 0.4],
                      [cube([ax - jw / 2.0, snout_y - jh, snout_z - jd + 1],
                            [jw, jh, jd], uv)],
                      parent=name, rotation=[jaw_drop, 0, 0]))

    tw, th, td = tooth_size
    for i in range(teeth):
        t = (i + 0.5) / teeth
        tx = ax - nw / 2.0 + 1 + t * (nw - 2)
        # Upper teeth point down from the snout, lower teeth up from the jaw.
        uv = atlas.box((tw, th, td))
        bones.append(bone("%s_tooth_u%d" % (name, i), [tx, snout_y, snout_z - nd + 1],
                          [cube([tx - tw / 2.0, snout_y - th, snout_z - nd + 1],
                                [tw, th, td], uv)], parent=name + "_snout"))
        uv = atlas.box((tw, th, td))
        bones.append(bone("%s_tooth_l%d" % (name, i), [tx, snout_y - jh, snout_z - nd + 1],
                          [cube([tx - tw / 2.0, snout_y - jh, snout_z - nd + 1],
                                [tw, th, td], uv)], parent=name + "_jaw"))

    if nostrils:
        for side in (1, -1):
            uv = atlas.box((2, 2, 2))
            nx = ax + side * nw * 0.24
            bones.append(bone("%s_nostril_%s" % (name, "l" if side > 0 else "r"),
                              [nx, snout_y + nh - 1, snout_z - nd],
                              [cube([nx - 1, snout_y + nh - 2.5, snout_z - nd - 0.5],
                                    [2, 2, 2], uv)], parent=name + "_snout"))

    for side in (1, -1):
        ew, eh, ed = 2, 3, 4
        ex = ax + side * (sw / 2.0 - 0.5)
        ey = ay + sh * 0.12
        uv = atlas.box((ew, eh, ed))
        bones.append(bone("%s_eye_%s" % (name, "l" if side > 0 else "r"),
                          [ex, ey, snout_z + 2],
                          [cube([ex - (0 if side > 0 else ew - 1), ey - eh / 2.0,
                                 snout_z + 1], [ew, eh, ed], uv,
                                mirror=side < 0)], parent=name))

    if brow:
        # An overhanging ridge. It is what puts the eyes in shadow, and eyes in
        # shadow are most of what makes a face look like it is looking at you.
        bw, bh, bd = sw + 1, 3, max(3, int(sd * 0.45))
        uv = atlas.box((bw, bh, bd))
        bones.append(bone(name + "_brow", [ax, ay + sh / 2.0 - 2, snout_z],
                          [cube([ax - bw / 2.0, ay + sh / 2.0 - 3.5, snout_z - bd + 1],
                                [bw, bh, bd], uv)], parent=name))

    return bones


def stand(bones, floor=0.0):
    """Lift a finished bone list so its lowest point sits on `floor`.

    Bedrock draws a model with the entity's feet at y=0, so any cube below
    that is buried in the ground - a beast built from the chest down ends up
    knee-deep in the island it is standing on. Legs get built downward from a
    hip height that is chosen for proportion, not for where the floor is, so
    rather than fudging the hip every time, the whole rig gets translated once
    at the end. Pivots and origins are all in the same model space, so a
    uniform shift keeps every joint exactly where it was.
    """
    low = None
    for entry in bones:
        for shape in entry.get("cubes") or []:
            bottom = shape["origin"][1] - (shape.get("inflate") or 0.0)
            low = bottom if low is None else min(low, bottom)
    if low is None:
        return bones
    delta = floor - low
    if abs(delta) < 1e-6:
        return bones
    for entry in bones:
        entry["pivot"][1] += delta
        for shape in entry.get("cubes") or []:
            shape["origin"][1] += delta
            if "pivot" in shape:
                shape["pivot"][1] += delta
    return bones
