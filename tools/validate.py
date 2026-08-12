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
SAMPLES = os.environ.get("BEDROCK_SAMPLES", "/workspace/mojang/bedrock-samples")
SCRIPT_MODULES = os.path.join(SAMPLES, "metadata/script_modules/@minecraft")
VANILLA_DATA = os.path.join(SAMPLES, "metadata/vanilladata_modules")


def script_module_version(name):
    """The version of a @minecraft/* module this pack's BP manifest asks for.

    Read from the manifest rather than hardcoded, so bumping the dependency
    automatically re-points every API check at the matching bindings instead
    of quietly validating against a stale version.
    """
    manifest = json.load(open(os.path.join(BP, "manifest.json")))
    for dep in manifest.get("dependencies", []):
        if dep.get("module_name") == name:
            return dep.get("version")
    return None


SERVER_VERSION = script_module_version("@minecraft/server") or "2.8.0"
BINDINGS = os.path.join(SCRIPT_MODULES, f"server-bindings_{SERVER_VERSION}.json")

errors = []
warnings = []
skipped = []


def err(msg):
    errors.append(msg)


def rel(p):
    return os.path.relpath(p, ROOT)


def js_source(path):
    """File contents with comments blanked out, line numbers preserved.

    The checks below scan source with regexes, and a comment that *describes*
    a bug reads exactly like the bug. Blanking comment bodies (rather than
    deleting them) keeps every offset intact so reported line numbers still
    point at the real line.
    """
    text = open(path).read()
    out = list(text)
    i, n = 0, len(text)
    in_str = quote = None
    while i < n:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                in_str = None
            i += 1
            continue
        if c in "\"'`":
            in_str, quote = True, c
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] not in "\r\n":
                out[i] = " "
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                if text[i] not in "\r\n":
                    out[i] = " "
                i += 1
            for _ in range(2):
                if i < n:
                    out[i] = " "
                    i += 1
            continue
        i += 1
    return "".join(out)


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


# --- 2b. dead and duplicated code ----------------------------------------
# None of these stop the pack loading, which is exactly why they accumulate:
# a duplicated switch case is unreachable, an unused constant is a fix that
# was half-applied, and a duplicated JSON key silently keeps only the last
# value. All three were present in this pack before this check existed.
def check_dead_code():
    for f in sorted(glob.glob(f"{BP}/scripts/**/*.js", recursive=True)):
        src = js_source(f)

        # Duplicate `case "x":` labels inside one switch block. Tracking brace
        # depth is enough to keep separate switches apart.
        depth, seen = 0, {}
        for lineno, line in enumerate(src.splitlines(), 1):
            if "switch" in line:
                seen[depth + line.count("{")] = set()
            m = re.match(r"\s*case\s+(\"[^\"]*\"|'[^']*'|[\w.]+)\s*:", line)
            if m:
                labels = seen.setdefault(depth, set())
                if m.group(1) in labels:
                    err(f"{rel(f)}:{lineno}: duplicate case {m.group(1)} - "
                        f"the second one can never run")
                labels.add(m.group(1))
            depth += line.count("{") - line.count("}")

        # Module-level constants nobody reads. `export`ed ones are part of the
        # module's surface, so they are left alone.
        for m in re.finditer(r"^const ([A-Z][A-Z0-9_]*)\s*=", src, re.M):
            name = m.group(1)
            uses = len(re.findall(rf"\b{name}\b", src))
            if uses <= 1:
                line = src[:m.start()].count("\n") + 1
                warnings.append(f"{rel(f)}:{line}: {name} is never used")

    # Duplicate keys in JSON. json.load keeps the last silently, so a file can
    # look correct and behave as something else entirely.
    def dup_keys(pairs, where):
        seen = set()
        for key, _ in pairs:
            if key in seen:
                err(f"{where}: duplicate key {key!r} - only the last one applies")
            seen.add(key)
        return dict(pairs)

    for f in glob.glob(f"{BP}/**/*.json", recursive=True) + glob.glob(f"{RP}/**/*.json", recursive=True):
        try:
            json.load(open(f), object_pairs_hook=lambda p, w=rel(f): dup_keys(p, w))
        except ValueError:
            pass                        # check_json already reported the parse error


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
        src = js_source(f)
        for m in re.finditer(r"world\.(afterEvents|beforeEvents)\.(\w+)", src):
            kind, ev = m.group(1), m.group(2)
            if ev not in valid[kinds[kind]]:
                line = src[:m.start()].count("\n") + 1
                err(f"{rel(f)}:{line}: world.{kind}.{ev} does not exist in "
                    f"@minecraft/server {SERVER_VERSION}")


# --- 3b. every event property we destructure actually exists --------------
# Same family of mistake as a wrong event name, and quieter: a misspelt or
# imagined property is simply `undefined`, so the handler runs and does the
# wrong thing forever without a single line in the log. The igniter reads
# `blockFace` off the interact event; if that were wrong it would silently
# light fires in the wrong place.
def check_event_properties():
    if not os.path.isfile(BINDINGS):
        skipped.append("Script API event properties (bedrock-samples not cloned)")
        return
    d = json.load(open(BINDINGS))
    classes = {c["name"]: c for c in d["classes"]}
    props_of = {n: {p["name"] for p in c.get("properties", [])} for n, c in classes.items()}

    def event_class(kind, name):
        """world.afterEvents.<name> -> the class handed to its callback."""
        holder = classes.get("WorldAfterEvents" if kind == "afterEvents" else "WorldBeforeEvents")
        signal = next((p["type"].get("name") for p in (holder or {}).get("properties", [])
                       if p["name"] == name), None)
        subscribe = next((fn for fn in classes.get(signal, {}).get("functions", [])
                          if fn["name"] == "subscribe"), None)
        if not subscribe:
            return None
        args = subscribe["arguments"][0]["type"].get("closure_type", {}).get("argument_types", [])
        return args[0]["name"] if args else None

    pattern = re.compile(
        r"world\.(afterEvents|beforeEvents)\.(\w+)\.subscribe\(\s*\(?\s*"
        r"(?:\{([^}]*)\}|(\w+))\s*\)?\s*=>", re.S)
    destructure = re.compile(r"const\s*\{([^}]*)\}\s*=\s*(\w+)\s*;")

    for f in glob.glob(f"{BP}/scripts/**/*.js", recursive=True):
        src = js_source(f)
        for m in pattern.finditer(src):
            kind, name, inline, param = m.group(1), m.group(2), m.group(3), m.group(4)
            cls = event_class(kind, name)
            known = props_of.get(cls)
            if not known:
                continue
            # Either destructured in the parameter list, or on the first line
            # of the body via `const { ... } = ev;`.
            fields = inline or ""
            if param:
                body = src[m.end():m.end() + 400]
                inner = destructure.search(body)
                if inner and inner.group(2) == param:
                    fields = inner.group(1)
            for raw in fields.split(","):
                key = raw.split(":")[0].split("=")[0].strip()
                if key and key not in known:
                    line = src[:m.start()].count("\n") + 1
                    err(f"{rel(f)}:{line}: {cls} has no property {key!r} - it will "
                        f"silently be undefined")


# --- 3c. every status effect a script applies actually exists -------------
# addEffect() with an unknown id throws, and every call site here wraps that
# in a try/catch, so an imaginary effect is completely silent - the ability
# just never happens. The Spirit Lantern's "reveal hidden poltergeists" was
# dead in every released build because it used "glowing", which is a Java
# effect; Bedrock ships 37 and that is not one of them.
def check_script_effects():
    path = os.path.join(VANILLA_DATA, "mojang-effects.json")
    if not os.path.isfile(path):
        skipped.append("status effect ids (bedrock-samples not cloned)")
        return
    valid = set()
    for e in json.load(open(path))["data_items"]:
        name = e.get("name", "")
        valid.add(name)
        valid.add(name.split(":", 1)[-1])
    for f in glob.glob(f"{BP}/scripts/**/*.js", recursive=True):
        src = js_source(f)
        for m in re.finditer(r'(?:add|remove)Effect\(\s*"([\w:]+)"', src):
            if m.group(1) not in valid:
                line = src[:m.start()].count("\n") + 1
                err(f"{rel(f)}:{line}: {m.group(1)!r} is not a Minecraft Bedrock "
                    f"status effect - the call throws and the ability silently "
                    f"never happens")


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

    # A no-gravity entity with no minecraft:can_fly is not treated as a flier
    # by the movement system, so knockback sends it upward and nothing ever
    # brings it back down - mobs literally fly off into the sky when hit.
    # Every vanilla no-gravity flier (allay, bat) declares can_fly.
    PROJECTILES = {"hollowveil:debris_projectile", "hollowveil:imp_fireball"}
    for f in sorted(glob.glob(f"{BP}/entities/*.json")):
        e = json.load(open(f))["minecraft:entity"]
        ident = e["description"]["identifier"]
        if ident in PROJECTILES:
            continue
        c = e["components"]
        nograv = c.get("minecraft:physics", {}).get("has_gravity", True) is False
        if nograv and "minecraft:can_fly" not in c:
            err(f"{ident}: has_gravity false but no minecraft:can_fly - knockback will launch it into the sky")
        if "minecraft:knockback_resistance" not in c:
            warnings.append(f"{ident}: no knockback_resistance")

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


# --- 9a. particle emitter schema -----------------------------------------
# A point emitter's `direction` must be an array of three Molang
# expressions; the string "outwards" is only legal on box/sphere emitters.
# Getting this wrong makes the effect fail to load entirely with
# "EmitterShapePointComponent | direction | error reading array" - so the
# pack looks like it has no particles at all, with no in-game clue why.
def check_particles():
    for f in sorted(glob.glob(f"{RP}/particles/*.json")):
        fx = json.load(open(f))["particle_effect"]
        comps = fx["components"]
        shapes = [k for k in comps if k.startswith("minecraft:emitter_shape_")]
        if not shapes:
            err(f"{rel(f)}: no emitter shape component")
            continue
        for shape in shapes:
            d = comps[shape].get("direction")
            if d is None:
                continue
            if shape.endswith("_point"):
                if not isinstance(d, list) or len(d) != 3:
                    err(f"{rel(f)}: {shape}.direction must be a 3-element array "
                        f"(got {d!r}) - \"outwards\" is box/sphere only")
            elif isinstance(d, str) and d not in ("outwards", "inwards"):
                err(f"{rel(f)}: {shape}.direction string must be 'outwards' or 'inwards' (got {d!r})")
        tex = fx["description"]["basic_render_parameters"]["texture"]
        if not os.path.isfile(os.path.join(RP, tex + ".png")):
            err(f"{rel(f)}: particle texture {tex!r} missing")


# --- 9b. geometry is box-UV safe and matches its texture size ------------
def check_geometry():
    from PIL import Image  # only needed here; keep the rest import-light
    for f in sorted(glob.glob(f"{RP}/models/entity/*.geo.json")):
        for g in json.load(open(f))["minecraft:geometry"]:
            ident = g["description"]["identifier"]
            tw = g["description"].get("texture_width")
            th = g["description"].get("texture_height")
            for b in g["bones"]:
                for c in b.get("cubes", []):
                    size = c["size"]
                    # Box UV paints whole pixels but Minecraft maps UVs from
                    # the cube's real size, so a fractional size samples a
                    # region that was never painted -> smeared texture.
                    if any(abs(v - round(v)) > 1e-6 for v in size):
                        err(f"{ident}: bone {b['name']} has non-integer cube size {size} (box-UV texture drift)")
                    if min(size) <= 0:
                        err(f"{ident}: bone {b['name']} has degenerate cube size {size}")
            name = os.path.basename(f).replace(".geo.json", "")
            png = os.path.join(RP, "textures", "entity", f"{name}.png")
            if os.path.isfile(png) and tw and th:
                im = Image.open(png)
                if (im.width, im.height) != (tw, th):
                    err(f"{ident}: geometry declares {tw}x{th} but {name}.png is {im.width}x{im.height}")


# --- 9c. the asset generators still run --------------------------------
# gen_entities.py silently crashed for a while after a refactor (a missing
# import), so "regenerating the art" quietly became a no-op and fixes to the
# generators never reached the pack. Importing each one catches that class
# of breakage.
def check_generators():
    # Importing is not enough: the crash that broke gen_entities.py was a
    # NameError inside a function, so the module imported fine and only blew
    # up when actually run. These have to be executed. They are deterministic
    # (see stable_seed) and idempotent, so re-running them here rewrites the
    # same bytes rather than churning the tree.
    tools_dir = os.path.join(ROOT, "tools")
    for mod in ("gen_assets.py", "gen_entities.py", "gen_animations.py",
                "gen_sounds.py", "gen_guide.py"):
        p = subprocess.run([sys.executable, mod], cwd=tools_dir, capture_output=True, text=True)
        if p.returncode != 0:
            last = p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "?"
            err(f"tools/{mod} fails to run: {last}")


# Blocks are the one domain where Mojang ships a single schema version, so a
# block declaring anything older than it is completely unverifiable - and the
# device proved that situation is fatal rather than theoretical: seventeen
# blocks at 1.21.0 died on a 1.26.20-only component this check could not see.
# Entities and items ship many schema versions and 21 entity files here
# legitimately declare 1.20.0 and load fine, so those stay a warning.
UNVERIFIABLE_IS_FATAL = {"block"}


def _report_unverified(unverified, snapshot):
    for domain, files in sorted(unverified.items()):
        floor = snapshot["oldest_schema"][domain]
        message = (f"{len(files)} {domain} file(s) declare a format_version older "
                   f"than {floor}, the oldest schema Mojang ships for {domain}s - "
                   f"nothing about their components can be verified: "
                   f"{', '.join(files[:4])}")
        (err if domain in UNVERIFIABLE_IS_FATAL else warnings.append)(message)


# --- 8b. full draft-07 validation against Mojang's official schemas --------
# The snapshot check above is stdlib-only and covers component shapes and
# field names. When the samples checkout and `jsonschema` are both present,
# tools/schema_check.py validates every entity, item and block against the
# real schemas - nested objects, enums, ranges, the lot - using vanilla's own
# content as a control group for the schemas' overlapping oneOf branches.
def check_official_schemas():
    script = os.path.join(ROOT, "tools", "schema_check.py")
    if not os.path.isfile(script):
        return
    p = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True)
    out = p.stdout.strip()
    if out.startswith("SKIP:"):
        skipped.append(out.splitlines()[0][6:].strip())
        return
    if p.returncode != 0:
        for line in out.splitlines():
            if line.startswith("  ") and ": " in line:
                err(f"schema: {line.strip()}")


# --- 9b2. the stat table and the items agree ------------------------------
# tools/balance.py is the single source of truth for every damage, protection,
# durability and enchantability value. If an item drifts from it - a hand-edit,
# a half-applied change - the pack ships two different balance passes at once.
def check_balance():
    script = os.path.join(ROOT, "tools", "balance.py")
    if not os.path.isfile(script):
        return
    p = subprocess.run([sys.executable, script, "--check", "--quiet"],
                       cwd=ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        for line in p.stdout.splitlines():
            if line.strip().startswith("hollowveil") or ": minecraft:" in line:
                err(f"balance: {line.strip()}")
        if not any("balance:" in e for e in errors):
            err("tools/balance.py reports item stats have drifted from the table")


# --- 9c. every item and block is reachable in survival --------------------
# An item with no recipe, no loot entry, no shop trade and no world placement
# exists only in the creative menu. `hollowveil:ember_core` shipped that way
# for several releases: a fuel nothing dropped and nothing crafted.
def check_reachability():
    def ids_in(node, out):
        if isinstance(node, str):
            out.add(node.split("<")[0].strip())
        elif isinstance(node, dict):
            if isinstance(node.get("item"), str):
                out.add(node["item"].split("<")[0].strip())
            for v in node.values():
                ids_in(v, out)
        elif isinstance(node, list):
            for v in node:
                ids_in(v, out)

    reachable = set()
    for f in glob.glob(f"{BP}/recipes/*.json"):
        for key, recipe in json.load(open(f)).items():
            if key.startswith("minecraft:recipe"):
                ids_in(recipe.get("result"), reachable)
                ids_in(recipe.get("output"), reachable)
    for f in glob.glob(f"{BP}/loot_tables/**/*.json", recursive=True):
        reachable |= set(re.findall(r'"name"\s*:\s*"(hollowveil:[\w]+)"', open(f).read()))
    # Shop stock, plus anything the builders place - a block a structure puts
    # in the world is obtainable by walking up and mining it. Placement is
    # indirect (ore ids live in a vein table, spawner ids are passed to a
    # helper), so rather than trace it, treat any identifier named by a
    # builder script as placed, and additionally read /fill and /setblock
    # command templates anywhere. Deliberately generous: the point is to
    # catch content nothing anywhere references, not to prove a spawn rate.
    BUILDERS = ("/world/", "/village/", "/bosses/", "/ui/shop.js")
    for f in glob.glob(f"{BP}/scripts/**/*.js", recursive=True):
        src = js_source(f)
        unix = f.replace("\\", "/")
        if any(part in unix for part in BUILDERS):
            reachable |= set(re.findall(r'(hollowveil:[\w]+)', src))
        for cmd in re.findall(r'`(?:fill|setblock)[^`]*`', src):
            reachable |= set(re.findall(r'(hollowveil:[\w]+)', cmd))

    for kind, pattern, root in (("item", f"{BP}/items/*.json", "minecraft:item"),
                                ("block", f"{BP}/blocks/*.json", "minecraft:block")):
        for f in sorted(glob.glob(pattern)):
            ident = json.load(open(f))[root]["description"]["identifier"]
            if ident not in reachable:
                err(f"{ident}: no survival source - not a recipe result, not in "
                    f"any loot table, not sold, not placed by world generation")


# --- 9d. every wearable item has the attachable that renders it -----------
# A custom armour piece with no matching attachable equips fine and renders
# as nothing at all on the player - the stat bonus applies but the model is
# invisible, which reads in-game as "the armour is broken".
def check_attachables():
    worn = {}
    for f in sorted(glob.glob(f"{BP}/items/*.json")):
        d = json.load(open(f))["minecraft:item"]
        if "minecraft:wearable" in d["components"]:
            worn[d["description"]["identifier"]] = d["components"]["minecraft:wearable"]

    bound = {}
    for f in glob.glob(f"{RP}/attachables/*.json"):
        desc = json.load(open(f))["minecraft:attachable"]["description"]
        for item_id in (desc.get("item") or {}):
            bound[item_id] = os.path.basename(f)
        for tex in (desc.get("textures") or {}).values():
            # Vanilla textures (the enchanted glint) live in the game's own
            # pack, so only ours need to exist on disk here.
            if tex.startswith("textures/models/armor/") and \
                    not os.path.exists(os.path.join(RP, tex + ".png")):
                err(f"{os.path.basename(f)}: texture {tex}.png is missing")

    for ident in worn:
        if ident not in bound:
            err(f"{ident}: wearable but no attachable binds it - it will equip "
                f"and render as nothing on the player")
    for ident in bound:
        if ident not in worn:
            err(f"{bound[ident]}: binds {ident}, which is not a wearable item")


# --- 9e. tool digger tags match tags blocks actually carry ----------------
# minecraft:digger speeds are matched by block tag. Every tool in this pack
# queried tags like 'stone' and 'diamond_pick_diggable' while not one custom
# block carried any tag at all, so no custom tool was ever faster than a bare
# hand on any custom block - the whole tool tier was cosmetic.
def check_tool_tags():
    block_tags = set()
    for f in glob.glob(f"{BP}/blocks/*.json"):
        tags = json.load(open(f))["minecraft:block"]["components"].get("minecraft:tags")
        if isinstance(tags, list):
            block_tags |= set(tags)
    for f in sorted(glob.glob(f"{BP}/items/*.json")):
        d = json.load(open(f))["minecraft:item"]
        digger = d["components"].get("minecraft:digger")
        if not digger:
            continue
        queried = set()
        for entry in digger.get("destroy_speeds", []):
            block = entry.get("block")
            if isinstance(block, dict) and isinstance(block.get("tags"), str):
                queried |= set(re.findall(r"'([^']+)'", block["tags"]))
        # Tags that only exist on vanilla blocks: a sword matching 'cobweb'
        # is correct even though this pack ships no cobweb.
        queried -= {"cobweb", "web", "leaves", "wool", "plant"}
        if queried and not (queried & block_tags):
            warnings.append(
                f"{d['description']['identifier']}: digger matches "
                f"{sorted(queried)} but no block in this pack carries any of "
                f"them - the tool is no faster than a bare hand here")


# --- 9b. the portal can actually be lit -----------------------------------
# "Portal tool doesn't light the gold blocks" was reported twice. The second
# time, frame detection required gold at the four corners - a frame built the
# way the game teaches you to build a nether portal has none, so every
# correct build was rejected. tools/test_portal.js runs the real detection
# code against a stub world containing exactly that frame.
def check_portal():
    test = os.path.join(ROOT, "tools", "test_portal.js")
    if not os.path.isfile(test):
        skipped.append("portal frame tests (tools/test_portal.js missing)")
        return
    p = subprocess.run(["node", test], cwd=ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        for line in p.stdout.splitlines():
            if line.strip().startswith("FAIL"):
                err(f"portal: {line.strip()[5:].strip()}")
        if not any(l.strip().startswith("FAIL") for l in p.stdout.splitlines()):
            err(f"tools/test_portal.js failed to run: {p.stderr.strip().splitlines()[-1:]}")


# --- 10. early-execution safety -------------------------------------------
# Script modules run during "early execution", where native world calls are
# forbidden. A top-level world.sendMessage throws and aborts the ENTIRE
# module, killing every subsystem - which is exactly how the portal, shop and
# item handlers all went dead while the log showed only one error.
EARLY_FORBIDDEN = ("world.sendMessage", "world.getDimension", "world.getAllPlayers", "world.playSound")


def check_early_execution():
    for f in glob.glob(f"{BP}/scripts/**/*.js", recursive=True):
        depth = 0
        for i, line in enumerate(open(f), 1):
            code = line.split("//")[0]
            if depth == 0:
                for bad in EARLY_FORBIDDEN:
                    if bad + "(" in code:
                        err(f"{rel(f)}:{i}: {bad}() at module top level - "
                            f"native world calls are not allowed during early execution "
                            f"and will abort the whole module")
            depth += code.count("{") - code.count("}")
            depth = max(0, depth)


# --- 11. component shapes and field names against the vanilla schema ------
# The single most expensive bug class in this addon. A component whose value
# has the wrong shape, or which contains a field the engine has never heard
# of, does not warn harmlessly and does not disable just that component: it
# voids the ENTIRE definition. The mob or item vanishes from the game and the
# only trace is one line in the content log. It has happened four separate
# times here - `minecraft:fire_immune: true`, `flying_speed: 0.09`,
# `behavior.random_fly.y_offset`, `use_modifiers.start_using` - each time
# after shipping, each time found by the user rather than by us.
#
# tools/schema/vanilla_components.json is generated from Mojang's own
# metadata/json_schemas by tools/gen_vanilla_schema.py, so this check needs
# nothing but the stdlib and the committed snapshot. tools/schema_check.py
# does the deeper draft-07 validation when the samples checkout is present.
SCHEMA_SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "schema", "vanilla_components.json")

JSON_TYPE_NAMES = {
    bool: "boolean", dict: "object", list: "array",
    int: "integer", float: "number", str: "string", type(None): "null",
}


def json_type(value):
    return JSON_TYPE_NAMES.get(type(value), "null")


def type_ok(value, allowed):
    name = json_type(value)
    if name in allowed:
        return True
    # JSON Schema treats every integer as a valid "number".
    return name == "integer" and "number" in allowed


# The mirror image of legacy_fields: members that exist in the current schema
# but were added after the format_version a file declares, so writing them
# there voids the components block. Only bedrock-samples' newest schema ships,
# so these cannot be derived - each entry needs its own evidence.
FORMAT_GATED = [
    {
        "domain": "item", "component": "minecraft:use_modifiers",
        "field": "start_using", "since": (1, 21, 60),
        # Device log, previous round: this voided the entire components block
        # on elk_marrow, ember_fruit and veil_marrow_stew - all format 1.21.0 -
        # so they lost their icons and their names along with it.
        "why": "added after 1.21.60; at an older format_version it voids the "
               "whole components block",
    },
]


def format_version_of(doc):
    return tuple(int(x) for x in re.findall(r"\d+", str(doc.get("format_version", "")))[:3])


def parse_version(text):
    parts = re.findall(r"\d+", str(text or ""))
    return tuple(int(p) for p in parts[:3]) if parts else ()


def check_format_gated(domain, ident, fmt, comps):
    for rule in FORMAT_GATED:
        if rule["domain"] != domain or fmt >= rule["since"]:
            continue
        node = comps.get(rule["component"])
        if isinstance(node, dict) and rule["field"] in node:
            err(f"{ident}: {rule['component']}.{rule['field']} - {rule['why']}")


def check_component_schema():
    if not os.path.exists(SCHEMA_SNAPSHOT):
        skipped.append(f"{rel(SCHEMA_SNAPSHOT)} missing - run tools/gen_vanilla_schema.py")
        return
    snapshot = json.load(open(SCHEMA_SNAPSHOT))

    domains = [
        ("entity", f"{BP}/entities/*.json", "minecraft:entity", ("component_groups",)),
        ("item", f"{BP}/items/*.json", "minecraft:item", ()),
        ("block", f"{BP}/blocks/*.json", "minecraft:block", ()),
    ]
    oldest = {k: parse_version(v) for k, v in (snapshot.get("oldest_schema") or {}).items() if v}
    unverified = {}

    for domain, pattern, root, group_keys in domains:
        known = snapshot.get(domain, {})
        if not known:
            continue
        for f in sorted(glob.glob(pattern)):
            d = json.load(open(f))
            doc = d.get(root, {})
            ident = doc.get("description", {}).get("identifier", rel(f))

            blocks = [("components", doc.get("components"))]
            for key in group_keys:
                for name, group in (doc.get(key) or {}).items():
                    blocks.append((f"{key}/{name}", group))
            for perm in doc.get("permutations") or []:
                blocks.append(("permutations", perm.get("components")))

            fmt = format_version_of(d)
            if isinstance(doc.get("components"), dict):
                check_format_gated(domain, ident, fmt, doc["components"])

            # A file whose format_version predates every schema Mojang ships
            # for its domain cannot be verified at all: the checks below are
            # measuring it against a parser newer than the one that will read
            # it. That is not a hypothetical - blocks declared 1.21.0 were
            # checked against the 1.26.20 block schema, which is how a
            # 1.26.20-only component got waved through and killed seventeen
            # of them on a real device.
            floor = oldest.get(domain)
            if fmt and floor and fmt < floor:
                unverified.setdefault(domain, []).append(
                    f"{ident} ({'.'.join(map(str, fmt))})")

            for where, comps in blocks:
                if not isinstance(comps, dict):
                    continue
                for comp, value in comps.items():
                    if not comp.startswith("minecraft:"):
                        continue
                    spec = known.get(comp)
                    # The version gate. A component the engine only learned
                    # about in a later format_version than this file declares
                    # is not "unsupported" - it fails the whole definition.
                    # Three separate regressions shipped this way before this
                    # check existed: minecraft:tags on 1.21.0 blocks (added
                    # 1.26.20) took out seventeen blocks, the FloatRange
                    # attack_interval on 1.20.0 entities (added 1.26.40) took
                    # out four mobs, and minecraft:pushable - which no schema
                    # has ever listed - took out the Veil Dragon the moment it
                    # moved to a modern format.
                    if spec is not None and fmt:
                        since = parse_version(spec.get("since")) if spec.get("since") else None
                        if since and fmt < since:
                            err(f"{ident} ({where}): {comp} was added in format "
                                f"{spec['since']}, but this file declares "
                                f"{'.'.join(map(str, fmt))} - the whole "
                                f"definition will fail to parse")
                            continue
                        if spec.get("in_schema") is False and fmt >= oldest.get(domain, (99, 0, 0)):
                            err(f"{ident} ({where}): {comp} is in no schema "
                                f"Mojang ships. The parser tolerates it below "
                                f"format {snapshot['oldest_schema'][domain]} "
                                f"and rejects it at or above - this file "
                                f"declares {'.'.join(map(str, fmt))}")
                            continue
                        for key in (value if isinstance(value, dict) else ()):
                            added = (spec.get("field_since") or {}).get(key)
                            if added and fmt < parse_version(added):
                                err(f"{ident} ({where}): {comp}.{key} was added "
                                    f"in format {added}, but this file declares "
                                    f"{'.'.join(map(str, fmt))} - the whole "
                                    f"definition will fail to parse")
                    if spec is None:
                        # patternProperties components (memory_behavior.*) carry
                        # a user-chosen suffix, so match on the prefix too.
                        if any(comp.startswith(k + ".") for k in known):
                            continue
                        err(f"{ident} ({where}): {comp} is not a component this "
                            f"engine knows - the whole definition will fail to load")
                        continue

                    allowed = spec.get("types")
                    if allowed and not type_ok(value, allowed):
                        err(f"{ident} ({where}): {comp} is a {json_type(value)}, "
                            f"the engine wants {' or '.join(allowed)} - the whole "
                            f"definition will fail to load")
                        continue

                    fields = spec.get("fields")
                    legacy = spec.get("legacy_fields") or []
                    if legacy and fmt and fmt < oldest.get(domain, (0, 0, 0)) \
                            and isinstance(value, dict):
                        # Only fields that a legacy field actually REPLACED -
                        # i.e. some legacy name extends this one, the way
                        # attack_interval_min extends attack_interval. Without
                        # that test this fired on `priority` and
                        # `attack_radius`, which have been valid forever.
                        modern = [k for k in value
                                  if k in (fields or []) and k not in legacy
                                  and any(old.startswith(k + "_") for old in legacy)]
                        if modern:
                            warnings.append(
                                f"{ident} ({where}): {comp} uses "
                                f"{', '.join(sorted(modern))} at format "
                                f"{'.'.join(map(str, fmt))}, which predates any "
                                f"schema describing this component. Vanilla "
                                f"content of this era writes "
                                f"{', '.join(sorted(legacy))} instead")
                    if fields and isinstance(value, dict):
                        for key in value:
                            if key in fields:
                                continue
                            if key in legacy and fmt and fmt < oldest.get(domain, (0, 0, 0)):
                                continue   # correct spelling for this format
                            if key in legacy:
                                # Vanilla content still writes this field but
                                # the current schema dropped it. Sometimes the
                                # engine shrugs (skeleton's attack_interval_min)
                                # and sometimes it voids the entity (parrot's
                                # random_fly.y_offset, which did exactly that
                                # here). Not worth the coin flip - use the
                                # field the schema still lists.
                                warnings.append(
                                    f"{ident} ({where}): {comp}.{key} is a legacy "
                                    f"field the current schema no longer lists")
                                continue
                            err(f"{ident} ({where}): {comp}.{key} is not in the "
                                f"schema - the whole definition will fail to load")

                    # Advisory tiers: the official schema declines to constrain
                    # this component, so disagreeing with vanilla is suspicious
                    # rather than provably fatal.
                    seen = spec.get("seen")
                    if not allowed and seen and not type_ok(value, seen):
                        warnings.append(
                            f"{ident} ({where}): {comp} is a {json_type(value)}; all "
                            f"{spec.get('seen_count')} vanilla uses are "
                            f"{' or '.join(seen)}")
                    doc_fields = spec.get("doc_fields")
                    if not fields and doc_fields and isinstance(value, dict):
                        for key in value:
                            if key not in doc_fields:
                                warnings.append(
                                    f"{ident} ({where}): {comp}.{key} is not in "
                                    f"Mojang's component reference")
    _report_unverified(unverified, snapshot)


# --- 12. entity particle references --------------------------------------
# particle_on_hit and friends only accept built-in legacy particle names.
# A custom RP particle identifier logs "Invalid particle type" and is
# silently dropped.
def check_entity_particles():
    for f in glob.glob(f"{BP}/entities/*.json"):
        d = json.load(open(f))
        ident = d["minecraft:entity"]["description"]["identifier"]
        for m in re.finditer(r'"particle_type"\s*:\s*"([^"]+)"', json.dumps(d)):
            p = m.group(1)
            if ":" in p:
                err(f"{ident}: particle_type {p!r} - entity components only accept "
                    f"built-in legacy particle names, not custom identifiers")


# --- 9. the two manifests agree with each other --------------------------
def check_manifests():
    bp = json.load(open(os.path.join(BP, "manifest.json")))
    rp = json.load(open(os.path.join(RP, "manifest.json")))
    for name, this, other in (("BP", bp, rp), ("RP", rp, bp)):
        other_uuid = other["header"]["uuid"]
        other_ver = other["header"]["version"]
        dep = next((d for d in this.get("dependencies", []) if d.get("uuid") == other_uuid), None)
        if dep is None:
            err(f"{name}/manifest.json: no dependency on the other pack ({other_uuid})")
        elif dep.get("version") != other_ver:
            # a stale dependency version reads as an unresolved dependency
            # in-game and the pack cannot be enabled
            err(f"{name}/manifest.json: dependency version {dep.get('version')} "
                f"does not match the other pack's header version {other_ver}")
    if bp["header"]["min_engine_version"] != rp["header"]["min_engine_version"]:
        warnings.append("BP and RP min_engine_version differ")

    # Every UUID in both manifests must be distinct. A repeated one makes the
    # game reject the import as a duplicate pack.
    seen = {}
    for side, man in (("BP", bp), ("RP", rp)):
        entries = [(f"{side} header", man["header"]["uuid"])]
        entries += [(f"{side} {m['type']} module", m["uuid"]) for m in man["modules"]]
        for label, u in entries:
            if u in seen:
                err(f"duplicate UUID {u} used by both {seen[u]} and {label}")
            seen[u] = label

    # These shipped in earlier builds. Reusing one is what produced the
    # "Duplicate pack detected" error on import, so they are now banned.
    RETIRED = {
        "0f251285-1535-4d56-89e7-41c4a1143e5e",
        "1335f7ba-d26c-4ed9-bc17-f29b193e18da",
        "2418701a-7fa0-47a8-bb18-c20a3b9b45e9",
        "2bce0818-2c7b-47cc-ab8e-b29c59646fec",
        "2d6693e3-30ef-4ab5-af8d-903e5fa06e3f",
        "36864a3d-4e54-465b-886c-66356c03db69",
        "36d910e6-19c8-4464-8aaa-e878ad5775bc",
        "3e151a25-ce4c-47db-aa91-4b6dc17a5ce1",
        "4079299a-d286-4658-8f7c-9cb6fbcd19a0",
        "464ebcd1-a74c-4109-94ae-8ff9a324e029",
        "46e6c8fa-b01e-4082-bc0d-8dc073d60e35",
        "4e86adc1-3bd9-4b84-9399-c5f0b391c6bf",
        "583094e0-638f-4560-8015-ff61a552ec14",
        "5d1cab31-7a08-4be1-bd30-58a88ee6c70e",
        "6022b7d6-f4db-4c7e-8437-5a463313d2c6",
        "64e7a8dd-cef4-42e5-a82e-9b9ccd145a19",
        "698cdb7f-e4b9-46d7-aaba-ca59becc38de",
        "72f17a26-4315-4da5-bd56-726b955baae4",
        "7356403b-01aa-4249-8c6e-f56aa98972db",
        "75d3b110-bcbd-4b4c-9b87-6e21508ad7c0",
        "7c58c9a1-0068-429a-9f2c-472760a3fefb",
        "7c86d2fc-67c1-4aa1-b552-93e58e3c7dfb",
        "7d9c8b34-de57-4fa7-8fbb-e474b13b215c",
        "873bb57b-2eec-4c8f-810a-380f2c9fbe4b",
        "885991b9-2285-453c-88d9-b9caa859c2fc",
        "88a14967-b1ec-4230-9a21-472358d351a4",
        "8b83720f-c727-40bf-b60b-fd9670e9f17d",
        "8c65e54f-84fb-4532-9199-45ebad51dd37",
        "915cf596-e3c7-4014-978e-df04a7f46861",
        "a63f5256-bccb-46d7-843b-853bd45956db",
        "a7f48924-5a1a-493f-b2cd-87735ab3b128",
        "ae6e6ecc-4012-4967-b18f-602b77319602",
        "b059cd3b-38ec-408e-b1bd-9862c445c434",
        "b5759d66-90c1-4161-a552-66a8226eb61f",
        "bf3fdb90-652d-40c2-acf9-2ee24737a2ad",
        "c351775c-40e4-4758-9d3c-d6e2dba24311",
        "c83a852e-3f02-435e-a3ca-4eace3dae3a7",
        "cefe0049-30d2-40ef-b2ce-08d0e44c481c",
        "d0efb2e8-1cfa-44bb-8426-a9d01ba0f437",
        "da0cf01f-a51c-4d87-b44b-34823328adf8",
        "e5fdc2a2-636c-4f4d-a1ad-20a1984128c7",
        "e7541459-702e-46a0-abc1-2a4b66b29eaf",
        "ec0289ad-f988-490b-b4c7-c14baa0c632e",
        "f0806793-e96d-4a61-a128-07ea3e3ed81b",
        "f8ce7466-bf38-46af-840c-f2fa41062087",
    }
    for u, label in seen.items():
        if u in RETIRED:
            err(f"{label} reuses a previously published UUID ({u}) - imports will collide")


def main():
    lang = load_lang()
    n_json = check_json()
    n_js = check_scripts()
    check_dead_code()
    check_events()
    check_event_properties()
    check_script_effects()
    check_items(lang)
    check_entities_blocks(lang)
    check_rp_refs()
    check_sounds_particles()
    check_references()
    check_particles()
    check_geometry()
    check_generators()
    check_balance()
    check_reachability()
    check_attachables()
    check_tool_tags()
    check_portal()
    check_early_execution()
    check_component_schema()
    check_official_schemas()
    check_entity_particles()
    check_manifests()

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
