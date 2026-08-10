#!/usr/bin/env python3
"""
Pre-ship validator for the Hallowed Depths addon.

Every check in here exists because a real device test caught the bug it
looks for. Run it before every build:

    python3 tools/validate.py

Exits non-zero if anything is wrong, so it can gate ./build_addon.sh.

The Script-API checks need Mojang's bindings metadata. Clone it once with:
    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 \
        https://github.com/Mojang/bedrock-samples /workspace/mojang/bedrock-samples
If it's missing those particular checks are skipped (and say so) rather
than silently passing.
"""
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "BP")
RP = os.path.join(ROOT, "RP")
SAMPLES = "/workspace/mojang/bedrock-samples"
BINDINGS = os.path.join(SAMPLES, "metadata/script_modules/@minecraft/server-bindings_2.8.0.json")

errors = []
warnings = []
skipped = []


def err(msg):
    errors.append(msg)


def rel(p):
    return os.path.relpath(p, ROOT)


def load_lang():
    lang = {}
    path = os.path.join(RP, "texts", "en_US.lang")
    for line in open(path):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            lang[k.strip()] = v.strip()
    return lang


# --- 1. every JSON file parses -------------------------------------------
def check_json():
    files = glob.glob(f"{BP}/**/*.json", recursive=True) + glob.glob(f"{RP}/**/*.json", recursive=True)
    for f in files:
        try:
            json.load(open(f))
        except Exception as e:
            err(f"invalid JSON: {rel(f)}: {e}")
    return len(files)


# --- 2. scripts parse as ES modules and their imports resolve -------------
def check_scripts():
    files = glob.glob(f"{BP}/scripts/**/*.js", recursive=True)
    for f in files:
        p = subprocess.run(["node", "--input-type=module", "--check"],
                           stdin=open(f), capture_output=True, text=True)
        if p.returncode != 0:
            err(f"JS syntax error in {rel(f)}: {p.stderr.strip().splitlines()[:3]}")
        src = open(f).read()
        for m in re.finditer(r'from\s+["\'](\.[^"\']+)["\']', src):
            target = os.path.normpath(os.path.join(os.path.dirname(f), m.group(1)))
            if not os.path.isfile(target):
                err(f"unresolved import in {rel(f)}: {m.group(1)}")
    return len(files)


# --- 3. every world event we subscribe to actually exists -----------------
# Subscribing to a nonexistent event throws at module load and silently
# disables every subsystem registered after it. This is exactly how the
# igniter, sigils, dragon egg and shop all went dead at once.
def check_events():
    if not os.path.isfile(BINDINGS):
        skipped.append("Script API event names (bedrock-samples not cloned)")
        return
    d = json.load(open(BINDINGS))
    valid = {}
    for c in d["classes"]:
        if c["name"] in ("WorldAfterEvents", "WorldBeforeEvents"):
            valid[c["name"]] = {p["name"] for p in c.get("properties", [])}
    kinds = {"afterEvents": "WorldAfterEvents", "beforeEvents": "WorldBeforeEvents"}
    for f in glob.glob(f"{BP}/scripts/**/*.js", recursive=True):
        src = open(f).read()
        for m in re.finditer(r"world\.(afterEvents|beforeEvents)\.(\w+)", src):
            kind, ev = m.group(1), m.group(2)
            if ev not in valid[kinds[kind]]:
                line = src[:m.start()].count("\n") + 1
                err(f"{rel(f)}:{line}: world.{kind}.{ev} does not exist in @minecraft/server 2.8.0")


# --- 4. item schema ------------------------------------------------------
FOOD_FIELDS = {"nutrition", "saturation_modifier", "can_always_eat", "effects",
               "on_use_action", "on_use_range", "cooldown_type", "cooldown_time",
               "using_converts_to"}


def check_items(lang):
    icons = {f[:-4] for f in os.listdir(os.path.join(RP, "textures", "items")) if f.endswith(".png")}
    atlas = json.load(open(os.path.join(RP, "textures", "item_texture.json")))["texture_data"]
    for f in sorted(glob.glob(f"{BP}/items/*.json")):
        d = json.load(open(f))
        item = d["minecraft:item"]
        ident = item["description"]["identifier"]
        comps = item["components"]
        fv = tuple(int(x) for x in d["format_version"].split(".")[:2])

        food = comps.get("minecraft:food")
        if food:
            sat = food.get("saturation_modifier")
            # The string enum ("good"/"normal"/...) is legacy-only. In a
            # 1.20+ format item it fails the WHOLE components block, so the
            # item loses its icon and name too.
            if isinstance(sat, str) and fv >= (1, 20):
                err(f"{ident}: food.saturation_modifier must be a float in format {d['format_version']} (got {sat!r})")
            for k in food:
                if k not in FOOD_FIELDS:
                    err(f"{ident}: unknown minecraft:food field {k!r}")

        icon = comps.get("minecraft:icon")
        name = icon if isinstance(icon, str) else (icon or {}).get("textures", {}).get("default")
        if not name:
            err(f"{ident}: no minecraft:icon")
        else:
            if name not in icons:
                err(f"{ident}: icon {name!r} has no PNG in RP/textures/items")
            if name not in atlas:
                err(f"{ident}: icon {name!r} not registered in item_texture.json")

        dn = comps.get("minecraft:display_name")
        if not dn:
            err(f"{ident}: no minecraft:display_name")
        elif dn["value"] not in lang:
            err(f"{ident}: display_name key {dn['value']!r} missing from en_US.lang")


# --- 5. entity + block naming, and BP<->RP entity pairing -----------------
def check_entities_blocks(lang):
    bp_ents, rp_ents = set(), set()
    for f in sorted(glob.glob(f"{BP}/entities/*.json")):
        desc = json.load(open(f))["minecraft:entity"]["description"]
        ident = desc["identifier"]
        bp_ents.add(ident)
        if f"entity.{ident}.name" not in lang:
            err(f"{ident}: missing entity.{ident}.name in en_US.lang")
        if desc.get("is_spawnable") and f"item.spawn_egg.entity.{ident}.name" not in lang:
            err(f"{ident}: spawnable but missing spawn-egg name in en_US.lang")
    for f in glob.glob(f"{RP}/entity/*.entity.json"):
        rp_ents.add(json.load(open(f))["minecraft:client_entity"]["description"]["identifier"])
    for i in bp_ents - rp_ents:
        err(f"{i}: behavior entity has no matching RP client entity (renders as invisible)")
    for i in rp_ents - bp_ents:
        err(f"{i}: RP client entity has no matching BP entity")

    blocks = {f[:-4] for f in os.listdir(os.path.join(RP, "textures", "blocks")) if f.endswith(".png")}
    for f in sorted(glob.glob(f"{BP}/blocks/*.json")):
        b = json.load(open(f))["minecraft:block"]
        ident = b["description"]["identifier"]
        if f"tile.{ident}.name" not in lang:
            err(f"{ident}: missing tile.{ident}.name in en_US.lang")
        for inst in b["components"].get("minecraft:material_instances", {}).values():
            tex = inst.get("texture")
            if tex and tex not in blocks:
                err(f"{ident}: texture {tex!r} missing from RP/textures/blocks")


# --- 6. RP entity references resolve --------------------------------------
def check_rp_refs():
    rc = set()
    for f in glob.glob(f"{RP}/render_controllers/*.json"):
        rc |= set(json.load(open(f)).get("render_controllers", {}).keys())
    anims = set()
    for f in glob.glob(f"{RP}/animations/*.json"):
        anims |= set(json.load(open(f)).get("animations", {}).keys())
    geos = set()
    for f in glob.glob(f"{RP}/models/entity/*.geo.json"):
        for g in json.load(open(f))["minecraft:geometry"]:
            geos.add(g["description"]["identifier"])

    for f in sorted(glob.glob(f"{RP}/entity/*.entity.json")):
        desc = json.load(open(f))["minecraft:client_entity"]["description"]
        for c in desc.get("render_controllers", []):
            n = c if isinstance(c, str) else list(c.keys())[0]
            if n not in rc:
                err(f"{rel(f)}: render controller {n!r} not defined")
        for g in desc.get("geometry", {}).values():
            if g not in geos:
                err(f"{rel(f)}: geometry {g!r} not defined")
        for t in desc.get("textures", {}).values():
            if not os.path.isfile(os.path.join(RP, t + ".png")):
                err(f"{rel(f)}: texture {t!r} missing")
        declared = desc.get("animations") or {}
        for key, val in declared.items():
            if val.startswith("animation.") and val not in anims:
                err(f"{rel(f)}: animation {val!r} not defined")
        for entry in (desc.get("scripts", {}).get("animate") or []):
            k = entry if isinstance(entry, str) else list(entry.keys())[0]
            if k not in declared:
                err(f"{rel(f)}: animate entry {k!r} has no matching animations key")


# --- 7. scripted sounds / particles exist ---------------------------------
def check_sounds_particles():
    sounds = set(json.load(open(os.path.join(RP, "sounds", "sound_definitions.json")))["sound_definitions"])
    particles = set()
    for f in glob.glob(f"{RP}/particles/*.json"):
        particles.add(json.load(open(f))["particle_effect"]["description"]["identifier"])
    for f in glob.glob(f"{BP}/scripts/**/*.js", recursive=True):
        src = open(f).read()
        for m in re.finditer(r'playSound\(\s*["\']([\w.]+)["\']', src):
            s = m.group(1)
            if s.startswith("hollowveil.") and s not in sounds:
                err(f"{rel(f)}: sound {s!r} not in sound_definitions.json")
        for m in re.finditer(r'spawnParticle\(\s*["\']([\w:.]+)["\']', src):
            p = m.group(1)
            if p.startswith("hollowveil:") and p not in particles:
                err(f"{rel(f)}: particle {p!r} not defined in RP/particles")


# --- 8. recipes/loot reference real items ---------------------------------
def check_references():
    known = set()
    for f in glob.glob(f"{BP}/items/*.json"):
        known.add(json.load(open(f))["minecraft:item"]["description"]["identifier"])
    for f in glob.glob(f"{BP}/blocks/*.json"):
        known.add(json.load(open(f))["minecraft:block"]["description"]["identifier"])
    # Only fields that name a real item/block count. A recipe's own
    # description.identifier is just the recipe's name and never resolves to
    # an item, so that subtree is skipped.
    REF_FIELDS = {"item", "name", "input", "output", "result"}

    def walk(node, out):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "description":
                    continue
                if k in REF_FIELDS:
                    for s in ([v] if isinstance(v, str) else
                              [x for x in v if isinstance(x, str)] if isinstance(v, list) else []):
                        if s.startswith("hollowveil:"):
                            out.add(s)
                walk(v, out)
        elif isinstance(node, list):
            for i in node:
                walk(i, out)

    for pattern in (f"{BP}/recipes/*.json", f"{BP}/loot_tables/**/*.json"):
        for f in glob.glob(pattern, recursive=True):
            refs = set()
            walk(json.load(open(f)), refs)
            for ident in sorted(refs):
                if ident not in known:
                    err(f"{rel(f)}: references undefined {ident}")


def main():
    lang = load_lang()
    n_json = check_json()
    n_js = check_scripts()
    check_events()
    check_items(lang)
    check_entities_blocks(lang)
    check_rp_refs()
    check_sounds_particles()
    check_references()

    print(f"checked {n_json} JSON files, {n_js} scripts")
    for s in skipped:
        print(f"  SKIPPED: {s}")
    for w in warnings:
        print(f"  WARN: {w}")
    if errors:
        print(f"\n{len(errors)} PROBLEM(S):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
