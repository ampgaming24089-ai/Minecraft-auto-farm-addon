#!/usr/bin/env python3
"""Snapshot the vanilla component schema out of Mojang's bedrock-samples.

Round after round, this addon shipped entities Minecraft silently refused to
load because one component had the wrong *shape*: a boolean where the engine
wanted an object (`minecraft:fire_immune`), a bare float where it wanted
`{"value": n}` (`minecraft:flying_speed`), a field name that does not exist
(`behavior.random_fly.y_offset`). Each of those voids the *entire* definition,
so a mob or an item vanishes from the game leaving one line in the content log.

Guessing is what caused those bugs, so nothing here guesses. Three sources,
all Mojang's own, are merged into tools/schema/vanilla_components.json:

  1. metadata/json_schemas - the official draft-07 schemas the engine is
     generated from. Authoritative for value types and field names.
  2. behavior_pack/entities + items - the shapes vanilla actually ships,
     which fills in every component the schemas mark "Dynamic value".
  3. documentation/*.html - the component reference, for field names on
     components the schemas leave open.

validate.py checks this pack against the snapshot using nothing but the stdlib,
so the check keeps working on a machine with no samples checkout. For the full
draft-07 validation (deeper, but needs the samples and `jsonschema`), see
tools/schema_check.py.

Usage:  python3 tools/gen_vanilla_schema.py [path-to-bedrock-samples]
"""
import html
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "schema", "vanilla_components.json")
DEFAULT_SAMPLES = os.environ.get("BEDROCK_SAMPLES", "/workspace/mojang/bedrock-samples")

# Where each domain's component map lives, and what the file is called in
# that domain's version folders. Mojang ships one folder per format version,
# so walking all of them tells us exactly WHICH VERSION introduced a given
# component or field - which is the thing that actually matters and the thing
# guessing got wrong three times.
DOMAINS = {
    "entity": ("server/entity", ["Entity component definitions.json"]),
    "item": ("server/item", ["Item Components.json", "Components.json"]),
    "block": ("server/block", ["Components.json"]),
}


# ---------------------------------------------------------------- JSONC ----
def strip_jsonc(text):
    """Vanilla sample JSON is really JSONC: // comments and trailing commas."""
    out, i, n = [], 0, len(text)
    in_str = esc = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def load_jsonc(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.loads(strip_jsonc(fh.read()))


# ------------------------------------------------------- official schemas ----
class SchemaSet:
    """Loads metadata/json_schemas and resolves the $ref graph on demand."""

    def __init__(self, root):
        self.root = root
        self._cache = {}

    def load(self, uri):
        uri = urllib.parse.unquote(uri)
        if uri not in self._cache:
            path = os.path.join(self.root, uri.lstrip("/"))
            with open(path, encoding="utf-8") as fh:
                self._cache[uri] = json.load(fh)
        return self._cache[uri]

    def resolve(self, node, base, depth=0):
        """Follow $ref until a concrete node; returns (node, base_uri).

        Internal `#/definitions/...` pointers have to be chased as well as
        external file refs. Older item schemas keep every component's shape in
        a local `definitions` block, so skipping internal refs made those
        versions look like they defined no fields at all - which in turn made
        every field look like it was introduced in the one version that uses
        external refs. That produced 200 confident, completely wrong "added in
        1.26.30" errors the first time this ran.
        """
        seen = 0
        while isinstance(node, dict) and "$ref" in node and seen < 16:
            ref = node["$ref"]
            if ref.startswith("#"):
                target = self.load(base)
                for part in ref.lstrip("#/").split("/"):
                    if not isinstance(target, dict) or part not in target:
                        return None, base
                    target = target[part]
                node = target
                seen += 1
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(base), ref))
            if not target.startswith("/"):
                target = "/" + target
            try:
                node = self.load(target)
            except (OSError, ValueError):
                return None, base
            base = target
            seen += 1
        return node, base

    def describe(self, node, base, depth=0):
        """-> (allowed json types or None, allowed field names or None).

        None means "unconstrained": the schema does not say, so validate.py
        must not complain. Only definite constraints are recorded.
        """
        node, base = self.resolve(node, base, depth)
        if not isinstance(node, dict) or depth > 6:
            return None, None

        branches = []
        for key in ("oneOf", "anyOf"):
            branches.extend(node.get(key) or [])
        if branches:
            types, fields, unconstrained = set(), set(), False
            for branch in branches:
                bt, bf = self.describe(branch, base, depth + 1)
                if bt is None:
                    unconstrained = True
                else:
                    types |= set(bt)
                if bf is None:
                    fields = None
                elif fields is not None:
                    fields |= set(bf)
            return (None if unconstrained else sorted(types),
                    None if fields is None else sorted(fields))

        types = node.get("type")
        if isinstance(types, str):
            types = [types]
        props = node.get("properties")
        fields = sorted(props) if isinstance(props, dict) else None
        if props is not None and types is None:
            types = ["object"]
        return (sorted(types) if types else None), fields

    def component_map(self, rel):
        """{component: (types, fields)} for one domain's component schema."""
        uri = "/" + rel
        root = self.load(uri)
        out = {}
        for comp, spec in (root.get("properties") or {}).items():
            if not comp.startswith("minecraft:"):
                continue
            out[comp] = self.describe(spec, uri)
        return out

    def versioned_maps(self, domain):
        """[(version tuple, version string, component map)] oldest first.

        One entry per format version Mojang ships a schema for. Diffing these
        is how `since` below is derived: the first version whose map contains
        a component is the version that introduced it.
        """
        folder, filenames = DOMAINS[domain]
        base = os.path.join(self.root, folder)
        found = []
        for name in sorted(os.listdir(base)):
            key = version_key(name)
            if not key:
                continue                 # "beta" and friends: not a real format
            for filename in filenames:
                rel = f"{folder}/{name}/{filename}"
                if os.path.exists(os.path.join(self.root, rel)):
                    found.append((key, name, self.component_map(rel)))
                    break
        found.sort()
        return found


def version_key(text):
    """"1.26.20" -> (1, 26, 20). Non-numeric folders ("beta") return None."""
    parts = re.findall(r"\d+", str(text))
    return tuple(int(p) for p in parts[:3]) if parts else None


def introduced(domain, schemas):
    """When each component, and each of its fields, first appears.

    Returns {component: {"since": "1.26.20", "fields": {name: "1.26.40"}}}.
    A component this pack uses at a format_version OLDER than its `since` is
    a component the engine has never heard of yet - it does not warn, it fails
    the whole definition. That is precisely how `minecraft:tags` (blocks,
    1.26.20) killed seventeen blocks declared at 1.21.0, and how the single
    FloatRange `attack_interval` (entities, 1.26.40) killed four entities
    declared at 1.20.0.
    """
    if not schemas:
        return {}
    oldest = schemas[0][1]
    first = {}
    for _, label, comps in schemas:
        for comp, (_types, fields) in comps.items():
            entry = first.setdefault(comp, {"since": label, "described": None, "fields": {}})
            if fields is None:
                continue
            # The first version that actually DESCRIBES the component's fields.
            # Before that the schema carries the component but says nothing
            # about its insides, so a field showing up in the first described
            # version is not evidence of anything. Missing this made the
            # generator announce that all sixteen fields of
            # behavior.ranged_attack arrived in 1.26.40, when 1.26.40 is
            # simply the first version that documents the component at all.
            if entry["described"] is None:
                entry["described"] = label
            for field in fields:
                entry["fields"].setdefault(field, label)

    # Anything already present in the OLDEST schema Mojang ships tells us
    # nothing about when it arrived - it is at least that old and probably far
    # older. Recording "since: <oldest>" would make every long-standing
    # component look brand new and bury the real finds: the first run of this
    # claimed minecraft:nameable was added in 1.21.80. Only differences that
    # appear after the first sample are evidence.
    out = {}
    for comp, entry in first.items():
        since = entry["since"] if entry["since"] != oldest else None
        described = entry["described"]
        fields = {f: v for f, v in entry["fields"].items()
                  if v != oldest and v != described}
        out[comp] = {"since": since, "fields": fields}
    return out


# ------------------------------------------------- shapes vanilla ships ----
JSON_TYPES = {
    bool: "boolean", dict: "object", list: "array",
    int: "integer", float: "number", str: "string", type(None): "null",
}


def shape_of(value):
    return JSON_TYPES.get(type(value), "null")


def observe(paths, root_key, nested_keys=()):
    """Union of value types, object keys and use counts, from real content."""
    types, fields, counts = {}, {}, {}

    def note(block):
        if not isinstance(block, dict):
            return
        for comp, val in block.items():
            if not comp.startswith("minecraft:"):
                continue
            types.setdefault(comp, set()).add(shape_of(val))
            counts[comp] = counts.get(comp, 0) + 1
            if isinstance(val, dict):
                fields.setdefault(comp, set()).update(val.keys())

    for path in paths:
        if not os.path.isdir(path):
            continue
        for fn in sorted(os.listdir(path)):
            if not fn.endswith(".json"):
                continue
            try:
                doc = load_jsonc(os.path.join(path, fn)).get(root_key, {})
            except ValueError:
                continue
            note(doc.get("components"))
            for key in nested_keys:
                for group in (doc.get(key) or {}).values():
                    note(group)
    return types, fields, counts


# --------------------------------------------------------- doc scraping ----
H2_RE = re.compile(r'<h2><p id="(minecraft:[^"]+)">')
ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def doc_fields(doc_path):
    """Field names per component from the HTML reference (a superset)."""
    if not os.path.exists(doc_path):
        return {}
    with open(doc_path, encoding="utf-8", errors="replace") as fh:
        doc = fh.read()
    anchors = [(m.group(1), m.start()) for m in H2_RE.finditer(doc)]
    out = {}
    for idx, (name, start) in enumerate(anchors):
        end = anchors[idx + 1][1] if idx + 1 < len(anchors) else len(doc)
        names = set()
        for row in ROW_RE.findall(doc[start:end]):
            cells = CELL_RE.findall(row)
            if not cells:
                continue
            field = html.unescape(re.sub(r"<[^>]+>", "", cells[0])).strip()
            if re.fullmatch(r"[A-Za-z0-9_.]+", field or ""):
                names.add(field)
        out.setdefault(name, set()).update(names)
    return out


# ------------------------------------------------------------- assembly ----
def merge(schema_map, obs_types, obs_fields, obs_counts=None, extra_fields=None):
    """Schema constraints widened by everything vanilla demonstrably ships.

    Widening matters: a schema that says `{"value": number}` while vanilla also
    ships a bare number would otherwise produce a false alarm. Only constraints
    that survive both sources become `types`/`fields`, which validate.py treats
    as hard errors.

    Field names are taken from the official schemas *only*. Widening them with
    what vanilla ships would be a mistake: `parrot.json` writes `y_offset` into
    `minecraft:behavior.random_fly`, the schema has no such field, and the
    engine rejects it - it rejected it in this pack, on a real device, and took
    nine entities down with it. Mojang's own content is not a safe allowlist.
    Where a schema leaves a component open, the HTML reference fills in as
    `doc_fields`, which validate.py reports as warnings rather than errors.

    Plenty of components are marked "Dynamic value" in the official schemas -
    Mojang's generator had nothing to say about them - yet every vanilla entity
    agrees on one shape anyway. `minecraft:flying_speed` is the example that
    bit this pack: unconstrained by schema, `{"value": n}` in all 127 vanilla
    entities, a bare float here. Those go in `seen` and validate.py reports
    them as warnings, because "nothing in vanilla looks like this" is a weaker
    claim than "the schema forbids this".
    """
    obs_counts = obs_counts or {}
    comps = set(schema_map) | set(obs_types) | set(extra_fields or {})
    out = {}
    for comp in sorted(comps):
        types, fields = schema_map.get(comp, (None, None))
        seen_types = obs_types.get(comp)
        if types is not None and seen_types:
            types = sorted(set(types) | seen_types)
        entry = {}
        if types:
            entry["types"] = types
        if fields:
            entry["fields"] = sorted(fields)
            # Fields vanilla content still writes that the current schema has
            # dropped. `skeleton.json` writes `attack_interval_min` into
            # `minecraft:behavior.ranged_attack`; `parrot.json` writes
            # `y_offset` into `minecraft:behavior.random_fly`. The engine
            # tolerates the first and rejected the second in this pack, so
            # validate.py warns about them instead of guessing which is which.
            legacy = sorted(obs_fields.get(comp, set()) - set(fields))
            if legacy:
                entry["legacy_fields"] = legacy
        else:
            docs = set((extra_fields or {}).get(comp, set()))
            if comp.startswith("minecraft:behavior."):
                # The HTML reference omits the two members every goal accepts.
                docs |= {"priority", "control_flags"}
            docs |= obs_fields.get(comp, set())
            if docs:
                entry["doc_fields"] = sorted(docs)
        # Advisory tier: only worth an opinion once vanilla has used the
        # component enough times for agreement to mean something.
        if not types and seen_types and obs_counts.get(comp, 0) >= 3:
            entry["seen"] = sorted(seen_types)
            entry["seen_count"] = obs_counts[comp]
        out[comp] = entry
    return out


def main():
    samples = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SAMPLES
    if not os.path.isdir(samples):
        print(f"bedrock-samples not found at {samples}", file=sys.stderr)
        print("Pass the path as an argument or set BEDROCK_SAMPLES.", file=sys.stderr)
        return 1

    bp = os.path.join(samples, "behavior_pack")
    docs = os.path.join(samples, "documentation")
    schemas = SchemaSet(os.path.join(samples, "metadata", "json_schemas"))

    ent_versions = schemas.versioned_maps("entity")
    ent_schema = ent_versions[-1][2]
    ent_since = introduced("entity", ent_versions)
    ent_types, ent_fields, ent_counts = observe(
        [os.path.join(bp, "entities")], "minecraft:entity", ("component_groups",))
    entity = merge(ent_schema, ent_types, ent_fields, ent_counts,
                   doc_fields(os.path.join(docs, "Entities.html")))

    item_versions = schemas.versioned_maps("item")
    item_schema = item_versions[-1][2]
    item_since = introduced("item", item_versions)
    item_types, item_fields, item_counts = observe(
        [os.path.join(bp, "items")], "minecraft:item")
    item = merge(item_schema, item_types, item_fields, item_counts)

    blk_versions = schemas.versioned_maps("block")
    blk_schema = blk_versions[-1][2] if blk_versions else {}
    blk_since = introduced("block", blk_versions)
    # Vanilla ships no block JSON, so the schema is the only source here.
    block = merge(blk_schema, {}, {})

    with open(os.path.join(samples, "version.json"), encoding="utf-8") as fh:
        version = json.load(fh).get("latest", {}).get("version", "unknown")

    for domain, since in (("entity", ent_since), ("item", item_since), ("block", blk_since)):
        table = {"entity": entity, "item": item, "block": block}[domain]
        for comp, entry in table.items():
            info = since.get(comp)
            # Whether ANY shipped schema lists this component at all. False
            # means vanilla content uses it but no schema has ever described
            # it - minecraft:pushable is the example. The engine tolerates
            # those below the oldest schema version and rejects them at or
            # above it, which is exactly how the Veil Dragon died.
            entry["in_schema"] = info is not None
            if info:
                if info["since"]:
                    entry["since"] = info["since"]
                if info["fields"]:
                    entry["field_since"] = info["fields"]

    snapshot = {
        "_source": "Mojang bedrock-samples",
        "_version": version,
        "_note": "Generated by tools/gen_vanilla_schema.py - do not hand-edit.",
        "_meaning": ("Per component: 'types' lists every JSON type the engine "
                     "accepts at the component root, 'fields' every top-level "
                     "key it accepts inside; both are hard constraints taken "
                     "from Mojang's official schemas. 'doc_fields' and "
                     "'since' is the oldest format_version whose schema lists "
                     "the component, and 'field_since' the same per field: "
                     "using either below that version fails the whole "
                     "definition. 'seen'/'seen_count' are advisory - the HTML reference's "
                     "field list, and the shapes vanilla content uses, for "
                     "components the schemas leave open. 'legacy_fields' are "
                     "fields vanilla still writes that the schema has dropped. "
                     "A missing key means unconstrained."),
        # The oldest format_version Mojang ships a schema for, per domain.
        # Below this the engine's parser predates the strict schema and
        # tolerates components that no schema lists (minecraft:pushable, for
        # one); at or above it, the same component fails the whole definition.
        "oldest_schema": {
            "entity": ent_versions[0][1] if ent_versions else None,
            "item": item_versions[0][1] if item_versions else None,
            "block": blk_versions[0][1] if blk_versions else None,
        },
        "entity": entity,
        "item": item,
        "block": block,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=1, sort_keys=False)
        fh.write("\n")

    def counted(domain):
        typed = sum(1 for v in domain.values() if "types" in v)
        fielded = sum(1 for v in domain.values() if "fields" in v)
        return f"{len(domain)} components ({typed} typed, {fielded} with field lists)"

    print(f"wrote {os.path.relpath(OUT)}  (vanilla {version})")
    print(f"  entity: {counted(entity)}")
    print(f"  item:   {counted(item)}")
    print(f"  block:  {counted(block)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
