import { world } from "@minecraft/server";

/** Small JSON-backed dynamic property helpers. Dynamic properties only
 * store primitives, so anything structured is JSON-serialised. Kept in one
 * place so the rest of the codebase never touches raw dynamic property
 * calls directly. */

export function getWorldFlag(key, fallback = false) {
  const v = world.getDynamicProperty(key);
  return v === undefined ? fallback : v;
}

export function setWorldFlag(key, value) {
  world.setDynamicProperty(key, value);
}

export function getWorldJson(key, fallback) {
  const raw = world.getDynamicProperty(key);
  if (typeof raw !== "string") return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function setWorldJson(key, value) {
  world.setDynamicProperty(key, JSON.stringify(value));
}

export function getPlayerJson(player, key, fallback) {
  const raw = player.getDynamicProperty(key);
  if (typeof raw !== "string") return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function setPlayerJson(player, key, value) {
  player.setDynamicProperty(key, JSON.stringify(value));
}

export const KEYS = {
  VILLAGE_BUILT: "hollowveil:village_built",
  VILLAGE_SHRINE_POS: "hollowveil:village_shrine_pos",
  ARRIVAL_BUILT: "hollowveil:arrival_built",
  BOSSES_DEFEATED: "hollowveil:bosses_defeated",
  BOSS_COOLDOWN: "hollowveil:boss_cooldown",
  QUEST_STAGE: "hollowveil:quest_stage",
  RETURN_POS: "hollowveil:return_pos",
  PORTAL_COOLDOWN: "hollowveil:portal_cooldown",
  ALTAR_POSITIONS: "hollowveil:altar_positions",
  SPAWNER_POSITIONS: "hollowveil:spawner_positions",
  BUILT_SECTORS: "hollowveil:built_sectors",
  SITES: "hollowveil:sites",
  BUILT_SITES: "hollowveil:built_sites",
  CURRENT_BIOME: "hollowveil:current_biome",
};

export function bossesDefeated() {
  return getWorldJson(KEYS.BOSSES_DEFEATED, []);
}

export function markBossDefeated(bossId) {
  const list = bossesDefeated();
  if (!list.includes(bossId)) {
    list.push(bossId);
    setWorldJson(KEYS.BOSSES_DEFEATED, list);
  }
  return list;
}

export function questStage(player) {
  return getPlayerJson(player, KEYS.QUEST_STAGE, 0);
}

export function setQuestStage(player, stage) {
  const cur = questStage(player);
  if (stage > cur) setPlayerJson(player, KEYS.QUEST_STAGE, stage);
}
