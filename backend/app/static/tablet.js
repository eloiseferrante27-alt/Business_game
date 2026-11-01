// Tablette du joueur : son interface globale (document v3).
// Elle donne accès à ce qui n'a pas de bloc physique : les fournisseurs du monde,
// le comparateur de coûts, les achats de MP, les commandes clients et les ordres de fabrication.

const TABS = [
  ["fournisseurs", "Fournisseurs"],
  ["comparateur", "Comparateur"],
  ["achats", "Achats MP"],
  ["clients", "Commandes clients"],
  ["of", "Ordres de fabrication"],
  ["stocks", "Stocks & alertes"],
];

const fmt = (value, digits = 0) => new Intl.NumberFormat("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

export function createTablet({ getState, refreshState, toast, onAction }) {
  const root = document.querySelector("#tablet-modal");
  const body = root.querySelector(".tablet-body");
  const tabsBar = root.querySelector(".tablet-tabs");
  let current = "fournisseurs";
  let draft = {};

  tabsBar.innerHTML = TABS.map(([id, label]) => `<button type="button" data-tab="${id}">${label}</button>`).join("");
  tabsBar.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab]");
    if (button) show(button.dataset.tab);
  });
  root.querySelector(".tablet-close").addEventListener("click", close);
  root.addEventListener("pointerdown", (event) => { if (event.target === root) close(); });

  const state = () => getState();
  const stocks = (...categories) => (state()?.stocks || []).filter((item) => categories.includes(item.category));
  const stockBySku = (sku) => (state()?.stocks || []).find((item) => item.sku === sku);
  const supplierName = (id) => state()?.suppliers?.find((item) => item.id === id)?.name || id;

  function open(tab = current, options = {}) {
    draft = { ...draft, ...options };
    root.hidden = false;
    show(tab);
  }
  function close() { root.hidden = true; }
  function show(tab) {
    current = tab;
    tabsBar.querySelectorAll("button").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
    const alerts = state()?.alerts?.length || 0;
    const late = (state()?.customer_orders || []).filter((order) => order.status === "en retard").length;
    tabsBar.querySelector('[data-tab="stocks"]').dataset.badge = alerts || "";
    tabsBar.querySelector('[data-tab="clients"]').dataset.badge = late || "";
    root.querySelector(".tablet-week").textContent = `Semaine ${state()?.current_week ?? "—"}`;
    ({ fournisseurs, comparateur, achats, clients, of, stocks: stockView })[tab]();
  }
  function render() { if (!root.hidden) show(current); }

  async function post(payload) {
    const response = await fetch("/api/decisions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail?.[0]?.msg || result.detail || `HTTP ${response.status}`);
    await refreshState();
    return result;
  }

  // ----------------------------------------------------------- fournisseurs
  function fournisseurs() {
    const materials = stocks("MP", "PDR");
    const rows = (state()?.suppliers || []).filter((s) => s.active).map((s) => `
      <tr><td><b>${esc(s.name)}</b><small>${esc(s.specialty)} · ${esc(s.region)}</small></td>
      <td class="num">${s.lead_time_weeks} sem.</td><td class="num">${fmt(s.reliability, 0)} %</td><td class="num">${fmt(s.nonconformity_rate, 1)} %</td>
      ${materials.map((m) => `<td class="num">${s.prices[m.sku] !== undefined ? `${fmt(s.prices[m.sku], 2)} €` : "<span class=muted>—</span>"}</td>`).join("")}</tr>`).join("");
    body.innerHTML = `
      <h3>Fournisseurs du monde</h3>
      <p class="hint">Prix unitaire par matière, délai de livraison, part livrée à l’heure et part non conforme. Les fournisseurs sont des variables du scénario : dans l’usine, on ne voit que leurs camions.</p>
      <div class="table-wrap"><table><thead><tr><th>Fournisseur</th><th>Délai</th><th>Fiabilité</th><th>Non-conf.</th>
      ${materials.map((m) => `<th title="${esc(m.name)}">${esc(m.sku)}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  // ------------------------------------------------------------ comparateur
  async function comparateur() {
    const materials = stocks("MP", "PDR");
    const sku = draft.sku && stockBySku(draft.sku) ? draft.sku : materials[0]?.sku;
    const item = stockBySku(sku);
    const quantity = draft.quantity || item?.reorder_qty || 500;
    body.innerHTML = `
      <h3>Comparer le coût du fournisseur X et du fournisseur Y</h3>
      <div class="form-row">
        <label>Matière<select id="cmp-sku">${materials.map((m) => `<option value="${m.sku}" ${m.sku === sku ? "selected" : ""}>${esc(m.name)}</option>`).join("")}</select></label>
        <label>Quantité<input id="cmp-qty" type="number" min="1" value="${quantity}"></label>
      </div>
      <div id="cmp-table" class="table-wrap"><p class="hint">Calcul…</p></div>
      <div id="cmp-xy"></div>`;
    body.querySelector("#cmp-sku").addEventListener("change", (e) => { draft.sku = e.target.value; draft.quantity = stockBySku(e.target.value)?.reorder_qty; comparateur(); });
    body.querySelector("#cmp-qty").addEventListener("change", (e) => { draft.quantity = Math.max(1, Number(e.target.value) || 1); comparateur(); });
    try {
      const response = await fetch(`/api/tablet/compare?sku=${encodeURIComponent(sku)}&quantity=${quantity}`);
      const quotes = await response.json();
      if (!response.ok) throw new Error(quotes.detail || `HTTP ${response.status}`);
      if (current !== "comparateur") return;
      if (!quotes.length) { body.querySelector("#cmp-table").innerHTML = '<p class="hint">Aucun fournisseur ne vend cette matière.</p>'; return; }
      const best = (key, lower = true) => quotes.reduce((a, b) => ((lower ? b[key] < a[key] : b[key] > a[key]) ? b : a))[key];
      const bestCost = best("total_cost"), bestLead = best("lead_time_weeks"), bestRel = best("reliability", false);
      body.querySelector("#cmp-table").innerHTML = `<table class="sheet"><thead><tr><th></th><th>Fournisseur</th><th>Prix u.</th><th>Coût total</th><th>Délai</th><th>Arrivée</th><th>Fiabilité</th><th>Conformes attendus</th><th></th></tr></thead><tbody>
        ${quotes.map((q, i) => `<tr>
          <td><input type="checkbox" class="cmp-pick" value="${q.supplier_id}" ${i < 2 ? "checked" : ""}></td>
          <td><b>${esc(q.supplier_name)}</b></td><td class="num">${fmt(q.unit_price, 2)} €</td>
          <td class="num ${q.total_cost === bestCost ? "best" : ""}">${fmt(q.total_cost, 2)} €</td>
          <td class="num ${q.lead_time_weeks === bestLead ? "best" : ""}">${q.lead_time_weeks} sem.</td><td class="num">S${q.expected_arrival_week}</td>
          <td class="num ${q.reliability === bestRel ? "best" : ""}">${fmt(q.reliability, 0)} %</td><td class="num">${fmt(q.expected_good_quantity)}</td>
          <td><button type="button" class="mini-button" data-buy="${q.supplier_id}">Commander →</button></td></tr>`).join("")}</tbody></table>`;
      const renderXY = () => {
        const picked = [...body.querySelectorAll(".cmp-pick:checked")].map((box) => quotes.find((q) => q.supplier_id === box.value));
        if (picked.length !== 2) { body.querySelector("#cmp-xy").innerHTML = '<p class="hint">Cochez deux fournisseurs pour les comparer (X et Y).</p>'; return; }
        const [x, y] = picked;
        const diff = y.total_cost - x.total_cost;
        const cheaper = diff > 0 ? x : y;
        body.querySelector("#cmp-xy").innerHTML = `<div class="xy">
          <div><small>X</small><b>${esc(x.supplier_name)}</b><span>${fmt(x.total_cost, 2)} € · ${x.lead_time_weeks} sem. · ${fmt(x.reliability, 0)} %</span></div>
          <div class="vs">vs</div>
          <div><small>Y</small><b>${esc(y.supplier_name)}</b><span>${fmt(y.total_cost, 2)} € · ${y.lead_time_weeks} sem. · ${fmt(y.reliability, 0)} %</span></div>
          <p>${diff === 0 ? "Même coût total." : `${esc(cheaper.supplier_name)} coûte ${fmt(Math.abs(diff), 2)} € de moins`} · écart de délai : ${Math.abs(x.lead_time_weeks - y.lead_time_weeks)} sem. · écart de fiabilité : ${fmt(Math.abs(x.reliability - y.reliability), 0)} pts.</p></div>`;
      };
      body.querySelectorAll(".cmp-pick").forEach((box) => box.addEventListener("change", renderXY));
      body.querySelectorAll("[data-buy]").forEach((button) => button.addEventListener("click", () => open("achats", { sku, supplier: button.dataset.buy, quantity })));
      renderXY();
    } catch (error) {
      body.querySelector("#cmp-table").innerHTML = `<p class="error">${esc(error.message)}</p>`;
    }
  }

  // ----------------------------------------------------------------- achats
  function achats() {
    const materials = stocks("MP", "PDR");
    const sku = draft.sku && stockBySku(draft.sku) && ["MP", "PDR"].includes(stockBySku(draft.sku).category) ? draft.sku : materials[0]?.sku;
    const item = stockBySku(sku);
    const sellers = (state()?.suppliers || []).filter((s) => s.active && s.prices[sku] !== undefined).sort((a, b) => a.prices[sku] - b.prices[sku]);
    const supplier = sellers.find((s) => s.id === draft.supplier)?.id || sellers[0]?.id;
    const quantity = draft.quantity || item?.reorder_qty || 100;
    const pending = state()?.purchase_orders || [];
    body.innerHTML = `
      <h3>Acheter de la matière première</h3>
      <form id="buy-form" class="form-row">
        <label>Matière<select id="buy-sku">${materials.map((m) => `<option value="${m.sku}" ${m.sku === sku ? "selected" : ""}>${esc(m.name)} · ${fmt(m.quantity)} en stock</option>`).join("")}</select></label>
        <label>Fournisseur<select id="buy-supplier">${sellers.map((s) => `<option value="${s.id}" ${s.id === supplier ? "selected" : ""}>${esc(s.name)} · ${fmt(s.prices[sku], 2)} €/u · ${s.lead_time_weeks} sem.</option>`).join("")}</select></label>
        <label>Quantité<input id="buy-qty" type="number" min="1" value="${quantity}"></label>
        <button type="submit" class="action-button">Commander <span>→</span></button>
      </form>
      <p class="hint">${item ? `Point de commande ${fmt(item.reorder_point)} · quantité conseillée ${fmt(item.reorder_qty)} · capacité ${fmt(item.capacity_max)}.` : ""} <span id="buy-cost"></span></p>
      <h4>Commandes en cours</h4>
      ${pending.length ? `<div class="table-wrap"><table><thead><tr><th>N°</th><th>Fournisseur</th><th>Matière</th><th>Qté</th><th>Prix u.</th><th>Passée</th><th>Arrivée prévue</th></tr></thead><tbody>
        ${pending.map((o) => `<tr><td>${o.id}</td><td>${esc(supplierName(o.supplier_id))}</td><td>${esc(stockBySku(o.sku)?.name || o.sku)}</td><td class="num">${fmt(o.quantity)}</td><td class="num">${fmt(o.unit_price, 2)} €</td><td class="num">S${o.week_ordered}</td><td class="num">S${o.arrival_week}</td></tr>`).join("")}
      </tbody></table></div>` : '<p class="hint">Aucune commande en cours.</p>'}`;
    const updateCost = () => {
      const s = sellers.find((x) => x.id === body.querySelector("#buy-supplier").value);
      const q = Number(body.querySelector("#buy-qty").value) || 0;
      body.querySelector("#buy-cost").textContent = s ? `Coût : ${fmt(s.prices[sku] * q, 2)} € · arrivée semaine ${state().current_week + s.lead_time_weeks}.` : "Aucun fournisseur ne vend cette matière.";
    };
    body.querySelector("#buy-sku").addEventListener("change", (e) => { draft = { sku: e.target.value }; achats(); });
    body.querySelector("#buy-supplier").addEventListener("change", (e) => { draft.supplier = e.target.value; updateCost(); });
    body.querySelector("#buy-qty").addEventListener("input", (e) => { draft.quantity = Number(e.target.value); updateCost(); });
    body.querySelector("#buy-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        await post({ orders: [{ supplier_id: body.querySelector("#buy-supplier").value, sku, quantity: Number(body.querySelector("#buy-qty").value) }] });
        toast("Commande passée. Le camion du fournisseur arrivera au quai de déchargement.");
        onAction("order");
        draft = {};
        achats();
      } catch (error) { toast(`Commande refusée : ${error.message}`, true); }
    });
    updateCost();
  }

  // -------------------------------------------------------- commandes clients
  function clients() {
    const orders = [...(state()?.customer_orders || [])].sort((a, b) => a.due_week - b.due_week || a.id.localeCompare(b.id));
    const open = orders.filter((o) => o.status === "ouverte" || o.status === "en retard");
    const byProduct = stocks("PF").map((pf) => ({ pf, need: open.filter((o) => o.sku === pf.sku).reduce((sum, o) => sum + o.quantity, 0) }));
    const badge = { ouverte: "open", "en retard": "late", livrée: "done", annulée: "cancel" };
    body.innerHTML = `
      <h3>Commandes clients</h3>
      <p class="hint">La logistique sert les commandes depuis le stock PF : livraison par nos camions, ou enlèvement par le camion du client au quai d’expédition.</p>
      <div class="cards">${byProduct.map(({ pf, need }) => `<div class="card ${need > pf.quantity ? "warn" : ""}"><small>${esc(pf.name)}</small><b>${fmt(need)}</b><span>à servir · ${fmt(pf.quantity)} en stock PF</span></div>`).join("")}</div>
      <div class="table-wrap"><table><thead><tr><th>N°</th><th>Client</th><th>Produit</th><th>Qté</th><th>Passée</th><th>Échéance</th><th>Mode</th><th>Statut</th></tr></thead><tbody>
      ${orders.map((o) => `<tr><td>${o.id}</td><td>${esc(o.customer)}</td><td>${esc(stockBySku(o.sku)?.name || o.sku)}</td><td class="num">${fmt(o.quantity)}</td><td class="num">S${o.week_placed}</td><td class="num">S${o.due_week}</td><td>${o.mode === "enlèvement" ? "Enlèvement (camion client)" : "Livraison (nos camions)"}</td><td><span class="status ${badge[o.status]}">${o.status}${o.status === "livrée" ? ` S${o.delivered_week}${o.on_time ? "" : " · retard"}` : ""}</span></td></tr>`).join("") || '<tr><td colspan="8" class="hint">Pas encore de commande : lancez une semaine.</td></tr>'}
      </tbody></table></div>`;
  }

  // ------------------------------------------------------ ordres de fabrication
  function of() {
    const products = stocks("PF");
    const sku = draft.product && stockBySku(draft.product) ? draft.product : products[0]?.sku;
    const item = stockBySku(sku);
    const line = (state()?.production_lines || []).find((l) => l.product_sku === sku);
    const orders = state()?.production_orders || [];
    body.innerHTML = `
      <h3>Lancer un ordre de fabrication</h3>
      <form id="of-form" class="form-row">
        <label>Produit<select id="of-sku">${products.map((p) => `<option value="${p.sku}" ${p.sku === sku ? "selected" : ""}>${esc(p.name)} · ${fmt(p.quantity)} en stock PF</option>`).join("")}</select></label>
        <label>Quantité<input id="of-qty" type="number" min="1" max="10000" value="${draft.ofQuantity || item?.reorder_qty || 300}"></label>
        <button type="submit" class="action-button">Lancer l’OF <span>→</span></button>
      </form>
      <p class="hint">${line ? `${esc(line.name)} · ${line.operational ? `efficacité ${fmt(line.efficiency)} %` : "<b class=error>en panne</b>"} · le produit passe au stock de semi-finis après M${line.semi_finished_after}.` : ""}</p>
      <h4>OF en cours</h4>
      ${orders.length ? `<div class="table-wrap"><table><thead><tr><th>N°</th><th>Produit</th><th>Qté</th><th>Semi-finis</th><th>Terminés</th><th>Lancé</th><th>Statut</th></tr></thead><tbody>
        ${orders.map((o) => `<tr><td>${o.id}</td><td>${esc(stockBySku(o.sku)?.name || o.sku)}</td><td class="num">${fmt(o.quantity)}</td>
        <td><div class="bar"><i style="width:${Math.round(100 * o.semi_finished_done / o.quantity)}%"></i></div>${fmt(o.semi_finished_done)}</td>
        <td><div class="bar"><i style="width:${Math.round(100 * o.finished_done / o.quantity)}%"></i></div>${fmt(o.finished_done)}</td>
        <td class="num">S${o.week_launched}</td><td>${o.status}</td></tr>`).join("")}</tbody></table></div>` : '<p class="hint">Aucun OF en cours.</p>'}`;
    body.querySelector("#of-sku").addEventListener("change", (e) => { draft.product = e.target.value; draft.ofQuantity = undefined; of(); });
    body.querySelector("#of-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        await post({ production_orders: [{ sku, quantity: Number(body.querySelector("#of-qty").value) }] });
        toast("OF transmis au chef de ligne. Lancez la semaine pour produire.");
        onAction("production");
        of();
      } catch (error) { toast(`OF refusé : ${error.message}`, true); }
    });
  }

  // ------------------------------------------------------------------ stocks
  function stockView() {
    const sections = [["MP", "Stock de MP"], ["SF", "Stock de semi-finis"], ["PF", "Stock de produits finis"], ["PDR", "Stock PDR (maintenance)"]];
    const broken = (state()?.production_lines || []).filter((l) => !l.operational);
    body.innerHTML = `
      <h3>Stocks et alertes</h3>
      ${(state()?.alerts || []).length ? `<ul class="alerts">${state().alerts.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>` : '<p class="hint">Aucune alerte de stock.</p>'}
      ${broken.length ? `<div class="breakdown">${broken.map((l) => `<span>${esc(l.name)} en panne</span><button type="button" class="mini-button" data-repair="${l.id}">Planifier l’intervention →</button>`).join("")}</div>` : ""}
      ${sections.map(([cat, title]) => `<h4>${title}</h4><div class="table-wrap"><table><thead><tr><th>Référence</th><th>Quantité</th><th></th><th>Initial</th><th>Minimum</th><th>Point de cde</th><th>Qté commandée</th><th>Capacité</th></tr></thead><tbody>
        ${stocks(cat).map((s) => `<tr class="${s.quantity <= s.reorder_point ? "low" : ""}"><td><b>${esc(s.name)}</b><small>${s.sku}</small></td><td class="num">${fmt(s.quantity)}</td>
        <td><div class="bar ${s.quantity < s.minimum ? "red" : s.quantity <= s.reorder_point ? "amber" : ""}"><i style="width:${Math.min(100, Math.round(100 * s.quantity / s.capacity_max))}%"></i></div></td>
        <td class="num">${fmt(s.initial)}</td><td class="num">${fmt(s.minimum)}</td><td class="num">${fmt(s.reorder_point)}</td><td class="num">${fmt(s.reorder_qty)}</td><td class="num">${fmt(s.capacity_max)}</td></tr>`).join("")}
      </tbody></table></div>`).join("")}`;
    body.querySelectorAll("[data-repair]").forEach((button) => button.addEventListener("click", async () => {
      try {
        await post({ maintenance_line_ids: [button.dataset.repair] });
        toast("Intervention planifiée : le technicien la fera pendant la semaine.");
        stockView();
      } catch (error) { toast(`Maintenance impossible : ${error.message}`, true); }
    }));
  }

  return { open, close, render, isOpen: () => !root.hidden };
}
