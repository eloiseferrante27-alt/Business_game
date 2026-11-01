const test = require("node:test");
const assert = require("node:assert/strict");
const { createMockApi } = require("../app/static/tablet/mock-api.js");

test("the shell exposes ten departments and starts on the rules screen", async () => {
  const api = createMockApi();
  const state = await api.getState();
  assert.equal(state.started, false);
  assert.equal(state.clock.paused, true);
  assert.equal(state.departments.length, 10);
  assert.equal(state.tools.length, 5);
  assert.equal(state.globalKpis.length, 6);
});

test("locked configuration is rejected with the specified message", async () => {
  const api = createMockApi();
  const result = await api.updateConfiguration("stock", "methode-sortie", "LIFO");
  assert.equal(result.ok, false);
  assert.equal(result.message, "Modification interdite : le formateur a fixé ce réglage pour toute la partie.");
  const state = await api.getState();
  const stock = state.departments.find((department) => department.id === "stock");
  assert.equal(stock.configurations.find((item) => item.id === "methode-sortie").value, "FIFO");
});

test("initial configuration becomes read-only after confirmation", async () => {
  const api = createMockApi();
  const before = await api.updateConfiguration("stock", "methode-reapprovisionnement", "Recomplètement périodique");
  assert.equal(before.ok, true);
  const started = await api.startGame({});
  assert.equal(started.started, true);
  const result = await api.updateConfiguration("stock", "methode-reapprovisionnement", "Point de commande");
  assert.equal(result.ok, false);
  assert.equal(result.message, "Modification interdite : ce réglage ne pouvait être choisi qu’avant le début de la partie.");
});

test("clock controls validate speed and advance to the supplied decision", async () => {
  const api = createMockApi();
  const invalid = await api.setSpeed(61);
  assert.equal(invalid.ok, false);
  const running = await api.setSpeed(60);
  assert.equal(running.clock.speed, 60);
  const advanced = await api.advanceToDecision();
  assert.equal(advanced.clock.time, "14:30");
  assert.equal(advanced.clock.paused, true);
});

test("separate mock sessions do not share configuration changes", async () => {
  const first = createMockApi();
  const second = createMockApi();
  await first.updateConfiguration("stock", "methode-reapprovisionnement", "Recomplètement périodique");
  const state = await second.getState();
  const stock = state.departments.find((department) => department.id === "stock");
  assert.equal(stock.configurations.find((item) => item.id === "methode-reapprovisionnement").value, "Point de commande");
});
