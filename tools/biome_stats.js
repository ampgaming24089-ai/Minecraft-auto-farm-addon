/**
 * Samples the biome field across the whole world and reports the split, plus
 * how far you typically walk before the biome changes.
 *
 * Biome choice is pure maths on coordinates - no world state - so it can be
 * measured exactly here instead of guessed at from screenshots. This is how
 * the earlier 50/37/8/4 split was caught (a single bucketed noise field), and
 * how BIOME_CELL was chosen when the world grew to 50,000.
 *
 *   node tools/biome_stats.js
 */
import { biomeAt, WORLD_RADIUS } from "../BP/scripts/world/biomes.js";

const counts = new Map();
let samples = 0;
const STEP = 137;                       // a prime, so the grid never aligns
for (let x = -WORLD_RADIUS; x < WORLD_RADIUS; x += STEP * 7) {
  for (let z = -WORLD_RADIUS; z < WORLD_RADIUS; z += STEP * 7) {
    if (Math.hypot(x, z) >= WORLD_RADIUS) continue;
    const id = biomeAt(x, z).id;
    counts.set(id, (counts.get(id) ?? 0) + 1);
    samples++;
  }
}
console.log(`biome split over ${samples.toLocaleString()} samples:`);
for (const [id, n] of [...counts].sort((a, b) => b[1] - a[1])) {
  console.log(`  ${id.padEnd(10)} ${((n / samples) * 100).toFixed(1)}%`);
}

// How far a straight walk goes before the ground changes underfoot.
const runs = [];
for (let trial = 0; trial < 40; trial++) {
  const z = -WORLD_RADIUS + 500 + trial * 2000;
  let last = null, run = 0;
  for (let x = -20000; x < 20000; x += 16) {
    const id = biomeAt(x, z).id;
    if (id === last) { run += 16; continue; }
    if (last !== null) runs.push(run);
    last = id; run = 16;
  }
}
runs.sort((a, b) => a - b);
const median = runs[Math.floor(runs.length / 2)];
console.log(`\nmedian unbroken stretch of one biome: ${median} blocks`);
console.log(`longest: ${runs[runs.length - 1]} blocks`);
