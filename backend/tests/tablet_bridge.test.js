const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// Exercise the shipped bridge with DOM doubles only: no browser, server or network.
const bridgeSource = fs.readFileSync(path.join(__dirname, "../app/static/tablet-bridge.js"), "utf8");

function eventTarget() {
  const listeners = new Map();
  return {
    addEventListener(type, listener, capture = false) {
      const entries = listeners.get(type) || [];
      entries.push({ listener, capture: capture === true });
      listeners.set(type, entries);
    },
    async dispatch(type, event = {}) {
      const entries = [...(listeners.get(type) || [])].sort((a, b) => Number(b.capture) - Number(a.capture));
      for (const { listener } of entries) await listener(event);
    }
  };
}

function fixture(refreshState = async () => {}) {
  const classes = new Set();
  const navigation = [];
  const game = { inert: false };
  const previousFocus = { calls: 0, focus() { this.calls++; } };
  const closeButton = { ...eventTarget(), focus() { document.activeElement = this; } };
  const dialogs = [];
  const iframeDocument = {
    ...eventTarget(),
    querySelectorAll(selector) {
      assert.equal(selector, '[role="dialog"]');
      return dialogs;
    }
  };
  const frame = {
    ...eventTarget(),
    contentDocument: iframeDocument,
    contentWindow: { location: new URL("http://gmix.test/blank") },
    get src() { return navigation.at(-1) || ""; },
    set src(value) {
      navigation.push(value);
      this.contentWindow.location = new URL(value);
    }
  };
  const attributes = {};
  const overlay = {
    ...eventTarget(),
    hidden: true,
    setAttribute(name, value) { attributes[name] = value; },
    querySelector(selector) {
      if (selector === "iframe") return frame;
      if (selector === "button") return closeButton;
      throw new Error(`Unexpected overlay selector: ${selector}`);
    }
  };
  const document = {
    ...eventTarget(),
    activeElement: previousFocus,
    body: {
      append(element) { assert.equal(element, overlay); },
      classList: { add(name) { classes.add(name); }, remove(name) { classes.delete(name); } }
    },
    createElement(tag) { assert.equal(tag, "section"); return overlay; },
    querySelector(selector) { assert.equal(selector, "#game"); return game; }
  };
  const window = { ...eventTarget(), location: { origin: "http://gmix.test" } };
  const context = vm.createContext({ document, window, URL });
  // Remove ESM export declarations so the unmodified implementation can run in a vm.
  vm.runInContext(bridgeSource.replace(/^export /gm, "") + "\nglobalThis.bridgeFactory = createTablet;", context);
  const tablet = context.bridgeFactory({ refreshState });
  return { tablet, frame, iframeDocument, dialogs, navigation, game, overlay, classes, previousFocus };
}

function escapeEvent() {
  return { key: "Escape", defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
}

test("reopening the same department navigates again and restores its requested route", async () => {
  const view = fixture();
  view.tablet.open("stock_mp");
  assert.equal(view.frame.contentWindow.location.hash, "#departement/stock/kpis");
  // A player may navigate within the iframe before returning to the 3D stage.
  view.frame.contentWindow.location.hash = "#departement/production/kpis";
  await view.tablet.close();
  view.tablet.open("stock_mp");
  assert.equal(view.navigation.length, 2);
  assert.equal(view.navigation[0], view.navigation[1]);
  assert.equal(view.frame.contentWindow.location.hash, "#departement/stock/kpis");
  assert.equal(view.tablet.isOpen(), true);
});

test("Escape in the iframe closes the tablet when its inner dialog is hidden", async () => {
  let refreshCalls = 0;
  const view = fixture(async () => { refreshCalls++; });
  view.dialogs.push({ getClientRects() { return []; } });
  view.tablet.open();
  await view.frame.dispatch("load");
  const event = escapeEvent();
  await view.iframeDocument.dispatch("keydown", event);
  assert.equal(event.defaultPrevented, true);
  assert.equal(view.tablet.isOpen(), false);
  assert.equal(view.overlay.hidden, true);
  assert.equal(view.game.inert, false);
  assert.equal(refreshCalls, 1);
});

test("a visible inner dialog handles Escape without closing the parent tablet", async () => {
  let refreshCalls = 0;
  const view = fixture(async () => { refreshCalls++; });
  const dialog = { hidden: false, getClientRects() { return this.hidden ? [] : [{}]; } };
  view.dialogs.push(dialog);
  view.tablet.open();
  await view.frame.dispatch("load");
  // The application handles its dialog after the bridge's capture listener.
  view.iframeDocument.addEventListener("keydown", (event) => {
    if (event.key === "Escape") { dialog.hidden = true; event.preventDefault(); }
  });
  await view.iframeDocument.dispatch("keydown", escapeEvent());
  assert.equal(dialog.hidden, true);
  assert.equal(view.tablet.isOpen(), true);
  assert.equal(view.overlay.hidden, false);
  assert.equal(view.game.inert, true);
  assert.equal(refreshCalls, 0);
});

test("close restores the parent stage and focus, and awaits its state refresh", async () => {
  let finishRefresh;
  let refreshCalls = 0;
  const view = fixture(() => {
    refreshCalls++;
    return new Promise((resolve) => { finishRefresh = resolve; });
  });
  view.tablet.open();
  assert.equal(view.game.inert, true);
  assert.equal(view.classes.has("live-tablet-open"), true);
  let completed = false;
  const closing = view.tablet.close().then(() => { completed = true; });
  assert.equal(view.tablet.isOpen(), false);
  assert.equal(view.overlay.hidden, true);
  assert.equal(view.game.inert, false);
  assert.equal(view.classes.has("live-tablet-open"), false);
  assert.equal(view.previousFocus.calls, 1);
  assert.equal(refreshCalls, 1);
  assert.equal(completed, false);
  finishRefresh();
  await closing;
  assert.equal(completed, true);
});
