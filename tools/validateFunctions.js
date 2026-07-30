import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const BP_FUNCTIONS = join(__dirname, "..", "BP", "functions");

const TILDE = /~-?\d+/;
const FILL_RE = new RegExp(`^fill (${TILDE.source}) (${TILDE.source}) (${TILDE.source}) (${TILDE.source}) (${TILDE.source}) (${TILDE.source}) ([a-z0-9_:]+)(\\[[^\\]]*\\])? ?(hollow|replace|keep|destroy|outline)?$`);
const SET_RE = new RegExp(`^setblock (${TILDE.source}) (${TILDE.source}) (${TILDE.source}) ([a-z0-9_:]+)(\\[[^\\]]*\\])?$`);
const SUMMON_RE = /^summon ([a-z0-9_:]+) (~-?\d+) (~-?\d+) (~-?\d+)$/;
const TELLRAW_RE = /^tellraw @s \{.*\}$/;
const COMMENT_RE = /^#/;

let errors = 0;
let totalLines = 0;
let fillCount = 0;
let setCount = 0;
let summonCount = 0;

function num(tilde) {
  return Number(tilde.slice(1));
}

for (const farm of ["iron_farm", "crop_farm"]) {
  const dir = join(BP_FUNCTIONS, farm);
  for (const file of readdirSync(dir).sort()) {
    const path = join(dir, file);
    const lines = readFileSync(path, "utf8").split("\n").filter((l) => l.length > 0);
    for (const [i, line] of lines.entries()) {
      totalLines++;
      if (COMMENT_RE.test(line) || TELLRAW_RE.test(line)) continue;

      let m;
      if ((m = FILL_RE.exec(line))) {
        fillCount++;
        const [, x1, y1, z1, x2, y2, z2] = m;
        if (num(x1) > num(x2) || num(y1) > num(y2) || num(z1) > num(z2)) {
          console.error(`${farm}/${file}:${i + 1}: fill "from" > "to" — ${line}`);
          errors++;
        }
      } else if ((m = SET_RE.exec(line))) {
        setCount++;
      } else if ((m = SUMMON_RE.exec(line))) {
        summonCount++;
      } else {
        console.error(`${farm}/${file}:${i + 1}: unrecognized command shape — ${line}`);
        errors++;
      }
    }
  }
}

console.log(`Checked ${totalLines} lines: ${fillCount} fill, ${setCount} setblock, ${summonCount} summon.`);
if (errors > 0) {
  console.error(`\n${errors} problem(s) found.`);
  process.exit(1);
} else {
  console.log("All command lines well-formed.");
}
