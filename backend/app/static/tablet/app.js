// Tablette G-MIX : interface de jeu.
// Un rail de départements en haut, la scène au centre, et le menu du bas en trois boutons :
// KPIs · Outils · Configuration. Les chiffres viennent du moteur (/api/v2/tablet) ;
// l'onglet Configuration réaménage aussi l'usine 3D (forme du stock, tampons de production).
(function () {
  "use strict";

  const api = window.GMixLiveAPI.createLiveApi();
  const spreadsheet = window.GMixSpreadsheet;
  const $ = (s, r = document) => r.querySelector(s);

  const DEPTS = {
    usine: { icon: "🏭", nom: "Usine", couleur: "#d8f18a" },
    fournisseurs: { icon: "🌍", nom: "Fournisseurs", couleur: "#7cc6ff" },
    "quai-dechargement": { icon: "🚚", nom: "Quai", couleur: "#9fd6c0" },
    reception: { icon: "📋", nom: "Réception", couleur: "#9fd6c0" },
    stock: { icon: "📦", nom: "Stock", couleur: "#e8c66a" },
    production: { icon: "⚙️", nom: "Production", couleur: "#6fe0d0" },
    qualite: { icon: "🔍", nom: "Qualité", couleur: "#b7a6ff" },
    emballage: { icon: "🎁", nom: "Emballage", couleur: "#f2a65a" },
    maintenance: { icon: "🔧", nom: "Maintenance", couleur: "#ff8a65" },
    logistique: { icon: "🚛", nom: "Logistique", couleur: "#8fd18a" },
    clients: { icon: "🏬", nom: "Clients", couleur: "#f48fb1" },
  };
  // Outils utiles à chaque département (pas tous partout).
  const OUTILS = {
    usine: ["carte", "graphiques", "journal"],
    fournisseurs: ["carte", "comparateur", "tableur"],
    "quai-dechargement": ["planning", "journal"],
    reception: ["graphiques", "journal"],
    stock: ["tableur", "graphiques"],
    production: ["planning", "graphiques", "tableur"],
    qualite: ["graphiques", "journal"],
    emballage: ["graphiques", "planning"],
    maintenance: ["planning", "journal"],
    logistique: ["carte", "planning"],
    clients: ["carte", "tableur", "graphiques"],
  };
  const NOMS_OUTILS = { carte: ["🗺️", "Carte du trafic"], comparateur: ["⚖️", "Comparateur"], tableur: ["🧮", "SurExel"], graphiques: ["📈", "Graphiques"], planning: ["🗓️", "Planning"], journal: ["📜", "Journal"] };
  // Icônes des trois onglets (traits simples, dessinées en SVG pour rester nettes).
  const ico = (d) => `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const ONGLETS = [
    ["kpis", ico('<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>'), "KPIs", "Suivre"],
    ["outils", ico('<path d="M14.7 6.3a4 4 0 0 0-5.4 5.2L3 17.8V21h3.2l6.3-6.3a4 4 0 0 0 5.2-5.4l-2.6 2.6-2.5-.6-.6-2.5z"/>'), "Outils", "Analyser"],
    ["configuration", ico('<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>'), "Configuration", "Aménager"],
  ];

  let S = null; // dernier instantané du moteur
  let layout = { stock: { forme: "I" }, production: { tampons: {} } };
  let vue = { dept: "usine", onglet: "kpis", outil: null };
  let animations = [];
  let carteLeaflet = null;

  // ------------------------------------------------------------------ utilitaires
  const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const nf = (v, d = 0) => (v === null || v === undefined || Number.isNaN(Number(v)) ? "—" : new Intl.NumberFormat("fr-FR", { maximumFractionDigits: d }).format(Number(v)));
  const deptData = (id) => (S?.departments || []).find((d) => d.id === id);
  const stocks = (...cats) => (S?.raw?.stocks || []).filter((s) => !cats.length || cats.includes(s.category));

  function notifier(texte, type = "info") {
    const n = $("#notice");
    n.textContent = texte;
    n.className = `notice notice-${type}`;
    n.hidden = false;
    clearTimeout(notifier.t);
    notifier.t = setTimeout(() => { n.hidden = true; }, 3800);
  }

  // Pop-up rouge des refus : en haut de l'écran pendant 4 secondes.
  function popupRouge(message) {
    const toast = $("#toast");
    toast.innerHTML = `${esc(message)}`;
    toast.hidden = false;
    clearTimeout(popupRouge.t);
    popupRouge.t = window.setTimeout(() => { toast.hidden = true; }, 4000);
  }

  function prevenirParent(type, extra = {}) {
    if (window.parent && window.parent !== window) window.parent.postMessage({ type, ...extra }, window.location.origin);
  }

  async function charger() {
    S = await api.getState();
    try { layout = await (await fetch("/api/v2/tablet/layout")).json(); } catch { /* aménagement par défaut */ }
  }

  // ------------------------------------------------------------------ navigation (#departement/<id>/<onglet>)
  function lireAdresse() {
    const h = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
    if (h[0] === "departement" && h[1]) {
      vue.dept = DEPTS[h[1]] ? h[1] : "usine";
      vue.onglet = { configurations: "configuration" }[h[2]] || (ONGLETS.some((o) => o[0] === h[2]) ? h[2] : "kpis");
      vue.outil = h[3] || null;
    } else if (h[0] === "surexel") {
      vue = { dept: DEPTS[h[1]] ? h[1] : "usine", onglet: "surexel", outil: "tableur" };
    } else if (h[0] === "regles") {
      vue = { dept: "usine", onglet: "regles", outil: null };
    } else {
      vue = { dept: "usine", onglet: h[0] && ONGLETS.some((o) => o[0] === h[0]) ? h[0] : "kpis", outil: h[1] || null };
    }
  }
  function aller(dept, onglet = vue.onglet === "regles" ? "kpis" : vue.onglet, outil = null) {
    const h = dept === "usine" ? `#${onglet}${outil ? "/" + outil : ""}` : `#departement/${dept}/${onglet}${outil ? "/" + outil : ""}`;
    if (location.hash === h) rendre(); else location.hash = h;
  }

  // ------------------------------------------------------------------ cadre : barre du haut, rail, menu du bas
  function rendreCadre() {
    const g = (id) => S.globalKpis.find((k) => k.id === id);
    const mini = [["otif", "Service"], ["trs", "Rendement"], ["stock_value", "Stock"]].map(([id, l]) => {
      const k = g(id);
      return k ? `<span class="mini-kpi"><small>${l}</small><b>${nf(k.value, 1)}${k.unit === "%" ? " %" : k.unit === "€" ? " €" : ""}</b></span>` : "";
    }).join("");
    const graves = S.alerts.filter((a) => a.severity === "grave").length;
    $("#topbar").innerHTML = `
      <a class="marque" href="#kpis" aria-label="Accueil"><span class="logo-g">G</span><span><b>${esc(S.companyName || "G-MIX")}</b><small>Tablette de pilotage</small></span></a>
      <div class="semaine"><small>PÉRIODE</small><b>${esc(S.clock.label)}</b></div>
      <div class="minis">${mini}</div>
      <button class="alertes-btn ${graves ? "rouge" : S.alerts.length ? "orange" : ""}" data-action="alertes" title="Alertes"><b>${S.alerts.length}</b></button>
      <button class="btn-tour" data-action="next-turn" ${S.started && S.clock.canAdvance ? "" : "disabled"}>${S.clock.unit === "week" ? "Semaine suivante" : "Période suivante"}</button>
      <a class="btn-3d" href="/" data-action="close-tablet" title="Retour à l’usine 3D">Monde 3D</a>`;
    const statut = (id) => id === "usine" ? (graves ? "rouge" : S.alerts.length ? "orange" : "vert") : (deptData(id)?.status || "vert");
    $("#rail").innerHTML = Object.entries(DEPTS).map(([id, d]) => `
      <button class="rail-item ${vue.dept === id ? "actif" : ""}" data-dept="${id}" style="--c:${d.couleur}">
        <span class="rail-icone">${d.icon}</span><span class="rail-nom">${d.nom}</span><i class="point point-${statut(id)}"></i>
      </button>`).join("");
    $("#rail .actif")?.scrollIntoView({ block: "nearest", inline: "center" });
    $("#dock").innerHTML = ONGLETS.map(([id, icone, label, verbe]) => `
      <button class="dock-btn onglet-${id} ${vue.onglet === id ? "actif" : ""}" data-onglet="${id}" ${vue.onglet === id ? 'aria-current="page"' : ""}><span class="dock-ico">${icone}</span><span class="dock-txt"><b>${label}</b><small>${verbe}</small></span></button>`).join("");
    $("#dock").hidden = !S.started;
    $("#rail").hidden = !S.started;
  }

  // ------------------------------------------------------------------ rendu principal
  function rendre() {
    animations.forEach((a) => cancelAnimationFrame(a));
    animations = [];
    if (carteLeaflet) { carteLeaflet.remove(); carteLeaflet = null; }
    lireAdresse();
    rendreCadre();
    const scene = $("#stage");
    if (!S.started) { scene.innerHTML = ecranDemarrage(); return; }
    document.body.classList.toggle("mode-surexel", vue.onglet === "surexel");
    if (vue.onglet === "surexel") {
      document.title = "SurExel — G-MIX";
      scene.innerHTML = `<section id="outil-zone" class="surexel-page"></section>`;
      outilTableur($("#outil-zone"));
      return;
    }
    const d = DEPTS[vue.dept];
    const titre = `<header class="scene-tete" style="--c:${d.couleur}"><span class="scene-icone">${d.icon}</span><div><small>${vue.dept === "usine" ? "VUE D’ENSEMBLE" : "DÉPARTEMENT"}</small><h1>${esc(vue.dept === "usine" ? "Votre usine" : deptData(vue.dept)?.name || d.nom)}</h1></div>
      <p>${esc(vue.dept === "usine" ? "Toute l’usine en un coup d’œil." : deptData(vue.dept)?.description || "")}</p></header>`;
    if (vue.onglet === "regles") scene.innerHTML = ecranRegles();
    else if (vue.onglet === "outils") { scene.innerHTML = titre + ecranOutils(); monterOutil(); }
    else if (vue.onglet === "configuration") { scene.innerHTML = titre + ecranConfiguration(); monterConfiguration(); }
    else { scene.innerHTML = titre + (vue.dept === "usine" ? ecranUsine() : ecranKpis()); monterKpis(); }
    scene.scrollTop = 0;
  }

  // ------------------------------------------------------------------ KPIs
  function jauge(valeur, max = 100, couleur = "var(--c)") {
    const v = Math.max(0, Math.min(1, (Number(valeur) || 0) / max));
    const r = 34, c = 2 * Math.PI * r;
    return `<svg class="jauge" viewBox="0 0 80 80"><circle cx="40" cy="40" r="${r}" class="jauge-fond"/><circle cx="40" cy="40" r="${r}" class="jauge-val" style="stroke:${couleur}" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - v)}"/></svg>`;
  }
  const CLE_HISTO = { "OTIF clients": "otif", "OTIF client": "otif", "Rendement des lignes": "trs", "Valeur du stock": "stock_value", "Produits conformes": "produced", "Taux de qualité": "quality_rate",
    "Unités expédiées": "delivered", "Taux de service": "service_rate", "Achats de la période": "purchases_cost", "Production de la période": "produced", "Produits expédiés": "delivered" };
  function sparkline(cle) {
    const pts = (S.history || []).map((h) => h[cle]).filter((v) => v !== null && v !== undefined);
    if (pts.length < 2) return "";
    const min = Math.min(...pts), max = Math.max(...pts), w = 120, h = 30;
    const p = pts.map((v, i) => `${(i / (pts.length - 1)) * w},${h - ((v - min) / (max - min || 1)) * (h - 4) - 2}`).join(" ");
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline points="${p}"/></svg>`;
  }
  function carteKpi(k, dept) {
    const pct = k.unit === "%";
    const cle = k.id || CLE_HISTO[k.label];
    return `<article class="kpi ${pct ? "kpi-jauge" : ""}" ${dept ? `data-dept="${dept}"` : ""}>
      ${pct ? `<div class="kpi-anneau">${jauge(k.value)}<b>${nf(k.value, 1)}<small>%</small></b></div>` : `<div class="kpi-nombre">${nf(k.value, k.value > 100 ? 0 : 1)}<small>${esc(k.unit || "")}</small></div>`}
      <div class="kpi-label">${esc(k.label)}</div>${cle ? sparkline(cle) : ""}</article>`;
  }
  function listeAlertes(alertes) {
    if (!alertes.length) return `<div class="vide">Aucune alerte : tout roule.</div>`;
    return `<ul class="alertes">${alertes.map((a) => `<li class="alerte ${a.severity}" data-dept="${a.departmentId}"><i>${a.severity === "grave" ? "!" : "•"}</i><div><b>${esc(a.title)}</b><small>${esc(a.detail)}</small></div><span>${DEPTS[a.departmentId]?.icon || ""}</span></li>`).join("")}</ul>`;
  }

  function ecranUsine() {
    const m = S.mission;
    const tuiles = S.departments.map((d) => {
      const k = d.kpis[0];
      return `<button class="tuile" data-dept="${d.id}" style="--c:${DEPTS[d.id].couleur}"><span class="tuile-icone">${DEPTS[d.id].icon}</span><i class="point point-${d.status}"></i>
        <b>${esc(d.shortName)}</b><small>${k ? `${esc(k.label)} · <em>${nf(k.value, 1)} ${esc(k.unit || "")}</em>` : ""}</small></button>`;
    }).join("");
    return `
      ${m ? `<section class="mission" data-dept="${m.departmentId || ""}"><span>🎯</span><div><small>MISSION · ${esc(S.clock.label)}</small><h2>${esc(m.title)}</h2><p>${esc(m.detail)}</p></div>
        ${m.actionId ? `<button class="btn-principal" data-act="${m.actionId}" data-dept-act="${m.departmentId}">Agir</button>` : ""}</section>` : ""}
      <section class="grille-kpis">${S.globalKpis.map((k) => carteKpi(k, k.departmentId)).join("")}</section>
      <div class="deux">
        <section class="panneau"><h3>Les départements</h3><div class="tuiles">${tuiles}</div></section>
        <section class="panneau"><h3>Alertes</h3>${listeAlertes(S.alerts)}<h3 class="mt">Objectifs</h3>
          ${(S.objectives || []).length ? `<ul class="objectifs">${S.objectives.map((o) => `<li>${esc(o.label || o.title || o)}</li>`).join("")}</ul>` : `<div class="vide">Servez vos clients à l’heure, sans rupture, avec des lignes qui tournent.</div>`}
          <a class="lien" href="#regles">Règles de la partie</a></section>
      </div>`;
  }

  function ecranKpis() {
    const d = deptData(vue.dept);
    const alertes = S.alerts.filter((a) => a.departmentId === vue.dept || (vue.dept === "production" && a.departmentId === "maintenance"));
    return `
      <section class="grille-kpis">${d.kpis.map((k) => carteKpi(k)).join("")}</section>
      ${d.actions.length ? `<section class="actions">${d.actions.map((a) => `<button class="action" data-act="${a.id}"><span>${{ purchase: "🛒", production: "▶️", maintenance: "🔧", compare: "⚖️" }[a.id] || "⚡"}</span><b>${esc(a.label)}</b></button>`).join("")}</section>` : ""}
      ${vueDirect(vue.dept)}
      <div class="deux">
        <section class="panneau"><h3>Alertes</h3>${listeAlertes(alertes)}</section>
        <section class="panneau"><h3>Derniers événements</h3>${fil(S.events.filter((e) => e.departmentId === vue.dept).slice(-8).reverse())}</section>
      </div>
      ${d.tables.map(tableau).join("")}`;
  }

  // Petite scène « en direct » propre à quelques départements.
  function vueDirect(id) {
    const raw = S.raw;
    if (id === "stock") {
      const parties = [["MP", "Matières premières"], ["SF", "Semi-finis"], ["PF", "Produits finis"], ["PDR", "Pièces de rechange"]];
      return `<section class="panneau"><h3>Niveaux de stock</h3><div class="niveaux">${parties.map(([c, l]) => {
        const items = stocks(c);
        if (!items.length) return "";
        return `<div class="niveau-groupe"><h4>${l}</h4>${items.map((s) => {
          const p = Math.min(1, s.quantity / (s.capacity_max || Math.max(1, s.reorder_point * 2)));
          const etat = s.quantity === 0 ? "rouge" : s.quantity <= s.reorder_point ? "orange" : "vert";
          return `<div class="niveau"><span>${esc(s.name.replace(/^Composant · /, ""))}</span><div class="barre"><i class="${etat}" style="width:${p * 100}%"></i><em style="left:${Math.min(100, (s.reorder_point / (s.capacity_max || s.reorder_point * 2)) * 100)}%"></em></div><b>${nf(s.quantity)}</b></div>`;
        }).join("")}</div>`;
      }).join("")}</div><p class="note">Le petit trait vertical marque le point de commande.</p></section>`;
    }
    if (id === "production" || id === "maintenance") {
      return `<section class="panneau"><h3>Lignes en direct</h3><div class="lignes">${raw.production_lines.map((l) => `
        <div class="papier"><div class="papier-tete"><b>${esc(l.name)}</b><small>${esc(l.product_sku)} · rendement ${nf(l.efficiency, 0)} %${l.operational ? "" : " · <em>à l’arrêt</em>"}</small></div>${croquisLigne(l)}</div>`).join("")}</div></section>`;
    }
    if (id === "fournisseurs" || id === "logistique" || id === "clients" || id === "quai-dechargement") {
      const enRoute = id === "fournisseurs" || id === "quai-dechargement" ? raw.purchase_orders : raw.customer_orders.filter((o) => o.status === "ouverte" || o.status === "en retard");
      return `<section class="panneau mini-carte-panneau"><h3>${id === "fournisseurs" || id === "quai-dechargement" ? "Camions en approche" : "Commandes à livrer"}</h3>
        ${enRoute.length ? `<div class="convoi">${enRoute.slice(0, 8).map((o) => {
          const fin = o.arrival_week ?? o.due_week ?? S.raw.current_week;
          const reste = Math.max(0, fin - S.raw.current_week);
          return `<div class="convoi-ligne"><span>${esc(o.supplier_id ? (S.raw.suppliers.find((s) => s.id === o.supplier_id)?.name || o.supplier_id) : o.customer)}</span><div class="piste"><i style="left:${Math.max(4, 92 - reste * 22)}%">${o.supplier_id ? "🚚" : "🚛"}</i></div><b>${reste ? `S+${reste}` : "cette semaine"}</b></div>`;
        }).join("")}</div>` : `<div class="vide">Rien sur la route pour l’instant.</div>`}
        <button class="lien-btn" data-outil-go="${id === "quai-dechargement" ? "planning" : "carte"}">Ouvrir ${id === "quai-dechargement" ? "le planning" : "la carte du trafic"} →</button></section>`;
    }
    return "";
  }

  function tableau(t) {
    if (!t.rows.length) return `<section class="panneau"><h3>${esc(t.title)}</h3><div class="vide">Aucune ligne pour l’instant.</div></section>`;
    return `<section class="panneau"><div class="panneau-tete"><h3>${esc(t.title)}</h3><button class="lien-btn" data-tableur="${esc(t.id)}">Envoyer au tableur</button></div>
      <div class="table-defile"><table><thead><tr>${t.columns.map((c) => `<th>${esc(c.label)}</th>`).join("")}</tr></thead>
      <tbody>${t.rows.slice(0, 40).map((r) => `<tr>${t.columns.map((c) => {
        const v = r[c.key];
        const etat = /statut|state|status|État/i.test(c.key + c.label) ? `<span class="badge b-${/panne|rupture|retard|annul/i.test(v) ? "rouge" : /seuil|attente|ouverte|planifi/i.test(v) ? "orange" : "vert"}">${esc(v)}</span>` : null;
        return `<td>${etat ?? (typeof v === "number" ? nf(v, 2) : esc(v))}</td>`;
      }).join("")}</tr>`).join("")}</tbody></table></div></section>`;
  }

  function fil(evenements) {
    if (!evenements.length) return `<div class="vide">Pas encore d’événement.</div>`;
    return `<ul class="fil">${evenements.map((e) => `<li class="cause-${esc(e.cause)}"><time>${esc(e.time)}</time><span>${esc(e.message)}</span></li>`).join("")}</ul>`;
  }

  function monterKpis() {}

  // ------------------------------------------------------------------ OUTILS
  function ecranOutils() {
    const liste = OUTILS[vue.dept] || OUTILS.usine;
    if (!vue.outil || !liste.includes(vue.outil)) vue.outil = liste[0];
    return `<nav class="outils-onglets">${liste.map((o) => `<button class="outil-btn ${o === vue.outil ? "actif" : ""}" data-outil="${o}"><span>${NOMS_OUTILS[o][0]}</span>${NOMS_OUTILS[o][1]}</button>`).join("")}</nav>
      <section class="outil-zone" id="outil-zone"></section>`;
  }
  function monterOutil() {
    const zone = $("#outil-zone");
    ({ carte: outilCarte, comparateur: outilComparateur, tableur: outilTableur, graphiques: outilGraphiques, planning: outilPlanning, journal: outilJournal })[vue.outil](zone);
  }

  // --- carte du trafic -------------------------------------------------
  const VILLES = { lille: [50.63, 3.06], bordeaux: [44.84, -0.58], nantes: [47.22, -1.55], strasbourg: [48.58, 7.75], lyon: [45.76, 4.84], toulouse: [43.6, 1.44],
    marseille: [43.3, 5.37], paris: [48.86, 2.35], rouen: [49.44, 1.1], montpellier: [43.61, 3.88], nice: [43.7, 7.26], rennes: [48.11, -1.68], dijon: [47.32, 5.04],
    milan: [45.46, 9.19], stuttgart: [48.78, 9.18], barcelone: [41.39, 2.17], madrid: [40.42, -3.7], bruxelles: [50.85, 4.35], tanger: [35.76, -5.83], casablanca: [33.57, -7.59],
    istanbul: [41.0, 28.97], shanghai: [31.23, 121.47], ningbo: [29.87, 121.54] };
  const USINE = { nom: "Usine G-MIX", gps: [45.68, 5.02] };
  const CLIENTS_GPS = { "Hypermarché Atlas": "paris", "Centrale Nord": "rouen", "Boutique Médina": "montpellier", "Distrib Sud": "nice" };
  function gpsDe(texte, graine = 0) {
    const cle = String(texte || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").split(/[ ,·-]/).find((m) => VILLES[m]);
    if (cle) return VILLES[cle];
    let h = graine; for (const c of String(texte)) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return [43 + (h % 700) / 100, -1 + ((h >> 8) % 900) / 100];
  }
  function arc(a, b, n = 40) {
    const [la, lo] = a, [lb, lob] = b;
    const mx = (la + lb) / 2 + Math.abs(lob - lo) * 0.18 + 0.4, my = (lo + lob) / 2;
    const pts = [];
    for (let i = 0; i <= n; i++) { const t = i / n; pts.push([(1 - t) ** 2 * la + 2 * (1 - t) * t * mx + t * t * lb, (1 - t) ** 2 * lo + 2 * (1 - t) * t * my + t * t * lob]); }
    return pts;
  }
  function flux() {
    const raw = S.raw;
    const vus = {};
    const fournisseurs = raw.suppliers.filter((s) => s.active).map((s, i) => {
      // Fournisseurs de la même ville (ou de la ville de l'usine) : écartés en cercle pour rester lisibles.
      let [la, lo] = gpsDe(s.region, i);
      const cle = `${la.toFixed(1)},${lo.toFixed(1)}`;
      const rang = (vus[cle] = (vus[cle] || 0) + 1);
      const pres = Math.hypot(la - USINE.gps[0], lo - USINE.gps[1]) < 0.6;
      if (rang > 1 || pres) { const a = (rang + (pres ? 1 : 0)) * 2.1; la += Math.sin(a) * 0.9; lo += Math.cos(a) * 1.2; }
      return { type: "fournisseur", id: s.id, nom: s.name, sous: s.specialty || s.region, gps: [la, lo], delai: s.lead_time_weeks, commandes: raw.purchase_orders.filter((o) => o.supplier_id === s.id) };
    });
    const noms = [...new Set([...Object.keys(CLIENTS_GPS), ...raw.customer_orders.map((o) => o.customer)])];
    const clients = noms.map((n, i) => ({ type: "client", id: n, nom: n, gps: VILLES[CLIENTS_GPS[n]] || gpsDe(n, i + 7), commandes: raw.customer_orders.filter((o) => o.customer === n && (o.status === "ouverte" || o.status === "en retard")) }));
    return { fournisseurs, clients };
  }
  const COULEURS = { fournisseur: "#0a84ff", client: "#5e5ce6" };
  function outilCarte(zone) {
    const { fournisseurs, clients } = flux();
    const montrerFour = vue.dept !== "clients" && vue.dept !== "logistique";
    const montrerCli = vue.dept !== "fournisseurs";
    const points = [...(montrerFour ? fournisseurs : []), ...(montrerCli ? clients : [])];
    const enCours = points.reduce((n, p) => n + p.commandes.length, 0);
    const carteItem = (p) => `<button class="carte-item ${p.type}" data-point="${esc(p.id)}"><b>${esc(p.nom)}</b>
      <small>${p.type === "fournisseur" ? `${esc(p.sous)} · ${p.delai} sem.` : "Client"}</small>${p.commandes.length ? `<em>${p.commandes.length} envoi${p.commandes.length > 1 ? "s" : ""} en cours</em>` : ""}</button>`;
    const groupe = (titre, liste) => liste.length ? `<h4 class="carte-groupe">${titre}</h4>${liste.map(carteItem).join("")}` : "";
    zone.innerHTML = `<div class="carte-jeu">
      <div class="carte-hud">${montrerFour ? `<span><i class="leg four"></i>Fournisseurs</span>` : ""}${montrerCli ? `<span><i class="leg cli"></i>Clients</span>` : ""}
        <span class="espace"></span><span><b>${enCours}</b> envoi${enCours > 1 ? "s" : ""} sur la route</span></div>
      <div class="carte-cadre"><div class="carte-fond" id="carte-fond" role="application" aria-label="Carte des fournisseurs et clients"></div><div class="carte-fiche" id="carte-fiche" hidden></div></div>
      <div class="carte-liste">${groupe("Fournisseurs", points.filter((p) => p.type === "fournisseur"))}${groupe("Clients", points.filter((p) => p.type === "client"))}</div></div>`;
    const fond = $("#carte-fond");
    let carte = null;
    const fiche = (p) => {
      const f = $("#carte-fiche");
      f.hidden = false;
      zone.querySelectorAll(".carte-item").forEach((b) => b.classList.toggle("actif", b.dataset.point === p.id));
      if (carte) carte.panTo(p.gps, { animate: true });
      f.innerHTML = `<button class="modal-fermer" data-fermer-fiche aria-label="Fermer">×</button><h4>${esc(p.nom)}</h4>
        ${p.type === "fournisseur" ? `<p>${esc(p.sous)} · délai ${p.delai} semaine${p.delai > 1 ? "s" : ""}</p>` : `<p>Client de l’usine</p>`}
        ${p.commandes.length ? `<ul>${p.commandes.map((o) => `<li>${nf(o.quantity)} × ${esc(o.sku)} · ${o.arrival_week ? `arrivée S${o.arrival_week}` : `échéance S${o.due_week}`}</li>`).join("")}</ul>` : `<p class="note">Aucun envoi en cours.</p>`}
        ${p.type === "fournisseur" ? `<button class="btn-principal" data-act="purchase" data-fournisseur="${esc(p.id)}">Commander</button>` : ""}`;
    };
    zone.querySelectorAll("[data-point]").forEach((b) => b.addEventListener("click", () => fiche(points.find((p) => p.id === b.dataset.point))));
    zone.addEventListener("click", (e) => { if (e.target.matches("[data-fermer-fiche]")) { $("#carte-fiche").hidden = true; zone.querySelectorAll(".carte-item.actif").forEach((b) => b.classList.remove("actif")); } });
    const avecFond = () => { fond.innerHTML = ""; carte = carteAvecFond(fond, points, fiche); };
    if (window.L) avecFond();
    else { carteSvg(fond, points, fiche); chargerLeaflet().then((ok) => { if (ok && document.body.contains(fond) && vue.outil === "carte") avecFond(); }); }
  }
  function chargerLeaflet() {
    if (window.L) return Promise.resolve(true);
    if (chargerLeaflet.p) return chargerLeaflet.p;
    chargerLeaflet.p = new Promise((ok) => {
      document.head.insertAdjacentHTML("beforeend", '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">');
      const s = document.createElement("script");
      s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
      const t = setTimeout(() => ok(false), 6000);
      s.onload = () => { clearTimeout(t); ok(!!window.L); };
      s.onerror = () => { clearTimeout(t); ok(false); };
      document.head.append(s);
    });
    return chargerLeaflet.p;
  }
  // Fond OpenStreetMap (données ouvertes, licence ODbL), adouci en CSS pour rester un décor.
  function carteAvecFond(fond, points, fiche) {
    const L = window.L;
    const carte = L.map(fond, { zoomControl: true, attributionControl: true, worldCopyJump: true, minZoom: 2 });
    carteLeaflet = carte;
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 12, attribution: "© contributeurs <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a>" }).addTo(carte);
    const mobiles = [];
    for (const p of points) {
      const chemin = p.type === "fournisseur" ? arc(p.gps, USINE.gps) : arc(USINE.gps, p.gps);
      const couleur = COULEURS[p.type];
      const actif = p.commandes.length > 0;
      L.polyline(chemin, { color: couleur, weight: actif ? 2.5 : 1.2, opacity: actif ? 0.85 : 0.35, dashArray: actif ? null : "3 6", interactive: false }).addTo(carte);
      L.circleMarker(p.gps, { radius: 7, color: "#fff", weight: 2, fillColor: couleur, fillOpacity: 1 })
        .bindTooltip(esc(p.nom), { className: "etiquette", direction: "top", offset: [0, -8] }).on("click", () => fiche(p)).addTo(carte);
      // Un point mobile par envoi réel : rien ne bouge s'il n'y a rien sur la route.
      p.commandes.forEach((_, i) => {
        const m = L.circleMarker(chemin[0], { radius: 4, color: "#fff", weight: 1.5, fillColor: couleur, fillOpacity: 1, interactive: false }).addTo(carte);
        mobiles.push({ m, chemin, phase: i / p.commandes.length, vitesse: 0.05 / Math.max(1, p.delai || 1) });
      });
    }
    L.marker(USINE.gps, { icon: L.divIcon({ className: "usine-carte", html: "<i></i><b>Usine</b>", iconSize: [0, 0] }), keyboard: false }).addTo(carte);
    carte.fitBounds(L.latLngBounds([USINE.gps, ...points.map((p) => p.gps)]), { padding: [56, 56], maxZoom: 7 });
    let dernier = performance.now();
    const boucle = (t) => {
      const dt = (t - dernier) / 1000; dernier = t;
      for (const o of mobiles) { o.phase = (o.phase + dt * o.vitesse) % 1; const i = Math.floor(o.phase * (o.chemin.length - 1)); o.m.setLatLng(o.chemin[i]); }
      animations.push(requestAnimationFrame(boucle));
    };
    if (mobiles.length && !matchMedia("(prefers-reduced-motion: reduce)").matches) animations.push(requestAnimationFrame(boucle));
    setTimeout(() => carte.invalidateSize(), 60);
    return carte;
  }
  // Carte de secours sans réseau : France stylisée, routes et envois animés en SVG.
  function carteSvg(fond, points, fiche) {
    const proj = ([la, lo]) => [(lo + 6) * 62, (52 - la) * 88];
    const contour = [[51.1, 2.5], [50.1, 1.6], [49.4, 0.1], [49.7, -1.9], [48.6, -1.6], [48.8, -3.2], [48.4, -4.8], [47.6, -3.0], [47.2, -2.2], [46.2, -1.2], [45.5, -1.2], [44.6, -1.25], [43.4, -1.7],
      [42.8, -0.3], [42.5, 1.8], [42.5, 3.1], [43.3, 3.5], [43.5, 4.6], [43.1, 6.0], [43.7, 7.5], [44.5, 6.9], [45.2, 7.1], [46.4, 6.8], [46.4, 6.1], [47.5, 7.6], [48.6, 7.8], [49.0, 8.2], [49.5, 6.4], [49.6, 5.4], [50.2, 4.2], [51.1, 2.5]];
    const pc = contour.map(proj).map((p) => p.join(",")).join(" ");
    const usine = proj(USINE.gps);
    let svg = `<svg class="carte-svg" viewBox="0 0 900 900"><rect width="900" height="900" class="mer"/><polygon points="${pc}" class="pays"/>`;
    points.forEach((p, k) => {
      const chemin = (p.type === "fournisseur" ? arc(p.gps, USINE.gps) : arc(USINE.gps, p.gps)).map(proj);
      const d = `M${chemin.map((x) => x.join(" ")).join(" L")}`;
      const couleur = COULEURS[p.type];
      svg += `<path d="${d}" class="route ${p.commandes.length ? "active" : ""}" style="stroke:${couleur}"/>`;
      const dur = 6 + (p.delai || 1) * 3;
      p.commandes.forEach((_, i) => {
        svg += `<circle r="5" fill="${couleur}" stroke="#fff" stroke-width="2"><animateMotion dur="${dur}s" begin="-${(i / p.commandes.length) * dur + k}s" repeatCount="indefinite" path="${d}"/></circle>`;
      });
      const [x, y] = proj(p.gps);
      svg += `<g class="ville" data-point="${esc(p.id)}"><circle cx="${x}" cy="${y}" r="9" fill="${couleur}" stroke="#fff" stroke-width="3"/><text x="${x + 14}" y="${y + 5}">${esc(p.nom)}</text></g>`;
    });
    svg += `<g class="usine-svg"><rect x="${usine[0] - 15}" y="${usine[1] - 15}" width="30" height="30" rx="8"/><text x="${usine[0]}" y="${usine[1] + 7}" text-anchor="middle">G</text><text class="usine-nom" x="${usine[0]}" y="${usine[1] + 36}" text-anchor="middle">Usine</text></g></svg>`;
    fond.innerHTML = svg;
    fond.querySelectorAll(".ville").forEach((g) => g.addEventListener("click", () => fiche(points.find((p) => p.id === g.dataset.point))));
  }

  // --- comparateur -----------------------------------------------------
  function outilComparateur(zone) {
    const mp = stocks("MP", "PDR");
    zone.innerHTML = `<div class="comparo"><div class="champ-ligne"><label>Matière <select id="cmp-sku">${mp.map((s) => `<option value="${esc(s.sku)}">${esc(s.name)}</option>`).join("")}</select></label>
      <label>Quantité <input id="cmp-qte" type="number" min="1" value="${mp[0]?.reorder_qty || 500}"></label><button class="btn-principal" id="cmp-go">Comparer</button></div><div id="cmp-res" class="cmp-res"></div></div>`;
    const go = async () => {
      const res = $("#cmp-res");
      try {
        const offres = await api.compare($("#cmp-sku").value, Number($("#cmp-qte").value) || 1);
        if (!offres.length) { res.innerHTML = `<div class="vide">Aucun fournisseur pour cette matière.</div>`; return; }
        const min = Math.min(...offres.map((o) => o.total_cost ?? Infinity));
        const maxCout = Math.max(...offres.map((o) => o.total_cost || 0));
        res.innerHTML = offres.map((o) => {
          const nom = o.supplier_name || S.raw.suppliers.find((s) => s.id === o.supplier_id)?.name || o.supplier_id;
          const best = o.total_cost === min;
          return `<article class="offre ${best ? "meilleure" : ""}">${best ? `<span class="ruban">MEILLEUR PRIX</span>` : ""}<h4>${esc(nom)}</h4>
            ${Object.keys(LIBELLES).filter((k) => typeof o[k] === "number").map((k) => `<div class="stat"><span>${esc(LIBELLES[k])}</span><b>${nf(o[k], 2)}</b></div>`).join("")}
            <div class="barre"><i class="${best ? "vert" : "orange"}" style="width:${((o.total_cost || 0) / (maxCout || 1)) * 100}%"></i></div>
            <button class="btn-secondaire" data-act="purchase" data-fournisseur="${esc(o.supplier_id)}" data-sku="${esc($("#cmp-sku").value)}" data-qte="${esc($("#cmp-qte").value)}">Commander</button></article>`;
        }).join("");
      } catch (e) { res.innerHTML = `<div class="vide">${esc(e.message)}</div>`; }
    };
    $("#cmp-go").addEventListener("click", go);
    go();
  }
  const LIBELLES = { unit_price: "Prix unitaire (€)", total_cost: "Coût total (€)", lead_time_weeks: "Délai (semaines)", expected_arrival_week: "Arrivée (semaine)", reliability: "Fiabilité (%)",
    nonconformity_rate: "Non-conformité (%)", expected_good_quantity: "Quantité conforme attendue" };

  // --- tableur ---------------------------------------------------------
  const cleTableur = () => `gmix-tableur:${S.gameId}:${S.companyName}`;
  function lireGrille() {
    try { const g = JSON.parse(localStorage.getItem(cleTableur())); if (Array.isArray(g) && g.length) return g; } catch { /* vide */ }
    return spreadsheet.createGrid(16, 8);
  }
  function ecrireGrille(g) { try { localStorage.setItem(cleTableur(), JSON.stringify(g)); } catch { /* stockage indisponible */ } }
  function envoyerTableur(tableId) {
    const t = (deptData(vue.dept)?.tables || []).find((x) => x.id === tableId);
    if (!t) return;
    const valeurs = [t.columns.map((c) => c.label), ...t.rows.map((r) => t.columns.map((c) => r[c.key] ?? ""))];
    ecrireGrille(spreadsheet.createGrid(Math.max(16, valeurs.length + 4), Math.max(8, t.columns.length + 2), valeurs));
    notifier(`« ${t.title} » envoyé dans SurExel.`, "ok");
    if (vue.onglet === "surexel") rendre(); else aller(vue.dept, "outils", "tableur");
  }
  // SurExel : le tableur de la tablette, présenté comme une appli de classeur.
  function outilTableur(zone) {
    let grille = lireGrille();
    let sel = { r: 0, c: 0 };
    const tables = (deptData(vue.dept)?.tables || []).filter((t) => t.rows.length);
    const nomCellule = (r, c) => `${spreadsheet.columnName(c)}${r + 1}`;
    const dessiner = () => {
      zone.innerHTML = `<div class="surexel">
        <header class="sx-titre"><span class="sx-logo" aria-hidden="true">S</span><b>SurExel</b><span class="sx-doc">Classeur · ${esc(DEPTS[vue.dept].nom)}</span><span class="espace"></span>
          ${vue.onglet === "surexel" ? "" : `<button class="sx-onglet" data-t="onglet">Ouvrir dans un nouvel onglet ↗</button>`}</header>
        <div class="sx-ruban">${tables.map((t) => `<button class="sx-outil" data-tableur="${esc(t.id)}">Importer « ${esc(t.title)} »</button>`).join("")}
          <span class="espace"></span><button class="sx-outil" data-t="ligne">+ Ligne</button><button class="sx-outil" data-t="col">+ Colonne</button><button class="sx-outil" data-t="csv">Exporter CSV</button><button class="sx-outil danger" data-t="vider">Effacer</button></div>
        <div class="sx-formule"><span class="sx-nom" id="sx-nom">A1</span><span class="sx-fx">fx</span><input id="sx-barre" aria-label="Contenu de la cellule sélectionnée" autocomplete="off" spellcheck="false"></div>
        <div class="tableur-defile"><table class="tableur"><thead><tr><th></th>${grille[0].map((_, c) => `<th data-col="${c}">${spreadsheet.columnName(c)}</th>`).join("")}</tr></thead>
        <tbody>${grille.map((ligne, r) => `<tr><th data-lig="${r}">${r + 1}</th>${ligne.map((v, c) => `<td><input data-r="${r}" data-c="${c}" value="${esc(v)}" aria-label="${nomCellule(r, c)}" spellcheck="false"><output data-o="${r}-${c}"></output></td>`).join("")}</tr>`).join("")}</tbody></table></div>
        <footer class="sx-feuilles"><span class="sx-feuille">Feuille 1</span><span class="sx-aide"><code>=SOMME(A1:A5)</code> <code>=MOYENNE(…)</code> <code>MIN</code> <code>MAX</code> <code>=SI(A1&gt;0;"oui";"non")</code> · SurExel ne modifie jamais la partie.</span></footer></div>`;
      calculer();
      choisir(sel.r, sel.c, false);
    };
    const calculer = () => zone.querySelectorAll("input[data-r]").forEach((i) => {
      const v = grille[i.dataset.r][i.dataset.c];
      const o = zone.querySelector(`[data-o="${i.dataset.r}-${i.dataset.c}"]`);
      const formule = typeof v === "string" && v.trim().startsWith("=");
      o.textContent = formule ? spreadsheet.evaluate(v, grille) : "";
      i.classList.toggle("formule", formule);
    });
    const choisir = (r, c, focus = true) => {
      if (!grille[r] || grille[r][c] === undefined) return;
      sel = { r, c };
      $("#sx-nom").textContent = nomCellule(r, c);
      $("#sx-barre").value = grille[r][c];
      zone.querySelectorAll(".sel").forEach((x) => x.classList.remove("sel"));
      zone.querySelector(`[data-col="${c}"]`)?.classList.add("sel");
      zone.querySelector(`[data-lig="${r}"]`)?.classList.add("sel");
      const i = zone.querySelector(`input[data-r="${r}"][data-c="${c}"]`);
      i?.parentElement.classList.add("sel");
      if (focus) i?.focus();
    };
    zone.addEventListener("focusin", (e) => { const i = e.target.closest("input[data-r]"); if (i) choisir(Number(i.dataset.r), Number(i.dataset.c), false); });
    zone.addEventListener("input", (e) => {
      if (e.target.id === "sx-barre") {
        grille[sel.r][sel.c] = e.target.value;
        zone.querySelector(`input[data-r="${sel.r}"][data-c="${sel.c}"]`).value = e.target.value;
      } else {
        const i = e.target.closest("input[data-r]"); if (!i) return;
        grille[i.dataset.r][i.dataset.c] = i.value;
        $("#sx-barre").value = i.value;
      }
      ecrireGrille(grille); calculer();
    });
    // Entrée descend d'une ligne, comme dans un classeur.
    zone.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      if (e.target.closest("input[data-r]") || e.target.id === "sx-barre") { e.preventDefault(); choisir(sel.r + 1, sel.c); }
    });
    zone.addEventListener("click", (e) => {
      const b = e.target.closest("[data-t]"); if (!b) return;
      if (b.dataset.t === "onglet") { window.open(`/tablet/#surexel/${vue.dept}`, "_blank", "noopener"); return; }
      if (b.dataset.t === "ligne") grille.push(grille[0].map(() => ""));
      if (b.dataset.t === "col") grille.forEach((l) => l.push(""));
      if (b.dataset.t === "vider") { if (!confirm("Effacer toute la feuille ?")) return; grille = spreadsheet.createGrid(16, 8); sel = { r: 0, c: 0 }; }
      if (b.dataset.t === "csv") {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob(["\ufeff", spreadsheet.toCsv(grille)], { type: "text/csv;charset=utf-8" }));
        a.download = "surexel-gmix.csv"; a.click(); return;
      }
      ecrireGrille(grille); dessiner();
    });
    dessiner();
  }
  // Le classeur ouvert dans un autre onglet suit les modifications.
  window.addEventListener("storage", (e) => { if (S && e.key === cleTableur() && vue.outil === "tableur") rendre(); });

  // --- graphiques ------------------------------------------------------
  const SERIES = [["otif", "OTIF clients", "%"], ["service_rate", "Taux de service", "%"], ["trs", "Rendement", "%"], ["quality_rate", "Qualité", "%"], ["produced", "Production", ""],
    ["delivered", "Expéditions", ""], ["stock_value", "Valeur du stock", "€"], ["purchases_cost", "Achats", "€"], ["stockouts", "Ruptures", ""]];
  const SERIES_DEPT = { stock: ["stock_value", "stockouts", "purchases_cost"], production: ["produced", "trs", "quality_rate"], qualite: ["quality_rate", "produced"], emballage: ["produced", "delivered"],
    reception: ["purchases_cost", "quality_rate"], clients: ["otif", "service_rate", "delivered"], usine: ["otif", "trs", "produced", "stock_value"] };
  function outilGraphiques(zone) {
    let choix = (SERIES_DEPT[vue.dept] || SERIES_DEPT.usine).slice(0, 2);
    const dessiner = () => {
      zone.innerHTML = `<div class="puces">${SERIES.map(([k, l]) => `<button class="puce ${choix.includes(k) ? "actif" : ""}" data-serie="${k}">${l}</button>`).join("")}</div>
        <div class="graph-cadre"><canvas id="graph" height="320"></canvas></div><div class="legende">${choix.map((k, i) => `<span><i style="background:${PALETTE[i]}"></i>${SERIES.find((s) => s[0] === k)[1]}</span>`).join("")}</div>
        ${(S.history || []).length < 2 ? `<p class="note">Jouez quelques semaines pour voir les courbes se dessiner.</p>` : ""}`;
      courbes($("#graph"), choix);
    };
    zone.addEventListener("click", (e) => {
      const b = e.target.closest("[data-serie]"); if (!b) return;
      const k = b.dataset.serie;
      choix = choix.includes(k) ? choix.filter((x) => x !== k) : [...choix, k].slice(-3);
      dessiner();
    });
    dessiner();
  }
  const PALETTE = ["#0071e3", "#5e5ce6", "#ff9f0a"];
  function courbes(canvas, cles) {
    const ratio = devicePixelRatio || 1, w = canvas.clientWidth || 700, h = 320;
    canvas.width = w * ratio; canvas.height = h * ratio;
    const ctx = canvas.getContext("2d"); ctx.scale(ratio, ratio);
    const histo = S.history || [];
    const m = { g: 44, d: 16, h: 16, b: 30 };
    ctx.font = "12px system-ui"; ctx.fillStyle = "#86868b";
    const n = Math.max(histo.length, 2);
    const x = (i) => m.g + (i / (n - 1)) * (w - m.g - m.d);
    for (let k = 0; k <= 4; k++) { const y = m.h + k * (h - m.h - m.b) / 4; ctx.strokeStyle = "#ececf0"; ctx.beginPath(); ctx.moveTo(m.g, y); ctx.lineTo(w - m.d, y); ctx.stroke(); }
    histo.forEach((p, i) => { if (n < 16 || i % Math.ceil(n / 12) === 0) ctx.fillText(`S${p.period}`, x(i) - 8, h - 8); });
    cles.forEach((cle, s) => {
      const vals = histo.map((p) => p[cle]);
      const ok = vals.filter((v) => v !== null && v !== undefined);
      if (!ok.length) return;
      const max = Math.max(...ok) * 1.1 || 1, min = Math.min(0, ...ok);
      const y = (v) => m.h + (1 - (v - min) / (max - min || 1)) * (h - m.h - m.b);
      const grad = ctx.createLinearGradient(0, m.h, 0, h - m.b); grad.addColorStop(0, PALETTE[s] + "22"); grad.addColorStop(1, PALETTE[s] + "00");
      ctx.beginPath(); let premier = null, dernierX = 0;
      vals.forEach((v, i) => { if (v === null || v === undefined) return; if (premier === null) { ctx.moveTo(x(i), y(v)); premier = i; } else ctx.lineTo(x(i), y(v)); dernierX = x(i); });
      ctx.strokeStyle = PALETTE[s]; ctx.lineWidth = 2; ctx.stroke();
      ctx.lineTo(dernierX, h - m.b); ctx.lineTo(x(premier), h - m.b); ctx.closePath(); ctx.fillStyle = grad; ctx.fill();
      vals.forEach((v, i) => { if (v === null || v === undefined) return; ctx.beginPath(); ctx.arc(x(i), y(v), 3, 0, 7); ctx.fillStyle = PALETTE[s]; ctx.fill(); });
    });
  }

  // --- planning --------------------------------------------------------
  function outilPlanning(zone) {
    const raw = S.raw, s0 = raw.current_week, semaines = Array.from({ length: 7 }, (_, i) => s0 + i);
    const col = (s) => Math.max(0, Math.min(semaines.length - 1, s - s0));
    const lignes = [];
    const nomF = (id) => raw.suppliers.find((s) => s.id === id)?.name || id;
    if (["quai-dechargement", "fournisseurs", "usine", "stock"].includes(vue.dept) || !["production", "maintenance", "emballage", "logistique"].includes(vue.dept))
      raw.purchase_orders.forEach((o) => lignes.push({ groupe: "Arrivées fournisseurs", nom: nomF(o.supplier_id), de: s0, a: o.arrival_week, label: `${nf(o.quantity)} × ${o.sku}`, c: "#0a84ff" }));
    if (["production", "emballage", "usine"].includes(vue.dept))
      raw.production_orders.forEach((o) => lignes.push({ groupe: "Ordres de fabrication", nom: o.id, de: s0, a: s0, label: `${nf(o.quantity)} × ${o.sku}`, c: "#30b0c7" }));
    if (["logistique", "emballage", "usine", "clients"].includes(vue.dept))
      raw.customer_orders.filter((o) => o.status === "ouverte" || o.status === "en retard").forEach((o) => lignes.push({ groupe: "Livraisons clients", nom: o.customer, de: Math.min(s0, o.due_week), a: o.due_week, label: `${nf(o.quantity)} × ${o.sku}`, c: o.status === "en retard" ? "#ff3b30" : "#5e5ce6" }));
    if (["maintenance", "production"].includes(vue.dept))
      raw.production_lines.forEach((l) => lignes.push({ groupe: "Maintenance", nom: l.name, de: s0, a: s0, label: l.operational ? (raw.maintenance_queue.includes(l.id) ? "Intervention planifiée" : "En service") : "EN PANNE", c: l.operational ? "#aeaeb2" : "#ff9f0a" }));
    const groupes = [...new Set(lignes.map((l) => l.groupe))];
    zone.innerHTML = `<div class="gantt"><div class="gantt-tete"><span></span>${semaines.map((s, i) => `<span class="${i === 0 ? "maintenant" : ""}">S${s}</span>`).join("")}</div>
      ${groupes.length ? groupes.map((g) => `<div class="gantt-groupe">${g}</div>${lignes.filter((l) => l.groupe === g).map((l) => `<div class="gantt-ligne"><span class="gantt-nom">${esc(l.nom)}</span>
        <div class="gantt-piste"><i class="gantt-barre" style="left:${(col(l.de) / semaines.length) * 100}%;width:${((col(l.a) - col(l.de) + 1) / semaines.length) * 100}%;background:${l.c}">${esc(l.label)}</i></div></div>`).join("")}`).join("")
        : `<div class="vide">Rien de prévu sur les prochaines semaines.</div>`}</div>`;
  }

  // --- journal ---------------------------------------------------------
  function outilJournal(zone) {
    let cause = "";
    const dessiner = () => {
      const evs = S.events.filter((e) => (vue.dept === "usine" || e.departmentId === vue.dept) && (!cause || e.cause === cause)).slice(-120).reverse();
      zone.innerHTML = `<div class="puces">${[["", "Tout"], ["decision", "Mes décisions"], ["regle", "Règles du moteur"], ["alea", "Aléas"]].map(([v, l]) => `<button class="puce ${cause === v ? "actif" : ""}" data-cause="${v}">${l}</button>`).join("")}</div>${fil(evs)}`;
    };
    zone.addEventListener("click", (e) => { const b = e.target.closest("[data-cause]"); if (b) { cause = b.dataset.cause; dessiner(); } });
    dessiner();
  }

  // ------------------------------------------------------------------ CONFIGURATION
  const FORMES = {
    I: ["En ligne", "Une rangée de racks contre le mur du fond. Simple, allées larges."],
    L: ["En L", "Le fond et un côté : plus de places, le chariot tourne une fois."],
    U: ["En U", "Trois côtés : capacité maximale, une seule allée centrale."],
    V: ["En V (épi)", "Racks inclinés en épi, ouverts vers l’allée : prélèvement rapide."],
  };
  function planForme(f) {
    const racks = { I: [[20, 14, 80, 14]], L: [[20, 14, 80, 14], [14, 20, 14, 62]], U: [[20, 14, 80, 14], [14, 20, 14, 62], [86, 20, 86, 62]], V: [[12, 12, 24, 36], [30, 12, 42, 36], [70, 12, 58, 36], [88, 12, 76, 36]] }[f];
    return `<svg viewBox="0 0 100 76" class="plan-forme"><rect x="2" y="2" width="96" height="72" rx="6" class="plan-sol"/>
      ${racks.map(([x1, y1, x2, y2]) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="plan-rack"/>`).join("")}
      <rect x="40" y="66" width="20" height="8" class="plan-porte"/><circle cx="50" cy="${f === "V" ? 54 : 44}" r="4" class="plan-chariot"/></svg>`;
  }
  const tampon = (ligne, i) => (layout.production.tampons[ligne] || [])[i] || 0;

  function ecranConfiguration() {
    const d = deptData(vue.dept);
    let contenu = "";
    if (vue.dept === "stock" || vue.dept === "usine") {
      const forme = layout.stock.forme;
      contenu += `<section class="panneau"><h3>Comment le stock est rangé</h3><p class="note">Choisissez la forme des racks : le magasin se réorganise aussitôt dans l’usine 3D.</p>
        <div class="formes">${Object.entries(FORMES).map(([f, [nom, txt]]) => `<button class="forme ${f === forme ? "actif" : ""}" data-forme="${f}"><span class="forme-lettre">${f}</span>${planForme(f)}<b>${nom}</b><small>${txt}</small>${f === forme ? `<em>En place</em>` : ""}</button>`).join("")}</div></section>`;
    }
    if (vue.dept === "production" || vue.dept === "usine") {
      const lignes = S.raw.production_lines;
      contenu += `<section class="panneau"><h3>Machines et tampons</h3><p class="note">Ajoutez un tampon entre deux machines pour absorber les à-coups : la table d’attente apparaît dans l’atelier 3D. Le goulot est la machine au cycle le plus long.</p>
        <div class="config-lignes">${lignes.map((l) => {
          const total = l.machines.slice(1).reduce((n, _, i) => n + tampon(l.id, i), 0);
          const fluidite = Math.min(100, 55 + total * 6 + (l.operational ? 10 : -20));
          return `<div class="config-ligne papier"><div class="config-ligne-tete"><b>${esc(l.name)}</b><small>${esc(l.product_sku)}</small>
            <div class="fluidite" title="Indicatif"><span>Fluidité</span><div class="barre"><i class="${fluidite > 75 ? "vert" : "orange"}" style="width:${fluidite}%"></i></div></div></div>
            ${croquisLigne(l, true)}</div>`;
        }).join("")}</div></section>`;
    }
    if (vue.dept !== "usine") {
      if (d.worldParameters.length) contenu += `<section class="panneau"><h3>Paramètres du monde</h3><div class="params">${d.worldParameters.map((p) => `<div class="param"><b>${esc(p.label)}</b><small>${esc(p.value)}</small></div>`).join("")}</div></section>`;
      if (d.configurations.length) contenu += `<section class="panneau"><h3>Réglages fixés par le formateur</h3><div class="params">${d.configurations.map((c) => `<button class="param verrou" data-config="${esc(c.id)}" data-valeur="${esc(c.value)}"><b>${esc(c.label)}</b><small>${esc(c.value)}</small></button>`).join("")}</div></section>`;
      if (!contenu) contenu = `<section class="panneau vide-grand"><span>${DEPTS[vue.dept].icon}</span><h3>Aménagement standard</h3><p>Ce département est aménagé par le formateur pour cette partie. Les réglages d’aménagement se trouvent dans <b>Stock</b> (forme des racks) et <b>Production</b> (tampons).</p>
        <div class="rangee"><button class="btn-secondaire" data-dept="stock">Stock</button><button class="btn-secondaire" data-dept="production">Production</button></div></section>`;
    }
    return contenu;
  }
  // Croquis « à main levée » d'une ligne : traits tremblés mais déterministes (même ligne, même dessin).
  function crayon(graine) {
    let h = 2166136261;
    for (const c of String(graine)) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
    return () => { h = Math.imul(h ^ (h >>> 15), 2246822507); h ^= h >>> 13; return ((h >>> 0) % 1000) / 1000 - 0.5; };
  }
  function trait(r, x1, y1, x2, y2, amp = 1.8) {
    const f = (v) => v.toFixed(1);
    return `M${f(x1 + r() * amp)} ${f(y1 + r() * amp)} Q${f((x1 + x2) / 2 + r() * amp * 2)} ${f((y1 + y2) / 2 + r() * amp * 2)} ${f(x2 + r() * amp)} ${f(y2 + r() * amp)}`;
  }
  const cadre = (r, x, y, w, h) => [0, 1].map(() => trait(r, x - 3, y, x + w + 2, y) + trait(r, x + w, y - 2, x + w, y + h + 3) + trait(r, x + w + 3, y + h, x - 2, y + h) + trait(r, x, y + h + 2, x, y - 3)).join("");
  const fleche = (r, x1, x2, y) => `<path class="cq-trait" d="${trait(r, x1, y, x2, y, 1.2)}${trait(r, x2 - 9, y - 6, x2, y, 0.8)}${trait(r, x2 - 9, y + 6, x2, y, 0.8)}"/>`;
  function croquisLigne(l, edition = false) {
    const r = crayon(l.id);
    const goulot = l.machines.reduce((a, b) => (b.cycle_minutes > a.cycle_minutes ? b : a), l.machines[0]);
    const W = 118, H = 76, G = 100, X0 = 64, Y = 52, mid = Y + H / 2;
    const largeur = X0 * 2 + l.machines.length * W + (l.machines.length - 1) * G;
    let svg = `<svg class="croquis" viewBox="0 0 ${largeur} ${edition ? 214 : 176}" role="img" aria-label="Croquis de ${esc(l.name)}">
      <text class="cq-note" x="10" y="${mid + 6}">MP</text>${fleche(r, 40, X0 - 8, mid)}`;
    l.machines.forEach((m, i) => {
      const x = X0 + i * (W + G);
      const panne = m.state === "panne";
      if (i) {
        const x0 = x - G + 8, x1 = x - 8, n = tampon(l.id, i - 1), cx = (x0 + x1) / 2;
        svg += fleche(r, x0, x1, mid);
        for (let k = 0; k < n; k++) svg += `<path class="cq-trait cq-tampon" d="${cadre(r, cx - 9, mid - 26 - k * 17, 18, 14)}"/>`;
        if (n) svg += `<text class="cq-petit" x="${cx}" y="${mid + 22}" text-anchor="middle">tampon ×${n}</text>`;
        if (edition) {
          const bouton = (dx, d, signe, actif, label) => `<g class="cq-btn ${actif ? "" : "cq-off"}" ${actif ? `data-tampon="${esc(l.id)}" data-i="${i - 1}" data-d="${d}" role="button" tabindex="0" aria-label="${label} entre ${esc(l.machines[i - 1].id)} et ${esc(m.id)}"` : 'aria-hidden="true"'}>
            <circle cx="${cx + dx}" cy="${Y + H + 42}" r="13"/><text x="${cx + dx}" y="${Y + H + 48}" text-anchor="middle">${signe}</text></g>`;
          svg += bouton(-17, -1, "−", n > 0, "Retirer un tampon") + bouton(17, 1, "+", n < 3, "Ajouter un tampon");
        }
      }
      svg += `<rect class="cq-fond" x="${x}" y="${Y}" width="${W}" height="${H}" rx="3" transform="rotate(${(r() * 1.6).toFixed(2)} ${x + W / 2} ${mid})"/>
        <path class="cq-trait" d="${cadre(r, x, Y, W, H)}"/>
        <path class="cq-trait cq-fin" d="${trait(r, x + 10, Y + 30, x + W - 10, Y + 30, 1)}"/>
        <text class="cq-titre" x="${x + 10}" y="${Y + 23}">${esc(m.id)}</text>
        <text class="cq-petit" x="${x + 10}" y="${Y + 48}">${esc(m.operation)}</text>
        <text class="cq-petit" x="${x + 10}" y="${Y + 66}">${nf(m.cycle_minutes, 1)} min / pièce</text>`;
      if (m.id === goulot.id) svg += `<ellipse class="cq-goulot" cx="${x + W / 2}" cy="${mid}" rx="${W / 2 + 14}" ry="${H / 2 + 13}" transform="rotate(-3 ${x + W / 2} ${mid})"/>
        <ellipse class="cq-goulot" cx="${x + W / 2 + 2}" cy="${mid + 1}" rx="${W / 2 + 11}" ry="${H / 2 + 15}" transform="rotate(2 ${x + W / 2} ${mid})"/>
        <text class="cq-alerte" x="${x + W / 2}" y="${Y - 22}" text-anchor="middle">goulot !</text>`;
      if (panne) svg += `<path class="cq-panne" d="${trait(r, x + 6, Y + 6, x + W - 6, Y + H - 6, 2)}${trait(r, x + W - 6, Y + 6, x + 6, Y + H - 6, 2)}"/>
        <text class="cq-panne-txt" x="${x + W / 2}" y="${Y + H + 24}" text-anchor="middle">en panne</text>`;
    });
    const xf = X0 + l.machines.length * (W + G) - G;
    return svg + `${fleche(r, xf + 8, xf + 40, mid)}<text class="cq-note" x="${xf + 46}" y="${mid + 6}">PF</text></svg>`;
  }
  function monterConfiguration() {}

  async function sauverLayout(changement, message) {
    try {
      const r = await fetch("/api/v2/tablet/layout", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(changement) });
      if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
      layout = await r.json();
      prevenirParent("GMIX_LAYOUT_CHANGED", { layout });
      notifier(message, "ok");
      rendre();
    } catch (e) { notifier(`Impossible d’enregistrer : ${e.message}`, "erreur"); }
  }

  // ------------------------------------------------------------------ actions (fenêtres)
  function ouvrirModal(html) { $("#modal-corps").innerHTML = html; $("#modal").hidden = false; $("#modal-corps input, #modal-corps select")?.focus(); }
  function fermerModal() { $("#modal").hidden = true; }
  function modalAction(id, pre = {}) {
    const raw = S.raw;
    if (id === "compare") { aller("fournisseurs", "outils", "comparateur"); return; }
    if (id === "purchase") {
      const mp = stocks("MP", "PDR");
      const sku = pre.sku || (pre.fournisseur ? mp.find((s) => raw.suppliers.find((f) => f.id === pre.fournisseur)?.prices?.[s.sku])?.sku : null) || mp.find((s) => s.quantity <= s.reorder_point)?.sku || mp[0]?.sku;
      ouvrirModal(`<h2 id="modal-titre">Commander de la matière</h2><form data-form="purchase" class="formulaire">
        <label>Matière<select name="sku">${mp.map((s) => `<option value="${esc(s.sku)}" ${s.sku === sku ? "selected" : ""}>${esc(s.name)} · stock ${nf(s.quantity)}</option>`).join("")}</select></label>
        <label>Fournisseur<select name="supplier_id"></select></label>
        <label>Quantité<input name="quantity" type="number" min="1" value="${esc(pre.qte || mp.find((s) => s.sku === sku)?.reorder_qty || 500)}"></label>
        <button class="btn-principal" type="submit">Passer la commande</button></form>`);
      const majFournisseurs = () => {
        const s = $("#modal [name=sku]").value;
        const liste = raw.suppliers.filter((f) => f.active && f.prices?.[s] !== undefined);
        $("#modal [name=supplier_id]").innerHTML = liste.map((f) => `<option value="${esc(f.id)}" ${f.id === pre.fournisseur ? "selected" : ""}>${esc(f.name)} · ${nf(f.prices[s], 2)} € · ${f.lead_time_weeks} sem. · ${nf(f.reliability, 0)} %</option>`).join("") || `<option value="">Aucun fournisseur</option>`;
      };
      $("#modal [name=sku]").addEventListener("change", majFournisseurs); majFournisseurs();
    } else if (id === "production") {
      const pf = stocks("PF");
      ouvrirModal(`<h2 id="modal-titre">▶️ Lancer un ordre de fabrication</h2><form data-form="production" class="formulaire">
        <label>Produit<select name="sku">${pf.map((s) => `<option value="${esc(s.sku)}">${esc(s.name)} · stock ${nf(s.quantity)}</option>`).join("")}</select></label>
        <label>Quantité<input name="quantity" type="number" min="1" value="600"></label><button class="btn-principal" type="submit">Lancer l’OF</button></form>`);
    } else if (id === "maintenance") {
      const lignes = raw.production_lines;
      ouvrirModal(`<h2 id="modal-titre">Planifier une réparation</h2><form data-form="maintenance" class="formulaire">
        <label>Ligne<select name="line_id">${lignes.map((l) => `<option value="${esc(l.id)}" ${l.operational ? "" : "selected"}>${esc(l.name)} · ${l.operational ? "en service" : "EN PANNE"}</option>`).join("")}</select></label>
        <button class="btn-principal" type="submit">Planifier</button></form>`);
    }
  }
  async function soumettre(form) {
    const f = new FormData(form);
    const action = { action: form.dataset.form };
    for (const [k, v] of f.entries()) action[k] = k === "quantity" ? Number(v) : v;
    try {
      S = await api.performAction(action);
      fermerModal();
      notifier({ purchase: "Commande passée : le camion est en route.", production: "OF lancé : les lignes s’activent.", maintenance: "Intervention planifiée." }[action.action], "ok");
      prevenirParent("GMIX_STATE_CHANGED");
      rendre();
    } catch (e) { notifier(e.message, "erreur"); }
  }

  async function semaineSuivante(bouton) {
    bouton.disabled = true;
    bouton.classList.add("charge");
    try {
      S = await api.nextTurn();
      const r = S.raw.last_week || {};
      notifier(`${S.clock.label} · fabriqué ${nf(r.produced)} · expédié ${nf(r.delivered)} · reçu ${nf(r.received_units)}`, "ok");
      prevenirParent("GMIX_STATE_CHANGED");
      rendre();
    } catch (e) { notifier(e.message, "erreur"); bouton.disabled = false; }
  }

  // ------------------------------------------------------------------ démarrage et règles
  function ecranDemarrage() {
    return `<section class="demarrage"><span class="logo-g grand">G</span><h1>Prenez les commandes de l’usine</h1><p>Approvisionnez, produisez, livrez. Chaque décision se voit dans l’usine 3D.</p>
      <form data-form="new-game" class="formulaire"><label>Nom de l’entreprise<input name="company_name" value="${esc(S.companyName || "G-mix")}" minlength="2" maxlength="32" required></label>
      <label>Difficulté<select name="difficulty"><option value="facile">Facile</option><option value="normal" selected>Équilibré</option><option value="difficile">Difficile</option></select></label>
      ${reglesCourtes()}<label class="case"><input type="checkbox" name="rules_confirmed" required> J’ai lu les règles de la partie</label>
      <button class="btn-principal grand" type="submit">Démarrer la partie</button></form></section>`;
  }
  function reglesCourtes() {
    return `<div class="regles-courtes"><div><b>KPIs</b><small>Suivez chaque département : service, rendement, stock.</small></div><div><b>Outils</b><small>Carte du trafic, tableur, graphiques, planning.</small></div>
      <div><b>Configuration</b><small>Réaménagez le stock et ajoutez des tampons : l’usine change.</small></div><div><b>▶ Semaine suivante</b><small>Le moteur simule une semaine avec vos décisions.</small></div></div>`;
  }
  function ecranRegles() {
    return `<header class="scene-tete" style="--c:#d8f18a"><span class="scene-icone">📘</span><div><small>PARTIE</small><h1>Règles de la partie</h1></div><p>Ce que vous pouvez faire et ce que le formateur a fixé.</p></header>
      <section class="panneau">${reglesCourtes()}</section>
      <section class="panneau"><h3>Les droits</h3><div class="params"><div class="param"><b>Verrouillé</b><small>Fixé par le formateur pour toute la partie : un essai affiche une alerte rouge.</small></div>
        <div class="param"><b>Initial seulement</b><small>Choisi avant le démarrage, figé ensuite.</small></div><div class="param"><b>Libre</b><small>Modifiable à tout moment, effet à la période suivante.</small></div>
        <div class="param"><b>Aménagement</b><small>Forme du stock et tampons : libres, visibles tout de suite dans l’usine 3D.</small></div></div></section>
      <section class="panneau"><h3>Les départements</h3><div class="tuiles">${S.departments.map((d) => `<button class="tuile" data-dept="${d.id}" style="--c:${DEPTS[d.id].couleur}"><span class="tuile-icone">${DEPTS[d.id].icon}</span><b>${esc(d.shortName)}</b><small>${esc(d.description)}</small></button>`).join("")}</div></section>`;
  }
  async function nouvellePartie(form) {
    const f = new FormData(form);
    try {
      S = await api.newGame({ company_name: f.get("company_name"), difficulty: f.get("difficulty"), rules_confirmed: f.get("rules_confirmed") === "on" });
      notifier("Partie lancée. Bonne chance !", "ok");
      prevenirParent("GMIX_STATE_CHANGED");
      aller("usine", "kpis");
    } catch (e) { notifier(e.message, "erreur"); }
  }

  // ------------------------------------------------------------------ événements
  document.addEventListener("click", async (e) => {
    const t = e.target;
    const deptBtn = t.closest("[data-dept]");
    const ongletBtn = t.closest("[data-onglet]");
    const act = t.closest("[data-act]");
    if (t.closest('[data-action="close-tablet"]')) {
      if (window.parent !== window) { e.preventDefault(); prevenirParent("GMIX_CLOSE_TABLET"); }
      return;
    }
    if (t.closest('[data-action="close-modal"]') || t.id === "modal") { fermerModal(); return; }
    if (t.closest('[data-action="next-turn"]')) { semaineSuivante(t.closest("button")); return; }
    if (t.closest('[data-action="alertes"]')) { aller("usine", "kpis"); return; }
    if (act) { e.preventDefault(); if (act.dataset.deptAct && act.dataset.deptAct !== vue.dept && act.dataset.act === "compare") aller(act.dataset.deptAct, "outils"); modalAction(act.dataset.act, { fournisseur: act.dataset.fournisseur, sku: act.dataset.sku, qte: act.dataset.qte }); return; }
    if (ongletBtn) { aller(vue.dept, ongletBtn.dataset.onglet); return; }
    const outil = t.closest("[data-outil]");
    if (outil) { aller(vue.dept, "outils", outil.dataset.outil); return; }
    const outilGo = t.closest("[data-outil-go]");
    if (outilGo) { aller(vue.dept, "outils", outilGo.dataset.outilGo); return; }
    const tab = t.closest("[data-tableur]");
    if (tab) { envoyerTableur(tab.dataset.tableur); return; }
    const forme = t.closest("[data-forme]");
    if (forme) { if (forme.dataset.forme !== layout.stock.forme) sauverLayout({ stock: { forme: forme.dataset.forme } }, `Le stock est réaménagé ${FORMES[forme.dataset.forme][0].toLowerCase()}.`); return; }
    const tp = t.closest("[data-tampon]");
    if (tp) {
      const ligne = tp.dataset.tampon, i = Number(tp.dataset.i);
      const l = S.raw.production_lines.find((x) => x.id === ligne);
      const valeurs = Array.from({ length: l.machines.length - 1 }, (_, k) => tampon(ligne, k));
      valeurs[i] = Math.max(0, Math.min(3, valeurs[i] + Number(tp.dataset.d)));
      sauverLayout({ production: { tampons: { [ligne]: valeurs } } }, valeurs[i] ? `Tampon de ${valeurs[i]} entre ${l.machines[i].id} et ${l.machines[i + 1].id}.` : `Tampon retiré entre ${l.machines[i].id} et ${l.machines[i + 1].id}.`);
      return;
    }
    const cfg = t.closest("[data-config]");
    if (cfg) {
      try { await api.updateConfiguration(vue.dept, cfg.dataset.config, cfg.dataset.valeur); }
      catch (err) { if (err.status === 403) popupRouge(err.message); else notifier(err.message, "erreur"); }
      return;
    }
    const alerte = t.closest(".alerte[data-dept], .kpi[data-dept], .mission[data-dept]");
    if (alerte && !act && alerte.dataset.dept && DEPTS[alerte.dataset.dept]) { aller(alerte.dataset.dept, "kpis"); return; }
    if (deptBtn && DEPTS[deptBtn.dataset.dept]) { aller(deptBtn.dataset.dept, vue.onglet === "regles" ? "kpis" : vue.onglet); return; }
  });
  document.addEventListener("submit", (e) => {
    const form = e.target.closest("form[data-form]");
    if (!form) return;
    e.preventDefault();
    if (form.dataset.form === "new-game") nouvellePartie(form); else soumettre(form);
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#modal").hidden) { e.stopPropagation(); fermerModal(); } }, true);
  document.addEventListener("keydown", (e) => { if ((e.key === "Enter" || e.key === " ") && e.target.matches?.('g[role="button"]')) { e.preventDefault(); e.target.dispatchEvent(new MouseEvent("click", { bubbles: true })); } });
  window.addEventListener("hashchange", rendre);
  window.addEventListener("resize", () => { if (vue.onglet === "outils" && vue.outil === "graphiques") rendre(); });

  charger().then(rendre).catch((e) => {
    $("#stage").innerHTML = `<div class="loading"><span class="logo-g">!</span><p>Serveur injoignable : ${esc(e.message)}</p></div>`;
  });
}());
