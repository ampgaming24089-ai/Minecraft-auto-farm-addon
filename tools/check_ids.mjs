/**
 * Verify every game identifier the pack references actually exists.
 *
 *   npm install --no-save @minecraft/vanilla-data
 *   node tools/check_ids.mjs
 *
 * A wrong vanilla id is the most common way an add-on breaks quietly: the
 * block is simply not placed, the recipe never appears, the loot slot comes up
 * empty, and nothing in game says why. Bedrock also does not use the same names
 * as Java - end stone bricks are `minecraft:end_bricks` here - so a name that
 * looks obviously right can still be wrong.
 *
 * This walks every JSON value and every JS string literal in the pack,
 * pulls out namespaced identifiers, and checks vanilla ones against Mojang's
 * published id lists and voidbound ones against what this pack defines.
 */

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const require = createRequire(import.meta.url);

let vanilla;
try {
  vanilla = require("@minecraft/vanilla-data");
} catch {
  console.error(
    "@minecraft/vanilla-data is not installed.\n" +
      "  npm install --no-save @minecraft/vanilla-data"
  );
  process.exit(2);
}

/** Union of every vanilla id list the package publishes. */
const VANILLA = new Set();
for (const [name, table] of Object.entries(vanilla)) {
  if (!name.startsWith("Minecraft") || typeof table !== "object") continue;
  for (const value of Object.values(table)) {
    if (typeof value === "string") VANILLA.add(value);
  }
}

/**
 * Vanilla strings that are namespaced but are not entity/block/item ids, so
 * they never appear in the published id lists. Each is a real engine name.
 */
const KNOWN_NON_ID = new Set([
  // Built-in block geometry and rendering.
  "minecraft:geometry.full_block",
  "minecraft:geometry.full_block_v1",
  "minecraft:geometry.cross",
  // Vanilla Vibrant Visuals and fog definitions we point at deliberately.
  "minecraft:default_water",
  "minecraft:default_color_grading",
  "minecraft:end_lighting",
  "minecraft:end_atmospherics",
  "minecraft:fog_the_end",
  // Component and particle names, which are namespaced but are not content ids.
  "minecraft:inventory",
  "minecraft:equippable",
  "minecraft:endrod",
]);

function walk(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else out.push(full);
  }
  return out;
}

/** Identifiers this pack defines, gathered from its own definition files. */
function packDefinitions() {
  const defined = new Set();
  const add = (value) => {
    if (typeof value === "string") defined.add(value);
  };

  const readIdentifier = (file, ...path) => {
    let node = JSON.parse(readFileSync(file, "utf8"));
    for (const step of path) {
      node = node?.[step];
      if (node === undefined) return;
    }
    add(node);
  };

  for (const file of walk(join(ROOT, "BP", "blocks"))) {
    readIdentifier(file, "minecraft:block", "description", "identifier");
  }
  for (const file of walk(join(ROOT, "BP", "items"))) {
    readIdentifier(file, "minecraft:item", "description", "identifier");
  }
  for (const file of walk(join(ROOT, "BP", "entities"))) {
    readIdentifier(file, "minecraft:entity", "description", "identifier");
  }
  for (const file of walk(join(ROOT, "BP", "features"))) {
    const data = JSON.parse(readFileSync(file, "utf8"));
    for (const [key, body] of Object.entries(data)) {
      if (key.startsWith("minecraft:")) add(body?.description?.identifier);
    }
  }
  for (const file of walk(join(ROOT, "BP", "feature_rules"))) {
    readIdentifier(file, "minecraft:feature_rules", "description", "identifier");
  }
  for (const folder of ["fogs", "lighting", "atmospherics", "color_grading"]) {
    for (const file of walk(join(ROOT, "RP", folder))) {
      const data = JSON.parse(readFileSync(file, "utf8"));
      for (const [key, body] of Object.entries(data)) {
        if (key.startsWith("minecraft:")) add(body?.description?.identifier);
      }
    }
  }
  for (const file of walk(join(ROOT, "BP", "recipes"))) {
    const data = JSON.parse(readFileSync(file, "utf8"));
    for (const [key, body] of Object.entries(data)) {
      if (key.startsWith("minecraft:recipe")) add(body?.description?.identifier);
    }
  }
  return defined;
}

const DEFINED = packDefinitions();

/** Namespaced identifier, as it appears in a value or a string literal. */
const ID_PATTERN = /^(minecraft|voidbound):[a-z0-9_]+$/;

function collectFromJson(node, sink) {
  if (typeof node === "string") {
    if (ID_PATTERN.test(node)) sink.add(node);
    return;
  }
  if (Array.isArray(node)) {
    for (const child of node) collectFromJson(child, sink);
    return;
  }
  if (node && typeof node === "object") {
    // Keys are component names, not identifiers - only values are checked.
    for (const value of Object.values(node)) collectFromJson(value, sink);
  }
}

const STRING_LITERAL = /(["'`])((?:\\.|(?!\1)[^\\])*)\1/g;

function collectFromScript(source, sink) {
  for (const match of source.matchAll(STRING_LITERAL)) {
    const value = match[2];
    if (ID_PATTERN.test(value)) sink.add(value);
  }
}

const references = new Map(); // id -> Set of files

function record(id, file) {
  if (!references.has(id)) references.set(id, new Set());
  references.get(id).add(relative(ROOT, file).split("\\").join("/"));
}

for (const file of [...walk(join(ROOT, "BP")), ...walk(join(ROOT, "RP"))]) {
  const found = new Set();
  if (file.endsWith(".json")) {
    try {
      collectFromJson(JSON.parse(readFileSync(file, "utf8")), found);
    } catch {
      continue; // The schema validator reports malformed JSON.
    }
  } else if (file.endsWith(".js")) {
    collectFromScript(readFileSync(file, "utf8"), found);
  } else {
    continue;
  }
  for (const id of found) record(id, file);
}

const problems = [];
for (const [id, files] of [...references].sort()) {
  if (KNOWN_NON_ID.has(id)) continue;
  if (id.startsWith("voidbound:")) {
    if (!DEFINED.has(id)) {
      problems.push({ id, files, why: "not defined anywhere in this pack" });
    }
    continue;
  }
  if (!VANILLA.has(id)) {
    problems.push({ id, files, why: "not a known vanilla identifier" });
  }
}

console.log(
  `checked ${references.size} distinct identifier(s) ` +
    `against ${VANILLA.size} vanilla ids and ${DEFINED.size} pack definitions`
);

if (problems.length === 0) {
  console.log("every referenced identifier resolves");
  process.exit(0);
}
for (const problem of problems) {
  console.log(`\n${problem.id}  (${problem.why})`);
  for (const file of problem.files) console.log(`    ${file}`);
}
console.log(`\n${problems.length} unresolved identifier(s)`);
process.exit(1);
