#!/usr/bin/env bash
# Package BP/ and RP/ into a single .mcaddon for one-tap import on mobile or
# drag-and-drop on desktop.
#
#   ./build_addon.sh            build only
#   ./build_addon.sh --check    run every validator first, and refuse to build
#                               if any of them fails
set -euo pipefail
cd "$(dirname "$0")"

OUT_DIR="dist"
OUT_FILE="$OUT_DIR/EndAscendant.mcaddon"

if [[ "${1:-}" == "--check" ]]; then
  echo "==> Regenerating textures"
  python3 tools/gen_art.py
  echo "==> Regenerating mob action clips"
  python3 tools/gen_mob_actions.py
  echo "==> Checking identifiers"
  node tools/check_ids.mjs
  echo "==> Validating JSON against Mojang schemas"
  node tools/validate.mjs
  echo "==> Running script logic checks"
  node tools/smoketest.mjs
  echo
fi

mkdir -p "$OUT_DIR"
rm -f "$OUT_FILE"

# -X drops platform extras that some importers choke on.
zip -r -q -X "$OUT_FILE" BP RP \
  -x "*.DS_Store" \
  -x "**/__pycache__/*" \
  -x "**/node_modules/*"

echo "Built $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
