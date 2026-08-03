import { world, system } from "@minecraft/server";
import { ActionFormData, ModalFormData } from "@minecraft/server-ui";
import { get4DirFacing, computeBounds } from "./lib/geometry.js";
import { placeAll, spawnAll, fillContainers } from "./lib/builder.js";
import { showOutline, clearOutline } from "./lib/outline.js";
import { registerAutoFishingRod } from "./lib/autoFishingRod.js";
import { registerVillagerManager } from "./lib/villagerManager.js";
import { IronFarm } from "./farms/ironFarm.js";
import { IronGolemFarm } from "./farms/ironGolemFarm.js";
import { CropFarm } from "./farms/cropFarm.js";
import { GiantCropFarm } from "./farms/giantCropFarm.js";
import { MobFarm } from "./farms/mobFarm.js";
import { KelpFarm } from "./farms/kelpFarm.js";
import { FishFarm } from "./farms/fishFarm.js";
import { PillagerOutpostFarm } from "./farms/pillagerOutpostFarm.js";
import { TradingHall } from "./farms/tradingHall.js";

const TOOL_ID = "autofarm:build_tool";
const FARMS = [
  IronFarm,
  IronGolemFarm,
  CropFarm,
  GiantCropFarm,
  KelpFarm,
  MobFarm,
  FishFarm,
  PillagerOutpostFarm,
  TradingHall,
];

registerAutoFishingRod(world);
registerVillagerManager(world);

/** Players currently inside the menu/preview/build flow, so the tool can't be re-triggered mid-flow. */
const busyPlayers = new Set();

// itemUse fires on every "use held item" action regardless of what's being
// looked at, unlike playerInteractWithBlock, which mobile touch controls
// only seem to dispatch for blocks the game already treats as interactive
// (chests, doors, etc). We raycast for the targeted block ourselves so
// plain terrain works too.
world.afterEvents.itemUse.subscribe((event) => {
  const { source: player, itemStack } = event;
  if (itemStack.typeId !== TOOL_ID) return;
  if (busyPlayers.has(player.id)) return;

  const hit = player.getBlockFromViewDirection({ maxDistance: 8 });
  if (!hit) {
    player.sendMessage("§cLook at a block within 8 blocks, then use the tool again.");
    return;
  }
  const block = hit.block;

  const facing = get4DirFacing(player.getViewDirection());
  const origin = { x: block.location.x, y: block.location.y + 1, z: block.location.z };

  busyPlayers.add(player.id);
  openFarmMenu(player, origin, facing).catch((err) => {
    console.warn(`[AutoFarm] menu flow error: ${err}`);
    busyPlayers.delete(player.id);
  });
});

/** @param {import("@minecraft/server").Player} player */
async function openFarmMenu(player, origin, facing) {
  const form = new ActionFormData()
    .title("Auto Farm Builder")
    .body("Choose a farm to instantly build. You'll see an outline preview before anything is placed.");
  for (const farm of FARMS) form.button(farm.name);

  const response = await form.show(player);
  if (response.canceled || response.selection === undefined) {
    busyPlayers.delete(player.id);
    return;
  }

  const farm = FARMS[response.selection];
  if (farm.fixedLevels) {
    await confirmAndBuild(player, origin, facing, farm, farm.fixedLevels, true);
    return;
  }
  await openLevelMenu(player, origin, facing, farm);
}

/** @param {import("@minecraft/server").Player} player */
async function openLevelMenu(player, origin, facing, farm) {
  const form = new ModalFormData()
    .title(farm.name)
    .slider(farm.levelLabel ?? "Stack height (levels)", 1, farm.maxLevels, { valueStep: 1, defaultValue: farm.maxLevels })
    .toggle("Show outline preview before building", { defaultValue: true });

  const response = await form.show(player);
  if (response.canceled || !response.formValues) {
    busyPlayers.delete(player.id);
    return;
  }

  const [levels, showPreview] = response.formValues;
  await confirmAndBuild(player, origin, facing, farm, levels, showPreview);
}

/** @param {import("@minecraft/server").Player} player */
async function confirmAndBuild(player, origin, facing, farm, levels, showPreview) {
  const bounds = computeBounds(origin, farm.size, levels, farm.levelSpacing, facing, farm.stackAxis ?? "y");

  if (showPreview) {
    showOutline(player, bounds.min, bounds.max);
  }

  const width = bounds.max.x - bounds.min.x + 1;
  const height = bounds.max.y - bounds.min.y + 1;
  const depth = bounds.max.z - bounds.min.z + 1;

  const unitNoun = farm.unitNoun ?? "Level";
  const form = new ActionFormData()
    .title(`Confirm: ${farm.name}`)
    .body(
      `${farm.shortDescription}\n\n` +
        `${unitNoun}s: ${levels}\n` +
        `Footprint: ${width} x ${depth}\n` +
        `Height: ${height}\n\n` +
        (showPreview ? "The outline is now visible in the world. " : "") +
        "This will instantly place blocks and spawn mobs. No commands or cheats are used, so achievements stay enabled."
    )
    .button("Build!")
    .button("Cancel");

  const response = await form.show(player);
  clearOutline(player);

  if (response.canceled || response.selection !== 0) {
    busyPlayers.delete(player.id);
    if (!response.canceled) {
      player.sendMessage("§7Auto Farm build canceled.");
    }
    return;
  }

  runBuild(player, origin, facing, farm, levels);
}

function runBuild(player, origin, facing, farm, levels) {
  const dimension = player.dimension;
  const { placements, spawns, fills } = farm.plan({ levels, facing });

  const unitNoun = (farm.unitNoun ?? "level").toLowerCase();
  player.sendMessage(`§aBuilding ${farm.name} (${levels} ${unitNoun}${levels > 1 ? "s" : ""})...`);

  system.runJob(
    buildJob(dimension, origin, facing, placements, spawns, fills ?? [], player)
  );
}

function* buildJob(dimension, origin, facing, placements, spawns, fills, player) {
  yield* placeAll(dimension, origin, placements, facing, 300, (done, total) => {
    try {
      player.onScreenDisplay.setActionBar(`§bPlacing blocks: ${done}/${total}`);
    } catch {
      // Player may have logged off mid-build — the job continues regardless.
    }
  });
  if (fills.length > 0) {
    try {
      player.onScreenDisplay.setActionBar("§bStocking fuel...");
    } catch {
      // Ignore — cosmetic only.
    }
    yield* fillContainers(dimension, origin, fills, facing);
  }
  try {
    player.onScreenDisplay.setActionBar("§bSpawning mobs...");
  } catch {
    // Ignore — cosmetic only.
  }
  yield* spawnAll(dimension, origin, spawns, facing);

  busyPlayers.delete(player.id);
  try {
    player.onScreenDisplay.setTitle("§aBuild Complete!", {
      subtitle: "Collection is all in one place — check the shared chest.",
      fadeInDuration: 10,
      stayDuration: 100,
      fadeOutDuration: 20,
    });
    player.sendMessage("§aAuto Farm build complete!");
    player.playSound("random.levelup");
  } catch {
    // Player may be gone — nothing left to notify.
  }
}
