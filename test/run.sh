#!/usr/bin/env bash
# Stubs @minecraft/server(-ui) into node_modules/ (gitignored, regenerated
# every run) so the farm modules' real "@minecraft/server" imports resolve
# to the mock in test/mock/, then runs the validator.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p node_modules/@minecraft/server node_modules/@minecraft/server-ui
cp test/mock/minecraft-server.js node_modules/@minecraft/server/index.js
cp test/mock/minecraft-server-ui.js node_modules/@minecraft/server-ui/index.js
cat > node_modules/@minecraft/server/package.json << 'EOF'
{ "name": "@minecraft/server", "version": "0.0.0-mock", "type": "module", "main": "index.js" }
EOF
cat > node_modules/@minecraft/server-ui/package.json << 'EOF'
{ "name": "@minecraft/server-ui", "version": "0.0.0-mock", "type": "module", "main": "index.js" }
EOF

node test/validate_farms.mjs
