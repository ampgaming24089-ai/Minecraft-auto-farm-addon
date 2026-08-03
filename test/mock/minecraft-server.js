// Minimal stub of @minecraft/server, just enough surface area for
// scripts/lib/builder.js and the farm modules to run outside the game so
// authoring bugs (bad imports, undefined states, malformed coordinates,
// runtime exceptions in plan()) get caught before this ever loads in a
// real world. It does NOT validate that block ids/states are real vanilla
// values — only the actual game can do that.

export class BlockPermutation {
  static resolve(id, states) {
    return { id, states: states ?? {} };
  }
}

export class ItemStack {
  constructor(typeId, amount = 1) {
    this.typeId = typeId;
    this.amount = amount;
  }
}

export const world = {
  afterEvents: {
    itemUse: { subscribe: () => {} },
    playerInteractWithEntity: { subscribe: () => {} },
    playerInteractWithBlock: { subscribe: () => {} },
  },
};

export const system = {
  runJob: (generator) => {
    // Drain the whole generator synchronously for the test harness.
    let result = generator.next();
    while (!result.done) result = generator.next();
  },
  runInterval: () => 1,
  runTimeout: () => 1,
  clearRun: () => {},
};
