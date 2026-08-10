#!/usr/bin/env bash
# Packages BP/ and RP/ into .mcpack files plus a combined .mcaddon.
# Usage: ./build_addon.sh [output_dir]  (defaults to ./dist)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$ROOT/dist}"
NAME="HallowDimensionV2"

# Gate the build on the validator. Several rounds of this addon shipped with
# bugs a static check would have caught (a script event name that does not
# exist, a food component shape that silently voided the whole item), so a
# pack that fails validation must not get packaged. Set SKIP_VALIDATE=1 to
# bypass deliberately.
if [ "${SKIP_VALIDATE:-0}" != "1" ]; then
  echo "Validating..."
  python3 "$ROOT/tools/validate.py" || {
    echo "Validation failed - refusing to build. (SKIP_VALIDATE=1 to override.)" >&2
    exit 1
  }
fi

rm -rf "$OUT"
mkdir -p "$OUT"

pack_dir() {
  local src="$1" dest="$2"
  (cd "$src" && zip -r -X -q "$dest" . -x '.*')
}

pack_dir "$ROOT/BP" "$OUT/${NAME}_BP.mcpack"
pack_dir "$ROOT/RP" "$OUT/${NAME}_RP.mcpack"

TMP="$(mktemp -d)"
mkdir -p "$TMP/BP" "$TMP/RP"
cp -r "$ROOT/BP/." "$TMP/BP/"
cp -r "$ROOT/RP/." "$TMP/RP/"
(cd "$TMP" && zip -r -X -q "$OUT/${NAME}.mcaddon" BP RP -x '.*')
rm -rf "$TMP"

echo "Built:"
ls -lh "$OUT"
echo
echo "Import ${NAME}.mcaddon on a device with Minecraft Bedrock installed"
echo "(or copy the BP/RP folders straight into com.mojang/development_*_packs)."
