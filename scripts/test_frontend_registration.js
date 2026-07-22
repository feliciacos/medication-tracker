#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const frontendPath = path.join(
  root,
  "custom_components",
  "medication_stock_manager",
  "frontend",
  "medication-stock-manager-card.js"
);
const source = fs.readFileSync(frontendPath, "utf8");

const registry = new Map();
class StubHTMLElement {
  attachShadow() {
    this.shadowRoot = {
      querySelector: () => null,
      querySelectorAll: () => [],
      childElementCount: 0,
    };
    return this.shadowRoot;
  }
}
class StubIconPicker extends StubHTMLElement {}
registry.set("ha-icon-picker", StubIconPicker);

let rebuildEvents = 0;
const errorCard = {
  textContent:
    "Configuration error Custom element doesn't exist: medication-stock-manager-card.",
  shadowRoot: null,
  dispatchEvent(event) {
    if (event.type === "ll-rebuild") rebuildEvents += 1;
    return true;
  },
};
const documentStub = {
  querySelectorAll(selector) {
    if (selector === "hui-error-card") return [errorCard];
    return [];
  },
  createElement() {
    return new StubHTMLElement();
  },
  dispatchEvent() {
    return true;
  },
};

const customElementsStub = {
  get(name) {
    return registry.get(name);
  },
  define(name, constructor) {
    if (registry.has(name)) {
      throw new Error(`Custom element already defined: ${name}`);
    }
    registry.set(name, constructor);
  },
  whenDefined(name) {
    return registry.has(name)
      ? Promise.resolve()
      : Promise.reject(new Error(`Element not defined in test: ${name}`));
  },
};

const immediateTimer = (callback) => {
  callback();
  return 1;
};
const context = {
  console,
  HTMLElement: StubHTMLElement,
  customElements: customElementsStub,
  document: documentStub,
  window: {
    customCards: [],
    setTimeout: immediateTimer,
    clearTimeout() {},
  },
  requestAnimationFrame: immediateTimer,
  setTimeout: immediateTimer,
  clearTimeout() {},
  CustomEvent: class CustomEvent {
    constructor(type, options = {}) {
      this.type = type;
      Object.assign(this, options);
    }
  },
  Event: class Event {
    constructor(type) {
      this.type = type;
    }
  },
  CSS: { escape: (value) => String(value) },
  confirm: () => true,
};
context.globalThis = context;
vm.createContext(context);
vm.runInContext(source, context, { filename: frontendPath });

const card = registry.get("medication-stock-manager-card");
if (!card) throw new Error("Medication Stock Manager card did not register");
if (card.prototype.msmVersion !== "1.5.3") {
  throw new Error(`Unexpected frontend version: ${card.prototype.msmVersion}`);
}
if (!registry.get("ha-panel-medication-stock-manager")) {
  throw new Error("Medication Stock Manager panel did not register");
}
if (rebuildEvents < 1) {
  throw new Error("Matching Lovelace error card did not receive ll-rebuild");
}

const testCard = new card();
const testItems = [
  { id: "med-a", owner: "owner-a", category: "medication", display_order: 0, name: "A" },
  { id: "med-b", owner: "owner-a", category: "medication", display_order: 1, name: "B" },
  { id: "supply-a", owner: "owner-a", category: "supply", display_order: 0, name: "Supply" },
  { id: "other-owner", owner: "owner-b", category: "medication", display_order: 0, name: "Other" },
];
testCard._items = () => testItems;
testCard._category = (item) => item.category;
const firstAvailability = testCard._moveAvailability(testItems[0]);
const secondAvailability = testCard._moveAvailability(testItems[1]);
if (firstAvailability.canMoveUp || !firstAvailability.canMoveDown) {
  throw new Error("First medication item has incorrect arrow availability");
}
if (!secondAvailability.canMoveUp || secondAvailability.canMoveDown) {
  throw new Error("Last medication item has incorrect arrow availability");
}
const supplyAvailability = testCard._moveAvailability(testItems[2]);
if (supplyAvailability.canMoveUp || supplyAvailability.canMoveDown) {
  throw new Error("Supply arrow availability crossed category boundaries");
}

console.log(
  `Frontend registration test passed; requested ${rebuildEvents} Lovelace rebuild(s).`
);
