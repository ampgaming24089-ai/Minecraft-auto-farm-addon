#!/usr/bin/env python3
"""Rename the pack and mint fresh UUIDs.

Minecraft identifies a pack by the UUIDs in its manifests, not by its name. Two
builds that share them are the same pack as far as the game is concerned, so
importing a new one over an old one gets "duplicate pack detected" and the
player is made to choose - and if they keep the old one, none of the new work
arrives at all.

Renaming without re-minting is the same trap wearing a different label. So this
does both together, and it rewrites the behaviour pack's dependency on the
resource pack in the same pass, because that dependency is a UUID too and a
stale one leaves the behaviour pack pointing at a resource pack that no longer
exists under that id.

    python3 tools/rename_pack.py "End Ascendant" 1.7.0
"""

import json
import os
import re
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    name, version_text = sys.argv[1], sys.argv[2]
    version = [int(part) for part in version_text.split(".")]
    if len(version) != 3:
        raise SystemExit("version must be major.minor.patch")

    bp_path = os.path.join(ROOT, "BP", "manifest.json")
    rp_path = os.path.join(ROOT, "RP", "manifest.json")
    bp = json.load(open(bp_path))
    rp = json.load(open(rp_path))
    old_name = bp["header"]["name"].split(" [")[0]

    fresh = lambda: str(uuid.uuid4())
    rp_header = fresh()

    rp["header"]["uuid"] = rp_header
    rp["header"]["name"] = "%s [Resources]" % name
    rp["header"]["version"] = version
    rp["modules"][0]["uuid"] = fresh()
    rp["modules"][0]["version"] = version
    rp["metadata"]["authors"] = [name]

    bp["header"]["uuid"] = fresh()
    bp["header"]["name"] = "%s [Behavior]" % name
    bp["header"]["version"] = version
    bp["metadata"]["authors"] = [name]
    for module in bp["modules"]:
        module["uuid"] = fresh()
        module["version"] = version
    for dependency in bp["dependencies"]:
        # The one dependency identified by uuid is the resource pack.
        if "uuid" in dependency:
            dependency["uuid"] = rp_header
            dependency["version"] = version

    for path, data in ((bp_path, bp), (rp_path, rp)):
        with open(path, "w") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")

    # The name also appears in every console warning and in the set-bonus
    # message, which is what a player actually sees.
    touched = 0
    for base, _dirs, files in os.walk(ROOT):
        if "node_modules" in base or "/.git" in base or "/dist" in base:
            continue
        for filename in files:
            if not filename.endswith((".js", ".md", ".json", ".sh")):
                continue
            full = os.path.join(base, filename)
            if full in (bp_path, rp_path):
                continue
            try:
                text = open(full).read()
            except (UnicodeDecodeError, OSError):
                continue
            if old_name not in text:
                continue
            open(full, "w").write(text.replace(old_name, name))
            touched += 1

    print("%s -> %s  v%s" % (old_name, name, version_text))
    print("  BP header  %s" % bp["header"]["uuid"])
    print("  RP header  %s" % rp_header)
    print("  %d other files mention the name and were updated" % touched)


if __name__ == "__main__":
    main()
