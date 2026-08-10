import { ActionFormData, MessageFormData } from "@minecraft/server-ui";
import { bossesDefeated } from "../lib/state.js";

const ICON = "textures/items/";

const CHAPTERS = [
  {
    id: "into_the_grey",
    title: "1. Into the Grey",
    icon: ICON + "journal",
    body:
      "You've crossed into the Hollow Veil - a grey country stitched between " +
      "the living world and whatever comes after. Find Hollow Hamlet and speak " +
      "with the Occultist at the shrine; they're the only living authority left " +
      "out here.",
    always: true,
  },
  {
    id: "proof_of_passage",
    title: "2. Proof of Passage",
    icon: ICON + "soul_shard",
    body:
      "Soul Shards and Ember Dust prove you can survive the Veil's wildlife. " +
      "Bring some to the Occultist's shop to unlock better goods.",
    always: true,
  },
  {
    id: "three_wardens",
    title: "3. The Three Wardens",
    icon: ICON + "sigil_hollow_king",
    body:
      "Three guardians of the old crossing were corrupted when something broke " +
      "through: the Hollow King (Sunken Crypt), the Weeping Widow (Widow's " +
      "Hollow), and Malacoda (Cinder Bastion). Craft each Warden's Sigil and " +
      "use it on a Ritual Altar to challenge them - defeating one drops their " +
      "unique weapon and a full armour set, and restores a piece of the Veil. " +
      "Sigils aren't one-time keys: gather more of the same materials, craft " +
      "another, and a Warden can be summoned and fought again once its altar " +
      "has settled.",
    always: true,
  },
  {
    id: "hollow_king",
    title: "Sunken Crypt - the Hollow King",
    icon: ICON + "hollow_kings_reaper",
    body: "A spectral king who hoarded the memories of the dead until they curdled into rage. Reward: Hollow King's Reaper + Spectral Regalia.",
    bossId: "hollow_king",
  },
  {
    id: "weeping_widow",
    title: "Widow's Hollow - the Weeping Widow",
    icon: ICON + "wailing_edge",
    body: "Her lullabies once eased the crossing; now they shatter minds. Reward: Wailing Edge + Mourner's Shroud.",
    bossId: "weeping_widow",
  },
  {
    id: "malacoda",
    title: "Cinder Bastion - Malacoda",
    icon: ICON + "malacodas_fang",
    body: "The Warden who opened the door that should have stayed shut, burned down into the shape of a demon. Reward: Malacoda's Fang + Ashen Demonplate.",
    bossId: "malacoda",
  },
  {
    id: "territories",
    title: "The Four Territories",
    icon: ICON + "veilsteel_ore",
    body:
      "Beyond the Hamlet: the Ashlands and Ember Bastion (Malacoda's heat, " +
      "Bastion Sentinels guarding old waystation vaults), Boneyard Marsh " +
      "(Bonehide Elk, Glimmershroom Toads - the one territory that still " +
      "feels a little alive), and the Sunken Ruins and Sunken City " +
      "(Wraithguards, Ashwing Bats roosting in drowned towers). Each has " +
      "its own materials, its own dangers.",
    always: true,
  },
  {
    id: "dragons",
    title: "Veil Dragons",
    icon: ICON + "dragon_egg",
    body:
      "Not Wardens, not corrupted, not native to the crossing at all. An egg " +
      "turns up sometimes where a Wraithguard falls. Feed a hatchling Ember " +
      "Fruit or Veil Marrow Stew until it trusts you, then ride it anywhere " +
      "in the Veil. They come in every color the Veil has ever worn.",
    always: true,
  },
  {
    id: "what_opened_the_door",
    title: "What Opened the Door",
    icon: ICON + "spectral_dust",
    body:
      "With all three Wardens fallen, the Occultist finally admits what they've " +
      "long suspected: Malacoda didn't act alone, and the door is still ajar. " +
      "...the Hollow Veil isn't finished with you yet.",
    requiresAll: true,
  },
];

export function openJournal(player) {
  const defeated = bossesDefeated();
  const form = new ActionFormData()
    .title("§l§5Hollow Veil Journal")
    .body(`§7A record of everything you've learned in the Veil.\n§7Wardens defeated: §e${defeated.length}§7/3`);

  const visible = CHAPTERS.filter((c) => {
    if (c.always) return true;
    if (c.bossId) return true; // always listed, but marked locked/complete below
    if (c.requiresAll) return defeated.length >= 3;
    return true;
  });

  for (const c of visible) {
    const done = c.bossId ? defeated.includes(c.bossId) : false;
    const prefix = c.bossId ? (done ? "§a[Defeated] " : "§c[Unclaimed] ") : "§e";
    form.button(prefix + c.title, c.icon);
  }

  form.show(player).then((res) => {
    if (res.canceled || res.selection === undefined) return;
    const chapter = visible[res.selection];
    if (!chapter) return;
    showChapter(player, chapter);
  });
}

function showChapter(player, chapter) {
  new MessageFormData()
    .title(chapter.title)
    .body(chapter.body)
    .button1("Back to Journal")
    .button2("Close")
    .show(player)
    .then((res) => {
      if (!res.canceled && res.selection === 0) openJournal(player);
    });
}
