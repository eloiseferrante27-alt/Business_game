(function () {
  "use strict";

  const api = window.GMixTabletAPI;
  const app = document.getElementById("app");
  const toast = document.getElementById("toast");
  const rightLabels = { verrouille: "Verrouillé", initial: "Initial seulement", libre: "Libre" };
  const statusLabels = { vert: "Aucune alerte", orange: "Alerte mineure", rouge: "Alerte grave" };
  let state;
  let toastTimer;

  const iconPaths = {
    home: '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5M9 20v-6h6v6"/>',
    rules: '<path d="M6 3h12v18H6zM9 7h6M9 11h6M9 15h4"/>',
    tools: '<path d="m14 6 4-4 4 4-4 4M4 20l9-9M3 3l7 7M3 3v4h4"/>',
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
    pause: '<path d="M8 5v14M16 5v14"/>',
    play: '<path d="m8 5 11 7-11 7z"/>',
    next: '<path d="m5 5 10 7L5 19zM19 5v14"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    alert: '<path d="M12 3 2 21h20zM12 9v5M12 18v.01"/>',
    arrow: '<path d="M5 12h14M14 7l5 5-5 5"/>',
    trendUp: '<path d="m4 16 6-6 4 4 6-8M15 6h5v5"/>',
    trendDown: '<path d="m4 8 6 6 4-4 6 8M15 18h5v-5"/>',
    flat: '<path d="M4 12h16"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    tableur: '<rect x="3" y="3" width="18" height="18" rx="1"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
    carte: '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15M15 6v15"/>',
    graphiques: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    planning: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M8 14h2M14 14h2M8 17h2"/>',
    journal: '<path d="M5 3h14v18H5zM9 7h6M9 11h6M9 15h6"/>'
  };

  function icon(name, className = "") {
    return `<svg class="icon ${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.production}</svg>`;
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
    })[character]);
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

  function notify(message, type = "error") {
    window.clearTimeout(toastTimer);
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `${icon(type === "error" ? "alert" : "check")}<span>${escapeHtml(message)}</span><button type="button" data-dismiss-toast aria-label="Fermer">×</button>`;
    toast.hidden = false;
    toastTimer = window.setTimeout(() => { toast.hidden = true; }, 4000);
  }

  function renderSidebar(current) {
    return `<aside class="sidebar" aria-label="Navigation principale">
      <a class="brand" href="#accueil" aria-label="G-MIX, accueil"><span class="brand-mark">G</span><span>G-MIX<small>TABLETTE DE PILOTAGE</small></span></a>
      <nav class="primary-nav">
        <a href="#accueil" ${current.view === "accueil" ? 'class="active" aria-current="page"' : ""}>${icon("home")}<span>Vue d’ensemble</span></a>
        <a href="#regles" ${current.view === "regles" ? 'class="active" aria-current="page"' : ""}>${icon("rules")}<span>Règles de la partie</span></a>
      </nav>
      <p class="nav-caption">DÉPARTEMENTS</p>
      <nav class="department-nav">${state.departments.map((department) => `<a href="#departement/${department.id}" ${current.id === department.id ? 'class="active" aria-current="page"' : ""}>${icon(departmentIcon(department.id))}<span>${escapeHtml(department.shortName)}</span><i class="status-dot status-${department.status}" aria-label="${statusLabels[department.status]}"></i></a>`).join("")}</nav>
      <div class="sidebar-foot"><span class="live-dot"></span><span>${state.started ? "Partie en cours" : "Configuration initiale"}</span></div>
    </aside>`;
  }

  function renderTopbar(title) {
    return `<header class="topbar"><div><span class="mobile-brand">G-MIX</span><span class="breadcrumb">Tablette <b>/</b> ${escapeHtml(title)}</span></div><span class="demo-badge">DONNÉES DE DÉMONSTRATION</span></header>`;
  }

  function renderClock() {
    const clock = state.clock;
    return `<section class="clock-card" aria-label="Horloge simulée">
      <div class="clock-time">${icon("clock")}<div><small>JOUR SIMULÉ</small><strong>Jour ${clock.day} <span>·</span> ${escapeHtml(clock.time)}</strong></div></div>
      <label class="speed-control">Vitesse<select data-speed aria-label="Vitesse de simulation">${Array.from({ length: 60 }, (_, index) => index + 1).map((speed) => `<option value="${speed}" ${speed === clock.speed ? "selected" : ""}>×${speed}</option>`).join("")}</select></label>
      <button class="icon-button" type="button" data-action="pause" aria-label="${clock.paused ? "Reprendre" : "Mettre en pause"}">${icon(clock.paused ? "play" : "pause")}<span>${clock.paused ? "Reprendre" : "Pause"}</span></button>
      <button class="next-decision" type="button" data-action="next-decision">${icon("next")}<span>Prochaine décision</span></button>
    </section>`;
  }

  function renderHome() {
    return `${renderTopbar("Vue d’ensemble")}
      <div class="page-heading home-heading"><div><p class="eyebrow">VUE D’ENSEMBLE</p><h1>Votre usine, en un regard.</h1><p>Suivez l’activité, repérez les alertes et passez à l’action.</p></div><a class="secondary-button" href="#regles">${icon("rules")} Règles de la partie</a></div>
      ${renderClock()}
      <section class="home-section"><div class="section-heading"><h2>Indicateurs globaux</h2><span>Données fournies par le moteur</span></div>
        <div class="global-kpis">${state.globalKpis.map((kpi) => `<a class="global-kpi" href="#departement/${kpi.departmentId}"><span>${escapeHtml(kpi.label)}</span><strong>${escapeHtml(kpi.value)} <small>${escapeHtml(kpi.unit)}</small></strong><span class="kpi-link">Voir le détail ${icon("arrow")}</span></a>`).join("")}</div>
      </section>
      <div class="home-grid">
        <section class="panel factory-panel"><div class="section-heading"><div><p class="eyebrow">PLAN DE L’USINE</p><h2>Les départements</h2></div><div class="status-legend"><span><i class="status-dot status-vert"></i>Vert</span><span><i class="status-dot status-orange"></i>Orange</span><span><i class="status-dot status-rouge"></i>Rouge</span></div></div>
          <div class="factory-map">${state.departments.map((department, index) => `<a class="factory-block block-${index + 1}" href="#departement/${department.id}"><span class="block-icon">${icon(departmentIcon(department.id))}</span><strong>${escapeHtml(department.shortName)}</strong><span class="block-state"><i class="status-dot status-${department.status}"></i>${statusLabels[department.status]}</span></a>`).join("")}</div>
        </section>
        <section class="panel alerts-panel"><div class="section-heading"><div><p class="eyebrow">À TRAITER</p><h2>Alertes en cours</h2></div><span class="count-badge">${state.alerts.length}</span></div>
          <div class="alert-list">${state.alerts.map((alert) => `<a class="alert-item severity-${alert.severity}" href="#departement/${alert.departmentId}"><span class="alert-symbol">${icon("alert")}</span><span><small>${escapeHtml(state.departments.find((department) => department.id === alert.departmentId).shortName)} · ${alert.severity === "grave" ? "GRAVE" : "MINEURE"}</small><strong>${escapeHtml(alert.title)}</strong><span>${escapeHtml(alert.detail)}</span></span>${icon("arrow")}</a>`).join("")}</div>
        </section>
      </div>
      <div class="home-grid lower-grid">
        <section class="panel objectives-panel"><div class="section-heading"><div><p class="eyebrow">CRITÈRES DE RÉUSSITE</p><h2>Progression des objectifs</h2></div></div>
          <div class="objective-list">${state.objectives.map((objective) => `<div class="objective"><div><strong>${escapeHtml(objective.label)}</strong><span>${escapeHtml(objective.current)}</span></div><div class="progress-track" role="progressbar" aria-label="${escapeHtml(objective.label)}" aria-valuenow="${objective.progress}" aria-valuemin="0" aria-valuemax="100"><i style="width:${objective.progress}%"></i></div><small>Progression vers l’objectif, sans verdict</small></div>`).join("")}</div>
        </section>
        <section class="panel tools-panel"><div class="section-heading"><div><p class="eyebrow">ESPACE DE TRAVAIL</p><h2>Outils du joueur</h2></div></div>${renderTools("accueil")}</section>
      </div>`;
  }

  function renderTools(context) {
    return `<div class="tool-list">${state.tools.map((tool) => tool.available ? `<a href="#outil/${tool.id}/${context}">${icon(tool.id)}<span><strong>${escapeHtml(tool.name)}</strong><small>${escapeHtml(tool.description)}</small></span>${icon("arrow")}</a>` : `<div class="disabled-tool">${icon(tool.id)}<span><strong>${escapeHtml(tool.name)}</strong><small>Outil désactivé par le formateur</small></span></div>`).join("")}</div>`;
  }

  function renderDepartment(department, tab) {
    const alerts = state.alerts.filter((alert) => alert.departmentId === department.id);
    let content;
    if (tab === "outils") {
      content = `<section class="panel tab-panel"><div class="section-heading"><div><p class="eyebrow">DONNÉES PRÉ-REMPLIES</p><h2>Outils · ${escapeHtml(department.name)}</h2></div></div>${renderTools(department.id)}</section>`;
    } else if (tab === "configurations") {
      content = `<section class="config-layout"><div class="panel config-panel"><div class="section-heading"><div><p class="eyebrow">MÉTHODES DE TRAVAIL</p><h2>Configurations du joueur</h2></div></div><div class="config-list">${department.configurations.map((configuration) => renderConfiguration(department, configuration, false)).join("")}</div></div><aside class="panel world-panel"><p class="eyebrow">LECTURE SEULE</p><h2>Paramètres du monde</h2><p>Fixés par le formateur pour ce scénario.</p>${department.worldParameters.map((parameter) => `<div class="world-parameter"><span>${escapeHtml(parameter.label)}</span><strong>${escapeHtml(parameter.value)}</strong></div>`).join("")}</aside></section>`;
    } else {
      tab = "kpis";
      content = `<section class="department-kpis">${department.kpis.map((kpi) => `<article class="department-kpi"><span>${escapeHtml(kpi.label)}</span><strong>${escapeHtml(kpi.value)} <small>${escapeHtml(kpi.unit)}</small></strong><p class="trend-${kpi.direction}">${icon(kpi.direction === "up" ? "trendUp" : kpi.direction === "down" ? "trendDown" : "flat")}${escapeHtml(kpi.trend)}</p></article>`).join("")}</section>
        <div class="department-grid"><section class="panel"><div class="section-heading"><div><p class="eyebrow">ÉTAT EN DIRECT</p><h2>Actions disponibles</h2></div><span class="state-pill state-${department.status}"><i class="status-dot status-${department.status}"></i>${statusLabels[department.status]}</span></div><div class="action-list">${department.actions.map((action) => `<button type="button" data-action="department-action" data-name="${escapeHtml(action)}">${escapeHtml(action)}${icon("arrow")}</button>`).join("")}</div></section>
        <section class="panel"><div class="section-heading"><div><p class="eyebrow">SURVEILLANCE</p><h2>Alertes du département</h2></div></div>${alerts.length ? `<div class="alert-list">${alerts.map((alert) => `<article class="alert-item severity-${alert.severity}"><span class="alert-symbol">${icon("alert")}</span><span><small>${alert.severity === "grave" ? "GRAVE" : "MINEURE"}</small><strong>${escapeHtml(alert.title)}</strong><span>${escapeHtml(alert.detail)}</span></span></article>`).join("")}</div>` : `<div class="empty-state">${icon("check")}<strong>Aucune alerte ouverte</strong><span>Le département fonctionne sans alerte.</span></div>`}</section></div>`;
    }
    return `${renderTopbar(department.name)}<div class="page-heading department-heading"><div class="department-title"><span class="department-hero-icon">${icon(departmentIcon(department.id))}</span><div><p class="eyebrow">DÉPARTEMENT</p><h1>${escapeHtml(department.name)}</h1><p>${escapeHtml(department.description)}</p></div></div><span class="state-pill state-${department.status}"><i class="status-dot status-${department.status}"></i>${statusLabels[department.status]}</span></div>
      ${renderClock()}<nav class="tabs" aria-label="Sections du département">${[["kpis", "KPIs"], ["outils", "Outils"], ["configurations", "Configurations"]].map(([id, label]) => `<a href="#departement/${department.id}/${id}" ${tab === id ? 'class="active" aria-current="page"' : ""}>${label}</a>`).join("")}</nav>${content}`;
  }

  function renderConfiguration(department, configuration, rulesMode) {
    const editable = rulesMode ? !state.started && configuration.right !== "verrouille" : configuration.right === "libre";
    const locked = configuration.right === "verrouille" || (configuration.right === "initial" && (state.started || !rulesMode));
    const canAttempt = locked && !(rulesMode && state.started);
    const attributes = editable ? `data-rule-config="${rulesMode}"` : canAttempt ? 'readonly data-action="attempt-config"' : "readonly";
    return `<div class="configuration"><div class="configuration-label"><label for="config-${rulesMode ? "rule-" : ""}${department.id}-${configuration.id}">${escapeHtml(configuration.label)}</label><span class="right-badge right-${configuration.right}">${configuration.right === "libre" ? "" : icon("lock")}${rightLabels[configuration.right]}</span></div><div class="configuration-input ${locked ? "is-locked" : ""}"><input id="config-${rulesMode ? "rule-" : ""}${department.id}-${configuration.id}" name="${department.id}.${configuration.id}" value="${escapeHtml(configuration.value)}" ${attributes} data-department="${department.id}" data-configuration="${configuration.id}" aria-readonly="${!editable}">${locked ? icon("lock") : ""}</div></div>`;
  }

  function renderRules() {
    const toolsAvailable = state.tools.filter((tool) => tool.available);
    return `${renderTopbar("Règles de la partie")}<div class="page-heading"><div><p class="eyebrow">AVANT DE JOUER</p><h1>Règles de la partie</h1><p>${state.started ? "Consultez les droits et les outils définis par le formateur." : "Réglez vos valeurs de départ, puis confirmez pour démarrer la partie."}</p></div>${state.started ? `<a class="secondary-button" href="#accueil">${icon("home")} Retour à l’accueil</a>` : ""}</div>
      <div class="rights-summary"><article><span class="right-badge right-verrouille">${icon("lock")}Verrouillé</span><p>Valeur fixée par le formateur pour toute la partie.</p></article><article><span class="right-badge right-initial">${icon("rules")}Initial seulement</span><p>À choisir maintenant, puis non modifiable pendant la partie.</p></article><article><span class="right-badge right-libre">Libre</span><p>Modifiable dans les limites définies par le formateur.</p></article></div>
      <form id="rules-form"><div class="rules-layout"><div class="rules-departments">${state.departments.map((department) => `<details class="panel rules-department" ${department.id === "stock" || state.departments.some((item) => item.configurations.some((configuration) => configuration.right === "initial")) ? "open" : ""}><summary><span>${icon(departmentIcon(department.id))}<strong>${escapeHtml(department.name)}</strong></span><span>${department.configurations.length} réglages</span></summary><div class="config-list">${department.configurations.map((configuration) => renderConfiguration(department, configuration, true)).join("")}</div></details>`).join("")}</div>
      <aside class="panel rules-tools"><p class="eyebrow">OUTILS DISPONIBLES</p><h2>Votre espace de travail</h2>${toolsAvailable.map((tool) => `<div class="rules-tool">${icon(tool.id)}<span><strong>${escapeHtml(tool.name)}</strong><small>Disponible</small></span>${icon("check")}</div>`).join("")}${state.tools.length !== toolsAvailable.length ? `<p class="muted">Certains outils ont été désactivés par le formateur.</p>` : ""}</aside></div>
      ${state.started ? "" : `<div class="rules-confirm"><p>${icon("alert")} La partie ne démarrera qu’après votre confirmation.</p><button class="primary-button" type="submit">Confirmer et démarrer ${icon("arrow")}</button></div>`}</form>`;
  }

  function renderTool(tool, context) {
    const department = state.departments.find((item) => item.id === context);
    return `${renderTopbar(tool.name)}<div class="page-heading"><div><p class="eyebrow">OUTIL DU JOUEUR</p><h1>${escapeHtml(tool.name)}</h1><p>${escapeHtml(tool.description)}</p></div><a class="secondary-button" href="${department ? `#departement/${department.id}/outils` : "#accueil"}">Retour</a></div><section class="panel tool-workspace">${icon(tool.id)}<p class="eyebrow">CONTEXTE · ${escapeHtml(department ? department.name : "USINE")}</p><h2>Espace ${escapeHtml(tool.name.toLowerCase())}</h2><p>La coque est prête à recevoir le module de l’outil et ses données pré-remplies.</p><span class="demo-badge">MODULE À CONNECTER</span></section>`;
  }

  function render() {
    if (!state) return;
    const current = route();
    let content;
    if (!state.started && current.view !== "regles") {
      window.location.hash = "#regles";
      return;
    }
    if (current.view === "departement") {
      const department = state.departments.find((item) => item.id === current.id);
      content = department ? renderDepartment(department, current.tab) : renderHome();
    } else if (current.view === "regles") {
      content = renderRules();
    } else if (current.view === "outil") {
      const tool = state.tools.find((item) => item.id === current.id && item.available);
      content = tool ? renderTool(tool, current.tab) : renderHome();
    } else {
      content = renderHome();
    }
    app.innerHTML = `${renderSidebar(current)}<main class="main-content" id="main-content">${content}</main>`;
  }

  async function updateState(request) {
    state = await request;
    render();
  }

  app.addEventListener("click", async (event) => {
    const trigger = event.target.closest("[data-action]");
    if (!trigger) return;
    const action = trigger.dataset.action;
    if (action === "pause") await updateState(api.togglePause());
    if (action === "next-decision") await updateState(api.advanceToDecision());
    if (action === "department-action") {
      const result = await api.performAction(trigger.dataset.name);
      notify(result.message, "success");
    }
    if (action === "attempt-config") {
      const result = await api.updateConfiguration(trigger.dataset.department, trigger.dataset.configuration, trigger.value);
      if (!result.ok) notify(result.message);
    }
  });

  app.addEventListener("change", async (event) => {
    if (event.target.matches("[data-speed]")) {
      await updateState(api.setSpeed(event.target.value));
      return;
    }
    const input = event.target.closest('input[data-rule-config="false"]');
    if (!input) return;
    const result = await api.updateConfiguration(input.dataset.department, input.dataset.configuration, input.value);
    if (!result.ok) {
      render();
      notify(result.message);
      return;
    }
    state = result.state;
    render();
    notify("Configuration enregistrée. Son effet est géré par le moteur.", "success");
  });

  app.addEventListener("submit", async (event) => {
    if (event.target.id !== "rules-form") return;
    event.preventDefault();
    const values = {};
    event.target.querySelectorAll('input[data-rule-config="true"]:not([readonly])').forEach((input) => { values[input.name] = input.value; });
    await updateState(api.startGame(values));
    window.location.hash = "#accueil";
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-dismiss-toast]")) {
      window.clearTimeout(toastTimer);
      toast.hidden = true;
    }
  });

  window.addEventListener("hashchange", render);
  api.getState().then((initialState) => {
    state = initialState;
    if (!state.started && route().view !== "regles") window.location.hash = "#regles";
    render();
  }).catch(() => {
    app.innerHTML = '<main class="loading" id="main-content"><p>Impossible de charger les données de la tablette.</p></main>';
  });
}());
