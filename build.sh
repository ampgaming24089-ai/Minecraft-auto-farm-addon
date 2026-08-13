#!/usr/bin/env bash
# Packages the three Aurora packs into a single .mcaddon for one-tap import on
# mobile, or drag-and-drop on desktop. Also emits each pack as a standalone
# .mcpack for anyone who only wants one of the three.
set -euo pipefail
cd "$(dirname "$0")"

OUT_DIR="dist"
BUNDLE="$OUT_DIR/Aurora.mcaddon"
PACKS=(aurora_visuals aurora_ui aurora_animations)

command -v zip >/dev/null || { echo "error: 'zip' is required" >&2; exit 1; }

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# A .mcaddon is a zip holding one folder per pack, each with its own manifest.
( cd packs && zip -r -X -q "../$BUNDLE" "${PACKS[@]}" \
    -x "*.DS_Store" -x "**/__pycache__/*" )
echo "built $BUNDLE"

# Standalone single-pack imports; contents sit at the archive root.
for pack in "${PACKS[@]}"; do
  ( cd "packs/$pack" && zip -r -X -q "../../$OUT_DIR/${pack}.mcpack" . \
      -x "*.DS_Store" -x "**/__pycache__/*" )
  echo "built $OUT_DIR/${pack}.mcpack"
done
