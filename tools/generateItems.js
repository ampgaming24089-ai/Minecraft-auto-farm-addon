import { mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

const FARMS = [
  {
    key: "iron",
    displayName: "Iron Farm Beacon",
    functionDir: "iron_farm",
    icon: "autofarm_iron_beacon",
    coreItem: "minecraft:iron_block",
  },
  {
    key: "crop",
    displayName: "Crop Farm Beacon",
    functionDir: "crop_farm",
    icon: "autofarm_crop_beacon",
    coreItem: "minecraft:hay_block",
  },
];

const langLines = [];

for (const farm of FARMS) {
  for (let level = 1; level <= 4; level++) {
    const id = `autofarm:${farm.key}_beacon_${level}`;
    const eventId = `autofarm:build_${farm.key}_${level}`;
    const itemJson = {
      format_version: "1.21.60",
      "minecraft:item": {
        description: {
          identifier: id,
          menu_category: { category: "equipment", group: "itemGroup.name.tool" },
        },
        components: {
          "minecraft:max_stack_size": 8,
          "minecraft:hand_equipped": true,
          "minecraft:glint": true,
          "minecraft:icon": { texture: farm.icon },
          "minecraft:display_name": { value: `item.${id}.name` },
          "minecraft:on_use": {
            event: eventId,
            target: "self",
          },
        },
        events: {
          [eventId]: {
            run_command: {
              command: [`function ${farm.functionDir}/level${level}`],
            },
          },
        },
      },
    };
    writeFileSync(
      join(ROOT, "BP", "items", `${farm.key}_beacon_${level}.json`),
      JSON.stringify(itemJson, null, 2) + "\n"
    );

    const recipeJson = {
      format_version: "1.21.60",
      "minecraft:recipe_shapeless": {
        description: { identifier: id },
        tags: ["crafting_table"],
        ingredients: [
          { item: farm.coreItem, count: 1 },
          { item: "minecraft:emerald", count: level },
          { item: "minecraft:stick", count: 1 },
        ],
        unlock: [{ item: "minecraft:emerald" }],
        result: { item: id, count: 1 },
      },
    };
    writeFileSync(
      join(ROOT, "BP", "recipes", `${farm.key}_beacon_${level}.json`),
      JSON.stringify(recipeJson, null, 2) + "\n"
    );

    langLines.push(
      `item.${id}.name=${farm.displayName} (${level} Level${level > 1 ? "s" : ""})`
    );
  }
}

mkdirSync(join(ROOT, "tools"), { recursive: true });
writeFileSync(join(ROOT, "tools", "generated_lang_items.txt"), langLines.join("\n") + "\n");
console.log(langLines.join("\n"));
console.log(`\nWrote ${FARMS.length * 4} items + ${FARMS.length * 4} recipes.`);
