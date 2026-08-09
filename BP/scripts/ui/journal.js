import { ActionFormData, MessageFormData } from "@minecraft/server-ui";
import { bossesDefeated } from "../lib/state.js";

const CHAPTERS = [
  {
    id: "into_the_grey",
    title: "1. Into the Grey",
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
    body:
      "Soul Shards and Ember Dust prove you can survive the Veil's wildlife. " +
      "Bring some to the Occultist to unlock their better trades.",
    always: true,
  },
  {
    id: "three_wardens",
    title: "3. The Three Wardens",
    body:
      "Three guardians of the old crossing were corrupted when something broke " +
      "through: the Hollow King (Sunken Crypt), the Weeping Widow (Widow's " +
      "Hollow), and Malacoda (Cinder Bastion). Craft each Warden's Sigil and " +
      "use it on a Ritual Altar to challenge them - defeating one drops their " +
      "unique weapon and a full armour set, and restores a piece of the Veil.",
    always: true,
  },
  {
    id: "hollow_king",
    title: "Sunken Crypt - the Hollow King",
    body: "A spectral king who hoarded the memories of the dead until they curdled into rage. Reward: Hollow King's Reaper + Spectral Regalia.",
    bossId: "hollow_king",
  },
  {
    id: "weeping_widow",
    title: "Widow's Hollow - the Weeping Widow",
    body: "Her lullabies once eased the crossing; now they shatter minds. Reward: Wailing Edge + Mourner's Shroud.",
    bossId: "weeping_widow",
  },
  {
    id: "malacoda",
    title: "Cinder Bastion - Malacoda",
    body: "The Warden who opened the door that should have stayed shut, burned down into the shape of a demon. Reward: Malacoda's Fang + Ashen Demonplate.",
    bossId: "malacoda",
  },
  {
    id: "what_opened_the_door",
    title: "What Opened the Door",
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
    .title("Hollow Veil Journal")
    .body("§7A record of everything you've learned in the Veil.");

  const visible = CHAPTERS.filter((c) => {
    if (c.always) return true;
    if (c.bossId) return true; // always listed, but marked locked/complete below
    if (c.requiresAll) return defeated.length >= 3;
    return true;
  });

  for (const c of visible) {
    const done = c.bossId ? defeated.includes(c.bossId) : false;
    const prefix = c.bossId ? (done ? "§a[Defeated] " : "§c[Unclaimed] ") : "§e";
    form.button(prefix + c.title);
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
