import { world, system } from "@minecraft/server";
import { ActionFormData, ModalFormData } from "@minecraft/server-ui";
import { get4DirFacing, computeBounds } from "./lib/geometry.js";
import { placeAll, spawnAll } from "./lib/builder.js";
import { showOutline, clearOutline } from "./lib/outline.js";
import { IronFarm } from "./farms/ironFarm.js";
import { CropFarm } from "./farms/cropFarm.js";

const TOOL_ID = "autofarm:build_tool";
const FARMS = [IronFarm, CropFarm];

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
  await openLevelMenu(player, origin, facing, farm);
}

/** @param {import("@minecraft/server").Player} player */
async function openLevelMenu(player, origin, facing, farm) {
  const form = new ModalFormData()
    .title(farm.name)
    .slider("Stack height (levels)", 1, farm.maxLevels, { valueStep: 1, defaultValue: farm.maxLevels })
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
  const bounds = computeBounds(origin, farm.size, levels, farm.levelSpacing, facing);

  if (showPreview) {
    showOutline(player, bounds.min, bounds.max);
  }

  const width = bounds.max.x - bounds.min.x + 1;
  const height = bounds.max.y - bounds.min.y + 1;
  const depth = bounds.max.z - bounds.min.z + 1;

  const form = new ActionFormData()
    .title(`Confirm: ${farm.name}`)
    .body(
      `${farm.shortDescription}\n\n` +
        `Levels: ${levels}\n` +
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
  const { placements, spawns } = farm.plan({ levels, facing });

  player.sendMessage(`§aBuilding ${farm.name} (${levels} level${levels > 1 ? "s" : ""})...`);

  system.runJob(
    buildJob(dimension, origin, facing, placements, spawns, player)
  );
}

function* buildJob(dimension, origin, facing, placements, spawns, player) {
  yield* placeAll(dimension, origin, placements, facing, 80, (done, total) => {
    try {
      player.onScreenDisplay.setActionBar(`§bPlacing blocks: ${done}/${total}`);
    } catch {
      // Player may have logged off mid-build — the job continues regardless.
    }
  });
  try {
    player.onScreenDisplay.setActionBar("§bSpawning villagers...");
  } catch {
    // Ignore — cosmetic only.
  }
  yield* spawnAll(dimension, origin, spawns, facing);

  busyPlayers.delete(player.id);
  try {
    player.sendMessage("§aAuto Farm build complete!");
    player.playSound("random.levelup");
  } catch {
    // Player may be gone — nothing left to notify.
  }
}
