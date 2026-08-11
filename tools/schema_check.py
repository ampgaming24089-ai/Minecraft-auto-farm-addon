#!/usr/bin/env python3
"""Validate this pack against Mojang's official JSON schemas.

bedrock-samples ships `metadata/json_schemas` - the draft-07 schemas the
engine's own parsers are generated from. Checking against them catches the
"entity silently failed to load" class of bug outright, which is worth a lot
more than reading content logs off a phone screenshot.

The catch is that the schemas are machine-generated and their `oneOf` branches
overlap, so plenty of *legal* content trips them ("is valid under each of").
Rather than hand-maintain an ignore list, this uses vanilla itself as a control
group: every schema location that Mojang's own 127 shipped entities trip is by
definition a false positive, so only failures vanilla never produces get
reported. That leaves signal.

Needs the samples checkout and `jsonschema`; both are optional, so validate.py
runs the committed snapshot check instead when they are missing. Run this one
whenever the samples checkout is available - it is stricter.

Usage:  python3 tools/schema_check.py [path-to-bedrock-samples]
"""
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_SAMPLES = os.environ.get("BEDROCK_SAMPLES", "/workspace/mojang/bedrock-samples")

sys.path.insert(0, HERE)
from gen_vanilla_schema import load_jsonc  # noqa: E402  (shared JSONC reader)

# Domain -> (pack dir, document root key, schema document, vanilla control dir)
DOMAINS = [
    ("entity", "BP/entities", "minecraft:entity",
     "/server/entity/1.26.40/ActorDocument.json", "behavior_pack/entities"),
    ("item", "BP/items", "minecraft:item",
     "/server/item/1.26.30/ItemDocument.json", "behavior_pack/items"),
    ("block", "BP/blocks", "minecraft:block",
     "/server/block/1.26.20/Blocks.json", None),
]


def build(samples):
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7

    root = os.path.join(samples, "metadata", "json_schemas")

    def retrieve(uri):
        path = os.path.join(root, urllib.parse.unquote(uri).lstrip("/"))
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        # Pin $id to the URI we asked for so sibling "./x.json" refs resolve
        # against the directory the file actually lives in.
        doc["$id"] = uri
        return Resource(contents=doc, specification=DRAFT7)

    registry = Registry(retrieve=retrieve)

    def validator(uri):
        return Draft7Validator(retrieve(uri).contents, registry=registry)

    return validator


# Only the newest schema of each kind ships in bedrock-samples, so a file that
# declares an older format_version gets measured against rules that did not
# exist when that format was current. Each entry here is a rule that Mojang
# added in a later format than the file declares, with the evidence for it.
# Keep this list short and justified - it is an admission that a check was
# turned off, not a dumping ground.
VERSION_GATED = [
    {
        # "The name also must start with a namespace" is a 1.21.60-era rule.
        # This pack's items declare format_version 1.21.0, where the bare
        # vanilla group names ("itemGroup.name.sword") are the correct form -
        # and they do appear in the creative menu in-game. Applies only to
        # items declaring 1.21.60 or newer.
        "domain": "item",
        "path_suffix": "properties/group/pattern",
        "since": (1, 21, 60),
        "why": "namespaced creative groups became mandatory after 1.21.60",
    },
]


def parse_version(text):
    parts = re.findall(r"\d+", str(text or ""))
    return tuple(int(p) for p in parts[:3]) or (0, 0, 0)


def version_gated(domain, err, fmt):
    for rule in VERSION_GATED:
        if rule["domain"] != domain:
            continue
        schema_path = "/".join(str(p) for p in err.absolute_schema_path)
        if schema_path.endswith(rule["path_suffix"]) and fmt < rule["since"]:
            return rule
    return None


def schema_overlap(err):
    """A `oneOf` whose own branches overlap - a schema bug, not a content bug.

    Mojang's generated schemas contain `oneOf`s with duplicate branches (the
    block descriptor used by `minecraft:digger`, for one). Data matching more
    than one branch fails `oneOf` by the letter of draft-07 while the engine
    accepts it perfectly happily.
    """
    return "is valid under each of" in err.message


def signature(err):
    """Where in the *schema* the failure happened - independent of the data.

    Two files failing the same overlapping `oneOf` produce the same signature,
    which is what makes the vanilla control group able to cancel them out.
    """
    return (err.validator, "/".join(str(p) for p in err.absolute_schema_path))


def control_signatures(validator, samples, control_dir, root_key):
    """Schema locations vanilla's own content trips: known false positives."""
    seen = set()
    path = os.path.join(samples, control_dir) if control_dir else None
    if not path or not os.path.isdir(path):
        return seen, 0
    count = 0
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".json"):
            continue
        try:
            doc = load_jsonc(os.path.join(path, fn)).get(root_key)
        except ValueError:
            continue
        if doc is None:
            continue
        count += 1
        for err in validator.iter_errors(doc):
            seen.add(signature(err))
    return seen, count


def main():
    samples = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SAMPLES
    if not os.path.isdir(samples):
        print(f"SKIP: bedrock-samples not found at {samples}")
        print("      Set BEDROCK_SAMPLES or pass the path; validate.py still "
              "runs the committed snapshot check.")
        return 0
    try:
        make_validator = build(samples)
    except ImportError:
        print("SKIP: `pip install jsonschema` for the deep official-schema check.")
        return 0

    failures = 0
    for name, pack_dir, root_key, schema_uri, control_dir in DOMAINS:
        pack_path = os.path.join(REPO, pack_dir)
        if not os.path.isdir(pack_path):
            continue
        try:
            validator = make_validator(schema_uri)
        except (OSError, ValueError) as err:
            print(f"[{name}] schema unavailable ({err}); skipped")
            continue

        control, control_n = control_signatures(validator, samples, control_dir, root_key)
        found, skipped = [], {}
        for fn in sorted(os.listdir(pack_path)):
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(pack_path, fn), encoding="utf-8") as fh:
                raw = json.load(fh)
            doc = raw.get(root_key)
            if doc is None:
                print(f"[{name}] {fn}: missing \"{root_key}\" root")
                failures += 1
                continue
            fmt = parse_version(raw.get("format_version"))
            for err in validator.iter_errors(doc):
                if signature(err) in control or schema_overlap(err):
                    continue
                rule = version_gated(name, err, fmt)
                if rule:
                    skipped[rule["why"]] = skipped.get(rule["why"], 0) + 1
                    continue
                where = "/".join(str(p) for p in err.absolute_path) or "<root>"
                found.append(f"  {fn}: {where}: {err.message}")

        note = f" (control: {control_n} vanilla files, {len(control)} known-noisy rules)"
        if found:
            print(f"[{name}] {len(found)} schema violation(s){note}")
            for line in found:
                print(line)
            failures += len(found)
        else:
            print(f"[{name}] clean{note}")
        for why, count in sorted(skipped.items()):
            print(f"  note: {count} finding(s) skipped - {why}")

    if failures:
        print(f"\n{failures} violation(s) against Mojang's official schemas.")
        return 1
    print("\nNo violations against Mojang's official schemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
