/**
 * Validate every JSON file in BP/ and RP/ against Mojang's published schemas.
 *
 *   npm install --no-save @minecraft/bedrock-schemas ajv
 *   node tools/validate.mjs
 *
 * Add-on JSON fails silently in game: a malformed file is skipped at load and
 * the block, item or lighting effect simply never appears, with the reason
 * buried in a log most players never open. Running the real schemas over the
 * pack turns those silent no-shows into build-time errors.
 *
 * The file -> schema mapping is read from the schema package's own catalog.json
 * rather than hardcoded here, so it keeps working as Mojang adds folders.
 */

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

function findSchemaRoot() {
  let dir = ROOT;
  for (let depth = 0; depth < 6; depth += 1) {
    const candidate = join(dir, "node_modules", "@minecraft", "bedrock-schemas", "schemas");
    if (existsSync(candidate)) return candidate;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

const SCHEMA_ROOT = findSchemaRoot();
if (!SCHEMA_ROOT) {
  console.error(
    "@minecraft/bedrock-schemas is not installed.\n" +
      "  npm install --no-save @minecraft/bedrock-schemas ajv"
  );
  process.exit(2);
}

let Ajv;
try {
  Ajv = (await import("ajv")).default;
} catch {
  console.error("ajv is not installed.\n  npm install --no-save @minecraft/bedrock-schemas ajv");
  process.exit(2);
}

const ajv = new Ajv({ strict: false, allErrors: true, validateFormats: false });

/** Register every packaged schema under a file:// id so relative $refs resolve. */
function registerSchemas(dir) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      registerSchemas(full);
      continue;
    }
    if (!name.endsWith(".schema.json")) continue;
    const schema = JSON.parse(readFileSync(full, "utf8"));
    schema.$id = pathToFileURL(full).href;
    try {
      ajv.addSchema(schema);
    } catch {
      // A duplicate or malformed schema in the package is not our problem;
      // files that need it will report "could not compile" below.
    }
  }
}
registerSchemas(SCHEMA_ROOT);

/**
 * The published package contains a few $refs pointing at files it does not
 * ship. Register a permissive stub for each so the surrounding schema still
 * compiles and can check everything else in the document.
 */
function stubMissingRefs(dir) {
  const missing = new Set();
  const scan = (node, baseDir) => {
    if (Array.isArray(node)) return node.forEach((child) => scan(child, baseDir));
    if (!node || typeof node !== "object") return;
    for (const [key, value] of Object.entries(node)) {
      if (key === "$ref" && typeof value === "string" && value.startsWith(".")) {
        const target = resolve(baseDir, value);
        if (!existsSync(target)) missing.add(target);
      } else {
        scan(value, baseDir);
      }
    }
  };
  const visit = (current) => {
    for (const name of readdirSync(current)) {
      const full = join(current, name);
      if (statSync(full).isDirectory()) visit(full);
      else if (name.endsWith(".schema.json")) scan(JSON.parse(readFileSync(full, "utf8")), current);
    }
  };
  visit(dir);
  for (const target of missing) {
    try {
      ajv.addSchema({ $id: pathToFileURL(target).href });
    } catch {
      // Already registered.
    }
  }
  return missing.size;
}
const stubbed = stubMissingRefs(SCHEMA_ROOT);

// packType + packFolder -> candidate schema files, straight from the catalog.
const catalog = JSON.parse(readFileSync(join(SCHEMA_ROOT, "catalog.json"), "utf8"));
const byFolder = new Map();
for (const doc of catalog.documents) {
  if (!doc.packFolder || !doc.packType) continue;
  const packDir = doc.packType === "behavior" ? "BP" : doc.packType === "resource" ? "RP" : null;
  if (!packDir) continue;
  const key = `${packDir}/${doc.packFolder}`;
  if (!byFolder.has(key)) byFolder.set(key, []);
  byFolder.get(key).push(join(doc.folder, doc.schemaFile));
}

// A handful of files live at a pack root rather than in a named folder.
const BY_EXACT_PATH = new Map([
  ["BP/manifest.json", ["bp/manifest/index.schema.json"]],
  ["RP/manifest.json", ["rp/manifest/index.schema.json"]],
  ["RP/blocks.json", ["rp/textures/blocks_resource.schema.json"]],
]);

// Where one folder holds several document types, pick by filename.
const BY_FILENAME = new Map([
  ["terrain_texture.json", ["rp/textures/terrain_texture.schema.json"]],
  ["item_texture.json", ["rp/textures/item_texture.schema.json"]],
  ["flipbook_textures.json", ["rp/textures/flipbook_textures.schema.json"]],
  ["languages.json", ["rp/texts/languages.schema.json"]],
]);

function candidatesFor(rel) {
  if (BY_EXACT_PATH.has(rel)) return BY_EXACT_PATH.get(rel);
  const name = basename(rel);
  if (name.endsWith(".texture_set.json")) return ["rp/textures/texture_set.schema.json"];
  if (BY_FILENAME.has(name)) return BY_FILENAME.get(name);
  const parts = rel.split("/");
  // Match the deepest folder first (BP/loot_tables/blocks -> BP/loot_tables).
  for (let depth = parts.length - 1; depth >= 2; depth -= 1) {
    const key = parts.slice(0, depth).join("/");
    if (byFolder.has(key)) return byFolder.get(key);
  }
  const shallow = parts.slice(0, 2).join("/");
  return byFolder.get(shallow) || null;
}

function walk(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (name.endsWith(".json")) out.push(full);
  }
  return out;
}

/**
 * Places where the published schema contradicts Mojang's own documentation or
 * the vanilla packs. Each entry is a warning, not a failure, with the reason
 * recorded so it can be retired when the schema package catches up.
 */
const KNOWN_SCHEMA_DEFECTS = [
  {
    match: /identifier must be boolean/,
    why: "fog/feature-rule identifiers are strings in the docs and in every vanilla pack",
  },
  {
    match: /^\/(modules|dependencies)\/\d+\/version must be string/,
    why: "manifest versions are [major, minor, patch] arrays in every vanilla pack",
  },
  {
    match: /^\/texture_data\/.*\/textures must be array/,
    why: "vanilla terrain_texture.json uses a bare string for single-variant textures",
  },
  {
    match: /minecraft:(display_name|loot) must be object/,
    why: "the schema's own description calls these a loc-string key and a loot table path",
  },
  {
    match: /minecraft:friction must be object/,
    why: "the schema's own description calls this a number in the range 0.0-0.9",
  },
  {
    match: /^\/minecraft:attachable\/description\/(materials|textures|geometry)\/\w+ must be object$/,
    why: "every vanilla attachable maps these names to plain strings (checked against netherite_helmet.json)",
  },
  {
    match: /allowed_faces must be object/,
    why: "the schema's own description calls this a list of face-name strings",
  },
];

/**
 * Schemas in the package that contradict the vanilla packs so broadly that
 * running them produces only noise. Files governed by these are reported as
 * unchecked rather than failing the build.
 */
const UNRELIABLE_SCHEMAS = new Map([
  [
    "rp/models/index.schema.json",
    "types every geometry vector as a Molang string; vanilla .geo.json files use plain numbers",
  ],
]);

function defectFor(error) {
  return KNOWN_SCHEMA_DEFECTS.find((defect) => defect.match.test(error));
}

let checked = 0;
const unreliable = [];
const warned = [];
const unmapped = [];
const uncompilable = [];
const failures = [];

for (const file of [...walk(join(ROOT, "BP")), ...walk(join(ROOT, "RP"))]) {
  const rel = relative(ROOT, file).split("\\").join("/");
  let data;
  try {
    data = JSON.parse(readFileSync(file, "utf8"));
  } catch (err) {
    failures.push({ rel, errors: [`not valid JSON: ${err.message}`] });
    continue;
  }

  const candidates = candidatesFor(rel);
  if (!candidates || candidates.length === 0) {
    unmapped.push(rel);
    continue;
  }

  const unusable = candidates.filter((candidate) => UNRELIABLE_SCHEMAS.has(candidate));
  if (unusable.length === candidates.length) {
    unreliable.push({ rel, why: UNRELIABLE_SCHEMAS.get(unusable[0]) });
    continue;
  }

  const rootKeys = Object.keys(data).filter((key) => key.startsWith("minecraft:"));

  let validated = false;
  let compiled = false;
  let best = null;
  for (const candidate of candidates) {
    const schemaPath = join(SCHEMA_ROOT, candidate);
    if (!existsSync(schemaPath)) continue;
    // A folder can hold several document types (recipes, textures). Skip any
    // schema whose required minecraft: key this document does not have.
    const raw = JSON.parse(readFileSync(schemaPath, "utf8"));
    const wants = (raw.required || []).filter((key) => key.startsWith("minecraft:"));
    if (rootKeys.length && wants.length && !wants.some((key) => key in data)) continue;
    let validate;
    try {
      validate = ajv.getSchema(pathToFileURL(schemaPath).href);
    } catch {
      continue; // Package-internal broken $ref; try the next candidate.
    }
    if (!validate) continue;
    compiled = true;
    if (validate(data)) {
      validated = true;
      break;
    }
    const errors = validate.errors.map((e) => `${e.instancePath || "/"} ${e.message}`);
    if (best === null || errors.length < best.length) best = errors;
  }

  if (!compiled) {
    uncompilable.push(rel);
    continue;
  }
  checked += 1;
  if (validated) continue;
  const errors = [...new Set(best || ["did not match any candidate schema"])];
  const real = errors.filter((error) => !defectFor(error));
  if (real.length === 0) {
    warned.push({ rel, errors });
  } else {
    failures.push({ rel, errors: real });
  }
}

// A manifest header that names a loc key relies on a lookup that does not
// always fire - it shipped once as a literal "pack.name" on screen. Names
// must be literal strings.
for (const manifest of ["BP/manifest.json", "RP/manifest.json"]) {
  const full = join(ROOT, manifest);
  if (!existsSync(full)) continue;
  const header = JSON.parse(readFileSync(full, "utf8")).header ?? {};
  for (const field of ["name", "description"]) {
    if (typeof header[field] === "string" && /^pack\./.test(header[field])) {
      failures.push({
        rel: manifest,
        errors: [`header.${field} is the loc key "${header[field]}" - use a literal string`],
      });
    }
  }
}

console.log(`schema-checked ${checked} file(s)` + (stubbed ? ` (stubbed ${stubbed} broken ref(s) in the schema package)` : ""));
if (unmapped.length) console.log(`  ${unmapped.length} with no schema in the catalog: ${unmapped.join(", ")}`);
if (uncompilable.length) console.log(`  ${uncompilable.length} whose schema the package cannot compile: ${uncompilable.join(", ")}`);
if (unreliable.length) {
  console.log(`  ${unreliable.length} skipped because their schema is unusable:`);
  for (const entry of unreliable) console.log(`    - ${entry.rel} (${entry.why})`);
}

if (warned.length) {
  const grouped = new Map();
  for (const warning of warned) {
    for (const error of warning.errors) {
      const defect = defectFor(error);
      if (!defect) continue;
      if (!grouped.has(defect.why)) grouped.set(defect.why, new Set());
      grouped.get(defect.why).add(warning.rel);
    }
  }
  console.log(`  ${warned.length} file(s) tripped known defects in the schema package:`);
  for (const [why, files] of grouped) {
    console.log(`    - ${why} (${files.size} file${files.size === 1 ? "" : "s"})`);
  }
}

if (failures.length === 0) {
  console.log("no schema violations");
  process.exit(0);
}
for (const failure of failures) {
  console.log(`\n${failure.rel}`);
  for (const error of [...new Set(failure.errors)].slice(0, 15)) console.log(`    ${error}`);
}
console.log(`\n${failures.length} file(s) with problems`);
process.exit(1);
