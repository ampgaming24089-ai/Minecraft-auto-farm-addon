// Loads every farm module against the mock @minecraft/server(-ui) in
// node_modules/@minecraft/ and exercises plan() across all 4 facings and
// every valid level count, checking for thrown errors, malformed
// coordinates, and empty/invalid block ids. This is NOT a substitute for
// real in-game testing (it can't verify vanilla block states, redstone
// timing, or villager AI) — it only catches authoring mistakes that would
// otherwise only surface as a silent failure or crash in-game.
import { IronFarm } from "../BP/scripts/farms/ironFarm.js";
import { CropFarm } from "../BP/scripts/farms/cropFarm.js";
import { GiantCropFarm } from "../BP/scripts/farms/giantCropFarm.js";
import { MobFarm } from "../BP/scripts/farms/mobFarm.js";
import { KelpFarm } from "../BP/scripts/farms/kelpFarm.js";
import { FishFarm } from "../BP/scripts/farms/fishFarm.js";
import { PillagerOutpostFarm } from "../BP/scripts/farms/pillagerOutpostFarm.js";
import { TradingHall } from "../BP/scripts/farms/tradingHall.js";

const FARMS = [IronFarm, CropFarm, GiantCropFarm, MobFarm, KelpFarm, FishFarm, PillagerOutpostFarm, TradingHall];
const FACINGS = ["north", "south", "east", "west"];

let failures = 0;
let checks = 0;

function checkPlacements(farmName, facing, levels, placements) {
  const seen = new Set();
  for (const p of placements) {
    checks++;
    if (![p.x, p.y, p.z].every(Number.isFinite)) {
      console.error(`FAIL ${farmName} facing=${facing} levels=${levels}: non-finite coordinate`, p);
      failures++;
    }
    if (typeof p.id !== "string" || !p.id.includes(":")) {
      console.error(`FAIL ${farmName} facing=${facing} levels=${levels}: bad block id`, p);
      failures++;
    }
    const key = `${p.x},${p.y},${p.z}`;
    seen.add(key);
  }
}

for (const farm of FARMS) {
  const maxLevels = farm.fixedLevels ?? farm.maxLevels ?? 1;
  const levelOptions = farm.fixedLevels ? [farm.fixedLevels] : Array.from({ length: maxLevels }, (_, i) => i + 1);

  for (const facing of FACINGS) {
    for (const levels of levelOptions) {
      checks++;
      try {
        const { placements, spawns, fills } = farm.plan({ levels, facing });
        if (!Array.isArray(placements) || placements.length === 0) {
          console.error(`FAIL ${farm.id} facing=${facing} levels=${levels}: no placements returned`);
          failures++;
          continue;
        }
        checkPlacements(farm.id, facing, levels, placements);
        for (const s of spawns ?? []) {
          if (![s.x, s.y, s.z].every(Number.isFinite) || typeof s.typeId !== "string") {
            console.error(`FAIL ${farm.id} facing=${facing} levels=${levels}: bad spawn`, s);
            failures++;
          }
        }
        for (const f of fills ?? []) {
          if (![f.x, f.y, f.z].every(Number.isFinite) || typeof f.itemId !== "string") {
            console.error(`FAIL ${farm.id} facing=${facing} levels=${levels}: bad fill`, f);
            failures++;
          }
        }
      } catch (err) {
        console.error(`FAIL ${farm.id} facing=${facing} levels=${levels}: threw`, err);
        failures++;
      }
    }
  }
}

console.log(`Checked ${FARMS.length} farm modules, ${checks} checks run.`);
if (failures > 0) {
  console.error(`${failures} FAILURES`);
  process.exit(1);
} else {
  console.log("All farm modules planned successfully across all facings/levels.");
}
