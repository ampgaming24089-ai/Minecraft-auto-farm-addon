#!/usr/bin/env python3
"""
Procedural asset generator for the Hollow Veil addon.
Regenerates every PNG in BP/RP from code so geometry and textures always
agree, and the whole art pass is reproducible. Run with: python3 tools/gen_assets.py

NOTE ON ART STYLE: these are stylised, low-poly / flat-shaded placeholder
textures generated algorithmically (silhouette + palette + noise), not
hand-painted art. They are fully functional in-game (correct UVs, correct
sizes, no missing-texture pink/black checkerboards) but a professional pack
would replace them with bespoke Blockbench models / hand-painted textures.
"""
import math
import random
import os

from PIL import Image, ImageDraw, ImageFilter

import boxuv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "BP")
RP = os.path.join(ROOT, "RP")


def path(*parts):
    p = os.path.join(*parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def save(img, *parts):
    p = path(*parts)
    img.save(p)
    return p


# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
PAL = {
    "wraith":        {"side": (150, 210, 190, 255), "top": (190, 235, 220, 255), "front": (120, 185, 165, 255)},
    "wraith_glow":   (210, 255, 235, 255),
    "banshee":       {"side": (200, 180, 220, 255), "top": (225, 205, 240, 255), "front": (170, 150, 195, 255)},
    "banshee_glow":  (255, 240, 255, 255),
    "poltergeist":   {"side": (140, 140, 150, 255), "top": (170, 170, 180, 255), "front": (110, 110, 120, 255)},
    "hellhound":     {"side": (40, 20, 20, 255), "top": (60, 30, 30, 255), "front": (25, 10, 10, 255)},
    "hellhound_fire": (255, 120, 30, 255),
    "imp":           {"side": (150, 40, 40, 255), "top": (175, 60, 60, 255), "front": (110, 25, 25, 255)},
    "shade":         {"side": (60, 60, 90, 255), "top": (90, 90, 130, 255), "front": (40, 40, 65, 255)},
    "knight":        {"side": (70, 75, 80, 255), "top": (95, 100, 105, 255), "front": (50, 55, 60, 255)},
    "knight_trim":   (110, 30, 30, 255),
    "soulwisp":      {"side": (255, 240, 190, 255), "top": (255, 250, 220, 255), "front": (240, 210, 150, 255)},
    "occultist":     {"side": (75, 45, 95, 255), "top": (100, 65, 120, 255), "front": (55, 30, 70, 255)},
    "occultist_trim": (210, 175, 90, 255),
    # bosses
    "hollow_king":   {"side": (225, 225, 235, 255), "top": (245, 245, 255, 255), "front": (190, 190, 205, 255)},
    "hollow_king_cloak": {"side": (40, 15, 55, 255), "top": (55, 25, 70, 255), "front": (25, 8, 35, 255)},
    "hollow_king_gold": (215, 185, 90, 255),
    "weeping_widow": {"side": (210, 195, 225, 255), "top": (230, 220, 240, 255), "front": (175, 160, 195, 255)},
    "weeping_widow_dress": {"side": (45, 25, 60, 255), "top": (60, 35, 75, 255), "front": (30, 15, 42, 255)},
    "malacoda":      {"side": (120, 30, 20, 255), "top": (150, 45, 30, 255), "front": (90, 20, 12, 255)},
    "malacoda_wing": {"side": (35, 15, 15, 255), "top": (45, 20, 20, 255), "front": (20, 8, 8, 255)},
    "malacoda_horn": (30, 25, 25, 255),
}


def noise_fill(size, base, variance=14, seed=0):
    w, h = size
    img = Image.new("RGBA", (w, h), base)
    px = img.load()
    rnd = random.Random(seed)
    for x in range(w):
        for y in range(h):
            j = rnd.randint(-variance, variance)
            r, g, b, a = base
            px[x, y] = (
                max(0, min(255, r + j)),
                max(0, min(255, g + j)),
                max(0, min(255, b + j)),
                a,
            )
    return img


def vignette_edge(img, color=(0, 0, 0, 255), width=1):
    d = ImageDraw.Draw(img)
    w, h = img.size
    d.rectangle([0, 0, w - 1, h - 1], outline=color, width=width)
    return img


# ---------------------------------------------------------------------------
# Pack icons
# ---------------------------------------------------------------------------
def gen_pack_icons():
    for pack, ring, core in [
        (os.path.join(BP, "pack_icon.png"), (35, 10, 45, 255), (150, 60, 210, 255)),
        (os.path.join(RP, "pack_icon.png"), (20, 45, 40, 255), (90, 220, 180, 255)),
    ]:
        img = Image.new("RGBA", (128, 128), (10, 5, 15, 255))
        d = ImageDraw.Draw(img)
        cx, cy = 64, 64
        for r in range(60, 0, -1):
            t = r / 60
            col = tuple(int(ring[i] * t + core[i] * (1 - t)) for i in range(3)) + (255,)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        # torn veil / rip through the middle
        rnd = random.Random(7)
        pts = [(20 + rnd.randint(-6, 6), y) for y in range(10, 118, 10)]
        pts2 = [(x + 18 + rnd.randint(-4, 4), y) for x, y in pts]
        d.line(pts, fill=(5, 2, 8, 255), width=6, joint="curve")
        # a pair of glowing "eyes" for a ghostly face motif
        d.ellipse([46, 54, 58, 66], fill=(230, 255, 240, 255))
        d.ellipse([70, 54, 82, 66], fill=(230, 255, 240, 255))
        d.ellipse([49, 57, 55, 63], fill=(20, 60, 45, 255))
        d.ellipse([73, 57, 79, 63], fill=(20, 60, 45, 255))
        img = img.filter(ImageFilter.SMOOTH)
        img.save(pack)
        print("wrote", pack)


# ---------------------------------------------------------------------------
# Item icons — 32x32 procedural silhouettes on transparent backgrounds
# ---------------------------------------------------------------------------
IS = 32  # icon size


def icon_canvas():
    return Image.new("RGBA", (IS, IS), (0, 0, 0, 0))


def shade(color, amt):
    return tuple(max(0, min(255, c + amt)) if i < 3 else c for i, c in enumerate(color))


def draw_gem(draw, color, cx=16, cy=17, r=9):
    pts = [(cx, cy - r), (cx + r * 0.8, cy - r * 0.2), (cx + r * 0.55, cy + r), (cx - r * 0.55, cy + r), (cx - r * 0.8, cy - r * 0.2)]
    draw.polygon(pts, fill=color, outline=shade(color, -70))
    draw.polygon([(cx, cy - r), (cx + r * 0.8, cy - r * 0.2), (cx, cy - r * 0.1)], fill=shade(color, 45))


def draw_shard(draw, color):
    pts = [(16, 4), (22, 14), (18, 28), (14, 20), (9, 15)]
    draw.polygon(pts, fill=color, outline=shade(color, -70))
    draw.line([(16, 4), (16, 22)], fill=shade(color, 60), width=1)


def draw_dust_pile(draw, color):
    rnd = random.Random(hash(color) % 1000)
    for _ in range(70):
        x = 16 + rnd.randint(-11, 11)
        y = 22 + rnd.randint(-6, 4)
        if (x - 16) ** 2 / 121 + (y - 20) ** 2 / 36 <= 1:
            draw.point((x, y), fill=shade(color, rnd.randint(-30, 30)))


def draw_nugget(draw, color):
    draw.ellipse([9, 12, 23, 23], fill=color, outline=shade(color, -70))
    draw.ellipse([11, 13, 17, 18], fill=shade(color, 50))


def draw_horn(draw, color):
    draw.polygon([(13, 26), (19, 26), (21, 14), (16, 5), (11, 14)], fill=color, outline=shade(color, -70))
    for i in range(3):
        y = 22 - i * 6
        draw.line([(12, y), (20, y - 2)], fill=shade(color, -40))


def draw_sword(draw, blade, hilt, size="normal"):
    draw.polygon([(16, 3), (19, 6), (19, 20), (13, 20), (13, 6)], fill=blade, outline=shade(blade, -70))
    draw.line([(16, 5), (16, 19)], fill=shade(blade, 70), width=1)
    draw.rectangle([11, 20, 21, 23], fill=hilt, outline=shade(hilt, -70))
    draw.rectangle([14, 23, 18, 29], fill=shade(hilt, -20), outline=shade(hilt, -70))


def draw_pickaxe(draw, head, handle):
    draw.line([(9, 9), (23, 23)], fill=handle, width=3)
    draw.arc([4, 2, 24, 18], start=200, end=340, fill=head, width=5)
    draw.line([(6, 8), (10, 4)], fill=shade(head, -60), width=3)
    draw.line([(22, 8), (18, 4)], fill=shade(head, -60), width=3)


def draw_axe(draw, head, handle):
    draw.line([(11, 6), (23, 26)], fill=handle, width=3)
    draw.polygon([(6, 3), (18, 3), (18, 15), (11, 18), (6, 13)], fill=head, outline=shade(head, -70))


def draw_helmet(draw, color):
    draw.pieslice([7, 5, 25, 23], 180, 360, fill=color, outline=shade(color, -70))
    draw.rectangle([7, 14, 25, 18], fill=color, outline=shade(color, -70))
    draw.rectangle([11, 14, 14, 18], fill=(10, 10, 12, 255))
    draw.rectangle([18, 14, 21, 18], fill=(10, 10, 12, 255))


def draw_chestplate(draw, color):
    draw.polygon([(9, 6), (23, 6), (25, 12), (23, 27), (9, 27), (7, 12)], fill=color, outline=shade(color, -70))
    draw.rectangle([14, 6, 18, 27], fill=shade(color, -25))
    draw.polygon([(9, 6), (13, 6), (11, 14), (7, 12)], fill=shade(color, 30))


def draw_leggings(draw, color):
    draw.polygon([(9, 5), (23, 5), (23, 16), (18, 16), (18, 27), (14, 27), (14, 16), (9, 16)], fill=color, outline=shade(color, -70))


def draw_boots(draw, color):
    draw.polygon([(9, 5), (15, 5), (15, 18), (20, 18), (20, 24), (9, 24)], fill=color, outline=shade(color, -70))
    draw.polygon([(17, 5), (23, 5), (23, 24), (22, 24), (22, 18), (17, 18)], fill=color, outline=shade(color, -70))


def draw_lantern(draw):
    draw.rectangle([13, 3, 19, 6], fill=(60, 60, 60, 255))
    draw.rectangle([11, 8, 21, 22], fill=(230, 210, 130, 230), outline=(50, 40, 20, 255))
    draw.rectangle([9, 6, 23, 9], fill=(45, 40, 35, 255))
    draw.rectangle([9, 21, 23, 24], fill=(45, 40, 35, 255))
    draw.ellipse([14, 11, 18, 19], fill=(255, 250, 200, 255))


def draw_compass(draw, accent):
    draw.ellipse([6, 6, 26, 26], fill=(180, 150, 90, 255), outline=(70, 50, 20, 255))
    draw.ellipse([10, 10, 22, 22], fill=(230, 225, 210, 255))
    draw.polygon([(16, 12), (18, 16), (16, 20), (14, 16)], fill=accent)


def draw_book(draw, cover):
    draw.rectangle([7, 6, 25, 26], fill=cover, outline=shade(cover, -70))
    draw.rectangle([9, 8, 23, 24], fill=(235, 220, 180, 255))
    for y in range(10, 23, 3):
        draw.line([(11, y), (21, y)], fill=(150, 130, 90, 255))
    draw.ellipse([14, 13, 18, 17], outline=(255, 215, 90, 255), width=1)


def draw_rune_paper(draw, accent):
    draw.polygon([(7, 5), (25, 5), (23, 27), (9, 27)], fill=(210, 195, 160, 255), outline=(90, 75, 50, 255))
    rnd = random.Random(hash(accent))
    for _ in range(5):
        y = rnd.randint(9, 22)
        x0, x1 = 11, 21
        draw.line([(x0, y), (x1, y)], fill=accent, width=1)
    draw.ellipse([13, 13, 19, 19], outline=accent, width=2)


def draw_igniter(draw):
    draw.line([(8, 24), (22, 8)], fill=(90, 90, 95, 255), width=4)
    draw.polygon([(19, 5), (26, 5), (26, 12), (22, 15), (18, 11)], fill=(210, 175, 90, 255), outline=(90, 70, 30, 255))


def draw_charm(draw, accent):
    draw.ellipse([10, 4, 22, 10], outline=(120, 110, 90, 255), width=2)
    draw.polygon([(9, 12), (23, 12), (16, 28)], fill=(70, 70, 80, 255), outline=shade(accent, -60))
    draw.ellipse([12, 15, 20, 23], fill=accent, outline=shade(accent, -70))


ITEM_ICONS = {
    "soul_shard": lambda d: draw_shard(d, (140, 220, 210, 255)),
    "ember_dust": lambda d: draw_dust_pile(d, (230, 120, 40, 255)),
    "spectral_dust": lambda d: draw_dust_pile(d, (200, 180, 230, 255)),
    "demon_horn": lambda d: draw_horn(d, (60, 25, 25, 255)),
    "banshee_vocal_cord": lambda d: draw_shard(d, (215, 190, 225, 255)),
    "wraithsteel_scrap": lambda d: draw_nugget(d, (110, 120, 130, 255)),
    "wraithsteel_ingot": lambda d: draw_nugget(d, (190, 200, 210, 255)),
    "ember_core": lambda d: draw_gem(d, (255, 130, 40, 255)),
    "ghost_ward_charm": lambda d: draw_charm(d, (150, 230, 210, 255)),
    "spirit_lantern": lambda d: draw_lantern(d),
    "soul_compass": lambda d: draw_compass(d, (150, 230, 210, 255)),
    "journal": lambda d: draw_book(d, (90, 40, 100, 255)),
    "wraithfire_igniter": lambda d: draw_igniter(d),
    "wraithsteel_sword": lambda d: draw_sword(d, (200, 205, 215, 255), (120, 90, 60, 255)),
    "wraithsteel_pickaxe": lambda d: draw_pickaxe(d, (200, 205, 215, 255), (120, 90, 60, 255)),
    "wraithsteel_axe": lambda d: draw_axe(d, (200, 205, 215, 255), (120, 90, 60, 255)),
    "hollow_kings_reaper": lambda d: draw_sword(d, (225, 225, 240, 255), (100, 60, 130, 255)),
    "wailing_edge": lambda d: draw_sword(d, (215, 195, 230, 255), (70, 50, 90, 255)),
    "malacodas_fang": lambda d: draw_sword(d, (230, 100, 60, 255), (60, 20, 15, 255)),
    "sigil_hollow_king": lambda d: draw_rune_paper(d, (140, 100, 210, 255)),
    "sigil_weeping_widow": lambda d: draw_rune_paper(d, (200, 140, 220, 255)),
    "sigil_malacoda": lambda d: draw_rune_paper(d, (230, 90, 40, 255)),
}

for setname, hcol, ccol, lcol, bcol in [
    ("spectral_regalia", (225, 225, 235, 255), (200, 200, 220, 255), (190, 190, 215, 255), (180, 180, 205, 255)),
    ("mourners_shroud", (210, 195, 225, 255), (185, 165, 205, 255), (170, 150, 195, 255), (160, 140, 185, 255)),
    ("ashen_demonplate", (120, 40, 30, 255), (100, 30, 22, 255), (90, 25, 18, 255), (80, 20, 15, 255)),
]:
    ITEM_ICONS[f"{setname}_helmet"] = (lambda c: (lambda d: draw_helmet(d, c)))(hcol)
    ITEM_ICONS[f"{setname}_chestplate"] = (lambda c: (lambda d: draw_chestplate(d, c)))(ccol)
    ITEM_ICONS[f"{setname}_leggings"] = (lambda c: (lambda d: draw_leggings(d, c)))(lcol)
    ITEM_ICONS[f"{setname}_boots"] = (lambda c: (lambda d: draw_boots(d, c)))(bcol)


def gen_item_icons():
    for name, fn in ITEM_ICONS.items():
        img = icon_canvas()
        d = ImageDraw.Draw(img)
        fn(d)
        save(img, RP, "textures", "items", f"{name}.png")
    print(f"wrote {len(ITEM_ICONS)} item icons")


# ---------------------------------------------------------------------------
# Block textures — 16x16 tileable-ish noise textures
# ---------------------------------------------------------------------------
def gen_block_textures():
    blocks = {
        "soulforged_obsidian": (28, 12, 42, 255),
        "ashwood_planks": (74, 55, 50, 255),
        "ashwood_log_side": (58, 42, 38, 255),
        "ashwood_log_top": (90, 68, 58, 255),
        "bonestone": (201, 195, 173, 255),
        "wraithsteel_ore": (79, 90, 99, 255),
        "ritual_altar_side": (95, 40, 90, 255),
        "ritual_altar_top": (130, 60, 120, 255),
        "soul_lantern": (244, 230, 184, 255),
        "veil_portal": (90, 40, 130, 200),
    }
    for name, color in blocks.items():
        img = noise_fill((16, 16), color, variance=16, seed=hash(name) % 999)
        d = ImageDraw.Draw(img)
        if name == "wraithsteel_ore":
            rnd = random.Random(3)
            for _ in range(10):
                x, y = rnd.randint(1, 14), rnd.randint(1, 14)
                d.ellipse([x, y, x + 2, y + 2], fill=(200, 210, 220, 255))
        if name == "soul_lantern":
            d.rectangle([3, 3, 12, 12], fill=(255, 250, 220, 255))
            d.rectangle([0, 0, 15, 15], outline=(120, 100, 60, 255))
        if name == "veil_portal":
            rnd = random.Random(9)
            for _ in range(40):
                x, y = rnd.randint(0, 15), rnd.randint(0, 15)
                d.point((x, y), fill=(200, 160, 255, 220))
        if name.startswith("ritual_altar") or name == "soulforged_obsidian":
            for i in range(0, 16, 4):
                d.line([(i, 0), (i, 15)], fill=shade(color, -20))
        save(img, RP, "textures", "blocks", f"{name}.png")
    print(f"wrote {len(blocks)} block textures")


# ---------------------------------------------------------------------------
# Particle textures — small glow sprites
# ---------------------------------------------------------------------------
def gen_particle_textures():
    particles = {
        "soul_wisp_particle": (220, 250, 220, 255),
        "banshee_scream_particle": (230, 210, 240, 255),
        "ember_particle": (255, 140, 40, 255),
        "hollow_king_pulse_particle": (200, 200, 230, 255),
        "shade_teleport_particle": (90, 90, 140, 255),
        "portal_particle": (170, 90, 220, 255),
    }
    for name, color in particles.items():
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for r in range(4, 0, -1):
            t = r / 4
            col = tuple(int(color[i] * (1 - t) + 255 * t) if i < 3 else int(255 * (r / 4)) for i in range(4))
            d.ellipse([4 - r, 4 - r, 4 + r, 4 + r], fill=col)
        save(img, RP, "textures", "particle", f"{name}.png")
    print(f"wrote {len(particles)} particle textures")


# ---------------------------------------------------------------------------
# UI icons (journal/shop button glyphs used in forms via raw text, so only
# a couple of simple standalone UI textures are needed: item icon on the
# inventory tab and a small emblem for the pack's loading screen use)
# ---------------------------------------------------------------------------
def gen_ui_textures():
    img = icon_canvas()
    d = ImageDraw.Draw(img)
    draw_book(d, (90, 40, 100, 255))
    save(img, RP, "textures", "ui", "hollowveil_journal_button.png")


# ---------------------------------------------------------------------------
# Texture atlases (item_texture.json / terrain_texture.json) — generated by
# scanning what's actually on disk so they can never drift out of sync.
# ---------------------------------------------------------------------------
def gen_texture_atlases():
    import json as _json

    item_dir = os.path.join(RP, "textures", "items")
    items = sorted(f[:-4] for f in os.listdir(item_dir) if f.endswith(".png"))
    item_atlas = {
        "resource_pack_name": "hollowveil_rp",
        "texture_name": "atlas.items",
        "texture_data": {name: {"textures": f"textures/items/{name}"} for name in items},
    }
    with open(os.path.join(RP, "textures", "item_texture.json"), "w") as f:
        _json.dump(item_atlas, f, indent=2)

    block_dir = os.path.join(RP, "textures", "blocks")
    blocks = sorted(f[:-4] for f in os.listdir(block_dir) if f.endswith(".png"))
    terrain_atlas = {
        "resource_pack_name": "hollowveil_rp",
        "texture_name": "atlas.terrain",
        "padding": 8,
        "num_mip_levels": 4,
        "texture_data": {name: {"textures": f"textures/blocks/{name}"} for name in blocks},
    }
    with open(os.path.join(RP, "textures", "terrain_texture.json"), "w") as f:
        _json.dump(terrain_atlas, f, indent=2)

    print(f"wrote item_texture.json ({len(items)} entries) and terrain_texture.json ({len(blocks)} entries)")


# ---------------------------------------------------------------------------
# Particle effect definitions (RP/particles) matching the sprites above
# ---------------------------------------------------------------------------
def gen_particle_definitions():
    import json as _json

    specs = {
        "soul_wisp_particle": {"speed": 0.8, "life": 0.8, "size": 0.12, "count": 8},
        "banshee_scream_particle": {"speed": 1.6, "life": 0.5, "size": 0.2, "count": 14},
        "ember_particle": {"speed": 1.0, "life": 0.6, "size": 0.15, "count": 10},
        "hollow_king_pulse_particle": {"speed": 1.8, "life": 0.7, "size": 0.25, "count": 20},
        "shade_teleport_particle": {"speed": 0.6, "life": 0.5, "size": 0.18, "count": 12},
        "portal_particle": {"speed": 0.5, "life": 1.0, "size": 0.15, "count": 6},
    }
    for name, s in specs.items():
        data = {
            "format_version": "1.10.0",
            "particle_effect": {
                "description": {
                    "identifier": f"hollowveil:{name}",
                    "basic_render_parameters": {
                        "material": "particles_alpha",
                        "texture": f"textures/particle/{name}",
                    },
                },
                "components": {
                    "minecraft:emitter_rate_instant": {"num_particles": s["count"]},
                    "minecraft:emitter_lifetime_once": {"active_time": 0.2},
                    "minecraft:emitter_shape_point": {"offset": [0, 0.5, 0], "direction": "outwards"},
                    "minecraft:particle_lifetime_expression": {"max_lifetime": s["life"]},
                    "minecraft:particle_initial_speed": s["speed"],
                    "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.1},
                    "minecraft:particle_appearance_billboard": {
                        "size": [s["size"], s["size"]],
                        "facing_camera_mode": "lookat_xyz",
                        "uv": {"texture_width": 8, "texture_height": 8, "uv": [0, 0], "uv_size": [8, 8]},
                    },
                },
            },
        }
        p = os.path.join(RP, "particles", f"{name}.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            _json.dump(data, f, indent=2)
    print(f"wrote {len(specs)} particle effect definitions")


if __name__ == "__main__":
    gen_pack_icons()
    gen_item_icons()
    gen_block_textures()
    gen_particle_textures()
    gen_particle_definitions()
    gen_ui_textures()
    gen_texture_atlases()
    print("Hollow Veil asset generator ready.")
