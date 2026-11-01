(function () {
  "use strict";

  const api = window.GMixLiveAPI.createLiveApi();
  const spreadsheet = window.GMixSpreadsheet;
  const app = document.getElementById("app");
  const toast = document.getElementById("toast");
  const modal = document.getElementById("action-modal");
  const modalContent = document.getElementById("modal-content");
  const networkStatus = document.getElementById("network-status");
  const rightLabels = { verrouille: "Verrouillé", initial: "Initial seulement", libre: "Libre" };
  const statusLabels = { vert: "Aucune alerte", orange: "Alerte mineure", rouge: "Alerte grave" };
  const supportedActions = new Set(["purchase", "production", "maintenance", "compare"]);
  let state;
  let toastTimer;
  let modalTrigger;
  let pendingSheet = null;
  let sheetKey = "";
  let sheetGrid = [];
  let saveTimer;
  let journalFilters = { department: "", type: "", cause: "", query: "" };
  let chartSelection = { first: "", second: "" };

  const iconPaths = {
    home: '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5M9 20v-6h6v6"/>',
    rules: '<path d="M6 3h12v18H6zM9 7h6M9 11h6M9 15h4"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    world: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.3 3 14.7 0 18M12 3c-3 3.3-3 14.7 0 18"/>',
    suppliers: '<path d="M3 16V8h11v8M14 11h4l3 3v2h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    dock: '<path d="M3 20h18M5 20V9h14v11M8 9V4h8v5M8 13h8M12 13v7"/>',
    reception: '<path d="M4 4h16v16H4zM8 2v4M16 2v4M8 12l3 3 5-6"/>',
    stock: '<path d="m3 7 9-4 9 4-9 4zM3 7v10l9 4 9-4V7M12 11v10"/>',
    production: '<path d="M3 21V10l6 3V9l6 4V5h6v16zM7 17h2M13 17h2M18 17h1"/>',
    quality: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="m8 12 3 3 5-6"/>',
    packing: '<path d="M4 7h16v14H4zM2 3h20v4H2zM9 11h6"/>',
    maintenance: '<path d="M14 6a5 5 0 0 0-6.5 6.5L3 17l4 4 4.5-4.5A5 5 0 0 0 18 10l-3 3-4-4z"/>',
    logistics: '<path d="M3 5h12v12H3zM15 9h4l2 3v5h-6z"/><circle cx="7" cy="19" r="2"/><circle cx="18" cy="19" r="2"/>',
    clients: '<circle cx="9" cy="8" r="4"/><path d="M2 21v-2a7 7 0 0 1 14 0v2M17 4a4 4 0 0 1 0 8M19 21v-2a7 7 0 0 0-2-4.9"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    next: '<path d="m5 5 10 7L5 19zM19 5v14"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    alert: '<path d="M12 3 2 21h20zM12 9v5M12 18v.01"/>',
    arrow: '<path d="M5 12h14M14 7l5 5-5 5"/>',
    trendUp: '<path d="m4 16 6-6 4 4 6-8M15 6h5v5"/>',
    trendDown: '<path d="m4 8 6 6 4-4 6 8M15 18h5v-5"/>',
    flat: '<path d="M4 12h16"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M18.5 9A7 7 0 0 0 6 6.5L4 9M5.5 15A7 7 0 0 0 18 17.5l2-2.5"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    download: '<path d="M12 3v12m-5-5 5 5 5-5M4 18v3h16v-3"/>',
    tableur: '<rect x="3" y="3" width="18" height="18" rx="1"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
    carte: '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15M15 6v15"/>',
    graphiques: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    planning: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M8 14h2M14 14h2M8 17h2"/>',
    journal: '<path d="M5 3h14v18H5zM9 7h6M9 11h6M9 15h6"/>'
  };

  function icon(name, className) {
    return `<svg class="icon ${className || ""}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.production}</svg>`;
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
    })[character]);
  }

  function display(value) {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "boolean") return value ? "Oui" : "Non";
    if (typeof value === "object") {
      try { return JSON.stringify(value); } catch (error) { return "—"; }
    }
    return String(value);
  }

  function route() {
    const parts = (window.location.hash.replace(/^#\/?/, "") || "accueil").split("/");
    return { view: parts[0], id: parts[1], tab: parts[2] || "kpis" };
  }

  function departmentIcon(id) {
    return ({
      fournisseurs: "suppliers", "quai-dechargement": "dock", reception: "reception",
      stock: "stock", production: "production", qualite: "quality", emballage: "packing",
      maintenance: "maintenance", logistique: "logistics", clients: "clients"
    })[id] || "production";
  }

  function departmentById(id) {
    return (state.departments || []).find((department) => department.id === id);
  }

  function notify(message, type) {
    window.clearTimeout(toastTimer);
    toast.className = `toast toast-${type || "error"}`;
    toast.innerHTML = `${icon(type === "success" ? "check" : "alert")}<span>${escapeHtml(message)}</span><button type="button" data-dismiss-toast aria-label="Fermer">×</button>`;
    toast.hidden = false;
    toastTimer = window.setTimeout(() => { toast.hidden = true; }, 4000);
  }

  function announce(message) {
    networkStatus.textContent = message;
  }

  function renderSidebar(current) {
    return `<aside class="sidebar" id="sidebar" aria-label="Navigation principale">
      <a class="brand" href="#accueil" aria-label="G-MIX, accueil"><span class="brand-mark">G</span><span>G-MIX<small>TERMINAL D’USINE</small></span></a>
      <nav class="primary-nav">
        <a href="#accueil" ${current.view === "accueil" ? 'class="active" aria-current="page"' : ""}>${icon("home")}<span>Vue d’ensemble</span></a>
        <a href="#regles" ${current.view === "regles" ? 'class="active" aria-current="page"' : ""}>${icon("rules")}<span>Règles de la partie</span></a>
        <a href="#nouvelle-partie" ${current.view === "nouvelle-partie" ? 'class="active" aria-current="page"' : ""}>${icon("plus")}<span>Nouvelle partie</span></a>
      </nav>
      <p class="nav-caption">LES DIX PAGES DE L’USINE</p>
      <nav class="department-nav">${(state.departments || []).map((department) => `<a href="#departement/${escapeHtml(department.id)}" ${current.id === department.id && current.view === "departement" ? 'class="active" aria-current="page"' : ""}>${icon(departmentIcon(department.id))}<span>${escapeHtml(department.shortName)}</span><i class="status-dot status-${escapeHtml(department.status)}" aria-label="${escapeHtml(statusLabels[department.status] || department.status)}"></i></a>`).join("")}</nav>
      <div class="sidebar-foot"><span class="live-dot"></span><span>Connecté au moteur · ${escapeHtml(state.clock.label)}</span></div>
    </aside><button class="menu-scrim" type="button" data-action="close-menu" aria-label="Fermer le menu"></button>`;
  }

  function renderTopbar(title) {
    return `<header class="topbar"><div class="topbar-left"><button class="menu-button" type="button" data-action="toggle-menu" aria-controls="sidebar" aria-label="Ouvrir le menu">${icon("menu")}</button><div><span class="breadcrumb">G-MIX <b>/</b> ${escapeHtml(title)}</span><span class="company-name">${escapeHtml(state.companyName)}</span></div></div><div class="topbar-actions"><span class="live-badge"><i></i>DONNÉES MOTEUR</span><button class="icon-only" type="button" data-action="refresh" aria-label="Actualiser les données" title="Actualiser">${icon("refresh")}</button><a class="world-link" href="/">${icon("world")}<span>Rejoindre le monde 3D</span></a></div></header>`;
  }

  function renderClock() {
    const clock = state.clock;
    return `<section class="period-bar" aria-label="Période de simulation"><div class="period-main">${icon("clock")}<div><small>PÉRIODE EN COURS</small><strong>${escapeHtml(clock.label)}</strong></div></div><span class="period-mode">${clock.supportsRealtime ? "Temps simulé" : "Simulation par période"}</span><button class="next-period" type="button" data-action="next-turn" ${clock.canAdvance ? "" : "disabled"}>${icon("next")}<span>Simuler la période suivante</span></button></section>`;
  }

  function metricValue(item) {
    return `${escapeHtml(display(item.value))}${item.unit ? ` <small>${escapeHtml(item.unit)}</small>` : ""}`;
  }

  function renderStatus(department) {
    return `<span class="state-pill state-${escapeHtml(department.status)}"><i class="status-dot status-${escapeHtml(department.status)}"></i>${escapeHtml(statusLabels[department.status] || department.status)}</span>`;
  }

  function renderFactoryPlan() {
    const internalIds = ["quai-dechargement", "reception", "stock", "production", "maintenance", "qualite", "emballage", "logistique"];
    const block = (department, external) => {
      if (!department) return "";
      return `<a class="factory-block ${external ? "external-block" : ""} status-border-${escapeHtml(department.status)}" href="#departement/${escapeHtml(department.id)}"><span class="block-top"><span class="block-icon">${icon(departmentIcon(department.id))}</span><i class="status-dot status-${escapeHtml(department.status)}" aria-label="${escapeHtml(statusLabels[department.status] || department.status)}"></i></span><strong>${escapeHtml(department.shortName)}</strong><small>${external ? "Partenaire externe" : "Ouvrir le poste"}</small><span class="block-arrow">${icon("arrow")}</span></a>`;
    };
    return `<div class="factory-plan"><div class="external-flow">${block(departmentById("fournisseurs"), true)}<span class="flow-caption">APPROVISIONNEMENT</span></div><div class="factory-floor"><span class="floor-label">USINE · 8 BLOCS</span><div class="factory-blocks">${internalIds.map((id) => block(departmentById(id), false)).join("")}</div></div><div class="external-flow">${block(departmentById("clients"), true)}<span class="flow-caption">DISTRIBUTION</span></div></div>`;
  }

  function renderAlerts(alerts, linked) {
    if (!alerts.length) return `<div class="empty-state compact">${icon("check")}<strong>Aucune alerte ouverte</strong><span>Le moteur ne signale aucune alerte ici.</span></div>`;
    return `<div class="alert-list">${alerts.map((alert) => {
      const department = departmentById(alert.departmentId);
      const inner = `<span class="alert-symbol">${icon("alert")}</span><span class="alert-copy"><small>${escapeHtml(department ? department.shortName : alert.departmentId)} · ${escapeHtml(alert.severity)}</small><strong>${escapeHtml(alert.title)}</strong><span>${escapeHtml(display(alert.detail))}</span></span>${linked ? icon("arrow") : ""}`;
      return linked ? `<a class="alert-item severity-${escapeHtml(alert.severity)}" href="#departement/${escapeHtml(alert.departmentId)}">${inner}</a>` : `<article class="alert-item severity-${escapeHtml(alert.severity)}">${inner}</article>`;
    }).join("")}</div>`;
  }

  function renderObjectives() {
    if (!state.objectives.length) return `<div class="empty-state compact">${icon("quality")}<strong>Objectifs de la partie</strong><span>Aucun objectif chiffré n’est défini pour ce scénario.</span></div>`;
    return `<div class="objective-list">${state.objectives.map((objective) => {
      const progress = Number(objective.progress);
      const hasProgress = Number.isFinite(progress);
      const width = Math.max(0, Math.min(100, progress));
      return `<article class="objective"><div><strong>${escapeHtml(display(objective.label))}</strong><span>${escapeHtml(display(objective.current))}</span></div>${hasProgress ? `<div class="progress-track" role="progressbar" aria-label="${escapeHtml(objective.label)}" aria-valuenow="${width}" aria-valuemin="0" aria-valuemax="100"><i style="width:${width}%"></i></div>` : ""}<small>${escapeHtml(display(objective.target || objective.detail || "Progression fournie par le moteur, sans verdict"))}</small></article>`;
    }).join("")}</div>`;
  }

  function renderHome() {
    const mission = state.objectives[0];
    return `${renderTopbar("Vue d’ensemble")}<div class="page-heading home-heading"><div><p class="eyebrow">POSTE DE PILOTAGE</p><h1>Bonjour, <span>${escapeHtml(state.companyName)}</span></h1><p>Votre usine vous attend. Observez, décidez, puis lancez la simulation.</p></div><a class="secondary-button" href="#regles">${icon("rules")} Règles & droits</a></div>
      ${state.started ? "" : `<section class="resume-banner">${icon("alert")}<div><strong>Votre première partie vous attend</strong><span>Nommez votre entreprise, consultez les règles et prenez les commandes de l’usine.</span></div><a href="#nouvelle-partie">Nouvelle partie</a></section>`}
      ${renderClock()}
      <section class="turn-mission"><div><p class="eyebrow">OBJECTIF OPÉRATIONNEL · ${escapeHtml(state.clock.label)}</p><h2>${escapeHtml(mission ? display(mission.label) : "Pilotez votre prochaine décision")}</h2><p>${escapeHtml(mission ? display(mission.current) : "Consultez les alertes, vérifiez vos stocks et préparez vos achats et votre production avant la prochaine période.")}</p></div><a href="#departement/production" class="mission-action">Aller aux décisions ${icon("arrow")}</a></section>
      <section class="home-section"><div class="section-heading"><div><p class="eyebrow">LE POULS DE L’USINE</p><h2>Indicateurs globaux</h2></div><span>Valeurs calculées par le moteur</span></div>${state.globalKpis.length ? `<div class="global-kpis">${state.globalKpis.map((kpi) => `<a class="global-kpi" href="#departement/${escapeHtml(kpi.departmentId)}"><span>${escapeHtml(kpi.label)}</span><strong>${metricValue(kpi)}</strong><span class="kpi-link">Comprendre ${icon("arrow")}</span></a>`).join("")}</div>` : `<div class="empty-state panel">${icon("graphiques")}<strong>Aucun indicateur disponible</strong></div>`}</section>
      <section class="panel factory-panel"><div class="section-heading"><div><p class="eyebrow">CIRCULATION DES FLUX</p><h2>Votre usine, à portée de main</h2></div><div class="status-legend"><span><i class="status-dot status-vert"></i>Vert</span><span><i class="status-dot status-orange"></i>Orange</span><span><i class="status-dot status-rouge"></i>Rouge</span></div></div>${renderFactoryPlan()}</section>
      <div class="home-grid"><section class="panel"><div class="section-heading"><div><p class="eyebrow">À TRAITER</p><h2>Alertes de l’usine</h2></div></div>${renderAlerts(state.alerts, true)}</section><section class="panel"><div class="section-heading"><div><p class="eyebrow">CAP À SUIVRE</p><h2>Objectifs de la partie</h2></div></div>${renderObjectives()}</section></div>
      <section class="panel tools-panel"><div class="section-heading"><div><p class="eyebrow">ESPACE DE TRAVAIL</p><h2>Outils du joueur</h2></div><span>Lecture et calculs locaux, sans effet sur la partie</span></div>${renderTools("accueil")}</section>`;
  }

  function renderTools(context) {
    return `<div class="tool-list">${state.tools.map((tool) => tool.available ? `<a href="#outil/${escapeHtml(tool.id)}/${escapeHtml(context)}">${icon(tool.id)}<span><strong>${escapeHtml(tool.name)}</strong><small>${escapeHtml(tool.description)}</small></span>${icon("arrow")}</a>` : `<div class="disabled-tool">${icon(tool.id)}<span><strong>${escapeHtml(tool.name)}</strong><small>Outil désactivé par le formateur</small></span>${icon("lock")}</div>`).join("")}</div>`;
  }

  function tableData(context) {
    if (context === "accueil") return state.departments.flatMap((department) => (department.tables || []).map((table) => ({ department, table })));
    const department = departmentById(context);
    return department ? (department.tables || []).map((table) => ({ department, table })) : [];
  }

  function renderTables(context) {
    const entries = tableData(context);
    if (!entries.length) return `<section class="panel"><div class="empty-state">${icon("tableur")}<strong>Aucune donnée disponible</strong><span>Les résultats apparaîtront après les premières opérations.</span></div></section>`;
    return entries.map(({ department, table }, tableIndex) => {
      const tableKey = `${context}-${tableIndex}`;
      const columns = table.columns || [];
      return `<section class="panel data-panel"><div class="section-heading"><div><p class="eyebrow">SITUATION DU POSTE${context === "accueil" ? ` · ${escapeHtml(department.shortName)}` : ""}</p><h2>${escapeHtml(table.title)}</h2></div><button class="text-button" type="button" data-action="send-table" data-context="${escapeHtml(context)}" data-table-id="${escapeHtml(table.id)}">${icon("tableur")} Envoyer au tableur</button></div><div class="table-filters"><label>${icon("search")}<span class="sr-only">Rechercher dans ${escapeHtml(table.title)}</span><input type="search" placeholder="Rechercher dans le tableau…" data-table-search="${escapeHtml(tableKey)}"></label><select data-table-column="${escapeHtml(tableKey)}" aria-label="Colonne à filtrer"><option value="">Toutes les colonnes</option>${columns.map((column) => `<option value="${escapeHtml(column.key)}">${escapeHtml(column.label)}</option>`).join("")}</select></div><div class="table-scroll"><table data-table="${escapeHtml(tableKey)}"><thead><tr>${columns.map((column) => `<th scope="col">${escapeHtml(column.label)}</th>`).join("")}</tr></thead><tbody>${(table.rows || []).map((row) => `<tr data-search="${escapeHtml(columns.map((column) => display(row[column.key])).join(" ").toLocaleLowerCase("fr"))}">${columns.map((column) => `<td data-column="${escapeHtml(column.key)}" data-value="${escapeHtml(display(row[column.key]).toLocaleLowerCase("fr"))}">${escapeHtml(display(row[column.key]))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>${(table.rows || []).length ? `<p class="filter-empty" data-filter-empty="${escapeHtml(tableKey)}" hidden>Aucune ligne ne correspond à cette recherche.</p>` : `<div class="empty-table">Aucune opération enregistrée.</div>`}</section>`;
    }).join("");
  }

  function renderActions(department) {
    if (!department.actions.length) return `<div class="empty-state compact">${icon("check")}<strong>Aucune décision disponible sur ce poste</strong></div>`;
    return `<div class="action-list">${department.actions.map((action) => {
      const supported = supportedActions.has(action.id);
      return `<button type="button" class="action-button" ${supported ? `data-action="open-action" data-action-id="${escapeHtml(action.id)}" data-action-label="${escapeHtml(action.label)}"` : "disabled"}><span class="action-button-icon">${icon(action.id === "purchase" ? "suppliers" : action.id === "production" ? "production" : action.id === "maintenance" ? "maintenance" : "lock")}</span><span><strong>${escapeHtml(action.label)}</strong><small>${supported ? "Agir sur votre usine" : "Indisponible dans cette partie"}</small></span>${supported ? icon("arrow") : icon("lock")}</button>`;
    }).join("")}</div>`;
  }

  function renderDepartment(department, tab) {
    const alerts = state.alerts.filter((alert) => alert.departmentId === department.id);
    let content;
    if (tab === "outils") {
      content = `<section class="panel"><div class="section-heading"><div><p class="eyebrow">PRÉ-REMPLIS AVEC CETTE PAGE</p><h2>Vos outils</h2></div></div>${renderTools(department.id)}</section>${renderTables(department.id)}`;
    } else if (tab === "configurations") {
      content = `<div class="config-layout"><section class="panel"><div class="section-heading"><div><p class="eyebrow">DROITS DU FORMATEUR</p><h2>Configurations du joueur</h2></div></div>${department.configurations.length ? `<div class="config-list">${department.configurations.map((configuration) => renderConfiguration(department, configuration)).join("")}</div>` : `<div class="empty-state compact">${icon("lock")}<strong>Aucun réglage disponible</strong></div>`}</section><aside class="panel world-panel"><p class="eyebrow">LECTURE SEULE</p><h2>Paramètres du monde</h2><p>Ces réalités physiques sont fixées par le scénario.</p>${department.worldParameters.length ? department.worldParameters.map((parameter) => `<div class="world-parameter"><span>${escapeHtml(parameter.label)}</span><strong>${escapeHtml(display(parameter.value))}</strong></div>`).join("") : `<p class="muted">Aucun paramètre disponible.</p>`}</aside></div>`;
    } else {
      tab = "kpis";
      content = `${department.kpis.length ? `<section class="department-kpis">${department.kpis.map((kpi) => `<article class="department-kpi"><span>${escapeHtml(kpi.label)}</span><strong>${metricValue(kpi)}</strong><p class="trend-${escapeHtml(kpi.direction)}">${icon(kpi.direction === "up" ? "trendUp" : kpi.direction === "down" ? "trendDown" : "flat")}${escapeHtml(display(kpi.trend))}</p></article>`).join("")}</section>` : `<div class="empty-state panel">${icon("graphiques")}<strong>Aucun indicateur disponible pour ce département</strong></div>`}<div class="department-grid"><section class="panel decision-panel"><div class="section-heading"><div><p class="eyebrow">À VOUS DE JOUER</p><h2>Décisions disponibles</h2></div></div>${renderActions(department)}</section><section class="panel"><div class="section-heading"><div><p class="eyebrow">SURVEILLANCE</p><h2>Alertes du département</h2></div></div>${renderAlerts(alerts, false)}</section></div>${renderTables(department.id)}`;
    }
    return `${renderTopbar(department.name)}<div class="page-heading department-heading"><div class="department-title"><span class="department-hero-icon">${icon(departmentIcon(department.id))}</span><div><p class="eyebrow">POSTE DE L’USINE</p><h1>${escapeHtml(department.name)}</h1><p>${escapeHtml(department.description)}</p></div></div>${renderStatus(department)}</div>${renderClock()}<nav class="tabs" aria-label="Sections du département">${[["kpis", "KPIs"], ["outils", "Outils"], ["configurations", "Configurations"]].map(([id, label]) => `<a href="#departement/${escapeHtml(department.id)}/${id}" ${tab === id ? 'class="active" aria-current="page"' : ""}>${label}</a>`).join("")}</nav>${content}`;
  }

  function renderConfiguration(department, configuration) {
    const locked = configuration.right === "verrouille" || (configuration.right === "initial" && state.started);
    const right = rightLabels[configuration.right] || configuration.right;
    if (locked) {
      return `<article class="configuration"><div class="configuration-label"><span>${escapeHtml(configuration.label)}</span><span class="right-badge right-${escapeHtml(configuration.right)}">${icon("lock")}${escapeHtml(right)}</span></div><button type="button" class="locked-value" data-action="attempt-config" data-department="${escapeHtml(department.id)}" data-configuration="${escapeHtml(configuration.id)}" data-value="${escapeHtml(display(configuration.value))}" aria-label="Réglage verrouillé : ${escapeHtml(configuration.label)}"><span>${escapeHtml(display(configuration.value))}</span>${icon("lock")}</button>${configuration.reason ? `<p class="config-reason">${escapeHtml(configuration.reason)}</p>` : ""}</article>`;
    }
    return `<form class="configuration config-form" data-department="${escapeHtml(department.id)}" data-configuration="${escapeHtml(configuration.id)}"><div class="configuration-label"><label for="config-${escapeHtml(department.id)}-${escapeHtml(configuration.id)}">${escapeHtml(configuration.label)}</label><span class="right-badge right-${escapeHtml(configuration.right)}">${escapeHtml(right)}</span></div><div class="editable-value"><input id="config-${escapeHtml(department.id)}-${escapeHtml(configuration.id)}" name="value" value="${escapeHtml(display(configuration.value))}" required><button type="submit" aria-label="Enregistrer ${escapeHtml(configuration.label)}">Enregistrer</button></div></form>`;
  }

  function renderRules() {
    return `${renderTopbar("Règles de la partie")}<div class="page-heading"><div><p class="eyebrow">LE CADRE DE JEU</p><h1>Règles de la partie</h1><p>Les droits ci-dessous viennent du monde actuel. Consultez-les avant toute nouvelle partie.</p></div><a class="secondary-button" href="#nouvelle-partie">${icon("plus")} Nouvelle partie</a></div><div class="rights-summary"><article><span class="right-badge right-verrouille">${icon("lock")}Verrouillé</span><p>Valeur fixée par le formateur pour toute la partie.</p></article><article><span class="right-badge right-initial">${icon("rules")}Initial seulement</span><p>Choix initial, puis réglage non modifiable pendant la partie.</p></article><article><span class="right-badge right-libre">Libre</span><p>Modifiable uniquement si le serveur l’autorise.</p></article></div><div class="rules-layout"><div class="rules-departments">${state.departments.map((department) => `<details class="panel rules-department"><summary><span>${icon(departmentIcon(department.id))}<strong>${escapeHtml(department.name)}</strong></span><span>${escapeHtml(department.configurations.length)} réglages</span></summary><div class="rules-configs">${department.configurations.length ? department.configurations.map((configuration) => `<div><span>${escapeHtml(configuration.label)}</span><strong>${escapeHtml(display(configuration.value))}</strong><span class="right-badge right-${escapeHtml(configuration.right)}">${escapeHtml(rightLabels[configuration.right] || configuration.right)}</span></div>`).join("") : `<p class="muted">Aucun réglage disponible.</p>`}</div></details>`).join("")}</div><aside class="panel rules-tools"><p class="eyebrow">OUTILS DE LA PARTIE</p><h2>Votre espace de travail</h2>${state.tools.map((tool) => `<div class="rules-tool">${icon(tool.id)}<span><strong>${escapeHtml(tool.name)}</strong><small>${tool.available ? "Disponible" : "Désactivé par le formateur"}</small></span>${icon(tool.available ? "check" : "lock")}</div>`).join("")}</aside></div>`;
  }

  function renderNewGame() {
    return `${renderTopbar("Nouvelle partie")}<div class="new-game-layout"><section class="new-game-intro"><p class="eyebrow">NOUVEAU SCÉNARIO</p><h1>Prêt à prendre les commandes&nbsp;?</h1><p>La création remplace la partie courante uniquement après l’envoi de ce formulaire. Tant que vous ne validez pas, votre sauvegarde reste disponible.</p><div class="new-game-steps"><span><b>1</b>Nommez votre entreprise</span><span><b>2</b>Consultez les règles et les droits</span><span><b>3</b>Confirmez le démarrage</span></div><a href="#regles" class="secondary-button">${icon("rules")} Consulter les règles</a><a href="#accueil" class="resume-link">${icon("arrow")} Reprendre la sauvegarde sans rien changer</a></section><form id="new-game-form" class="panel new-game-form"><p class="eyebrow">ACTION EXPLICITE DU JOUEUR</p><h2>Créer une partie</h2><label>Nom de l’entreprise<input name="company_name" minlength="2" maxlength="32" autocomplete="organization" placeholder="Nom de votre entreprise" required></label><label>Difficulté<select name="difficulty" required><option value="facile">Facile</option><option value="normal" selected>Normal</option><option value="difficile">Difficile</option></select></label><input type="hidden" name="scenario_id" value="default"><label class="rules-check"><input type="checkbox" name="rules_confirmed" required><span>J’ai consulté l’écran « Règles de la partie » et je confirme le démarrage d’une nouvelle partie.</span></label><button class="primary-button" type="submit">Confirmer et créer la partie ${icon("arrow")}</button><p class="form-note">Le serveur refusera la création sans cette confirmation.</p></form></div>`;
  }

  function tablesWithDeadlines(context) {
    return tableData(context).map((entry) => {
      const dueColumns = entry.table.columns.filter((column) => /(^|_)(due|arrival|date|echeance|deadline|planned|preventif)/i.test(column.key) || /échéance|arrivée|date|prévu/i.test(column.label));
      const rows = dueColumns.length ? entry.table.rows.filter((row) => dueColumns.some((column) => row[column.key] !== null && row[column.key] !== undefined && row[column.key] !== "")) : [];
      return Object.assign({}, entry, { dueColumns, rows });
    }).filter((entry) => entry.dueColumns.length && entry.rows.length);
  }

  function renderPlanning(context) {
    const entries = tablesWithDeadlines(context);
    if (!entries.length) return `<div class="empty-state tool-empty">${icon("planning")}<strong>Aucune échéance transmise</strong><span>Le planning se remplit à partir des dates et périodes présentes dans les tableaux du moteur. Aucune date n’est déduite dans la tablette.</span></div>`;
    return `<div class="planning-period">${icon("clock")}Échéances rattachées à la période moteur <strong>${escapeHtml(state.clock.label)}</strong></div><div class="planning-list">${entries.map(({ department, table, dueColumns, rows }) => `<section class="planning-group"><div class="section-heading"><div><p class="eyebrow">${escapeHtml(department.name)}</p><h2>${escapeHtml(table.title)}</h2></div></div>${rows.map((row) => `<article class="planning-row"><div class="due-marker">${dueColumns.map((column) => `<small>${escapeHtml(column.label)}</small><strong>${escapeHtml(display(row[column.key]))}</strong>`).join("")}</div><dl>${table.columns.filter((column) => !dueColumns.includes(column)).map((column) => `<div><dt>${escapeHtml(column.label)}</dt><dd>${escapeHtml(display(row[column.key]))}</dd></div>`).join("")}</dl></article>`).join("")}</section>`).join("")}</div>`;
  }

  function renderJournal() {
    const departments = [...new Set(state.events.map((event) => event.departmentId).filter(Boolean))];
    const types = [...new Set(state.events.map((event) => event.type).filter(Boolean))];
    const causes = [...new Set(state.events.map((event) => event.cause).filter(Boolean))];
    const query = journalFilters.query.toLocaleLowerCase("fr");
    const events = state.events.filter((event) => (!journalFilters.department || event.departmentId === journalFilters.department) && (!journalFilters.type || event.type === journalFilters.type) && (!journalFilters.cause || event.cause === journalFilters.cause) && (!query || `${event.message || ""} ${event.time || ""}`.toLocaleLowerCase("fr").includes(query)));
    return `<div class="journal-filters"><label>${icon("search")}<span class="sr-only">Rechercher dans le journal</span><input type="search" data-journal="query" value="${escapeHtml(journalFilters.query)}" placeholder="Rechercher un événement…"></label><select data-journal="department" aria-label="Filtrer par département"><option value="">Tous les départements</option>${departments.map((id) => `<option value="${escapeHtml(id)}" ${journalFilters.department === id ? "selected" : ""}>${escapeHtml(departmentById(id) ? departmentById(id).shortName : id)}</option>`).join("")}</select><select data-journal="type" aria-label="Filtrer par type"><option value="">Tous les types</option>${types.map((type) => `<option value="${escapeHtml(type)}" ${journalFilters.type === type ? "selected" : ""}>${escapeHtml(type)}</option>`).join("")}</select><select data-journal="cause" aria-label="Filtrer par cause"><option value="">Toutes les causes</option>${causes.map((cause) => `<option value="${escapeHtml(cause)}" ${journalFilters.cause === cause ? "selected" : ""}>${escapeHtml(cause)}</option>`).join("")}</select></div>${events.length ? `<div class="journal-list">${events.map((event) => { const department = departmentById(event.departmentId); return `<article class="journal-event"><span class="event-time">${escapeHtml(display(event.time))}</span><span class="event-icon">${icon(department ? departmentIcon(department.id) : "journal")}</span><div><small>${escapeHtml(department ? department.name : display(event.departmentId))} · ${escapeHtml(display(event.type))} · ${escapeHtml(display(event.cause))}</small><p>${escapeHtml(display(event.message))}</p></div></article>`; }).join("")}</div>` : `<div class="empty-state tool-empty">${icon("journal")}<strong>Aucun événement à afficher</strong><span>${state.events.length ? "Modifiez les filtres pour retrouver un événement." : "Le journal du moteur est vide pour le moment."}</span></div>`}`;
  }

  function historySeries() {
    if (!Array.isArray(state.history) || !state.history.length) return { periods: [], series: [] };
    const periods = state.history.map((item) => display(item.period ?? item.label ?? item.time ?? item.week));
    const keys = [];
    state.history.forEach((item) => {
      const values = item.values && typeof item.values === "object" ? item.values : item;
      Object.keys(values).forEach((key) => {
        if (["period", "label", "time", "week"].includes(key)) return;
        if (typeof values[key] === "number" && !keys.includes(key)) keys.push(key);
      });
    });
    return { periods, series: keys.map((key) => ({ key, label: ({otif:"OTIF clients (%)",trs:"Rendement des lignes (%)",produced:"Production (produits)",delivered:"Expéditions (produits)",quality_rate:"Qualité (%)",stock_value:"Valeur du stock (€)",service_rate:"Taux de service (%)",purchases_cost:"Achats (€)",stockouts:"PF sous leur minimum"})[key] || key, values: state.history.map((item) => { const values = item.values && typeof item.values === "object" ? item.values : item; return typeof values[key] === "number" ? values[key] : null; }) })) };
  }

  function chartPolyline(values, periods, color) {
    const valid = values.filter((value) => typeof value === "number");
    if (valid.length < 2) return "";
    const min = Math.min(...valid);
    const max = Math.max(...valid);
    const range = max - min || 1;
    const points = values.map((value, index) => typeof value === "number" ? `${40 + index * (720 / Math.max(1, values.length - 1))},${210 - ((value - min) / range) * 170}` : null).filter(Boolean).join(" ");
    const dots = values.map((value, index) => typeof value === "number" ? `<circle cx="${40 + index * (720 / Math.max(1, values.length - 1))}" cy="${210 - ((value - min) / range) * 170}" r="4" fill="${color}"><title>${escapeHtml(periods[index])} : ${value}</title></circle>` : "").join("");
    return `<polyline points="${points}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${dots}`;
  }

  function renderCharts() {
    const data = historySeries();
    if (!data.series.length || data.series.every((series) => series.values.filter((value) => typeof value === "number").length < 2)) return `<div class="empty-state tool-empty">${icon("graphiques")}<strong>Aucune série historique exploitable</strong><span>Simulez au moins deux périodes pour suivre l’évolution de vos résultats.</span></div>`;
    if (!data.series.some((series) => series.key === chartSelection.first)) chartSelection.first = data.series[0].key;
    const first = data.series.find((series) => series.key === chartSelection.first);
    const second = data.series.find((series) => series.key === chartSelection.second);
    const options = data.series.map((series) => `<option value="${escapeHtml(series.key)}">${escapeHtml(series.label)}</option>`).join("");
    return `<div class="chart-controls"><label>Première série<select data-chart="first">${options}</select></label><label>Comparer avec<select data-chart="second"><option value="">Aucune</option>${options}</select></label><span>Évolution des résultats enregistrés</span></div><div class="chart-canvas"><svg viewBox="0 0 800 250" role="img" aria-label="Courbes des séries historiques"><path d="M40 40H770M40 210H770" stroke="#dedfd4" stroke-width="1"/>${chartPolyline(first.values, data.periods, "#d67b32")}${second ? chartPolyline(second.values, data.periods, "#28614f") : ""}</svg><div class="chart-periods">${data.periods.map((period) => `<span>${escapeHtml(period)}</span>`).join("")}</div></div><div class="chart-legend"><span><i class="legend-first"></i>${escapeHtml(first.label)}</span>${second ? `<span><i class="legend-second"></i>${escapeHtml(second.label)}</span>` : ""}</div><details class="chart-data"><summary>Afficher les valeurs sources</summary><div class="table-scroll"><table><thead><tr><th>Période</th>${(second ? [first, second] : [first]).map((series) => `<th>${escapeHtml(series.label)}</th>`).join("")}</tr></thead><tbody>${data.periods.map((period, index) => `<tr><td>${escapeHtml(period)}</td>${(second ? [first, second] : [first]).map((series) => `<td>${escapeHtml(display(series.values[index]))}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details><p class="tool-note">Chaque courbe utilise sa propre échelle. Consultez les valeurs ci-dessus pour comparer les niveaux.</p>`;
  }

  function currentSheetKey() {
    return `gmix.tableur.${encodeURIComponent(state.companyName)}.${encodeURIComponent(state.raw.scenario_id || "default")}.${encodeURIComponent(state.gameId ?? "legacy")}`;
  }

  function ensureSheet() {
    const key = currentSheetKey();
    if (key === sheetKey && sheetGrid.length) return;
    sheetKey = key;
    sheetGrid = spreadsheet.createGrid(12, 8);
    try {
      const saved = window.localStorage.getItem(key);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length && parsed.every(Array.isArray)) sheetGrid = parsed;
      }
    } catch (error) {
      announce("La sauvegarde locale du tableur est indisponible.");
    }
    if (pendingSheet) {
      sheetGrid = pendingSheet;
      pendingSheet = null;
      saveSheet();
    }
  }

  function saveSheet() {
    try { window.localStorage.setItem(sheetKey, JSON.stringify(sheetGrid)); }
    catch (error) { announce("Impossible de sauvegarder localement le tableur."); }
  }

  function renderSpreadsheet() {
    ensureSheet();
    return `<div class="sheet-toolbar"><span>${icon("check")} Sauvegarde locale pour ${escapeHtml(state.companyName)}</span><div><button type="button" class="secondary-button" data-action="add-row">${icon("plus")} Ligne</button><button type="button" class="secondary-button" data-action="add-column">${icon("plus")} Colonne</button><button type="button" class="secondary-button" data-action="export-sheet">${icon("download")} Exporter CSV</button><button type="button" class="text-button danger-text" data-action="clear-sheet">Effacer</button></div></div><p class="tool-note">Formules locales : <code>=A1+B2</code>, <code>=SOMME(A1:A5)</code>, <code>=MOYENNE(A1:A5)</code>, <code>MIN</code>, <code>MAX</code>, <code>=SI(A1&gt;0;"Oui";"Non")</code>. Séparez les arguments avec « ; ».</p><div class="sheet-scroll"><table class="spreadsheet"><thead><tr><th></th>${sheetGrid[0].map((unused, column) => `<th>${spreadsheet.columnName(column)}</th>`).join("")}</tr></thead><tbody>${sheetGrid.map((row, rowIndex) => `<tr><th>${rowIndex + 1}</th>${row.map((value, columnIndex) => `<td><input aria-label="Cellule ${spreadsheet.columnName(columnIndex)}${rowIndex + 1}" data-cell-row="${rowIndex}" data-cell-column="${columnIndex}" value="${escapeHtml(value)}"><output class="cell-result" data-result-row="${rowIndex}" data-result-column="${columnIndex}"></output></td>`).join("")}</tr>`).join("")}</tbody></table></div><p class="tool-note">Ce tableur est un carnet de calcul du joueur : il ne modifie jamais la partie.</p>`;
  }

  function renderMap() {
    const suppliers = state.raw.suppliers || [];
    const customers = state.raw.customers || state.raw.clients || [];
    const hasCoordinates = [...suppliers, ...customers].some((partner) => partner.gps || partner.coordinates || partner.latitude !== undefined);
    return `${hasCoordinates ? "" : `<div class="map-unavailable">${icon("carte")}<div><strong>Plan de votre usine</strong><p>Ouvrez un poste pour consulter sa situation et prendre vos décisions. Les itinéraires géographiques ne sont pas disponibles dans cette partie.</p></div></div>`}${renderFactoryPlan()}`;
  }

  function renderTool(tool, context) {
    const department = departmentById(context);
    let workspace;
    if (tool.id === "tableur") workspace = renderSpreadsheet();
    else if (tool.id === "planning") workspace = renderPlanning(context);
    else if (tool.id === "journal") workspace = renderJournal();
    else if (tool.id === "graphiques") workspace = renderCharts();
    else workspace = renderMap();
    return `${renderTopbar(tool.name)}<div class="page-heading"><div><p class="eyebrow">OUTIL DU JOUEUR · ${escapeHtml(department ? department.name : "USINE")}</p><h1>${escapeHtml(tool.name)}</h1><p>${escapeHtml(tool.description)}</p></div><a class="secondary-button" href="${department ? `#departement/${escapeHtml(department.id)}/outils` : "#accueil"}">Retour</a></div><section class="panel tool-workspace">${workspace}</section>`;
  }

  function render() {
    if (!state) return;
    const current = route();
    let content;
    if (current.view === "departement") {
      const department = departmentById(current.id);
      content = department ? renderDepartment(department, current.tab) : renderHome();
    } else if (current.view === "regles") content = renderRules();
    else if (current.view === "nouvelle-partie") content = renderNewGame();
    else if (current.view === "outil") {
      const tool = state.tools.find((item) => item.id === current.id && item.available);
      content = tool ? renderTool(tool, current.tab) : renderHome();
    } else content = renderHome();
    app.innerHTML = `${renderSidebar(current)}<main class="main-content" id="main-content">${content}</main>`;
    document.body.classList.remove("menu-open");
    if (current.view === "outil" && current.id === "tableur") refreshSheetResults();
    if (current.view === "outil" && current.id === "graphiques") {
      const first = document.querySelector('[data-chart="first"]');
      const second = document.querySelector('[data-chart="second"]');
      if (first) first.value = chartSelection.first;
      if (second) second.value = chartSelection.second;
    }
  }

  function renderLoadError(message) {
    app.innerHTML = `<main class="loading-screen error-screen" id="main-content"><span class="brand-mark">G</span>${icon("alert")}<h1>La tablette ne peut pas se connecter</h1><p>${escapeHtml(message)}</p><button type="button" class="primary-button" data-action="retry-load">${icon("refresh")} Réessayer</button><a href="/">Rejoindre le monde 3D</a></main>`;
  }

  async function loadState() {
    app.setAttribute("aria-busy", "true");
    announce("Chargement des données du moteur.");
    try {
      state = await api.getState();
      sheetKey = "";
      render();
      announce("Données de la tablette chargées.");
    } catch (error) {
      renderLoadError(error.message);
    } finally {
      app.removeAttribute("aria-busy");
    }
  }

  async function withBusy(trigger, work) {
    if (trigger) trigger.disabled = true;
    document.body.classList.add("is-busy");
    announce("Communication avec le moteur en cours.");
    try {
      return await work();
    } catch (error) {
      notify(error.message);
      return null;
    } finally {
      if (trigger) trigger.disabled = false;
      document.body.classList.remove("is-busy");
      announce("Communication terminée.");
    }
  }

  function rawStocks(categories) {
    return (state.raw.stocks || []).filter((item) => categories.includes(item.category));
  }

  function skuOptions(items) {
    return items.map((item) => `<option value="${escapeHtml(item.sku)}">${escapeHtml(item.sku)} · ${escapeHtml(item.name)}</option>`).join("");
  }

  function supplierOptions(sku) {
    return (state.raw.suppliers || []).filter((supplier) => supplier.active && supplier.prices && Object.prototype.hasOwnProperty.call(supplier.prices, sku));
  }

  function supplierOptionsHtml(sku) {
    const suppliers = supplierOptions(sku);
    return suppliers.length ? suppliers.map((supplier) => `<option value="${escapeHtml(supplier.id)}">${escapeHtml(supplier.name)}</option>`).join("") : '<option value="">Aucun fournisseur pour cet article</option>';
  }

  function openAction(actionId, label, trigger) {
    let form = "";
    if (actionId === "purchase" || actionId === "compare") {
      const stocks = rawStocks(["MP", "PDR"]);
      form = stocks.length ? `<form id="action-form" data-action-type="purchase"><label>Article MP ou PDR<select name="sku" data-purchase-sku required>${skuOptions(stocks)}</select></label><label>Fournisseur<select name="supplier_id" data-purchase-supplier required>${supplierOptionsHtml(stocks[0].sku)}</select></label><label>Quantité<input name="quantity" type="number" min="1" step="1" inputmode="numeric" required></label><div class="quote-actions"><button type="button" class="secondary-button" data-action="compare-quotes">${icon("graphiques")} Comparer les offres</button><span>Coûts et arrivées calculés par le moteur.</span></div><div id="quote-results" aria-live="polite"></div><button type="submit" class="primary-button">Passer la commande ${icon("arrow")}</button></form>` : `<div class="empty-state">${icon("stock")}<strong>Aucune matière ni pièce disponible</strong><span>Le scénario ne propose aucun article à commander.</span></div>`;
    } else if (actionId === "production") {
      const products = rawStocks(["PF"]);
      form = products.length ? `<form id="action-form" data-action-type="production"><label>Produit fini<select name="sku" required>${skuOptions(products)}</select></label><label>Quantité de l’OF<input name="quantity" type="number" min="1" step="1" inputmode="numeric" required></label><p class="form-note">Le lancement, le kit et les conséquences de l’OF sont gérés par le moteur.</p><button type="submit" class="primary-button">Lancer l’ordre de fabrication ${icon("arrow")}</button></form>` : `<div class="empty-state">${icon("production")}<strong>Aucun produit disponible</strong><span>Le scénario ne propose aucun produit à fabriquer.</span></div>`;
    } else if (actionId === "maintenance") {
      const lines = (state.raw.production_lines || []).filter((line) => (line.machines || []).some((machine) => machine.state === "panne"));
      form = lines.length ? `<form id="action-form" data-action-type="maintenance"><label>Ligne en panne<select name="line_id" required>${lines.map((line) => `<option value="${escapeHtml(line.id)}">${escapeHtml(line.name)} · ${escapeHtml(line.id)}</option>`).join("")}</select></label><p class="form-note">Seules les lignes dont une machine est en panne sont proposées.</p><button type="submit" class="primary-button">Envoyer le technicien ${icon("arrow")}</button></form>` : `<div class="empty-state">${icon("check")}<strong>Aucune ligne en panne</strong><span>Aucune intervention corrective ne peut être lancée depuis ce formulaire.</span></div>`;
    }
    openModal(`<p class="eyebrow">DÉCISION DU JOUEUR</p><h2 id="modal-title">${escapeHtml(label)}</h2><p class="modal-intro">Vérifiez votre choix, puis confirmez votre décision.</p>${form}`, trigger);
  }

  function openModal(content, trigger) {
    modalTrigger = trigger || document.activeElement;
    modalContent.innerHTML = content;
    modal.hidden = false;
    document.body.classList.add("modal-open");
    window.setTimeout(() => {
      const target = modalContent.querySelector("input, select, button") || modal.querySelector(".modal-close");
      target.focus();
    }, 0);
  }

  function closeModal() {
    modal.hidden = true;
    document.body.classList.remove("modal-open");
    modalContent.innerHTML = "";
    if (modalTrigger && document.contains(modalTrigger)) modalTrigger.focus();
  }

  async function compareQuotes(trigger) {
    const form = document.getElementById("action-form");
    const sku = form.elements.sku.value;
    const quantity = Number(form.elements.quantity.value);
    if (!form.elements.quantity.reportValidity()) return;
    const container = document.getElementById("quote-results");
    container.innerHTML = '<p class="inline-loading"><span class="loader"></span>Le moteur compare les offres…</p>';
    const quotes = await withBusy(trigger, () => api.compare(sku, quantity));
    if (!document.getElementById("quote-results")) return;
    if (!quotes) {
      container.innerHTML = '<div class="empty-state compact"><strong>Comparaison indisponible</strong><span>Vérifiez la connexion puis utilisez à nouveau « Comparer les offres ».</span></div>';
      return;
    }
    container.innerHTML = quotes.length ? `<div class="quote-grid">${quotes.map((quote) => `<article class="quote-card"><div><strong>${escapeHtml(quote.supplier_name)}</strong><small>${escapeHtml(quote.supplier_id)}</small></div><dl><div><dt>Prix unitaire</dt><dd>${escapeHtml(display(quote.unit_price))} €</dd></div><div><dt>Coût total moteur</dt><dd>${escapeHtml(display(quote.total_cost))} €</dd></div><div><dt>Délai moteur</dt><dd>${escapeHtml(display(quote.lead_time_weeks))} sem.</dd></div><div><dt>Arrivée prévue</dt><dd>Semaine ${escapeHtml(display(quote.expected_arrival_week))}</dd></div><div><dt>Fiabilité</dt><dd>${escapeHtml(display(quote.reliability))} %</dd></div><div><dt>Non-conformité</dt><dd>${escapeHtml(display(quote.nonconformity_rate))} %</dd></div><div><dt>Quantité conforme attendue</dt><dd>${escapeHtml(display(quote.expected_good_quantity))}</dd></div></dl><button type="button" class="secondary-button" data-action="use-quote" data-supplier="${escapeHtml(quote.supplier_id)}">Choisir cette offre</button></article>`).join("")}</div>` : '<div class="empty-state compact"><strong>Aucune offre disponible</strong><span>Le moteur ne propose aucun fournisseur pour cet article.</span></div>';
  }

  function findTable(context, tableId) {
    return tableData(context).find((entry) => entry.table.id === tableId);
  }

  function sendTableToSheet(context, tableId) {
    const entry = findTable(context, tableId);
    if (!entry) return;
    const values = [entry.table.columns.map((column) => column.label), ...entry.table.rows.map((row) => entry.table.columns.map((column) => display(row[column.key])))];
    pendingSheet = spreadsheet.createGrid(Math.max(12, values.length + 2), Math.max(8, entry.table.columns.length), values);
    sheetKey = "";
    window.location.hash = `#outil/tableur/${context}`;
    notify("Tableau copié dans le tableur local.", "success");
  }

  function refreshSheetResults() {
    document.querySelectorAll("[data-result-row]").forEach((output) => {
      const row = Number(output.dataset.resultRow);
      const column = Number(output.dataset.resultColumn);
      const raw = sheetGrid[row] && sheetGrid[row][column];
      if (typeof raw === "string" && raw.trim().startsWith("=")) {
        const result = spreadsheet.evaluate(raw, sheetGrid);
        output.value = display(result);
        output.classList.toggle("formula-error", typeof result === "string" && result.startsWith("#"));
      } else {
        output.value = "";
        output.classList.remove("formula-error");
      }
    });
  }

  function exportSheet() {
    const blob = new Blob(["\ufeff", spreadsheet.toCsv(sheetGrid)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `gmix-${state.raw.scenario_id || "default"}-tableur.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function applyTableFilter(key) {
    const table = document.querySelector(`[data-table="${CSS.escape(key)}"]`);
    const search = document.querySelector(`[data-table-search="${CSS.escape(key)}"]`);
    const column = document.querySelector(`[data-table-column="${CSS.escape(key)}"]`);
    if (!table || !search || !column) return;
    const query = search.value.trim().toLocaleLowerCase("fr");
    let visible = 0;
    table.querySelectorAll("tbody tr").forEach((row) => {
      let haystack = row.dataset.search;
      if (column.value) {
        const cell = [...row.children].find((item) => item.dataset.column === column.value);
        haystack = cell ? cell.dataset.value : "";
      }
      const show = !query || haystack.includes(query);
      row.hidden = !show;
      if (show) visible += 1;
    });
    const empty = document.querySelector(`[data-filter-empty="${CSS.escape(key)}"]`);
    if (empty) empty.hidden = visible !== 0;
  }

  document.addEventListener("click", async (event) => {
    if (event.target.closest("[data-dismiss-toast]")) {
      window.clearTimeout(toastTimer);
      toast.hidden = true;
      return;
    }
    if (event.target === modal) { closeModal(); return; }
    const trigger = event.target.closest("[data-action]");
    if (!trigger) {
      if (event.target.closest(".sidebar a")) document.body.classList.remove("menu-open");
      return;
    }
    const action = trigger.dataset.action;
    if (action === "toggle-menu") document.body.classList.toggle("menu-open");
    else if (action === "close-menu") document.body.classList.remove("menu-open");
    else if (action === "retry-load") await loadState();
    else if (action === "refresh") {
      const snapshot = await withBusy(trigger, () => api.getState());
      if (snapshot) { state = snapshot; sheetKey = ""; render(); notify("Situation de l’usine actualisée.", "success"); }
    } else if (action === "next-turn") {
      const snapshot = await withBusy(trigger, () => api.nextTurn());
      if (snapshot) { state = snapshot; sheetKey = ""; render(); notify(`${state.clock.label} : simulation terminée.`, "success"); }
    } else if (action === "open-action") openAction(trigger.dataset.actionId, trigger.dataset.actionLabel, trigger);
    else if (action === "close-modal") closeModal();
    else if (action === "compare-quotes") await compareQuotes(trigger);
    else if (action === "use-quote") {
      const supplier = document.querySelector("[data-purchase-supplier]");
      if (supplier) { supplier.value = trigger.dataset.supplier; supplier.focus(); }
    } else if (action === "attempt-config") {
      const department = departmentById(trigger.dataset.department);
      const configuration = department && department.configurations.find((item) => item.id === trigger.dataset.configuration);
      if (configuration) await withBusy(trigger, () => api.updateConfiguration(department.id, configuration.id, configuration.value));
    } else if (action === "send-table") sendTableToSheet(trigger.dataset.context, trigger.dataset.tableId);
    else if (action === "add-row") {
      sheetGrid.push(Array(sheetGrid[0].length).fill(""));
      saveSheet(); render();
    } else if (action === "add-column") {
      sheetGrid.forEach((row) => row.push(""));
      saveSheet(); render();
    } else if (action === "export-sheet") exportSheet();
    else if (action === "clear-sheet") {
      if (window.confirm("Effacer uniquement ce tableur local ? La partie ne sera pas modifiée.")) {
        sheetGrid = spreadsheet.createGrid(12, 8); saveSheet(); render();
      }
    }
  });

  document.addEventListener("input", (event) => {
    const target = event.target;
    if (target.matches("[data-table-search]")) applyTableFilter(target.dataset.tableSearch);
    if (target.matches("[data-cell-row]")) {
      const row = Number(target.dataset.cellRow);
      const column = Number(target.dataset.cellColumn);
      sheetGrid[row][column] = target.value;
      refreshSheetResults();
      window.clearTimeout(saveTimer);
      saveTimer = window.setTimeout(saveSheet, 250);
    }
  });

  document.addEventListener("change", (event) => {
    const target = event.target;
    if (target.matches("[data-table-column]")) applyTableFilter(target.dataset.tableColumn);
    if (target.matches("[data-purchase-sku]")) {
      const supplier = document.querySelector("[data-purchase-supplier]");
      supplier.innerHTML = supplierOptionsHtml(target.value);
      document.getElementById("quote-results").innerHTML = "";
    }
    if (target.matches("[data-journal]")) {
      journalFilters[target.dataset.journal] = target.value;
      render();
    }
    if (target.matches("[data-chart]")) {
      chartSelection[target.dataset.chart] = target.value;
      render();
    }
  });

  document.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    if (form.id === "new-game-form") {
      const data = new FormData(form);
      const setup = { company_name: String(data.get("company_name")).trim(), difficulty: data.get("difficulty"), rules_confirmed: data.get("rules_confirmed") === "on" };
      if (!form.reportValidity()) return;
      const snapshot = await withBusy(form.querySelector('[type="submit"]'), () => api.newGame(setup));
      if (snapshot) { state = snapshot; sheetKey = ""; window.location.hash = "#accueil"; render(); notify("Votre nouvelle partie est prête.", "success"); }
      return;
    }
    if (form.id === "action-form") {
      if (!form.reportValidity()) return;
      const data = new FormData(form);
      const type = form.dataset.actionType;
      let payload;
      if (type === "purchase") payload = { action: "purchase", supplier_id: data.get("supplier_id"), sku: data.get("sku"), quantity: Number(data.get("quantity")) };
      else if (type === "production") payload = { action: "production", sku: data.get("sku"), quantity: Number(data.get("quantity")) };
      else payload = { action: "maintenance", line_id: data.get("line_id") };
      const snapshot = await withBusy(form.querySelector('[type="submit"]'), () => api.performAction(payload));
      if (snapshot) { closeModal(); state = snapshot; sheetKey = ""; render(); notify("Décision enregistrée dans votre partie.", "success"); }
      return;
    }
    if (form.classList.contains("config-form")) {
      if (!form.reportValidity()) return;
      const value = new FormData(form).get("value");
      const snapshot = await withBusy(form.querySelector('[type="submit"]'), () => api.updateConfiguration(form.dataset.department, form.dataset.configuration, value));
      if (snapshot) { state = snapshot; render(); notify("Configuration enregistrée par le moteur.", "success"); }
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (!modal.hidden) closeModal();
      document.body.classList.remove("menu-open");
    }
    if (event.key === "Tab" && !modal.hidden) {
      const focusable = [...modal.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), a[href], [tabindex="0"]')];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });

  window.addEventListener("hashchange", render);
  loadState();
}());
