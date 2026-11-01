const test = require("node:test");
const assert = require("node:assert/strict");
const { createLiveApi, ApiError } = require("../app/static/tablet/live-api.js");
const spreadsheet = require("../app/static/tablet/spreadsheet.js");

function fixtureSnapshot() {
  return {
    mode: "live",
    companyName: "Partie de test",
    started: true,
    clock: { unit: "week", period: 1, label: "Semaine 1", canAdvance: true, supportsRealtime: false },
    globalKpis: [{ id: "service", label: "Service", value: null, unit: "%", departmentId: "clients" }],
    departments: [], tools: [], alerts: [], objectives: [], events: [], history: [],
    raw: { scenario_id: "default", stocks: [], suppliers: [], production_lines: [] }
  };
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), { status, headers: { "Content-Type": "application/json" } });
}

test("live adapter reads the v2 snapshot with same-origin credentials", async () => {
  const calls = [];
  const api = createLiveApi({ fetchImpl: async (url, init) => {
    calls.push({ url, init });
    return jsonResponse(fixtureSnapshot());
  } });
  const snapshot = await api.getState();
  assert.equal(snapshot.mode, "live");
  assert.equal(calls[0].url, "/api/v2/tablet");
  assert.equal(calls[0].init.credentials, "same-origin");
  assert.equal(calls[0].init.headers.Accept, "application/json");
});

test("new game is explicit and always includes rules confirmation and default scenario", async () => {
  const calls = [];
  const api = createLiveApi({ fetchImpl: async (url, init) => {
    calls.push({ url, init });
    return jsonResponse(fixtureSnapshot());
  } });
  await api.newGame({ company_name: "Atelier test", difficulty: "normal", rules_confirmed: true });
  assert.equal(calls[0].url, "/api/v2/tablet/new-game");
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    company_name: "Atelier test", difficulty: "normal", scenario_id: "default", rules_confirmed: true
  });
});

test("turn, purchase, production and maintenance use the agreed mutation contracts", async () => {
  const bodies = [];
  const api = createLiveApi({ fetchImpl: async (url, init) => {
    bodies.push({ url, body: JSON.parse(init.body) });
    return jsonResponse(fixtureSnapshot());
  } });
  await api.nextTurn();
  await api.performAction({ action: "purchase", supplier_id: "SUP-01", sku: "MAT-01", quantity: 500 });
  await api.performAction({ action: "production", sku: "SKU-01", quantity: 20 });
  await api.performAction({ action: "maintenance", line_id: "LINE-01" });
  assert.deepEqual(bodies, [
    { url: "/api/v2/tablet/next-turn", body: {} },
    { url: "/api/v2/tablet/actions", body: { action: "purchase", supplier_id: "SUP-01", sku: "MAT-01", quantity: 500 } },
    { url: "/api/v2/tablet/actions", body: { action: "production", sku: "SKU-01", quantity: 20 } },
    { url: "/api/v2/tablet/actions", body: { action: "maintenance", line_id: "LINE-01" } }
  ]);
});

test("configuration refusal preserves the exact server detail and HTTP status", async () => {
  const message = "Modification interdite : le formateur a fixé ce réglage pour toute la partie.";
  const api = createLiveApi({ fetchImpl: async () => jsonResponse({ detail: message }, 403) });
  await assert.rejects(api.updateConfiguration("stock", "methode_sortie", "FIFO"), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 403);
    assert.equal(error.message, message);
    return true;
  });
});

test("supplier comparison delegates quantity and SKU to the engine endpoint", async () => {
  let requestedUrl;
  const api = createLiveApi({ fetchImpl: async (url) => {
    requestedUrl = url;
    return jsonResponse([{ supplier_id: "SUP-01", total_cost: 1250, expected_arrival_week: 4 }]);
  } });
  const quotes = await api.compare("MAT-01", 500);
  assert.equal(requestedUrl, "/api/tablet/compare?sku=MAT-01&quantity=500");
  assert.equal(quotes[0].total_cost, 1250);
  assert.equal(quotes[0].expected_arrival_week, 4);
});

test("adapter exposes useful network and malformed-response failures", async () => {
  const offline = createLiveApi({ fetchImpl: async () => { throw new Error("offline"); } });
  await assert.rejects(offline.getState(), /injoignable/);
  const malformed = createLiveApi({ fetchImpl: async () => new Response("not-json", { status: 200 }) });
  await assert.rejects(malformed.getState(), /illisible/);
});

test("spreadsheet evaluates basic operations and French aggregate functions", () => {
  const grid = spreadsheet.createGrid(5, 3, [[10, 20, 30], [null, "", "=A1+B1*2"]]);
  assert.equal(spreadsheet.evaluate("=A1+B1*2", grid), 50);
  assert.equal(spreadsheet.evaluate("=SOMME(A1:C1)", grid), 60);
  assert.equal(spreadsheet.evaluate("=MOYENNE(A1:C1)", grid), 20);
  assert.equal(spreadsheet.evaluate("=MIN(A1:C1)", grid), 10);
  assert.equal(spreadsheet.evaluate("=MAX(A1:C1)", grid), 30);
  assert.equal(spreadsheet.evaluate("=SI(A1<B1;\"oui\";\"non\")", grid), "oui");
  assert.equal(spreadsheet.evaluate("=(A1+B1)/2", grid), 15);
});

test("spreadsheet rejects unsafe or invalid formulas without eval", () => {
  const grid = spreadsheet.createGrid(2, 2, [["=B1", "=A1"]]);
  assert.equal(spreadsheet.evaluate("=A1", grid), "#CIRC");
  assert.equal(spreadsheet.evaluate("=1/0", grid), "#ERREUR");
  assert.equal(spreadsheet.evaluate("=CONCATENER(A1;A2)", grid), "#ERREUR");
  assert.equal(spreadsheet.evaluate("=globalThis.process.exit()", grid), "#ERREUR");
});

test("CSV export contains formula results and neutralizes spreadsheet injection", () => {
  const grid = spreadsheet.createGrid(2, 2, [[2, 3], ["=SOMME(A1:B1)", "@commande"]]);
  const csv = spreadsheet.toCsv(grid);
  assert.match(csv, /5;'@commande/);
  assert.doesNotMatch(csv, /\r\n=SOMME/);
});
