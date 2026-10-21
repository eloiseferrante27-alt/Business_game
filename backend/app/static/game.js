const $ = (selector) => document.querySelector(selector);
let currentState = null;
let busy = false;

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail || `Erreur HTTP ${response.status}`;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join(", ") : detail);
  }
  return data;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function number(value) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Number(value || 0));
}

function notify(text, kind = "success") {
  const box = $("#notice");
  box.textContent = text;
  box.className = `show ${kind}`;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => { box.className = ""; }, 5000);
}

function render(state) {
  currentState = state;
  const kpi = state.kpis || {};
  $("#week").textContent = `Semaine ${String(state.current_week || 1).padStart(2, "0")}`;
  $("#otif").textContent = Number(kpi.otif || 0).toFixed(1).replace(".", ",");
  $("#trs").textContent = Number(kpi.trs || 0).toFixed(1).replace(".", ",");
  $("#stock-value").textContent = number(kpi.stock_value);
  $("#stockouts").textContent = number(kpi.stockouts);
  const ruptures = Number(kpi.stockouts || 0) > 0;
  $("#rupture-caption").innerHTML = `<i class="dot ${ruptures ? "red" : "green"}"></i> ${ruptures ? "Rupture à traiter" : "Tout est sous contrôle"}`;
  $("#connection").textContent = "API CONNECTÉE";
  $(".connected").innerHTML = "<i></i> Simulation active &nbsp;·&nbsp; G-MIX 2026";
  renderStocks(state.stocks || []);
  renderSuppliers(state.suppliers || []);
  renderLines(state.production_lines || []);
  renderEvents(state.events || []);
}

function renderStocks(stocks) {
  $("#sku-count").textContent = `${stocks.length} référence${stocks.length > 1 ? "s" : ""}`;
  if (!stocks.length) {
    $("#stock-rows").innerHTML = '<tr><td colspan="4">Aucun stock disponible.</td></tr>';
    return;
  }
  $("#stock-rows").innerHTML = stocks.map((stock, index) => {
    const qty = Number(stock.quantity);
    const safety = Number(stock.safety_stock);
    const status = qty <= 0 ? ["empty", "Rupture"] : qty < safety ? ["low", "À surveiller"] : ["healthy", "Sain"];
    const percent = Math.min(100, Math.round(qty / Math.max(1, safety * 3) * 100));
    return `<tr><td><div class="product"><span class="product-icon">${["▦", "◇", "▧", "◈"][index % 4]}</span><span><b>${escapeHTML(stock.name)}</b><small>${escapeHTML(stock.sku)}</small></span></div></td>
      <td class="quantity">${number(qty)} <small>u.</small></td>
      <td><span class="bar"><i class="${status[0]}" style="width:${percent}%"></i></span>${number(safety)} <small>u.</small></td>
      <td><span class="pill ${status[0]}"><i></i>${status[1]}</span></td></tr>`;
  }).join("");
  const sku = $("#sku");
  const selection = sku.value;
  sku.innerHTML = '<option value="">Choisir une référence…</option>' + stocks.map((item) =>
    `<option value="${escapeHTML(item.sku)}">${escapeHTML(item.name)} · ${number(item.quantity)} en stock</option>`
  ).join("");
  if (stocks.some((item) => item.sku === selection)) sku.value = selection;
}

function renderSuppliers(suppliers) {
  const select = $("#supplier");
  const selection = select.value;
  const active = suppliers.filter((supplier) => supplier.active !== false);
  select.innerHTML = '<option value="">Choisir un fournisseur…</option>' + active.map((item) =>
    `<option value="${escapeHTML(item.id)}">${escapeHTML(item.name)} · ${item.lead_time_weeks} sem. · ${Number(item.reliability).toFixed(0)}% fiable</option>`
  ).join("");
  if (active.some((item) => item.id === selection)) select.value = selection;
}

function renderLines(lines) {
  $("#lines").innerHTML = lines.length ? lines.map((line) => `<div class="line">
    <div class="line-head"><span>${escapeHTML(line.name)}</span><span>● OPÉRATIONNELLE</span></div>
    <p>${escapeHTML(line.product_sku)} · ${number(line.weekly_capacity)} u./sem.</p>
    <div class="line-track"><i style="width:${Math.max(0, Math.min(100, Number(line.efficiency)))}%"></i></div>
    <div class="line-meta"><span>TRS</span><span>${Number(line.efficiency).toFixed(0)}%</span></div>
  </div>`).join("") : "Aucune ligne configurée.");
}

function renderEvents(events) {
  if (!events.length) {
    $("#events").innerHTML = '<div class="event"><i></i><div><b>Marché stable</b><p>Aucun aléa signalé cette semaine.</p></div></div>';
    return;
  }
  $("#events").innerHTML = events.map((event) => {
    const text = String(event);
    const redSea = text.toLowerCase().includes("mer rouge");
    const materials = text.toLowerCase().includes("matières");
    const kind = redSea ? "disruption" : materials ? "materials" : "disruption";
    const title = redSea ? "Perturbation logistique" : materials ? "Hausse des matières" : "Aléa de marché";
    return `<div class="event ${kind}"><i></i><div><b>${title}</b><p>${escapeHTML(text)}</p></div></div>`;
  }).join("");
}

async function loadState() {
  try {
    render(await api("/api/state"));
  } catch (error) {
    $("#connection").textContent = "API HORS LIGNE";
    $(".connected").innerHTML = "<i></i> API déconnectée";
    notify(`Connexion impossible : ${error.message}`, "error");
  }
}

async function nextWeek() {
  if (busy) return;
  busy = true;
  const button = $("#next-turn");
  button.disabled = true;
  button.textContent = "◌  Simulation en cours…";
  try {
    const state = await api("/api/next-turn", { method: "POST", body: "{}" });
    render(state);
    notify(`Semaine ${state.current_week} simulée. Consultez les stocks et le marché.`);
  } catch (error) {
    notify(`La semaine n’a pas pu être lancée : ${error.message}`, "error");
  } finally {
    busy = false;
    button.disabled = false;
    button.innerHTML = "▶ &nbsp; Lancer la semaine <b>↗</b>";
  }
}

async function placeOrder(event) {
  event.preventDefault();
  const supplierId = $("#supplier").value;
  const sku = $("#sku").value;
  const quantity = Number($("#quantity").value);
  if (!supplierId || !sku || !Number.isInteger(quantity) || quantity < 1) {
    notify("Choisissez un fournisseur, une référence et une quantité valide.", "error");
    return;
  }
  const button = $(".confirm");
  button.disabled = true;
  try {
    const result = await api("/api/decisions", {
      method: "POST",
      body: JSON.stringify({ orders: [{ supplier_id: supplierId, sku, quantity }] }),
    });
    const supplier = currentState.suppliers.find((item) => item.id === supplierId);
    const arrival = Number(currentState.current_week) + Number(supplier?.lead_time_weeks || 0);
    $("#order-feedback").textContent = `${result.orders_queued} commande confirmée · arrivée estimée semaine ${arrival}.`;
    $("#quantity").value = "250";
    notify("Commande enregistrée et transmise à la simulation.");
  } catch (error) {
    notify(`Commande refusée : ${error.message}`, "error");
  } finally {
    button.disabled = false;
  }
}

$("#next-turn").addEventListener("click", nextWeek);
$("#order-form").addEventListener("submit", placeOrder);
loadState();
