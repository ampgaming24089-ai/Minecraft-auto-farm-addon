import { world } from "@minecraft/server";
import { KEYS, getWorldJson, setWorldJson } from "../lib/state.js";

const BOSS_COOLDOWN_TICKS = 24000; // 20 minutes real-time, set the instant a chamber is used

const BOSSES = {
  hollow_king: {
    entity: "hollowveil:hollow_king",
    label: "The Hollow King",
    floor: "hollowveil:bonestone",
    wall: "minecraft:deepslate_bricks",
    pillar: "hollowveil:soulforged_obsidian",
    accent: "hollowveil:soul_lantern",
  },
  weeping_widow: {
    entity: "hollowveil:weeping_widow",
    label: "The Weeping Widow",
    floor: "minecraft:dark_oak_planks",
    wall: "minecraft:blackstone",
    pillar: "minecraft:polished_blackstone",
    accent: "minecraft:cobweb",
  },
  malacoda: {
    entity: "hollowveil:malacoda",
    label: "Malacoda, the Ashen Demon",
    floor: "minecraft:polished_blackstone_bricks",
    wall: "minecraft:blackstone",
    pillar: "minecraft:magma_block",
    accent: "minecraft:soul_fire_torch",
  },
};

export function bossIdFromSigil(itemId) {
  const m = /^hollowveil:sigil_(.+)$/.exec(itemId ?? "");
  if (!m) return null;
  return BOSSES[m[1]] ? m[1] : null;
}

function cooldowns() {
  return getWorldJson(KEYS.BOSS_COOLDOWN, {});
}

export function isBossOnCooldown(bossId, currentTick) {
  const map = cooldowns();
  return (map[bossId] ?? 0) > currentTick;
}

function setCooldown(bossId, currentTick) {
  const map = cooldowns();
  map[bossId] = currentTick + BOSS_COOLDOWN_TICKS;
  setWorldJson(KEYS.BOSS_COOLDOWN, map);
}

/** Clears and rebuilds a themed room around `origin` (the altar), then
 * spawns the boss at its centre. See docs/STRUCTURES.md. */
export function buildChamberAndSpawn(dimension, origin, bossId, currentTick) {
  const cfg = BOSSES[bossId];
  if (!cfg) return false;
  const { x, y, z } = origin;
  const r = 8;
  const run = (cmd) => dimension.runCommandAsync(cmd);

  run(`fill ${x - r} ${y} ${z - r} ${x + r} ${y + 8} ${z + r} air`);
  run(`fill ${x - r} ${y - 1} ${z - r} ${x + r} ${y - 1} ${z + r} ${cfg.floor}`);
  run(`fill ${x - r} ${y} ${z - r} ${x + r} ${y + 8} ${z - r} ${cfg.wall}`);
  run(`fill ${x - r} ${y} ${z + r} ${x + r} ${y + 8} ${z + r} ${cfg.wall}`);
  run(`fill ${x - r} ${y} ${z - r} ${x - r} ${y + 8} ${z + r} ${cfg.wall}`);
  run(`fill ${x + r} ${y} ${z - r} ${x + r} ${y + 8} ${z + r} ${cfg.wall}`);
  run(`fill ${x - r} ${y + 9} ${z - r} ${x + r} ${y + 9} ${z + r} ${cfg.wall}`);
  // keep the altar itself standing at the entrance
  run(`setblock ${x} ${y - 1} ${z} hollowveil:ritual_altar`);

  const corners = [
    { cx: x - r + 2, cz: z - r + 2 },
    { cx: x + r - 2, cz: z - r + 2 },
    { cx: x - r + 2, cz: z + r - 2 },
    { cx: x + r - 2, cz: z + r - 2 },
  ];
  for (const { cx, cz } of corners) {
    run(`fill ${cx} ${y} ${cz} ${cx} ${y + 4} ${cz} ${cfg.pillar}`);
    run(`setblock ${cx} ${y + 5} ${cz} ${cfg.accent}`);
  }

  // A doorway. The chamber used to be a sealed box: four walls, a ceiling and
  // no opening anywhere, so winning the fight left the player walled inside a
  // 17x17 room with nothing to do but mine out. Two blocks of the north wall
  // come back out, lit on both sides so it reads as a door rather than damage.
  run(`fill ${x - 1} ${y} ${z - r} ${x + 1} ${y + 2} ${z - r} air`);
  run(`setblock ${x - 2} ${y + 2} ${z - r} ${cfg.accent}`);
  run(`setblock ${x + 2} ${y + 2} ${z - r} ${cfg.accent}`);

  // The boss goes at the far side of the arena, not on top of the altar the
  // player is standing at - spawning it in their face gave away the opening
  // seconds of every fight.
  const spawnAt = { x, y, z: z + r - 3 };
  try {
    const boss = dimension.spawnEntity(cfg.entity, spawnAt);
    boss.nameTag = cfg.label;
  } catch {
    /* if the spawn point is somehow obstructed, the chamber is still built
     * and usable - the altar cooldown below prevents a silent soft-lock */
  }
  setCooldown(bossId, currentTick);
  return true;
}

export function bossLabel(bossId) {
  return BOSSES[bossId]?.label ?? bossId;
}

export function allBossIds() {
  return Object.keys(BOSSES);
}

/** Called from main.js's itemUseOn handler when a player uses a sigil on a
 * hollowveil:ritual_altar block. */
export function useSigilOnAltar(player, dimension, blockPos, sigilItemId, currentTick) {
  const bossId = bossIdFromSigil(sigilItemId);
  if (!bossId) return false;
  if (isBossOnCooldown(bossId, currentTick)) {
    player.sendMessage(`§7${bossLabel(bossId)} is not ready to be summoned yet.`);
    return false;
  }
  const origin = { x: blockPos.x, y: blockPos.y + 1, z: blockPos.z };
  const ok = buildChamberAndSpawn(dimension, origin, bossId, currentTick);
  if (ok) {
    player.sendMessage(`§5${bossLabel(bossId)} rises to meet you.`);
  }
  return ok;
}
