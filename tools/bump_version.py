#!/usr/bin/env python3
"""Raise the pack version, so an import updates instead of duplicating.

"Duplicate pack detected" has two causes and they want opposite fixes.

A *UUID* collision is two genuinely different packs claiming the same id, and
the fix is to re-mint - tools/rename_pack.py does that.

The one that keeps happening here is the other kind: the same pack, same
UUIDs, imported again at the same version number. Bedrock replaces an
installed pack only when the incoming one is strictly *newer*; at an equal
version it has no way to tell an update from a second copy, so it asks, and
whichever the player keeps, half the work is missing. Re-minting to escape that
is the wrong medicine - new UUIDs orphan the pack in every world already using
it.

So every build raises the patch number. The behaviour pack's dependency on the
resource pack carries a version too, and it is raised in step: a dependency
pinned to a version the resource pack no longer has is a behaviour pack that
loads with no resources at all.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "BP", "manifest.json")
RP = os.path.join(ROOT, "RP", "manifest.json")


def load(path):
    with open(path) as handle:
        return json.load(handle)


def save(path, data):
    with open(path, "w") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def main():
    part = sys.argv[1] if len(sys.argv) > 1 else "patch"
    bp, rp = load(BP), load(RP)

    current = list(bp["header"]["version"])
    if list(rp["header"]["version"]) != current:
        # They must move together: the dependency below is version-pinned.
        current = [max(a, b) for a, b in zip(current, rp["header"]["version"])]

    index = {"major": 0, "minor": 1, "patch": 2}[part]
    current[index] += 1
    for tail in range(index + 1, 3):
        current[tail] = 0

    for manifest in (bp, rp):
        manifest["header"]["version"] = list(current)
        for module in manifest.get("modules", []):
            module["version"] = list(current)
    for dependency in bp.get("dependencies", []):
        if "uuid" in dependency:                 # the resource pack
            dependency["version"] = list(current)

    save(BP, bp)
    save(RP, rp)
    print("version %s" % ".".join(str(part) for part in current))


if __name__ == "__main__":
    main()
