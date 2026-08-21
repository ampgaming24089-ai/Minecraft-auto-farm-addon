"""
Generate the End's tree species: blocks, art, drops and recipes.

Every region of the End Everlasting map paints its own ground and grows its own
flora, but until now they all shared one tree - the Ender tree - and most of
them grew none at all. Seven regions with one tree between them is why the map
reads as one place with different filters on it.

So this emits a full wood set per region: a log, its leaves, a sapling and
planks, with the textures, the atlas entries, the drops, the crafting recipes
and the language strings that make each of them a real block. The Verdant
Canopy's Ender wood already existed and is left exactly as it is; the other six
are generated here.

    python3 build.py

The runtime side is `BP/scripts/lib/tree.js`, which is generated from the same
species table so a species can never be shaped one way in the world and another
way when a sapling grows it.
"""

from __future__ import annotations

import json
import os
import sys

HERE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE_DIR, "..", "mobgen"))
sys.path.insert(0, os.path.join(HERE_DIR, ".."))

from PIL import Image  # noqa: E402

from langblock import write_block  # noqa: E402
from paint import Rng, hex_to_rgb, mix, scale, string_seed  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
BP = os.path.join(ROOT, "BP")
RP = os.path.join(ROOT, "RP")

NS = "voidbound"


class Species:
    """
    One wood set.

    `shape` picks the canopy the trunk carries, which is the difference
    between a region having a different palette and a region having a
    different skyline:

      round    a classic broad crown
      weeping  a crown that trails hanging growth off its edge
      cap      a single wide mushroom cap on a bare stalk
      spire    a narrow conifer that tapers as it climbs
      flat     a low wide umbrella
    """

    def __init__(self, key, name, biome, shape, bark, bark_top, leaf, glow,
                 map_bark, map_leaf, height, radius, light, hangs=None,
                 fruit=None):
        self.key = key
        self.name = name
        self.biome = biome
        self.shape = shape
        self.bark = bark
        self.bark_top = bark_top
        self.leaf = leaf
        self.glow = glow
        self.map_bark = map_bark
        self.map_leaf = map_leaf
        self.height = height          # (min, max) trunk height in blocks
        self.radius = radius          # canopy radius in blocks
        self.light = light            # leaf light emission
        self.hangs = hangs            # block trailed off the canopy, or None
        self.fruit = fruit            # rare extra drop from the leaves

    @property
    def log(self):
        return f"{NS}:{self.key}_log"

    @property
    def leaves(self):
        return f"{NS}:{self.key}_leaves"

    @property
    def sapling(self):
        return f"{NS}:{self.key}_sapling"

    @property
    def planks(self):
        return f"{NS}:{self.key}_planks"


# The Verdant Canopy's Ender wood is hand-written and stays that way; it is
# listed here only so the runtime tree table can grow it like any other.
ENDER = Species(
    "ender", "Ender", "verdant", "round",
    bark="#4A3A5E", bark_top="#6E5F86", leaf="#7B3FA8", glow="#C77BFF",
    map_bark="#6E5F86", map_leaf="#7B3FA8",
    height=(6, 10), radius=3, light=3,
    hangs=f"{NS}:ender_vines", fruit=f"{NS}:ender_fruit",
)

SPECIES = [
    Species(
        "sporewood", "Sporewood", "glowspore", "cap",
        bark="#4A3352", bark_top="#6B4E75", leaf="#B8479E", glow="#FF8CE8",
        map_bark="#6B4E75", map_leaf="#B8479E",
        height=(5, 9), radius=4, light=8,
        hangs=f"{NS}:spore_tendril", fruit=f"{NS}:lumen_berry",
    ),
    Species(
        "bonewood", "Bonewood", "bonespire", "spire",
        bark="#B9B2A0", bark_top="#D6D0C0", leaf="#9FD8E8", glow="#DFF6FF",
        map_bark="#D6D0C0", map_leaf="#9FD8E8",
        height=(7, 13), radius=3, light=2,
        hangs=f"{NS}:frost_icicle",
    ),
    Species(
        "shardwood", "Shardwood", "crystalline", "spire",
        bark="#3B2A55", bark_top="#5A4180", leaf="#8E5BE0", glow="#D9A0FF",
        map_bark="#5A4180", map_leaf="#8E5BE0",
        height=(6, 11), radius=3, light=6,
        hangs=f"{NS}:crystal_dripstone", fruit=f"{NS}:void_crystal",
    ),
    Species(
        "cinderwood", "Cinderwood", "ashen", "flat",
        bark="#3A2A24", bark_top="#544034", leaf="#7A3A22", glow="#FF7A2A",
        map_bark="#544034", map_leaf="#7A3A22",
        height=(5, 9), radius=4, light=5,
        hangs=f"{NS}:ash_stalactite",
    ),
    Species(
        "auralwood", "Auralwood", "aurora", "weeping",
        bark="#2E3A52", bark_top="#47597A", leaf="#3FB8D8", glow="#9FF0FF",
        map_bark="#47597A", map_leaf="#3FB8D8",
        height=(6, 11), radius=4, light=7,
        hangs=f"{NS}:aurora_veil", fruit=f"{NS}:lumen_berry",
    ),
    Species(
        "voidwood", "Voidwood", "barrens", "weeping",
        bark="#2A2436", bark_top="#3E3750", leaf="#4B3A6B", glow="#8E5BE0",
        map_bark="#3E3750", map_leaf="#4B3A6B",
        height=(5, 10), radius=3, light=2,
        hangs=f"{NS}:ender_vines",
    ),
]

ALL_SPECIES = [ENDER] + SPECIES


# ---------------------------------------------------------------------------
# Textures
# ---------------------------------------------------------------------------

SIZE = 16


def _blank():
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def bark_texture(species):
    """Vertical grain, with the odd lit fleck so the wood belongs in the End."""
    image = _blank()
    px = image.load()
    base = hex_to_rgb(species.bark)
    glow = hex_to_rgb(species.glow)
    rng = Rng(string_seed(species.key + "bark"))
    for x in range(SIZE):
        streak = scale(base, 0.82 + rng.next() * 0.36)
        for y in range(SIZE):
            tone = streak if rng.chance(0.72) else scale(base, 0.7 + rng.next() * 0.5)
            px[x, y] = (*tone, 255)
    for _ in range(4):
        x, y = int(rng.between(1, SIZE - 2)), int(rng.between(1, SIZE - 3))
        for dy in range(int(rng.between(1, 4))):
            px[x, y + dy] = (*mix(base, glow, 0.75), 254)
    return image


def bark_top_texture(species):
    """Growth rings."""
    image = _blank()
    px = image.load()
    base = hex_to_rgb(species.bark_top)
    dark = hex_to_rgb(species.bark)
    rng = Rng(string_seed(species.key + "top"))
    centre = (SIZE - 1) / 2
    for y in range(SIZE):
        for x in range(SIZE):
            distance = ((x - centre) ** 2 + (y - centre) ** 2) ** 0.5
            ring = int(distance) % 3 == 0
            tone = mix(base, dark, 0.55 if ring else 0.12)
            tone = scale(tone, 0.9 + rng.next() * 0.2)
            px[x, y] = (*tone, 255)
    return image


def leaf_texture(species):
    """
    Clumped foliage with holes through it.

    Leaves render with `alpha_test`, so a fully transparent texel is a gap you
    can see sky through - which is the whole reason a leaf block reads as
    foliage rather than a green cube.
    """
    image = _blank()
    px = image.load()
    base = hex_to_rgb(species.leaf)
    glow = hex_to_rgb(species.glow)
    rng = Rng(string_seed(species.key + "leaf"))
    for y in range(SIZE):
        for x in range(SIZE):
            if rng.chance(0.12):
                continue  # a hole through the canopy
            shade = 0.72 + rng.next() * 0.6
            tone = scale(base, shade)
            if rng.chance(0.07):
                px[x, y] = (*mix(tone, glow, 0.8), 254)
            else:
                px[x, y] = (*tone, 255)
    return image


def sapling_texture(species):
    """A stem with a small crown, on a mostly empty square."""
    image = _blank()
    px = image.load()
    stem = hex_to_rgb(species.bark)
    leaf = hex_to_rgb(species.leaf)
    glow = hex_to_rgb(species.glow)
    rng = Rng(string_seed(species.key + "sapling"))

    for y in range(9, 16):
        px[7, y] = (*scale(stem, 1.0), 255)
        px[8, y] = (*scale(stem, 0.8), 255)

    for y in range(3, 11):
        spread = 4 - abs(y - 6) // 2
        for x in range(8 - spread, 8 + spread):
            if rng.chance(0.22):
                continue
            tone = scale(leaf, 0.8 + rng.next() * 0.5)
            if rng.chance(0.12):
                px[x, y] = (*mix(tone, glow, 0.8), 254)
            else:
                px[x, y] = (*tone, 255)
    return image


def plank_texture(species):
    """Laid boards, four to a block."""
    image = _blank()
    px = image.load()
    base = hex_to_rgb(species.bark_top)
    dark = hex_to_rgb(species.bark)
    rng = Rng(string_seed(species.key + "plank"))
    for y in range(SIZE):
        board = y // 4
        seam = y % 4 == 0
        for x in range(SIZE):
            tone = mix(base, dark, 0.5 if seam else 0.1 + (board % 2) * 0.12)
            tone = scale(tone, 0.9 + rng.next() * 0.2)
            px[x, y] = (*tone, 255)
        if seam:
            continue
    # A short butt joint per board, so the courses do not run the full width.
    for board in range(4):
        x = int(rng.between(3, SIZE - 3))
        for y in range(board * 4 + 1, board * 4 + 4):
            px[x, y] = (*scale(dark, 0.7), 255)
    return image


def mer_for(image, roughness):
    """Metalness / emissive / roughness, with emissive read off the glow mask."""
    mer = Image.new("RGBA", image.size, (0, 0, 0, 255))
    src = image.load()
    dst = mer.load()
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            alpha = src[x, y][3]
            dst[x, y] = (0, 255 if alpha == 254 else 0, roughness, 255)
    return mer


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def log_block(species):
    return {
        "format_version": "1.21.120",
        "minecraft:block": {
            "description": {
                "identifier": species.log,
                "menu_category": {"category": "construction"},
            },
            "components": {
                "minecraft:display_name": f"tile.{species.log}.name",
                "minecraft:geometry": "minecraft:geometry.full_block",
                "minecraft:material_instances": {
                    "*": {
                        "texture": f"{NS}_{species.key}_log",
                        "render_method": "opaque",
                        "ambient_occlusion": 1.0,
                    },
                    "up": {
                        "texture": f"{NS}_{species.key}_log_top",
                        "render_method": "opaque",
                        "ambient_occlusion": 1.0,
                    },
                    "down": {
                        "texture": f"{NS}_{species.key}_log_top",
                        "render_method": "opaque",
                        "ambient_occlusion": 1.0,
                    },
                },
                "minecraft:map_color": species.map_bark,
                "minecraft:destructible_by_mining": {"seconds_to_destroy": 1.4},
                "minecraft:destructible_by_explosion": {"explosion_resistance": 6},
                "minecraft:light_emission": 1,
                "minecraft:flammable": {
                    "catch_chance_modifier": 0,
                    "destroy_chance_modifier": 0,
                },
            },
        },
    }


def leaves_block(species):
    return {
        "format_version": "1.21.120",
        "minecraft:block": {
            "description": {
                "identifier": species.leaves,
                "menu_category": {"category": "nature"},
            },
            "components": {
                "minecraft:display_name": f"tile.{species.leaves}.name",
                "minecraft:geometry": "minecraft:geometry.full_block",
                "minecraft:material_instances": {
                    "*": {
                        "texture": f"{NS}_{species.key}_leaves",
                        "render_method": "alpha_test",
                        "ambient_occlusion": 0.0,
                        "face_dimming": False,
                    }
                },
                "minecraft:map_color": species.map_leaf,
                "minecraft:destructible_by_mining": {"seconds_to_destroy": 0.2},
                "minecraft:destructible_by_explosion": {"explosion_resistance": 0.2},
                "minecraft:light_dampening": 1,
                "minecraft:light_emission": species.light,
                "minecraft:loot": f"loot_tables/blocks/{species.key}_leaves.json",
            },
        },
    }


def sapling_block(species):
    return {
        "format_version": "1.21.120",
        "minecraft:block": {
            "description": {
                "identifier": species.sapling,
                "menu_category": {"category": "nature"},
            },
            "components": {
                "minecraft:display_name": f"tile.{species.sapling}.name",
                "minecraft:geometry": "minecraft:geometry.cross",
                "minecraft:material_instances": {
                    "*": {
                        "texture": f"{NS}_{species.key}_sapling",
                        "render_method": "alpha_test",
                        "ambient_occlusion": 0.0,
                        "face_dimming": False,
                    }
                },
                "minecraft:map_color": species.map_leaf,
                "minecraft:destructible_by_mining": {"seconds_to_destroy": 0.0},
                "minecraft:destructible_by_explosion": {"explosion_resistance": 0},
                "minecraft:light_emission": 2,
                "minecraft:light_dampening": 0,
                "minecraft:collision_box": False,
                "minecraft:selection_box": {
                    "origin": [-6, 0, -6],
                    "size": [12, 14, 12],
                },
                "minecraft:replaceable": {},
                "minecraft:flower_pottable": {},
                "minecraft:random_offset": {
                    "x": {"range": {"min": -0.25, "max": 0.25}, "steps": 4},
                    "z": {"range": {"min": -0.25, "max": 0.25}, "steps": 4},
                },
                "minecraft:placement_filter": {
                    "conditions": [{
                        "allowed_faces": ["up"],
                        "block_filter": [{"name": name} for name in GROUND],
                    }]
                },
            },
        },
    }


def planks_block(species):
    return {
        "format_version": "1.21.120",
        "minecraft:block": {
            "description": {
                "identifier": species.planks,
                "menu_category": {"category": "construction"},
            },
            "components": {
                "minecraft:display_name": f"tile.{species.planks}.name",
                "minecraft:geometry": "minecraft:geometry.full_block",
                "minecraft:material_instances": {
                    "*": {
                        "texture": f"{NS}_{species.key}_planks",
                        "render_method": "opaque",
                        "ambient_occlusion": 1.0,
                    }
                },
                "minecraft:map_color": species.map_bark,
                "minecraft:destructible_by_mining": {"seconds_to_destroy": 1.2},
                "minecraft:destructible_by_explosion": {"explosion_resistance": 6},
                "minecraft:flammable": {
                    "catch_chance_modifier": 0,
                    "destroy_chance_modifier": 0,
                },
            },
        },
    }


# Everything a sapling of any species is allowed to be planted on. Every
# region's painted surface is here, so a sapling can be planted where its own
# species grows wild.
GROUND = [
    "minecraft:end_stone",
    f"{NS}:shattered_end_stone",
    f"{NS}:verdant_end_stone",
    f"{NS}:mossy_end_stone",
    f"{NS}:glowspore_soil",
    f"{NS}:crystalline_end_stone",
    f"{NS}:ashen_end_stone",
    f"{NS}:bonespire_stone",
    f"{NS}:aurora_stone",
]


def leaves_loot(species):
    pools = [{
        "rolls": 1,
        "entries": [
            {"type": "item", "name": species.sapling, "weight": 1},
            {"type": "empty", "weight": 14},
        ],
    }]
    if species.fruit:
        pools.append({
            "rolls": 1,
            "entries": [
                {"type": "item", "name": species.fruit, "weight": 1},
                {"type": "empty", "weight": 16},
            ],
        })
    return {"pools": pools}


def planks_recipe(species):
    return {
        "format_version": "1.20.10",
        "minecraft:recipe_shapeless": {
            "description": {"identifier": f"{NS}:{species.key}_planks"},
            "tags": ["crafting_table"],
            "ingredients": [{"item": species.log}],
            "unlock": [{"item": species.log}],
            "result": {"item": species.planks, "count": 4},
        },
    }


# ---------------------------------------------------------------------------
# The runtime species table
# ---------------------------------------------------------------------------

def tree_module():
    """
    Emit `BP/scripts/lib/tree.js`.

    One table, three callers: the painter grows wild trees from it, the sky
    islands grow theirs from it, and a planted sapling grows the same tree the
    wild ones are. Generated so those three can never disagree.
    """
    entries = []
    for species in ALL_SPECIES:
        entries.append(
            f'  {species.key}: {{\n'
            f'    key: "{species.key}",\n'
            f'    name: "{species.name}",\n'
            f'    biome: "{species.biome}",\n'
            f'    shape: "{species.shape}",\n'
            f'    log: "{species.log}",\n'
            f'    leaves: "{species.leaves}",\n'
            f'    sapling: "{species.sapling}",\n'
            f'    minHeight: {species.height[0]},\n'
            f'    maxHeight: {species.height[1]},\n'
            f'    radius: {species.radius},\n'
            f'    hangs: {json.dumps(species.hangs)},\n'
            f'  }},'
        )
    body = "\n".join(entries)
    return f'''/**
 * The End's tree species, and how to grow one.
 *
 * Generated by tools/treegen/build.py - do not edit by hand.
 *
 * Every region of the map has its own wood, and a region's trees are the
 * fastest way to tell it apart from the one next door: the Bonespire's pale
 * spires and the Glowspore Basin's magenta caps read as different places from
 * a long way further off than a change of ground colour ever does.
 *
 * `growTree` is deliberately synchronous and bounded. It is called from the
 * painter, from the sky-island builder and from a sapling's growth pass, all
 * of which are already inside a `system.runJob`, so it must not yield and it
 * must not run long: one tree is at most a few hundred block writes.
 */

import {{ BlockPermutation }} from "@minecraft/server";

export const SPECIES = {{
{body}
}};

/** The species a region grows, by biome id. */
export const BY_BIOME = Object.fromEntries(
  Object.values(SPECIES).map((species) => [species.biome, species])
);

/** Look a species up from the sapling block a player placed. */
export const BY_SAPLING = Object.fromEntries(
  Object.values(SPECIES).map((species) => [species.sapling, species])
);

/** Blocks a trunk or canopy may grow through. Anything else stops it. */
const PASSABLE = new Set([
  "minecraft:air",
  ...Object.values(SPECIES).map((species) => species.sapling),
  ...Object.values(SPECIES).map((species) => species.leaves),
  "{NS}:ender_bush",
  "{NS}:voidbloom",
  "{NS}:lumen_bulb",
  "{NS}:sporelight_fungus",
  "{NS}:pale_shroom",
  "{NS}:frost_bloom",
]);

const permutations = new Map();
function permutation(id) {{
  if (!permutations.has(id)) {{
    try {{
      permutations.set(id, BlockPermutation.resolve(id));
    }} catch {{
      permutations.set(id, undefined);
    }}
  }}
  return permutations.get(id);
}}

function passable(dimension, x, y, z) {{
  try {{
    const block = dimension.getBlock({{ x, y, z }});
    return block ? PASSABLE.has(block.typeId) : false;
  }} catch {{
    return false;
  }}
}}

function put(dimension, x, y, z, id) {{
  const wanted = permutation(id);
  if (!wanted) return false;
  try {{
    const block = dimension.getBlock({{ x, y, z }});
    if (!block || !PASSABLE.has(block.typeId)) return false;
    block.setPermutation(wanted);
    return true;
  }} catch {{
    return false;
  }}
}}

/**
 * The canopy discs for a species, as (dy, radius) pairs.
 *
 * The shape is the species' whole silhouette, so this is where a Bonewood
 * stops being a recoloured Ender tree.
 */
function canopy(species, height, rng) {{
  const r = species.radius;
  switch (species.shape) {{
    case "cap":
      // One wide mushroom cap, and nothing under it.
      return [
        {{ dy: 0, radius: r + 0.6 }},
        {{ dy: 1, radius: r - 0.4 }},
      ];
    case "spire":
      // A conifer: wide at the bottom, a point at the top.
      return [
        {{ dy: -3, radius: r }},
        {{ dy: -2, radius: r - 0.5 }},
        {{ dy: -1, radius: r - 1.0 }},
        {{ dy: 0, radius: r - 1.4 }},
        {{ dy: 1, radius: 0.8 }},
      ];
    case "flat":
      // A low umbrella, the way a thing that grows in ash grows.
      return [
        {{ dy: -1, radius: r + 0.4 }},
        {{ dy: 0, radius: r }},
      ];
    case "weeping":
      return [
        {{ dy: -1, radius: r }},
        {{ dy: 0, radius: r - 0.2 }},
        {{ dy: 1, radius: r - 1.4 }},
      ];
    default:
      return [
        {{ dy: -1, radius: r - 0.4 }},
        {{ dy: 0, radius: r }},
        {{ dy: 1, radius: r - 1.2 }},
      ];
  }}
}}

/**
 * Grow one tree with its base at `base`.
 *
 * @returns true if a tree was actually placed. False means the spot could not
 * hold one - no headroom, or something in the way - and the caller should
 * leave whatever was there alone rather than deleting it into nothing.
 */
export function growTree(dimension, base, species, rng) {{
  const height = rng.int(species.minHeight, species.maxHeight);

  // Headroom first. A tree that grows into a ceiling looks like a bug.
  for (let dy = 1; dy <= height + 2; dy++) {{
    if (!passable(dimension, base.x, base.y + dy, base.z)) return false;
  }}

  // Trunk, with one lean, so a grove is not a row of posts. A mushroom cap
  // grows dead straight - a leaning stalk reads as damage, not character.
  const straight = species.shape === "cap";
  const leanAt = straight ? height + 1 : rng.int(2, Math.max(2, height - 2));
  const leanX = rng.chance(0.5) ? (rng.chance(0.5) ? 1 : -1) : 0;
  const leanZ = leanX === 0 ? (rng.chance(0.5) ? 1 : -1) : 0;

  let tipX = base.x;
  let tipZ = base.z;
  for (let dy = 0; dy < height; dy++) {{
    if (dy === leanAt) {{
      // Bridge the step, or the trunk breaks into a floating diagonal.
      put(dimension, tipX, base.y + dy, tipZ, species.log);
      tipX += leanX;
      tipZ += leanZ;
    }}
    put(dimension, tipX, base.y + dy, tipZ, species.log);
  }}

  const top = base.y + height;
  for (const disc of canopy(species, height, rng)) {{
    const radius = disc.radius;
    const reach = Math.ceil(radius);
    for (let dx = -reach; dx <= reach; dx++) {{
      for (let dz = -reach; dz <= reach; dz++) {{
        const distance = Math.hypot(dx, dz);
        if (distance > radius) continue;
        // Thin the corners, so the crown is not a cylinder.
        if (distance > radius - 0.9 && rng.chance(0.45)) continue;
        put(dimension, tipX + dx, top + disc.dy, tipZ + dz, species.leaves);
      }}
    }}
  }}

  // A cap sits on its stalk; everything else closes over the trunk.
  if (species.shape === "cap") {{
    put(dimension, tipX, top - 1, tipZ, species.log);
  }}

  // What trails off the crown. This is most of why a canopy reads as alive
  // rather than as a lump of leaves on a stick.
  if (species.hangs) {{
    const reach = Math.ceil(species.radius);
    for (let dx = -reach; dx <= reach; dx++) {{
      for (let dz = -reach; dz <= reach; dz++) {{
        if (Math.hypot(dx, dz) < species.radius - 1.2) continue;
        if (!rng.chance(0.3)) continue;
        const length = rng.int(1, 4);
        for (let down = 1; down <= length; down++) {{
          if (!put(dimension, tipX + dx, top - 1 - down, tipZ + dz, species.hangs)) {{
            break;
          }}
        }}
      }}
    }}
  }}

  return true;
}}
'''


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def write_png(path, image):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, "PNG", optimize=True)


def build():
    atlas_additions = {}
    sounds = {}
    lang = ["## Eternal End wood sets"]

    for species in SPECIES:
        write_json(os.path.join(BP, "blocks", f"{species.key}_log.json"),
                   log_block(species))
        write_json(os.path.join(BP, "blocks", f"{species.key}_leaves.json"),
                   leaves_block(species))
        write_json(os.path.join(BP, "blocks", f"{species.key}_sapling.json"),
                   sapling_block(species))
        write_json(os.path.join(BP, "blocks", f"{species.key}_planks.json"),
                   planks_block(species))
        write_json(os.path.join(BP, "loot_tables", "blocks",
                                f"{species.key}_leaves.json"),
                   leaves_loot(species))
        write_json(os.path.join(BP, "recipes", f"{species.key}_planks.json"),
                   planks_recipe(species))

        art = {
            f"{species.key}_log": (bark_texture(species), 210),
            f"{species.key}_log_top": (bark_top_texture(species), 205),
            f"{species.key}_leaves": (leaf_texture(species), 225),
            f"{species.key}_sapling": (sapling_texture(species), 225),
            f"{species.key}_planks": (plank_texture(species), 200),
        }
        for name, (image, roughness) in art.items():
            short = f"{NS}_{name}"
            path = os.path.join(RP, "textures", "blocks", f"{short}.png")
            write_png(path, image)
            write_png(os.path.join(RP, "textures", "blocks", f"{short}_mer.png"),
                      mer_for(image, roughness))
            write_json(os.path.join(RP, "textures", "blocks",
                                    f"{short}.texture_set.json"), {
                "format_version": "1.16.100",
                "minecraft:texture_set": {
                    "color": short,
                    "metalness_emissive_roughness": f"{short}_mer",
                },
            })
            atlas_additions[short] = {"textures": f"textures/blocks/{short}"}

        sounds[species.log] = {"sound": "wood"}
        sounds[species.planks] = {"sound": "wood"}
        sounds[species.leaves] = {"sound": "grass"}
        sounds[species.sapling] = {"sound": "grass"}

        lang.append(f"tile.{species.log}.name={species.name} Log")
        lang.append(f"tile.{species.leaves}.name={species.name} Leaves")
        lang.append(f"tile.{species.sapling}.name={species.name} Sapling")
        lang.append(f"tile.{species.planks}.name={species.name} Planks")
        print(f"  {species.key:12} {species.shape:8} {species.biome}")

    # Atlas.
    atlas_path = os.path.join(RP, "textures", "terrain_texture.json")
    with open(atlas_path, encoding="utf-8") as handle:
        atlas = json.load(handle)
    atlas["texture_data"].update(atlas_additions)
    write_json(atlas_path, atlas)

    # Block sounds.
    blocks_path = os.path.join(RP, "blocks.json")
    with open(blocks_path, encoding="utf-8") as handle:
        blocks = json.load(handle)
    blocks.update(sounds)
    write_json(blocks_path, blocks)

    write_block(os.path.join(RP, "texts", "en_US.lang"), "treegen", lang)

    # Runtime table.
    module_path = os.path.join(BP, "scripts", "lib", "tree.js")
    with open(module_path, "w", encoding="utf-8") as handle:
        handle.write(tree_module())

    print(f"\n  {len(SPECIES)} new species, "
          f"{len(atlas_additions)} textures, {len(ALL_SPECIES)} in the runtime table")


if __name__ == "__main__":
    print("Building the End's wood sets...")
    build()
