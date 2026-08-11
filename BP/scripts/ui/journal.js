import { ActionFormData, MessageFormData } from "@minecraft/server-ui";
import { bossesDefeated } from "../lib/state.js";
import { GUIDE } from "./guidedata.js";

const ICON = "textures/items/";

/**
 * The Field Guide.
 *
 * This used to be a story journal and nothing else - eight chapters of prose
 * and no answer to "what does this item do" or "where do I find that ore".
 * For a pack people download and open cold, that is the wrong first screen.
 *
 * It is now two halves. The reference half is generated: `guidedata.js` is
 * built by tools/gen_guide.py from the pack's own items, recipes, loot tables
 * and spawner rosters, so every number in it is true by construction and
 * stays true when the pack changes. The story half is hand-written and lives
 * here, gated on which Wardens the world has actually beaten.
 */

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
    id: "dragons",
    title: "Veil Dragons",
    icon: ICON + "dragon_egg",
    body:
      "Not Wardens, not corrupted, not native to the crossing at all. Wild " +
      "adults ride the thermals over the Ashlands, and an egg turns up " +
      "sometimes where a Wraithguard falls. Feed one until it trusts you, " +
      "then ride it anywhere in the Veil. They come in every colour the Veil " +
      "has ever worn.",
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

// Bedrock's form bodies scroll, but a wall of text on a phone is unreadable.
// Long entries are split into pages the player can step through.
const PAGE_CHARS = 780;

function paginate(text) {
  if (text.length <= PAGE_CHARS) return [text];
  const pages = [];
  let rest = text;
  while (rest.length > PAGE_CHARS) {
    // Break on a paragraph if there is one in range, otherwise a space, so a
    // page never ends mid-word.
    let cut = rest.lastIndexOf("\n\n", PAGE_CHARS);
    if (cut < PAGE_CHARS * 0.5) cut = rest.lastIndexOf(" ", PAGE_CHARS);
    if (cut < 1) cut = PAGE_CHARS;
    pages.push(rest.slice(0, cut).trim());
    rest = rest.slice(cut).trim();
  }
  if (rest) pages.push(rest);
  return pages;
}

export function openJournal(player) {
  const form = new ActionFormData()
    .title("§l§5Hollow Veil Field Guide")
    .body("§7Everything in the Veil, and what to do with it.");

  for (const section of GUIDE.sections) {
    form.button(`§e${section.title}`, ICON + section.icon);
  }
  form.button("§dThe Story", ICON + "journal");

  form.show(player).then((res) => {
    if (res.canceled || res.selection === undefined) return;
    if (res.selection === GUIDE.sections.length) {
      openStory(player);
      return;
    }
    openSection(player, GUIDE.sections[res.selection]);
  });
}

function openSection(player, section) {
  // A section with no sub-entries is a single page of prose - show it rather
  // than making the player click through a menu of one.
  if (!section.entries?.length) {
    showPages(player, section.title, section.text ?? "", () => openJournal(player));
    return;
  }

  const form = new ActionFormData()
    .title(`§5${section.title}`)
    .body(section.text ? `§7${section.text}` : "§7Pick an entry:");
  for (const entry of section.entries) {
    form.button(entry.name);
  }
  form.show(player).then((res) => {
    if (res.canceled || res.selection === undefined) {
      openJournal(player);
      return;
    }
    const entry = section.entries[res.selection];
    showPages(player, entry.name, entry.text, () => openSection(player, section));
  });
}

/** Shows `text` a page at a time, then returns to `back`. */
function showPages(player, title, text, back, page = 0) {
  const pages = paginate(text || "-");
  const last = page >= pages.length - 1;
  const header = pages.length > 1 ? `§8Page ${page + 1}/${pages.length}\n\n` : "";
  new MessageFormData()
    .title(`§5${title}`)
    .body(header + "§7" + pages[page])
    .button1(last ? "Back" : "Next page")
    .button2("Close")
    .show(player)
    .then((res) => {
      if (res.canceled || res.selection !== 0) return;
      if (last) back();
      else showPages(player, title, text, back, page + 1);
    });
}

function openStory(player) {
  const defeated = bossesDefeated();
  const form = new ActionFormData()
    .title("§l§5The Story")
    .body(`§7Wardens defeated: §e${defeated.length}§7/3`);

  const visible = CHAPTERS.filter((c) => c.always || c.bossId ||
                                         (c.requiresAll && defeated.length >= 3));
  for (const chapter of visible) {
    const done = chapter.bossId ? defeated.includes(chapter.bossId) : false;
    const prefix = chapter.bossId ? (done ? "§a[Defeated] " : "§c[Unclaimed] ") : "§e";
    form.button(prefix + chapter.title, chapter.icon);
  }

  form.show(player).then((res) => {
    if (res.canceled || res.selection === undefined) {
      openJournal(player);
      return;
    }
    const chapter = visible[res.selection];
    if (chapter) showPages(player, chapter.title, chapter.body, () => openStory(player));
  });
}
