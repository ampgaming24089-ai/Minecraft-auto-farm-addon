#!/usr/bin/env bash
# Packages BP/ and RP/ into a single .mcaddon for one-tap import on mobile,
# or drag-and-drop import on desktop.
set -euo pipefail
cd "$(dirname "$0")"

OUT_DIR="dist"
OUT_FILE="$OUT_DIR/AutoFarmAddon.mcaddon"

mkdir -p "$OUT_DIR"
rm -f "$OUT_FILE"

zip -r -X "$OUT_FILE" BP RP \
  -x "*.DS_Store" \
  -x "**/__pycache__/*"

echo "Built $OUT_FILE"
